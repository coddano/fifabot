import os
import asyncio
from telethon import TelegramClient, events
import re

# === VARIABLES D'ENVIRONNEMENT (pour Railway) ===
API_ID = int(os.getenv('API_ID') or 0)
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not all([API_ID, API_HASH, BOT_TOKEN]):
    print("ERREUR : API_ID, API_HASH, ou BOT_TOKEN est manquant.")
    exit()

# Notre "base de données" en mémoire (se vide à chaque redémarrage)
matches = []

# === TRANSLITTÉRATION (Russe -> Français/Anglais) ===
TRANSLIT = {
    'Арсенал': 'Arsenal', 'Эвертон': 'Everton', 'ВестХэмЮнайтед': 'West Ham United',
    'НьюкаслЮнайтед': 'Newcastle United', 'Ливерпуль': 'Liverpool', 'МанчестерСити': 'Manchester City',
    'Челси': 'Chelsea', 'Тоттенхэм': 'Tottenham', 'МанчестерЮнайтед': 'Manchester United',
    'ШеффилдЮнайтед': 'Sheffield United', 'Бернли': 'Burnley',
    'НоттингемФорест': 'Nottingham Forest', 'Вулверхэмптон': 'Wolverhampton',
    'АстонВилла': 'Aston Villa', 'КристалПэлэс': 'Crystal Palace',
    'Борнмут': 'Bournemouth', 'БрайтонэндХавАльбион': 'Brighton & Hove Albion',
    'Брентфорд': 'Brentford', 'Фулхэм': 'Fulham', 'ЛутонТаун': 'Luton Town',
    'ТоттенхэмХотспур': 'Tottenham Hotspur', 
}

# === NOUVEAU : MAP DE PRÉDICTION (Hashtag Français -> Nom Canonique) ===
# Crée un dictionnaire pour mapper 'westhamunited' (tapé par l'utilisateur)
# à 'West Ham United' (stocké dans la liste 'matches').
FRENCH_HASHTAG_MAP = {}
for name in TRANSLIT.values():
    # Clé: 'westhamunited' (minuscule, sans espace)
    # Valeur: 'West Ham United' (nom officiel)
    key = name.replace(" ", "").lower()
    FRENCH_HASHTAG_MAP[key] = name

# Initialiser le client en mode bot
client = TelegramClient('bot_session_name', API_ID, API_HASH)

# === GESTIONNAIRE POUR AJOUTER DES MATCHS (en lot) ===
@client.on(events.NewMessage(incoming=True))
async def message_handler(event):
    
    if not event.is_private:
        return

    msg = event.message.message
    
    # Ne pas traiter les commandes
    if msg.startswith('/'):
        return
        
    print("\n" + "="*60 + f"\nMESSAGE BLOC REÇU (privé) :\n{msg}\n" + "="*60)

    match_snippets = msg.split("> 🔰 FC24 4X4:")
    
    if len(match_snippets) < 2:
        print("Format de lot non reconnu. Traitement comme message simple.")
        parsed = parse_final_match(msg)
        if parsed and not is_duplicate(parsed):
            matches.append(parsed)
            await event.reply(f"✅ MATCH AJOUTÉ (simple) ! → {parsed['home']} {parsed['home_goals']}-{parsed['away_goals']} {parsed['away']}")
        else:
            await event.reply("❌ Format non reconnu ou match non terminé.")
        return

    added_matches_info = []
    total_added = 0
    total_skipped = 0

    for snippet in match_snippets[1:]:
        print(f"--- Analyse du snippet ---\n{snippet.strip()}\n-------------------------")
        parsed = parse_final_match(snippet)
        
        if parsed:
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

    if total_added > 0:
        reply_msg = f"**Rapport d'analyse (Lot)**\n\n{total_added} match(s) ajouté(s) avec succès :\n"
        reply_msg += "\n".join(added_matches_info)
        
        if total_skipped > 0:
            reply_msg += f"\n\n{total_skipped} snippet(s) ignoré(s) (non valides ou doublons)."
        
        reply_msg += f"\n\nTotal en mémoire : {len(matches)}"
        await event.reply(reply_msg)
    else:
        await event.reply(f"❌ Aucun nouveau match valide n'a été trouvé dans le bloc de {len(match_snippets)-1} snippet(s).")


# === FONCTIONS UTILITAIRES ===

def is_duplicate(parsed_match):
    return any(m['home'] == parsed_match['home'] and m['away'] == parsed_match['away'] for m in matches[-20:])

def parse_final_match(text):
    # Cette fonction gère toujours l'entrée Russe
    team_match = re.search(r'#([А-Яа-яA-Za-z0-9_]{3,50})_([А-Яа-яA-Za-z0-9_]{3,50})', text)
    if not team_match: 
        print("Debug Parse: Échec (Pas de teams)")
        return None
    
    home_raw, away_raw = team_match.group(1), team_match.group(2)
    home = TRANSLIT.get(home_raw, home_raw.replace('_', ' '))
    away = TRANSLIT.get(away_raw, away_raw.replace('_', ' '))

    score_match = re.search(r'(\d+):(\d+)', text)
    if not score_match:
        score_match = re.search(r'(\d+)\s*-\s*(\d+)', text)

    if not score_match: 
        print("Debug Parse: Échec (Pas de score)")
        return None
    
    home_goals, away_goals = int(score_match.group(1)), int(score_match.group(2))

    if not re.search(r'⏰\s*2-й\s+тайм\s+\d+:\d{2}', text, re.IGNORECASE):
        print("Debug Parse: Échec (Pas de marqueur de fin ⏰ 2-й тайм H:MM)")
        return None

    return {'home': home, 'away': away, 'home_goals': home_goals, 'away_goals': away_goals, 'total': home_goals + away_goals}

