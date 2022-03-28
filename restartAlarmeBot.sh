# RECHARGE LE BOT

# navigue dans le bon dossier
cd && cd /home/`whoami`/Documents/alarmeBot

# stopppe le conteneur
docker stop alarme_bot_1

# supprime le conteneur
docker rm alarme_bot_1

# supprime l'image
docker image rm alarme_bot

# reconstruit l'image
docker build -t alarme_bot .

# lance le nouveau conteneur
docker run -d --name alarme_bot_1 alarme_bot

# fin
cd
