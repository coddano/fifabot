import os
import asyncio
from telethon import TelegramClient, events
import re

# === VARIABLES ===
API_ID = int(os.getenv('API_ID') or 0)
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL = os.getenv('CHANNEL')

matches = []

# === TRANSLITTÉRATION ===
TRANSLIT = {
    'Арсенал': 'Arsenal', 'Эвертон': 'Everton', 'ВестХэмЮнайтед': 'West Ham United',
    'НьюкаслЮнайтед': 'Newcastle United', 'Ливерпуль': 'Liverpool', 'МанчестерСити': 'Manchester City',
    'Челси': 'Chelsea', 'Тоттенхэм': 'Tottenham', 'МанчестерЮнайтед': 'Manchester United',
}

client = TelegramClient('bot_debug', API_ID, API_HASH)

# === DEBUG : AFFICHE TOUT ===
@client.on(events.NewMessage(chats=CHANNEL))
async def debug_handler(event):
    msg = event.message.message
    print("\n" + "="*60)
    print("MESSAGE REÇU DU CANAL :")
    print(msg)
    print("="*60)

    team_match = re.search(r'#([А-Яа-яA-Za-z0-9_]{3,50})_([А-Яа-яA-Za-z0-9_]{3,50})', msg)
    if team_match:
        print(f"ÉQUIPES : {team_match.group(1)} vs {team_match.group(2)}")
    else:
        print("AUCUNE ÉQUIPE")

    score_match = re.search(r'(\d+)\s*[:\-]\s*(\d+)', msg)
    if score_match:
        print(f"SCORE : {score_match.group(1)} - {score_match.group(2)}")
    else:
        print("AUCUN SCORE")

    final_match = re.search(r'⏰\s*2-й\s+тайм\s+6:00', msg, re.IGNORECASE)
    if final_match:
        print("FIN DÉTECTÉE : ⏰ 2-й тайм 6:00")
    else:
        print("PAS DE FIN")

    parsed = parse_final_match(msg)
    if parsed:
        matches.append(parsed)
        print(f"MATCH AJOUTÉ ! → {parsed['home']} {parsed['home_goals']}-{parsed['away_goals']} {parsed['away']}")
    else:
        print("MATCH NON AJOUTÉ")

def parse_final_match(text):
    team_match = re.search(r'#([А-Яа-яA-Za-z0-9_]{3,50})_([А-Яа-яA-Za-z0-9_]{3,50})', text)
    if not team_match: return None
    home_raw, away_raw = team_match.group(1), team_match.group(2)
    home = TRANSLIT.get(home_raw, home_raw.replace('_', ' '))
    away = TRANSLIT.get(away_raw, away_raw.replace('_', ' '))

    score_match = re.search(r'(\d+)\s*[:\-]\s*(\d+)', text)
    if not score_match: return None
    home_goals, away_goals = int(score_match.group(1)), int(score_match.group(2))

    if not re.search(r'⏰\s*2-й\s+тайм\s+6:00', text, re.IGNORECASE):
        return None

    if any(m['home'] == home and m['away'] == away for m in matches[-10:]):
        return None

    return {'home': home, 'away': away, 'home_goals': home_goals, 'away_goals': away_goals, 'total': home_goals + away_goals}

# === COMMANDES ===
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply(f"Debug ON\nMatchs: {len(matches)}")

@client.on(events.NewMessage(pattern='/stats'))
async def stats(event):
    await event.reply(f"Matchs détectés : {len(matches)}")

# === LANCEMENT ===
async def main():
    await client.start(bot_token=BOT_TOKEN)
    print("BOT EN MODE DEBUG - TOUT EST LOGGÉ")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