# === FONCTION D'ANALYSE STATISTIQUE (inchangée) ===
def get_team_stats(team_name):
    team_matches = []
    for m in matches:
        if m['home'] == team_name or m['away'] == team_name:
            team_matches.append(m)
    
    if not team_matches:
        return {'count': 0, 'avg_total': 0, 'pair_pct': 0.5, 'impaire_pct': 0.5}

    total_goals = 0
    pair_count = 0
    
    for m in team_matches:
        total = m['total']
        total_goals += total
        if total % 2 == 0:
            pair_count += 1
            
    count = len(team_matches)
    pair_pct = pair_count / count
    
    return {
        'count': count,
        'avg_total': total_goals / count,
        'pair_pct': pair_pct,
        'impaire_pct': 1.0 - pair_pct
    }

# === COMMANDES ===
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply(f"Bot de stats (Mode Lot) ON\n\nEnvoyez un ou plusieurs résultats (en Russe) pour les enregistrer.\n\nDemandez une prédiction (en Français) avec :\n`/predict #EquipeA_EquipeB`\n\nMatchs en mémoire : {len(matches)}")

@client.on(events.NewMessage(pattern='/stats'))
async def stats(event):
    if not matches:
        await event.reply("Aucun match en mémoire depuis le démarrage.")
        return

    reply_msg = f"Matchs détectés depuis le démarrage : {len(matches)}\n\n**10 Derniers Matchs :**\n"
    for match in matches[-10:]:
        reply_msg += f"- {match['home']} {match['home_goals']} - {match['away_goals']} {match['away']}\n"
    
    await event.reply(reply_msg)

# === COMMANDE DE PRÉDICTION (MISE À JOUR) ===
# Le pattern n'accepte que les lettres latines (français/anglais)
# et les chiffres. PAS d'underscores DANS les noms.
@client.on(events.NewMessage(pattern=r'/predict #([A-Za-z0-9]+)_([A-Za-z0-9]+)'))
async def predict_handler(event):
    try:
        # 1. Obtenir les noms du hashtag (ex: 'WestHamUnited' et 'Chelsea')
        # On met tout en minuscule pour correspondre aux clés du MAP
        home_raw_hashtag = event.pattern_match.group(1).lower()
        away_raw_hashtag = event.pattern_match.group(2).lower()
        
        # 2. Traduire les noms hashtag en noms canoniques
        # .get(clé, défaut)
        # ex: 'westhamunited' -> 'West Ham United'
        # ex: 'arsenal' -> 'Arsenal'
        home = FRENCH_HASHTAG_MAP.get(home_raw_hashtag, home_raw_hashtag.capitalize())
        away = FRENCH_HASHTAG_MAP.get(away_raw_hashtag, away_raw_hashtag.capitalize())
        
        print(f"Demande de prédiction reçue pour : {home} vs {away}")

        # 3. Obtenir les stats pour chaque équipe
        home_stats = get_team_stats(home)
        away_stats = get_team_stats(away)
        
        # 4. Vérifier si on a des données
        total_data = home_stats['count'] + away_stats['count']
        if total_data == 0:
            await event.reply(f"Désolé, je n'ai **aucune donnée** ni pour {home} ni pour {away}. Impossible de prédire.")
            return
            
        # 5. Calculer les prédictions
        all_avgs = []
        if home_stats['count'] > 0: all_avgs.append(home_stats['avg_total'])
        if away_stats['count'] > 0: all_avgs.append(away_stats['avg_total'])
        final_avg_total = sum(all_avgs) / len(all_avgs)
        
        final_pair_pct = (home_stats['pair_pct'] + away_stats['pair_pct']) / 2
        final_impaire_pct = (home_stats['impaire_pct'] + away_stats['impaire_pct']) / 2
        
        prediction_pair_impaire = "**Pair**" if final_pair_pct >= final_impaire_pct else "**Impaire**"
        
        # 6. Construire la réponse
        reply = f"📊 **Prédiction pour {home} vs {away}** 📊\n\n"
        reply += f"Basé sur {home_stats['count']} match(s) pour {home} et {away_stats['count']} match(s) pour {away} (Total: {len(matches)}).\n"
        reply += "--- \n"
        reply += f"📈 **Total de Buts Attendu (Moyenne) :** **~{final_avg_total:.1f} buts**\n"
        reply += f"   (Moy. {home}: {home_stats['avg_total']:.1f}, Moy. {away}: {away_stats['avg_total']:.1f})\n\n"
        reply += f"⚖️ **Prédiction Pair / Impaire :**\n"
        reply += f"   - Chance 'Pair' : {final_pair_pct:.1%}\n"
        reply += f"   - Chance 'Impaire' : {final_impaire_pct:.1%}\n"
        reply += f"   - **Mon choix : {prediction_pair_impaire}**\n\n"
        reply += "*(Rappel : Prédictions basées uniquement sur les données en mémoire.)*"
            
        await event.reply(reply)

    except Exception as e:
        print(f"Erreur de prédiction : {e}")
        await event.reply(f"Erreur de prédiction. Assurez-vous d'utiliser le format :\n`/predict #EquipeA_EquipeB` (en français, sans espaces)")

# === LANCEMENT ===
async def main():
    await client.start(bot_token=BOT_TOKEN)
    print("BOT EN MODE LOT & PRÉDICTION - PRÊT")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
