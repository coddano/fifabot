import os
import asyncio
from telethon import TelegramClient, events
import pandas as pd
import numpy as np
from scipy.stats import poisson
import re

# === VARIABLES SECRÈTES (Railway → Variables) ===
API_ID = int(os.getenv('API_ID') or 0)
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL = os.getenv('CHANNEL')

# === TRANSLITTÉRATION ÉQUIPES ANGLETERRE FC 24 (complet) ===
TRANSLIT = {
    # Équipes Angleterre typiques
    'Арсенал': 'Arsenal',
    'АстонВилла': 'Aston Villa',
    'Борнмут': 'Bournemouth',
    'Брайтон': 'Brighton',
    'ВестХэмЮнайтед': 'West Ham United',
    'Вулверхэмптон': 'Wolverhampton',
    'Эвертон': 'Everton',
    'Фулхэм': 'Fulham',
    'КристалПэлас': 'Crystal Palace',
    'ЛестерСити': 'Leicester City',
    'Ливерпуль': 'Liverpool',
    'МанчестерСити': 'Manchester City',
    'МанчестерЮнайтед': 'Manchester United',
    'НоттингемФорест': 'Nottingham Forest',
    'НьюкаслЮнайтед': 'Newcastle United',
    'Саутгемптон': 'Southampton',
    'Тоттенхэм': 'Tottenham',
    'Челси': 'Chelsea',
    'Брентфорд': 'Brentford',
    'ВестБромвич': 'West Bromwich Albion',
}

# === STOCKAGE ===
matches = []

# === PARSER OPTIMISÉ FC 24 4x4 ===
def parse_fc24_score(text):
    # 1. Hashtag #Équipe1_Équipe2
    team_match = re.search(r'#([А-Яа-яA-Za-z0-9_]{3,50})_([А-Яа-яA-Za-z0-9_]{3,50})', text)
    if not team_match:
        return None
    
    home_raw = team_match.group(1)
    away_raw = team_match.group(2)
    
    # Translittération
    home = TRANSLIT.get(home_raw, home_raw.replace('_', ' '))
    away = TRANSLIT.get(away_raw, away_raw.replace('_', ' '))

    # 2. Score final : X:Y avant ( 
    score_patterns = [
        r'(\d+):(\d+)\s*\(',
        r'(\d+)-(\d+)\s*\('
    ]
    score_match = None
    for pat in score_patterns:
        score_match = re.search(pat, text)
        if score_match:
            break
    
    if not score_match:
        return None

    home_goals = int(score_match.group(1))
    away_goals = int(score_match.group(2))
    total = home_goals + away_goals

    # 3. Match FINI ? (pas de ⏰ + тайм, ou #T9)
    is_live = '⏰' in text and ('тайм' in text or 'мин' in text)
    is_final = '#T9' in text or 'Финал' in text or not is_live
    
    if not is_final:
        return None  # Ignore live updates

    # Anti-doublon
    if any(m['home'] == home and m['away'] == away and m['home_goals'] == home_goals for m in matches[-10:]):
        return None

    return {
        'home': home,
        'away': away,
        'home_goals': home_goals,
        'away_goals': away_goals,
        'total': total,
        'pair': total % 2 == 0
    }

# === CLIENT BOT ===
client = TelegramClient('bot_session', API_ID, API_HASH)

# === ÉCOUTE CANAL FC 24 4x4 ===
@client.on(events.NewMessage(chats=CHANNEL))
async def handler_channel(event):
    global matches
    parsed = parse_fc24_score(event.message.message)
    if parsed:
        matches.append(parsed)
        print(f"✅ FC24 4x4 AJOUTÉ: {parsed['home']} {parsed['home_goals']}-{parsed['away_goals']} {parsed['away']} (Total {parsed['total']} {'PAIR' if parsed['pair'] else 'IMPAIR'})")
        # Limite à 100 derniers matchs
        if len(matches) > 100:
            matches = matches[-100:]

