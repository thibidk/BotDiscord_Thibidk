# Bot Discord Multi-Fonctions (LoL, OpenAI, Prières, etc.)

## Description

Ceci est mon premier projet sur Python, sans but particulier j'ai implanté des fonctionnalités qui pourrait être utile à moi et mes amis sur notre serveur discord. Je rajoute des fonctionnalités lorsque nous avons une idée. 

Ce bot Discord propose :
- Suivi de parties League of Legends (récupération du rang, champion, winrate, etc.), Attention, je n'ai pas réussi à récupérer l'élo du joueur. L'embed discord n'est pas encore à jour, il y a seulement le strict minimum.
- Réponses personnalisées selon les messages ou mentions.
- Chat IA avec OpenAI (texte et images, si tu as accès à GPT-4o via API openAI, attention il faut payer pour avoir des tokens sur votre key, le bot ne pourra pas fournir de réponse s'il n'y a pas de token)
- Rappel des horaires de prières (Strasbourg mais reste modidifiable)
- Réponses aux messages privés (texte et images)
- Commandes diverses comme `!dé` pour lancer deux dés aléatoires.

---

## Installation

### 1. **Création du bot discord + récupération des API keys**
```sh
- Création via le portail développeur Discord pour obtenir un token
- Passer en mode développeur dans les paramètre de l'application discord 
- Récupération des API keys à placer plus tard dans un fichier .env (OpenAI, Riot Games et Discord token)
```

### 2. **Cloner le projet**
```sh
git clone https://github.com/thibidk/Tibidk.git
cd BotDiscord
```

### 2. **Installer les dépendances**
```sh
pip install -r requirements.txt (Pas encore effectif)
```
> Il faudra installer manuellement :
> pip install discord.py aiohttp requests python-dotenv openai

> Version python 3.13

### 3. **Créer un fichier .env**

Exemple de mon contenu :

- DISCORD_TOKEN=ton_token_discord (à récupérer lors de la création du Bot discord)
- RIOT_TOKEN=ta_cle_riot (à générer sur le site Riot developper portal)
- OPENAI_API_KEY=ta_cle_openai (à récupérer sur le site openAI)
- GAME_CHANNEL_ID=ID_du_channel (clic droit copier l'identifiant du salon)
- GENERAL_CHANNEL_ID=ID_du_channel (clic droit copier l'identifiant du salon)
- USER_IDS_TO_NOTIFY=USER_ID=USER_ID (clic droit sur une personne discord)

Pour les channels ainsi que user IDs, il est possible d'ajouter plusieurs ID de cette manière (attention aux virgules et aux espaces) : 

EXEMPLE_CHANNEL_ID=ID_du_channel_1,ID_du_channel_2,ID_du_channel_3  etc... pas d'espace, pas de ' et une virgule entre les IDS

### 4. **Changer le contenu du code**

Il vous faudra changer quelques paramètres pour que le bot vous soit utile comme par exemple :
-  **Pour la fonctionnalité Lol** : Remplacer les gamenames par les noms d'invocateurs de votre choix et les taglines par les # (EUW par exemple)
-  **Pour la fonctionnalité prière** : Il suffit de remplacer le lien Aladhan par celui de votre ville dans 
```sh
async def get_prayer_times_aladhan():
```
- **Possibilité de modifier l'heure du rappel** : Modifier le temps dans la variable PRAYER_ADVANCE_MINUTES
- **Possibilité d'ajouter des membres ou des channels dans le .env** : Coller l'ID (suivre l'exemple du .3)
- **Modifier les réponses du bot** : Change le dictionnaire `reponses` ou les conditions dans `on_message`.

### 5. **Lancer le bot**
```sh
python botlol.py
```
Ou run directement avec le bouton sur VCS

## Fonctionnalités principales

- **Chat IA** : Mentionne le bot ou parle-lui en DM pour une réponse IA (texte ou image).
- **Réponses personnalisées** : Blagues, réponses à certains pseudos, interactions selon certaines mots... 
- **Rappel de prières** : Envoie un rappel en DM avant chaque prière (Strasbourg). Possibilité de changer les DM par un channel discord.
- **Suivi LoL** : Annonce automatiquement quand un joueur de la liste lance une partie.
- **!dé** : Lance deux dés (1 à 6) et affiche le résultat.
---

## Dépendances

- `discord.py`
- `aiohttp`
- `requests`
- `python-dotenv`
- `openai`

---

## Attention pour ces fonctionnalités
Comme dis plus haut, 

- Pour utiliser l’API OpenAI, il te faut une clé valide et du crédit sur ton compte.
- Pour l’API Riot, la clé de développement doit être régénérée toutes les 24h (sauf clé production).
- Pour l’hébergement 24/7, utilise un VPS ou un service cloud.
- Pense à bien mettre les noms d'invocateurs+# des gens que te veux suivre
- Si le bot run sur un serveur attantion à ce que l'heure du serveur soit bien la même que la tienne sinon le rappel sera en décalé

## Auteur
Leclerc Thibault
> Adapté et structuré avec l'aide de GitHub Copilot 
