# =============== IMPORTS & VARIABLES ===============
from email.mime import message, text
import os
import random
import datetime
import aiohttp
import urllib.parse
import openai
import subprocess
import sys
import asyncio
import discord
from dataclasses import dataclass
from discord.ext import tasks
from hadiths import HADITHS_LOCAL
from dotenv import load_dotenv
from champions import CHAMPION_NAME_TO_ID, CHAMPION_NAME_FIX

def log(msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

def split_message(text, max_length=2000):
    return [text[i:i+max_length] for i in range(0, len(text), max_length)]

log("Lancement du bot...")

load_dotenv()
RIOT_TOKEN = os.getenv('RIOT_TOKEN')
openai.api_key = os.getenv("OPENAI_API_KEY")
GAME_CHANNEL_ID = int(os.getenv('GAME_CHANNEL_ID'))
GENERAL_CHANNEL_ID = int(os.getenv('GENERAL_CHANNEL_ID'))
user_ids_raw = os.getenv('USER_IDS_TO_NOTIFY', '')
USER_IDS_TO_NOTIFY = [int(uid.strip()) for uid in user_ids_raw.split(',') if uid.strip()]
user_ids_hadith_raw = os.getenv('USER_IDS_HADITH', '')
USER_IDS_HADITH = [int(uid.strip()) for uid in user_ids_hadith_raw.split(',') if uid.strip()]
PRAYER_ADVANCE_MINUTES = 60

# =============== DATACLASSES & JOUEURS ===============
@dataclass
class Player:
    gameName: str
    tagLine: str
    puuid: str = None

PLAYERS = [
    Player(gameName="FREE Palestine", tagLine="01234"),
    Player(gameName="Krant", tagLine="2121"),
    Player(gameName="Free Palestine", tagLine="WVK0"),
    Player(gameName="TPASCONTENTRIPLE", tagLine="oui"),
    Player(gameName="Tεutεu", tagLine="EUW"),
    Player(gameName="Random Dash", tagLine="jinx"),
    Player(gameName="La Bête 8 degrés", tagLine="2121"),
    Player(gameName="C ikard", tagLine="6969"),
    Player(gameName="GrosGolemm", tagLine="EUW"),
    Player(gameName="GOULEM DE FARINE", tagLine="EUW"),
]

# Remplissage du puuid pour chaque joueur 
async def fetch_puuids():
    async with aiohttp.ClientSession() as session:
        for player in PLAYERS:
            url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{player.gameName}/{player.tagLine}?api_key={RIOT_TOKEN}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    player.puuid = data['puuid']
                    log(f"{player.gameName}#{player.tagLine} → PUUID : {data['puuid']}")
                else:
                    log(f"Erreur pour {player.gameName}#{player.tagLine} : {response.status} - {await response.text()}")

last_announced_game_ids = {}  # clé = puuid, valeur = gameId

# =============== FONCTIONS OPENAI ===============
async def ask_gpt(prompt):
    try:
        response = await asyncio.to_thread(
            openai.ChatCompletion.create,
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        log(f"Erreur OpenAI : {e}")
        return "Je n'ai pas pu répondre pour le moment."

# =============== FONCTIONS LOL ===============
async def fetch_current_game(puuid, platform, riot_token):
    url_game = (
        f"https://{platform}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/"
        f"{puuid}?api_key={riot_token}"
    )
    async with aiohttp.ClientSession() as session:
        async with session.get(url_game) as resp:
            if resp.status != 200:
                return None
            game_data = await resp.json()
        for participant in game_data.get("participants", []):
            if participant.get("puuid") == puuid:
                return {
                    "gameId": game_data.get("gameId"),
                    "championId": participant.get("championId"),
                    "queueType": game_data.get("gameMode")
                }
        return None

async def get_summoner_id(encryptedPUUID, region, riot_token):
    url = (
        f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{encryptedPUUID}?api_key={riot_token}"
    )
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            return data.get("id")

async def fetch_summoner_rank(player, region, riot_token):
    game_name_encoded = urllib.parse.quote(player.gameName)
    url_summoner = (
        f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-name/"
        f"{game_name_encoded}?api_key={riot_token}"
    )
    async with aiohttp.ClientSession() as session:
        async with session.get(url_summoner) as resp:
            if resp.status != 200:
                log(f"Erreur summonerId pour {player.gameName}: {resp.status}")
                return "Unranked"
            data = await resp.json()
            summoner_id = data.get("id")
            if not summoner_id:
                log(f"Aucun summonerId trouvé pour {player.gameName}")
                return "Unranked"

        url_rank = (
            f"https://{region}.api.riotgames.com/lol/league/v4/entries/by-summoner/"
            f"{summoner_id}?api_key={riot_token}"
        )
        async with session.get(url_rank) as resp:
            if resp.status != 200:
                log(f"Erreur league-v4 pour {player.gameName} : {resp.status}")
                return "Unranked"
            ranks = await resp.json()
            for entry in ranks:
                if entry.get("queueType") == "RANKED_SOLO_5x5":
                    tier = entry.get("tier", "Unranked").capitalize()
                    rank = entry.get("rank", "")
                    lp = entry.get("leaguePoints", 0)
                    return f"{tier} {rank} ({lp} LP)"
            if ranks:
                entry = ranks[0]
                tier = entry.get("tier", "Unranked").capitalize()
                rank = entry.get("rank", "")
                lp = entry.get("leaguePoints", 0)
                queue = entry.get("queueType", "")
                return f"{tier} {rank} ({lp} LP) [{queue}]"
            return "Unranked"

async def fetch_winrate(puuid, champion_id, region, riot_token, max_matches=20):
    url_matches = (
        f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/"
        f"{puuid}/ids?start=0&count={max_matches}&api_key={riot_token}"
    )
    async with aiohttp.ClientSession() as session:
        async with session.get(url_matches) as resp:
            if resp.status != 200:
                log(f"Erreur récupération des matchs : {resp.status}")
                return "N/A"
            match_ids = await resp.json()

        wins = 0
        total = 0

        for match_id in match_ids:
            url_match = (
                f"https://{region}.api.riotgames.com/lol/match/v5/matches/"
                f"{match_id}?api_key={riot_token}"
            )
            async with session.get(url_match) as resp:
                if resp.status != 200:
                    continue
                match_data = await resp.json()
                for participant in match_data["info"]["participants"]:
                    if participant["puuid"] == puuid and participant["championId"] == champion_id:
                        total += 1
                        if participant["win"]:
                            wins += 1
                        break

        if total == 0:
            return "N/A"
        winrate = round((wins / total) * 100)
        loses = total - wins
        return f"{winrate}% ({wins}/{loses})"

# =============== FONCTIONS PRIÈRES & Hadiths & versets & sourates ===============

async def get_prayer_times_aladhan():
    url = "https://api.aladhan.com/v1/timingsByCity?city=Strasbourg&country=France&method=2"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return data['data']['timings']

def parse_time(time_str):
    return datetime.datetime.strptime(time_str, "%H:%M").time()

async def get_random_hadith():
    return f"🕌 {random.choice(HADITHS_LOCAL)}"

async def get_hadith_categories():
    url = "https://hadeethenc.com/api/v1/categories/list/?language=fr"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return "Impossible de récupérer les catégories."
            data = await resp.json()
            return data
        
async def get_random_ayah(edition="fr.hamidullah"):
    url = f"https://api.alquran.cloud/v1/ayah/random/{edition}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return "Impossible de récupérer un verset pour le moment."
            data = await resp.json()
            ayah = data.get("data", {})
            texte = ayah.get("text", "Verset inconnu.")
            sourate = ayah.get("surah", {}).get("englishName", "")
            numero = ayah.get("numberInSurah", "")
            return f"**{sourate} [{numero}]**\n{texte}"
        
async def get_random_surah(edition="fr.hamidullah"):
    surah_number = random.randint(1, 114)
    url = f"https://api.alquran.cloud/v1/surah/{surah_number}/{edition}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return "Impossible de récupérer une sourate pour le moment."
            data = await resp.json()
            surah = data.get("data", {})
            name = surah.get("englishName", "Nom inconnu")
            name_fr = surah.get("name", "")
            ayahs = surah.get("ayahs", [])
            ayah_texts = "\n".join([f"{a['numberInSurah']}. {a['text']}" for a in ayahs[:5]])
            full_texts = "\n".join([f"{a['numberInSurah']}. {a['text']}" for a in ayahs])
            titre = f"**{name_fr} ({name})**"
            return titre, ayah_texts, full_texts, surah_number

# =============== DISCORD BOT ===============

intents = discord.Intents.all()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    await fetch_puuids()
    if not check_games.is_running():
        check_games.start()
    if not prayer_reminder.is_running():
        prayer_reminder.start()
    asyncio.create_task(auto_update()) 
    if not daily_ayah.is_running():
        daily_ayah.start()

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if isinstance(message.channel, discord.DMChannel):
        await message.channel.typing()
        try:
            if message.attachments:
                image_url = message.attachments[0].url
                user_text = message.content if message.content else "Décris cette image"
                response = await asyncio.to_thread(
                    openai.ChatCompletion.create,
                    model="gpt-4o",
                    messages=[
                        {"role": "user", "content": [
                            {"type": "text", "text": user_text},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]}
                    ]
                )
                await message.channel.send(response.choices[0].message.content)
            else:
                reponse = await ask_gpt(message.content)
                await message.channel.send(reponse)
        except Exception as e:
            log(f"Erreur OpenAI DM : {e}")
            await message.channel.send("Je n'ai pas pu répondre pour le moment.")
        return
    
    contenu = message.content.lower()
    reponses = {
        'idaily': 'Laisse moi dehak',
        'salam alaykoum': 'wa 3alaykoum salam',
        'salut': 'Salut bg',
        'ramène la meute': "<@283962205680959488>,<@206010121371779073>,<@516681520669523979>,<@270582327657103362>,<@300644159566381060>,<@252789076229488640>,<@292972602735984640> il est l'heure de jouer 🦍🦍🦍 ",
    }

    for mot, rep in reponses.items():
        if mot in contenu:
            await message.channel.send(rep)
            return

    if client.user in message.mentions and any(mot in contenu for mot in ('bonjour', 'wesh', 'coucou', 'wsh', 'bjr', 'slt', 'cc')):
        reponses_bonjour = [
            'Salut le boss',
            'Yo les ptits potes',
            'Bip Boop, Bip Boop 🤖'
        ]
        await message.channel.send(random.choice(reponses_bonjour))
        return

    if client.user in message.mentions and any(mot in contenu for mot in ('ça va', 'cv', 'tu vas bien','ca va','cava','çava')):
        reponses_ca_va = [
            'Oui ça va et toi?',
            'ça va Al hamdulillah et toi?',
            "C'est la débrouille"
        ]
        await message.channel.send(random.choice(reponses_ca_va))
        return
    
    if client.user in message.mentions and any(mot in contenu for mot in('c qui la plus grosse',"c'est qui la plus grosse","c'est qui le plus gros",'c qui le plus gros')):
        reponses_qui = [
            "C'est <@300644159566381060>,",
        ]
        await message.channel.send(random.choice(reponses_qui))
        return
    
    SPECIAL_USERS = [300644159566381060, 1279835513150378017]  

    if client.user in message.mentions:
        if message.author.id in SPECIAL_USERS:
            r = random.random()
            if r < 0.10:
                await message.channel.send("Couché le toutou")
            elif r < 0.20:
                await message.channel.send("Je dois ping le nul, <@300644159566381060>")
            elif r < 0.30:
                await message.channel.send("Ta gueule Jav")
            elif r < 0.40:
                await message.channel.send("menfou")
            else:
                await message.channel.typing()
                reponse = await ask_gpt(contenu)
                await message.channel.send(reponse)
        else:
            await message.channel.typing()
            reponse = await ask_gpt(contenu)
            await message.channel.send(reponse)
        return
    
    if message.content.lower().startswith("!verset"):
        await message.channel.typing()
        ayah = await get_random_ayah()
        await message.channel.send(ayah)
        return

    if message.content.lower().startswith("!sourate"):
        await message.channel.typing()
        titre, ayah_texts, full_texts, surah_number = await get_random_surah()
        for part in split_message(f"{titre} (N°{surah_number})\n{full_texts}"):
            await message.channel.send(part)
        return

    if message.content.lower().startswith("!hadith"):
        await message.channel.typing()
        hadith = await get_random_hadith()
        await message.channel.send(hadith)
        return

    if message.content.lower().startswith("!prière"):
        times = await get_prayer_times_aladhan()
        now = datetime.datetime.now().time()
        prochaine = None
        for nom in ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']:
            heure = parse_time(times[nom])
            if now < heure:
                prochaine = (nom, heure)
                break
        if prochaine:
            await message.channel.send(f"La prochaine prière est **{prochaine[0]}** à {prochaine[1].strftime('%H:%M')}.")
        else:
            await message.channel.send("Toutes les prières d'aujourd'hui sont passées.")
        return

    if "!dé" in message.content.lower():
        de1 = random.randint(1, 6)
        de2 = random.randint(1, 6)
        await message.channel.send(f"🎲 Tu as lancé : {de1} et {de2} !")
        return

    if "!nombre" in message.content.lower():
        nombre = random.randint(1, 10)
        await message.channel.send(f"🔢 Le nombre aléatoire est : {nombre} !")
        return
    
    if (
        any(mot in contenu for mot in ('goulth', 'pouyol', 'bouyol', 'groulth')) 
        or any(user.id == 206010121371779073 for user in message.mentions)
    ):
        r = random.random()
        if r < 0.10:
            await message.channel.send('Je suis le Goulth')
        elif r < 0.20:
            await message.channel.send("Tititititi")
        elif r < 0.30:
            await message.channel.send('Ah oui ah oui heiiiiiiin')
        return

    if (
        any(mot in contenu for mot in ('teuteu', 'teutgem',)) 
        or any(user.id == 516681520669523979 for user in message.mentions)
    ):
        r = random.random()
        if r < 0.10:
            await message.channel.send('Monsieur <@516681520669523979>, vous avez été mentionné')
        elif r < 0.20:
            await message.channel.send("Fiiiiiiiiin")
        return

    if message.author.id == 206010121371779073:
        r = random.random()
        if r < 0.10:
            await message.channel.send('Le <@206010121371779073> a parlé')
        return

    if message.author.id == 252789076229488640:
        r = random.random()
        if r < 0.10:
            await message.channel.send('Ouiii Quentiti')
        return

    if message.author.id == 300644159566381060:
        r = random.random()
        if r < 0.10:
            await message.channel.send('Ping le nul<@300644159566381060>')
        return

    if message.channel.id != GAME_CHANNEL_ID:
        if contenu in reponses:
            await message.channel.send(reponses[contenu])
        return

# =============== Loop Lol ===============
@tasks.loop(minutes=3)
async def check_games():
    try:
        channel = await client.fetch_channel(GAME_CHANNEL_ID)
        for player in PLAYERS:
            if not player.puuid:
                continue
            platform = "euw1"
            region_api = "euw1"
            region_match = "europe"
            rank = await fetch_summoner_rank(player, region_api, RIOT_TOKEN)
            game = await fetch_current_game(player.puuid, platform, RIOT_TOKEN)
            if not game:
                continue
            game_id = game.get('gameId')
            if last_announced_game_ids.get(player.puuid) == game_id:
                continue
            if game_id:
                last_announced_game_ids[player.puuid] = game_id

            champion_id = game.get('championId')
            queue_type = game.get('queueType', 'Inconnue')
            if queue_type == "CLASSIC":
                queue_type = "Classée"
            elif queue_type == "ARAM":
                queue_type = "ARAM"
            elif queue_type == "CHERRY":
                queue_type = "ARENA"
            elif queue_type == "RUBY":
                queue_type = "DOOMBOT"

            # Trouver le nom du champion à partir de l'ID
            champion_name = None
            for name, cid in CHAMPION_NAME_TO_ID.items():
                if cid == champion_id:
                    champion_name = name
                    break
            champion_name_fixed = CHAMPION_NAME_FIX.get(champion_name, champion_name)

            if champion_id is None or champion_name is None:
                winrate = "N/A"
            else:
                winrate = await fetch_winrate(player.puuid, champion_id, region_match, RIOT_TOKEN)

            if champion_name_fixed:
                champion_image_url = f"https://ddragon.leagueoflegends.com/cdn/14.12.1/img/champion/{champion_name_fixed.replace(' ', '')}.png"
            else:
                champion_image_url = None

            embed = discord.Embed(title="Une bête vient de lancer")
            embed.add_field(name="Summoner", value=player.gameName, inline=True)
            embed.add_field(name="File", value=queue_type or "Inconnue", inline=True)
            embed.add_field(name="Champion", value=champion_name_fixed or "Inconnu", inline=True)
            embed.add_field(name="Elo", value=rank or "Unranked", inline=True)
            embed.add_field(name="Winrate sur ce champion", value=winrate or "Inconnue", inline=True)

            if champion_image_url:
                embed.set_thumbnail(url=champion_image_url)

            await channel.send(embed=embed)
    except Exception as e:
        log(f"Erreur dans check_games: {e}")
        
# =============== Loop prière ===============
@tasks.loop(minutes=1)
async def prayer_reminder():
    try:
        now = datetime.datetime.now()
        times = await get_prayer_times_aladhan()
        prayers = ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']
        for prayer in prayers:
            prayer_time_str = times.get(prayer)
            if not prayer_time_str:
                continue
            prayer_time = parse_time(prayer_time_str)
            reminder_dt = (datetime.datetime.combine(now.date(), prayer_time) - datetime.timedelta(minutes=PRAYER_ADVANCE_MINUTES))
            if now.hour == reminder_dt.hour and now.minute == reminder_dt.minute:
                log(f"Pour {prayer}: rappel à {reminder_dt.strftime('%H:%M')}, il est {now.strftime('%H:%M')}")
                for user_id in USER_IDS_TO_NOTIFY:
                    log(f"Tentative d'envoi à {user_id}")
                    user = await client.fetch_user(user_id)
                    await user.send(f"⏰ Rappel : {prayer} dans {PRAYER_ADVANCE_MINUTES} minutes environ inshaAllah ! Regarde ton téléphone ")
    except Exception as e:
        log(f"Erreur dans prayer_reminder: {e}")

# =============== Loop Hadith ===============

@tasks.loop(minutes=1)
async def daily_hadith():
    now = datetime.datetime.now()
    if now.hour == 8 and now.minute == 0:
        for user_id in USER_IDS_HADITH:
            hadith = random.choice(HADITHS_LOCAL)
            user = await client.fetch_user(user_id)
            log(f"Envoi du hadith à {user_id} à {now.strftime('%H:%M')}")
            await user.send(f"🕌 {hadith}")

# =============== Loop Versets ===============

@tasks.loop(minutes=1)
async def daily_ayah():
    now = datetime.datetime.now()
    if now.hour == 8 and now.minute == 0:
        ayah = await get_random_ayah()
        for user_id in USER_IDS_HADITH:
            user = await client.fetch_user(user_id)
            log(f"Envoi du verset à {user_id} à {now.strftime('%H:%M')}")
            await user.send(f"🕌 {ayah}")

# =============== Loop Sourates ===============

@tasks.loop(minutes=1)
async def daily_surah():
    now = datetime.datetime.now()
    if now.hour == 8 and now.minute == 0:
        titre, ayah_texts, full_texts, surah_number = await get_random_surah()
        for user_id in USER_IDS_HADITH:
            user = await client.fetch_user(user_id)
            log(f"Envoi de la sourate à {user_id} à {now.strftime('%H:%M')}")
            for part in split_message(f"🕌 {titre} (N°{surah_number})\n{full_texts}", max_length=2000):
                await user.send(part)

@client.event
async def on_ready():
    await fetch_puuids()
    if not check_games.is_running():
        check_games.start()
    if not prayer_reminder.is_running():
        prayer_reminder.start()
    if not daily_hadith.is_running():
        daily_hadith.start()
    if not daily_surah.is_running():
        daily_surah.start()
    asyncio.create_task(auto_update())

# =============== Mise à jour automatique du bot ===============

async def auto_update(interval_minutes=60):
    await asyncio.sleep(10)  
    while True:
        await asyncio.sleep(interval_minutes * 60)
        log("Vérification des mises à jour...")
        result = subprocess.run(['git', 'pull'], capture_output=True, text=True)
        log(result.stdout)
        if "Already up to date." not in result.stdout:
            log("Mise à jour détectée, redémarrage du bot...")
            os.execv(sys.executable, [sys.executable] + sys.argv)

# =============== LANCEMENT DU BOT ===============
client.run(os.getenv('DISCORD_TOKEN'))