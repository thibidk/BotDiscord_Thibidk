# Bot Discord Multi-Fonctions (LoL, OpenAI, Prières, etc.)

## Description

Ceci est mon premier projet sur Python, sans but particulier j'ai implanté des fonctionnalités qui pourrait être utile à moi et mes amis sur notre serveur discord. Je rajoute des fonctionnalités lorsque nous avons une idée. 

Ce bot Discord propose :
- Suivi de parties League of Legends (récupération du rang, champion, winrate, etc.), Attention, je n'ai pas réussi à récupérer l'élo du joueur.
- Commandes diverses comme `!dé` pour lancer deux dés aléatoires.
- Réponses personnalisées selon les messages ou mentions.
- Chat IA avec OpenAI (texte et images, si tu as accès à GPT-4o via API openAI)
- Rappel des horaires de prières (Strasbourg mais reste modidifiable via l'API)
- Réponses aux messages privés (texte et images)

---

## Installation

### 1. **Cloner le projet**
```sh
git clone https://github.com/thibidk/Tibidk.git
cd BotDiscord
```

### 2. **Installer les dépendances**
```sh
pip install -r requirements.txt
```
> Si tu n’as pas de `requirements.txt`, installe :
> pip install discord.py aiohttp requests python-dotenv openai

> Version python 3.13

### 3. **Créer un fichier .env

Exemple de mon contenu :

- DISCORD_TOKEN=ton_token_discord (à récupérer lors de la création du Bot discord)
- RIOT_TOKEN=ta_cle_riot (à générer sur le site Riot API)
- OPENAI_API_KEY=ta_cle_openai (à récupérer sur le site openAI)
- GAME_CHANNEL_ID=ID_du_channel (clic droit copier l'identifiant du salon)
- GENERAL_CHANNEL_ID=ID_du_channel (clic droit copier l'identifiant du salon)


### 4. **Lancer le bot**
```sh
python botlol.py
```

---

## Fonctionnalités principales

- **!dé** : Lance deux dés (1 à 6) et affiche le résultat.
- **Suivi LoL** : Annonce automatiquement quand un joueur de la liste lance une partie.
- **Chat IA** : Mentionne le bot ou parle-lui en DM pour une réponse IA (texte ou image).
- **Réponses personnalisées** : Blagues, réponses à certains pseudos, interactions selon certaines mots... 
- **Rappel de prières** : Envoie un rappel en DM avant chaque prière (Strasbourg). Possibilité de changer les DM par un channel discord.

---

## Personnalisation

- **Ajouter/retirer des joueurs LoL** : Modifie la liste `PLAYERS` dans `botlol.py`.
- **Changer les channels** : Modifie les IDs dans le `.env`.
- **Modifier les réponses du bot** : Change le dictionnaire `reponses` ou les conditions dans `on_message`.

---

## Dépendances

- `discord.py`
- `aiohttp`
- `requests`
- `python-dotenv`
- `openai`

---

## Remarques

- Pour utiliser l’API OpenAI, il te faut une clé valide et du crédit sur ton compte.
- Pour l’API Riot, la clé de développement doit être régénérée toutes les 24h (sauf clé production).
- Pour l’hébergement 24/7, utilise un VPS ou un service cloud.


## Auteur
Leclerc Thibault
> Adapté et structuré avec l'aide de GitHub Copilot 
