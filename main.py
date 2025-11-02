# FIFA 1XBET PREDICTOR BOT - PRÊT À L'EMPLOI
from telethon import TelegramClient, events
import pandas as pd
import numpy as np
from scipy.stats import poisson
import re

# === À REMPLIR PAR TOI ===
API_ID = 1234567                  # ← Ton api_id (my.telegram.org)
API_HASH = 'abcdef123456...'      # ← Ton api_hash
BOT_TOKEN = '687654321:AAH...'    # ← Ton token BotFather
CHANNEL = '@ton_canal_ici'        # ← EX: @fifa1xbet_live

# === NE RIEN TOUCHER CI-DESSOUS ===
client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
matches = []

def parse_score(text):
    pattern = r'([A-Za-zÀ-ÿ\s\']{2,30})\s+(\d+)[-\–](\d+)\s+([A-Za-zÀ-ÿ\s\']{2,30})'
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        home, hg, ag, away = m.groups()
        return {
            'home': home.strip(),
            'home_goals': int(hg),
            'away': away.strip(),
            'away_goals': int(ag),
            'total': int(hg) + int(ag)
        }
    return None

@client.on(events.NewMessage(chats=CHANNEL))
async def on_new_match(event):
    global matches
    parsed = parse_score(event.message.message)
    if parsed:
        matches.append(parsed)
        print(f"Match ajouté : {parsed['home']} {parsed['home_goals']}-{parsed['away_goals']} {parsed['away']}")

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply(
        "FIFA 1xbet Predictor\n\n"
        "Commandes :\n"
        "/predict Équipe1 Équipe2 → prédiction\n"
        "/stats → statistiques\n\n"
        "En écoute du canal...",
        parse_mode='md'
    )

@client.on(events.NewMessage(pattern='/predict'))
async def predict(event):
    if len(matches) < 5:
        await event.reply("Pas assez de matchs. Attends un peu !")
        return
    
    args = event.message.message.split()[1:]
    if len(args) < 2:
        await event.reply("Usage: `/predict Équipe1 Équipe2`")
        return

    home = " ".join(args[:len(args)//2])
    away = " ".join(args[len(args)//2:])

    df = pd.DataFrame(matches)
    lambda_home = df['home_goals'].mean()
    lambda_away = df['away_goals'].mean()

    sim = 10000
    home_goals = poisson.rvs(lambda_home, size=sim)
    away_goals = poisson.rvs(lambda_away, size=sim)
    total = home_goals + away_goals

    pair = np.mean(total % 2 == 0) * 100
    impair = 100 - pair
    avg = total.mean()

    await event.reply(
        f"*{home} vs {away}*\n\n"
        f"Buts moyens : {avg:.2f}\n"
        f"**PAIR** : {pair:.1f}%\n"
        f"**IMPAIR** : {impair:.1f}%\n\n"
        f"Sur {len(matches)} matchs",
        parse_mode='md'
    )

@client.on(events.NewMessage(pattern='/stats'))
async def stats(event):
    if not matches:
        await event.reply("Aucun match encore.")
        return
    df = pd.DataFrame(matches)
    total = len(df)
    avg = df['total'].mean()
    pair_pct = (df['total'] % 2 == 0).mean() * 100
    await event.reply(
        f"*Stats FIFA 1xbet*\n\n"
        f"Matchs : {total}\n"
        f"Buts/match : {avg:.2f}\n"
        f"Totaux pairs : {pair_pct:.1f}%\n"
        f"Totaux impairs : {100-pair_pct:.1f}%",
        parse_mode='md'
    )

print("Bot démarré !")
client.run_until_disconnected()