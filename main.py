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
    exit()

matches = []

# === TRANSLITTÉRATION ===
TRANSLIT = {
    'Арсенал': 'Arsenal', 'Эвертон': 'Everton', 'ВестХэмЮнайтед': 'West Ham United',
    'НьюкаслЮнайтед': 'Newcastle United', 'Ливерпуль': 'Liverpool', 'МанчестерСити': 'Manchester City',
    'Челси': 'Chelsea', 'Тоттенхэм': 'Tottenham', 'МанчестерЮнайтед': 'Manchester United',
    # Ajout des équipes de votre exemple
    'ШеффилдЮнайтед': 'Sheffield United', 'Бернли': 'Burnley',
    'НоттингемФорест': 'Nottingham Forest', 'Вулверхэмптон': 'Wolverhampton',
    'АстонВилла': 'Aston Villa', 'КристалПэлэс': 'Crystal Palace',
    'Борнмут': 'Bournemouth', 'БрайтонэндХавАльбион': 'Brighton & Hove Albion',
    'Брентфорд': 'Brentford', 'Фулхэм': 'Fulham', 'ЛутонТаун': 'Luton Town',
    'ТоттенхэмХотспур': 'Tottenham Hotspur', # Au cas où
}

# Initialiser le client en mode bot
client = TelegramClient('bot_session_name', API_ID, API_HASH)

# === NOUVEAU GESTIONNAIRE DE MESSAGES (POUR LES LOTS) ===
@client.on(events.NewMessage(incoming=True))
async def message_handler(event):
    
    if not event.is_private:
        return

    msg = event.message.message
    print("\n" + "="*60 + f"\nMESSAGE BLOC REÇU (privé) :\n{msg}\n" + "="*60)

    if msg.startswith('/'):
        return

    # 1. On divise le message en blocs, en utilisant votre séparateur
    # Le premier élément est souvent vide, donc on le saute avec [1:]
    match_snippets = msg.split("> 🔰 FC24 4X4:")
    
    if len(match_snippets) < 2:
        print("Format de lot non reconnu. Traitement comme message simple.")
        # On garde l'ancienne logique pour un seul match
        parsed = parse_final_match(msg)
        if parsed and not is_duplicate(parsed):
            matches.append(parsed)
            await event.reply(f"✅ MATCH AJOUTÉ (simple) ! → {parsed['home']} {parsed['home_goals']}-{parsed['away_goals']} {parsed['away']}")
        else:
            await event.reply("❌ Format non reconnu ou match non terminé.")
        return

    added_matches_info = [] # Pour la réponse finale
    total_added = 0
    total_skipped = 0

    # 2. On boucle sur chaque bloc trouvé
    for snippet in match_snippets[1:]:
        print(f"--- Analyse du snippet ---\n{snippet.strip()}\n-------------------------")
        parsed = parse_final_match(snippet)
        
        if parsed:
            # 3. On vérifie les doublons avant d'ajouter
            if not is_duplicate(parsed):
                matches.append(parsed)
                added_matches_info.append(f"✅ {parsed['home']} {parsed['home_goals']}-{parsed['away_goals']} {parsed['away']}")
                total_added += 1
                print(f"MATCH AJOUTÉ ! → {parsed['home']} {parsed['home_goals']}-{parsed['away_goals']} {parsed['away']}")
            else:
                total_skipped += 1
                print(f"DOUBLON IGNORÉ → {parsed['home']} vs {parsed['away']}")
        else:
            total_skipped += 1
            print("SNIPPET NON VALIDE (format non reconnu ou match non final)")

    # 4. On envoie une seule réponse résumant le tout
    if total_added > 0:
        reply_msg = f"**Rapport d'analyse (Lot)**\n\n{total_added} match(s) ajouté(s) avec succès :\n"
        reply_msg += "\n".join(added_matches_info)
        
        if total_skipped > 0:
            reply_msg += f"\n\n{total_skipped} snippet(s) ignoré(s) (non valides ou doublons)."
        
        reply_msg += f"\n\nTotal en mémoire : {len(matches)}"
        await event.reply(reply_msg)
    else:
        await event.reply(f"❌ Aucun nouveau match valide n'a été trouvé dans le bloc de {len(match_snippets)-1} snippet(s).")


# Fonction séparée pour vérifier les doublons
def is_duplicate(parsed_match):
    # Vérifie les 20 derniers matchs pour éviter les doublons
    return any(m['home'] == parsed_match['home'] and m['away'] == parsed_match['away'] for m in matches[-20:])


def parse_final_match(text):
    team_match = re.search(r'#([А-Яа-яA-Za-z0-9_]{3,50})_([А-Яа-яA-Za-z0-9_]{3,50})', text)
    if not team_match: 
        print("Debug Parse: Échec (Pas de teams)")
        return None
    
    home_raw, away_raw = team_match.group(1), team_match.group(2)
    home = TRANSLIT.get(home_raw, home_raw.replace('_', ' '))
    away = TRANSLIT.get(away_raw, away_raw.replace('_', ' '))

    # On cherche le score. Le format '4:7' est prioritaire
    score_match = re.search(r'(\d+):(\d+)', text)
    # S'il n'y a pas ':', on cherche '4 - 7'
    if not score_match:
        score_match = re.search(r'(\d+)\s*-\s*(\d+)', text)

    if not score_match: 
        print("Debug Parse: Échec (Pas de score)")
        return None
    
    home_goals, away_goals = int(score_match.group(1)), int(score_match.group(2))

    # === LA CORRECTION EST ICI ===
    # On cherche '2-й тайм' suivi d'une heure (pas seulement 6:00)
    # Accepte 6:00, 5:59, 5:53, etc.
    if not re.search(r'⏰\s*2-й\s+тайм\s+\d+:\d{2}', text, re.IGNORECASE):
        print("Debug Parse: Échec (Pas de marqueur de fin ⏰ 2-й тайм H:MM)")
        return None
    # ============================

    return {'home': home, 'away': away, 'home_goals': home_goals, 'away_goals': away_goals, 'total': home_goals + away_goals}

# === COMMANDES (inchangées) ===
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply(f"Bot de stats (Mode Lot) ON\n\nEnvoyez un ou plusieurs résultats pour les enregistrer.\nMatchs en mémoire : {len(matches)}")

@client.on(events.NewMessage(pattern='/stats'))
async def stats(event):
    if not matches:
        await event.reply("Aucun match en mémoire depuis le démarrage.")
        return

    reply_msg = f"Matchs détectés depuis le démarrage : {len(matches)}\n\n**10 Derniers Matchs :**\n"
    for match in matches[-10:]: # Affiche les 10 derniers
        reply_msg += f"- {match['home']} {match['home_goals']} - {match['away_goals']} {match['away']}\n"
    
    await event.reply(reply_msg)

# === LANCEMENT ===
async def main():
    await client.start(bot_token=BOT_TOKEN)
    print("BOT EN MODE LOT - PRÊT À RECEVOIR DES RÉSULTATS")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
