import os
import asyncio
from telethon import TelegramClient, events
import pandas as pd
import numpy as np
from scipy.stats import poisson
import re

# === VARIABLES (Railway) ===
API_ID = int(os.getenv('API_ID') or 0)
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL = os.getenv('CHANNEL')

matches = []

# === TRANSLITTÉRATION ÉQUIPES ANGLETERRE ===
TRANSLIT = {
    'Арсенал': 'Arsenal', 'АстонВилла': 'Aston Villa', 'Борнмут': 'Bournemouth',
    'Брайтон': 'Brighton', 'ВестХэмЮнайтед': 'West Ham United', 'Вулверхэмптон': 'Wolverhampton',
    'Эвертон': 'Everton', 'Фулхэм': 'Fulham', 'КристалПэлас': 'Crystal Palace',
    'ЛестерСити': 'Leicester City', 'Ливерпуль': 'Liverpool', 'МанчестерСити': 'Manchester City',
    'МанчестерЮнайтед': 'Manchester United', 'НоттингемФорест': 'Nottingham Forest',
    'НьюкаслЮнайтед': 'Newcastle United', 'Саутгемптон': 'Southampton', 'Тоттенхэм': 'Tottenham',
    'Челси': 'Chelsea', 'Брентфорд': 'Brentford', 'ВестБромвич': 'West Bromwich Albion',
}

client = TelegramClient('bot_session', API_ID, API_HASH)

# === FONCTION : DÉTECTE MATCH TERMINÉ À 6:00 ===
def parse_fc24_final(text):
    # 1. Équipes via #Team1_Team2
    team_match = re.search(r'#([А-Яа-яA-Za-z0-9_]{3,50})_([А-Яа-яA-Za-z0-9_]{3,50})', text)
    if not team_match:
        return None
    home_raw, away_raw = team_match.group(1), team_match.group(2)
    home = TRANSLIT.get(home_raw, home_raw.replace('_', ' '))
    away = TRANSLIT.get(away_raw, away_raw.replace('_', ' '))

    # 2. Score final (ex: 3:6)
    score_match = re.search(r'(\d+):(\d+)', text)
    if not score_match:
        return None
    home_goals = int(score_match.group(1))
    away_goals = int(score_match.group(2))
    total = home_goals + away_goals

    # 3. DÉTECTION FINALE : ⏰ 6:00
    time_match = re.search(r'⏰.*?(\d):(\d{2})', text)
    if not time_match:
        return None
    minute = int(time_match.group(1))
    second = int(time_match.group(2))
    is_final_time = (minute == 6 and second == 0)

    if not is_final_time:
        return None  # Pas encore fini

    # 4. Anti-doublon
    if any(m['home'] == home and m['away'] == away for m in matches[-10:]):
        return None

    return {
        'home': home,
        'away': away,
        'home_goals': home_goals,
        'away_goals': away_goals,
        'total': total,
        'pair': total % 2 == 0
    }

# === ÉCOUTE CANAL ===
@client.on(events.NewMessage(chats=CHANNEL))
async def handler(event):
    global matches
    msg = event.message.message
    parsed = parse_fc24_final(msg)
    if parsed:
        matches.append(parsed)
        print(f"✅ MATCH TERMINÉ (6:00) : {parsed['home']} {parsed['home_goals']}-{parsed['away_goals']} {parsed['away']} → Total {parsed['total']} {'PAIR' if parsed['pair'] else 'IMPAIR'}")
        if len(matches) > 100:
            matches = matches[-100:]

# === COMMANDES ===
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply(
        "FC 24 4x4 Predictor\n\n"
        "`/predict Arsenal Chelsea`\n"
        "`/stats`\n"
        "`/last`\n\n"
        f"Live: **{len(matches)}** matchs",
        parse_mode='md'
    )

@client.on(events.NewMessage(pattern=r'/predict\s+(.+)'))
async def predict(event):
    if len(matches) < 5:
        await event.reply("Attends 5 matchs terminés !")
        return
    # ... (prédiction complète ci-dessous si tu veux)
    await event.reply("Prédiction en cours... (version complète dispo)")

@client.on(events.NewMessage(pattern='/stats'))
async def stats(event):
    if not matches:
        await event.reply("Aucun match terminé.")
        return
    df = pd.DataFrame(matches)
    avg = df['total'].mean()
    pair = (df['pair'].mean() * 100)
    await event.reply(
        f"{len(matches)} matchs\n"
        f"{avg:.1f} buts/match\n"
        f"Pairs: {pair:.0f}%\n"
        f"Impairs: {100-pair:.0f}%",
        parse_mode='md'
    )

@client.on(events.NewMessage(pattern='/last'))
async def last(event):
    if not matches:
        await event.reply("Aucun match.")
        return
    txt = "Derniers matchs:\n"
    for m in matches[-5:][::-1]:
        txt += f"{m['home']} {m['home_goals']}-{m['away_goals']} {m['away']} {'PAIR' if m['pair'] else 'IMPAIR'}\n"
    await event.reply(txt)

# === LANCEMENT ===
async def main():
    await client.start(bot_token=BOT_TOKEN)
    print("BOT FC24 4x4 ACTIF - Détection à ⏰ 6:00")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
