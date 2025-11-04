import os
import asyncio
from telethon import TelegramClient, events
import re

# === VARIABLES D'ENVIRONNEMENT (pour Railway) ===
API_ID = int(os.getenv('API_ID') or 0)
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')

# S'assure que les variables essentielles sont chargées
if not all([API_ID, API_HASH, BOT_TOKEN]):
    print("ERREUR : API_ID, API_HASH, ou BOT_TOKEN est manquant.")
    print("Assurez-vous qu'ils sont définis dans les variables d'environnement de Railway.")
    exit()

matches = []

# === TRANSLITTÉRATION ===
TRANSLIT = {
    'Арсенал': 'Arsenal', 'Эвертон': 'Everton', 'ВестХэмЮнайтед': 'West Ham United',
    'НьюкаслЮнайтед': 'Newcastle United', 'Ливерпуль': 'Liverpool', 'МанчестерСити': 'Manchester City',
    'Челси': 'Chelsea', 'Тоттенхэм': 'Tottenham', 'МанчестерЮнайтед': 'Manchester United',
}

# Initialiser le client en mode bot
# 'bot_session_name' peut être n'importe quelle chaîne, 
# elle sera utilisée pour nommer le fichier .session du bot
client = TelegramClient('bot_session_name', API_ID, API_HASH)

# === GESTIONNAIRE DE MESSAGES ===
# On écoute TOUS les messages entrants
@client.on(events.NewMessage(incoming=True))
async def message_handler(event):
    
    # === LA CORRECTION EST ICI ===
    # On vérifie si le message est privé (conversation 1-à-1 avec le bot)
    # Si ce n'est pas privé (ex: un groupe), on l'ignore.
    if not event.is_private:
        return
    # ============================

    msg = event.message.message
    print("\n" + "="*60)
    print("MESSAGE REÇU (privé) :")
    print(msg)
    print("="*60)

    # On ignore les commandes pour ne pas les parser comme des matchs
    if msg.startswith('/'):
        return

    # On utilise la même logique de parsing que vous aviez
    parsed = parse_final_match(msg)
    
    if parsed:
        matches.append(parsed)
        match_str = f"✅ MATCH AJOUTÉ ! → {parsed['home']} {parsed['home_goals']}-{parsed['away_goals']} {parsed['away']}"
        print(match_str)
        # Répondre à l'utilisateur pour confirmer
        await event.reply(match_str)
    else:
        print("MATCH NON AJOUTÉ (format non reconnu ou match non final)")
        await event.reply("❌ Format non reconnu ou match non terminé (⏰ 2-й тайм 6:00 manquant).")


def parse_final_match(text):
    # (Votre fonction parse_final_match reste exactement la même)
    team_match = re.search(r'#([А-Яа-яA-Za-z0-9_]{3,50})_([А-Яа-яA-Za-z0-9_]{3,50})', text)
    if not team_match: 
        print("Debug Parse: Échec (Pas de teams)")
        return None
    home_raw, away_raw = team_match.group(1), team_match.group(2)
    home = TRANSLIT.get(home_raw, home_raw.replace('_', ' '))
    away = TRANSLIT.get(away_raw, away_raw.replace('_', ' '))

    score_match = re.search(r'(\d+)\s*[:\-]\s*(\d+)', text)
    if not score_match: 
        print("Debug Parse: Échec (Pas de score)")
        return None
    home_goals, away_goals = int(score_match.group(1)), int(score_match.group(2))

    if not re.search(r'⏰\s*2-й\s+тайм\s+6:00', text, re.IGNORECASE):
        print("Debug Parse: Échec (Pas de marqueur de fin)")
        return None

    # Vérification anti-doublon (optionnelle mais utile)
    if any(m['home'] == home and m['away'] == away for m in matches[-10:]):
        print("Debug Parse: Échec (Doublon détecté)")
        return None

    return {'home': home, 'away': away, 'home_goals': home_goals, 'away_goals': away_goals, 'total': home_goals + away_goals}

# === COMMANDES ===
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply(f"Bot de stats (mode manuel) ON\n\nEnvoyez-moi les résultats pour les enregistrer.\nMatchs en mémoire : {len(matches)}")

@client.on(events.NewMessage(pattern='/stats'))
async def stats(event):
    if not matches:
        await event.reply("Aucun match en mémoire depuis le démarrage.")
        return

    # Formatte la liste pour l'affichage
    reply_msg = f"Matchs détectés depuis le démarrage : {len(matches)}\n\n"
    # Affiche les 10 derniers matchs
    for match in matches[-10:]:
        reply_msg += f"- {match['home']} {match['home_goals']} - {match['away_goals']} {match['away']}\n"
    
    await event.reply(reply_msg)

# === LANCEMENT ===
async def main():
    # Se connecte en utilisant le BOT_TOKEN
    await client.start(bot_token=BOT_TOKEN)
    print("BOT EN MODE MANUEL - PRÊT À RECEVOIR DES RÉSULTATS")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
