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

# === TRANSLITTÉRATION ===
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

# === PARSER : DÉTECTION FIN À "⏰ 2-й тайм 6:00" ===
def parse_fc24_final(text):
    # 1. ÉQUIPES
    team_match = re.search(r'#([А-Яа-яA-Za-z0-9_]{3,50})_([А-Яа-яA-Za-z0-9_]{3,50})', text)
    if not team_match:
        return None
    home_raw = team_match.group(1)
    away_raw = team_match.group(2)
    home = TRANSLIT.get(home_raw, home_raw.replace('_', ' '))
    away = TRANSLIT.get(away_raw, away_raw.replace('_', ' '))

    # 2. SCORE FINAL
    score_match = re.search(r'(\d+)\s*[:\-]\s*(\d+)', text)
    if not score_match:
        return None
    home_goals = int(score_match.group(1))
    away_goals = int(score_match.group(2))
    total = home_goals + away_goals

    # 3. DÉTECTION EXACTE : ⏰ 2-й тайм 6:00
    final_time_match = re.search(r'⏰\s*2-й\s+тайм\s+6:00', text, re.IGNORECASE)
    if not final_time_match:
        return None  # Pas le signal final

    # 4. Anti-doublon
    if any(m['home'] == home and m['away'] == away for m in matches[-20:]):
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
    parsed = parse_fc24_final(event.message.message)
    if parsed:
        matches.append(parsed)
        print(f"FINAL 6:00 DÉTECTÉ ! {parsed['home']} {parsed['home_goals']}-{parsed['away_goals']} {parsed['away']} → {parsed['total']} buts")
        if len(matches) > 200:
            matches = matches[-200:]

# === COMMANDES ===
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply(
        "FC 24 4x4 Predictor\n\n"
        "`/predict Arsenal Everton`\n"
        "`/stats`\n"
        "`/last`\n\n"
        f"Live: **{len(matches)}** matchs terminés",
        parse_mode='md'
    )

@client.on(events.NewMessage(pattern=r'/predict\s+(.+)'))
async def predict(event):
    if len(matches) < 5:
        await event.reply("Attends 5 matchs avec ⏰ 2-й тайм 6:00 !")
        return
    
    query = event.pattern_match.group(1).strip()
    teams = re.split(r'\s+vs\s+|\s+', query)
    if len(teams) < 2:
        await event.reply("❌ `/predict Arsenal Everton`")
        return
    
    home = " ".join(teams[0].split()).title()
    away = " ".join(teams[-1].split()).title()

    df = pd.DataFrame(matches)
    lambda_home = df['home_goals'].mean()
    lambda_away = df['away_goals'].mean()

    n_sim = 20000
    home_sim = poisson.rvs(lambda_home, size=n_sim)
    away_sim = poisson.rvs(lambda_away, size=n_sim)
    total_sim = home_sim + away_sim

    prob_pair = np.mean(total_sim % 2 == 0) * 100
    prob_impair = 100 - prob_pair
    avg_total = np.mean(total_sim)

    reco = "PAIR" if prob_pair > 55 else "IMPAIR" if prob_impair > 55 else "ÉQUILIBRÉ"

    await event.reply(
        f"*{home} vs {away}*\n\n"
        f"Buts moyens: **{avg_total:.1f}**\n"
        f"**PAIR**: **{prob_pair:.1f}%**\n"
        f"**IMPAIR**: **{prob_impair:.1f}%**\n\n"
        f"**{reco}**\n\n"
        f"Sur **{len(matches)}** matchs",
        parse_mode='md'
    )

@client.on(events.NewMessage(pattern='/stats'))
async def stats(event):
    if not matches:
        await event.reply("Aucun match avec ⏰ 2-й тайм 6:00.")
        return
    df = pd.DataFrame(matches)
    await event.reply(
        f"*{len(df)}* matchs terminés\n"
        f"**{df['total'].mean():.1f}** buts/match\n"
        f"Pairs: **{(df['pair'].mean()*100):.0f}%**\n"
        f"Impairs: **{(1-df['pair'].mean())*100:.0f}%**",
        parse_mode='md'
    )

@client.on(events.NewMessage(pattern='/last'))
async def last(event):
    if not matches:
        await event.reply("Aucun match.")
        return
    txt = "*5 Derniers matchs (6:00)*\n\n"
    for m in matches[-5:][::-1]:
        txt += f"*{m['home']}* {m['home_goals']}-{m['away_goals']} *{m['away']}* → **{m['total']}** ({'PAIR' if m['pair'] else 'IMPAIR'})\n"
    await event.reply(txt, parse_mode='md')

# === LANCEMENT ===
async def main():
    await client.start(bot_token=BOT_TOKEN)
    print("BOT ACTIF - Détection FIN à ⏰ 2-й тайм 6:00")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
