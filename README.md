# ALARMEBOT

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/python-telegram-bot)

![](photo_alarmeBot.svg)

Un bot telegram qui permet de faire detecteur de présence ! :fairy: :detective: :bell:

## protocole d'installation

Copier le dossier sur le serveur et créer un fichier **.env** qui va contenir le token d'identitification du bot.
```sh
# récupération du projet sur le serveur
gh repo clone spystrach/alarmeBot && cd alarmeBot
# ajoute le token
echo "token={TOKEN}" > .env
```
Il faut ensuite modifier les fichiers **authorized_accounts.yml** et **horaires_alertes.yml** afin d'y ajouter les nom d'utilisateurs qui seront autorisé a dialoguer et la plage horaire d'envoit des alertes. Puis lancer le conteneur docker avec :
```sh
# construit l'image et lance le docker
sh restartAlarmeBot.sh
```

## protocole de développement

Pour tester et améliorer le bot, il faut télécharger ce dossier en local, créer un environnement virtuel python et lancer le programme :
```sh
# récupération du projet
gh repo clone spystrach/musicaBot && cd musicaBot
# ajoute le token
echo "token={TOKEN}" > .env
# environnement virtuel de développement
python3 -m venv venv && source venv/bin/activate
# dépendances
pip3 install -r requirements_dev.txt
# lancer le programme
python3 alarmeBot.py
```

## protocole de mise à jour

Le script *alarmeBot_update.py* sert à mettre à jour le bot sur le serveur à partir du dossier distant. Il néccessite un **accès ssh fonctionnel** avec un empreinte ssh enregistrée et une installation locale pour le développement. Il faut ensuite ajouter le nom de l'utilisateur du serveur et le chemin vers le dossier alarmeBot :
```sh
# ajoute le nom d'utilisateur et le dossier d'alarmeBot du serveur
echo "username={USERNAME}" >> .env
echo "folder=~/{PATH}/{TO}/{MUSICABOT}" >> .env
# met à jour le bot
python3 alarmeBot_update.py
```

Il faut aussi modifier le chemin ligne 4 de *restartAlarmeBot.sh*

## à faire

- [ ] : ajouter photo du bot
- [x] : changer le module telepot par python-telegram-bot
- [ ] : gerer les logs avec une base de données
- [x] : gerer les mots de passe autrement qu'en clair sur un fichier texte
- [ ]  :faire une version en mixant la v1 et v2
- [ ] : faire un script permettant de tester le programme en simulant le detecteur
- [ ] : integrer un Dockerfile au projet
- [ ] : integrer une caméra au projet
- [ ] : ajouter des tests
- [x] : vérifier le statut de l'utilsateur avec un décorateur