# === /start ===
@client.on(events.NewMessage(pattern=r'^/start'))
async def cmd_start(event):
    await event.reply(
        "⚽ *FC 24 4x4 Angleterre Predictor*\n\n"
        "📱 *Commandes :*\n"
        "`/predict Arsenal Chelsea` → pair/impair\n"
        "`/stats` → stats ligue\n"
        "`/last` → 5 derniers matchs\n\n"
        f"🔴 En live: {len(matches)} matchs analysés\n"
        "Championnat Angleterre uniquement !",
        parse_mode='md'
    )

# === /predict ===
@client.on(events.NewMessage(pattern=r'^/predict\s+(.+)'))
async def cmd_predict(event):
    if len(matches) < 5:
        await event.reply("⏳ Pas assez de matchs. Attends 3-5 fins de match !")
        return
    
    query = event.pattern_match.group(1).strip()
    teams = query.split('vs') if 'vs' in query else query.split()
    if len(teams) < 2:
        await event.reply("❌ Usage: `/predict Arsenal Chelsea` ou `/predict Arsenal vs Chelsea`")
        return
    
    home = " ".join(teams[0].split()).strip().title()
    away = " ".join(teams[-1].split()).strip().title()

    df = pd.DataFrame(matches)
    lambda_home = df['home_goals'].mean()
    lambda_away = df['away_goals'].mean()
    
    # Simulation 20k (plus précis)
    n_sim = 20000
    home_sim = poisson.rvs(lambda_home, size=n_sim)
    away_sim = poisson.rvs(lambda_away, size=n_sim)
    total_sim = home_sim + away_sim
    
    prob_pair = np.mean(total_sim % 2 == 0) * 100
    prob_impair = 100 - prob_pair
    avg_total = np.mean(total_sim)
    
    reco = "💰 **MISER PAIR**" if prob_pair > 55 else "💰 **MISER IMPAIR**" if prob_impair > 55 else "⚖️ 50/50"

    await event.reply(
        f"⚽ *{home} vs {away}* (FC24 4x4)\n\n"
        f"📊 Moyenne buts: **{avg_total:.1f}**\n\n"
        f"✅ **PAIR** : **{prob_pair:.1f}%**\n"
        f"❌ **IMPAIR** : **{prob_impair:.1f}%**\n\n"
        f"{reco}\n\n"
        f"Sur **{len(matches)}** matchs Angleterre",
        parse_mode='md'
    )

# === /stats ===
@client.on(events.NewMessage(pattern=r'^/(stats|ligue)'))
async def cmd_stats(event):
    if not matches:
        await event.reply("⏳ Aucun match terminé. Premier match en cours...")
        return
    
    df = pd.DataFrame(matches)
    total_matches = len(df)
    avg_total = df['total'].mean()
    pair_pct = df['pair'].mean() * 100
    over25_pct = (df['total'] > 2.5).mean() * 100
    
    await event.reply(
        f"🏆 *FC 24 4x4 Angleterre*\n\n"
        f"📈 **{total_matches}** matchs terminés\n"
        f"⚽ **{avg_total:.1f}** buts/match\n"
        f"✅ **Pairs** : **{pair_pct:.1f}%**\n"
        f"❌ **Impairs** : **{100-pair_pct:.1f}%**\n"
        f"🔥 **Over 2.5** : **{over25_pct:.1f}%**\n\n"
        f"Home avg: **{df['home_goals'].mean():.1f}** | Away: **{df['away_goals'].mean():.1f}**",
        parse_mode='md'
    )

# === /last ===
@client.on(events.NewMessage(pattern=r'^/last'))
async def cmd_last(event):
    if not matches:
        return
    recent = matches[-5:][::-1]
    msg = "📋 *5 DERNIERS MATCHS FC24 4x4*\n\n"
    for m in recent:
        parity = "🟢 PAIR" if m['pair'] else "🔴 IMPAIR"
        msg += f"*{m['home']}* {m['home_goals']}-{m['away_goals']} *{m['away']}*  {parity}\n"
    msg += f"\n**Total analysés: {len(matches)}**"
    await event.reply(msg, parse_mode='md')

# === LANCEMENT ===
async def main():
    await client.start(bot_token=BOT_TOKEN)
    print(f"🚀 Bot FC24 4x4 Angleterre LIVE sur {CHANNEL}")
    print(f"📊 Matchs actuels: {len(matches)}")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
