#!/usr/bin/env python
# -*- coding: utf-8 -*-
## ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ##
##																				   ##
##  ----  ----  ----        BOT TELEGRAM ALARME ET CAMERA        ----  ----  ----  ##
##																				   ##
## ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ##

## programme pour détecter via Telegram du mouvement et prendre des photos des intrus

## ~~~~~~~~~~~~~~~~~~~~~~~~~~        PARAMETRES         ~~~~~~~~~~~~~~~~~~~~~~~~~~ ##

# modules complémentaires
import os
import sys
from re import compile as reCompile
from datetime import datetime, timedelta, time
from functools import partial
from hashlib import md5
from yaml import load as yaml_load, FullLoader as yaml_FullLoader
from telegram.ext import Updater, CommandHandler

# le temps de latence avant de re-vérifier l'état du détecteur IR
TIMEOUT = timedelta(seconds=3)
# le temps sans detection pour considerer l'endroit vide'
TIMELATENCE = timedelta(minutes=2)
# le temps depuis le début de l'alerte pour renvoyer un rappel d'alerte
TIMERAPPEL = timedelta(seconds=5)

# dossiers du projet
BASEPATH = os.path.realpath(os.path.dirname(sys.argv[0]))
# chemin vers la base de donnée
BDD_PATH = os.path.join(BASEPATH, "data.db")
# table de la base de donnée
BDD_TABLE = "alertes"
# configuration du .env
REGEX_TOKEN = reCompile("token=[0-9]{8,10}:[a-zA-Z0-9_-]{35}")

# les erreurs critiques
class Exit(Exception):
    pass

## ~~~~~~~~~~~~~~~~~~~~~~~~~~	  GESTION DU SQL	   ~~~~~~~~~~~~~~~~~~~~~~~~~~ ##

# la classe qui va contenir la base de donnée
class obj_bdd():
	# fonction d'initialisation et de fermeture de la connection
	def __init__(self, FULLPATH, tableName):
		try:
			# curseur et connection de la base de donnée
			self._conn = sqlite3.connect(FULLPATH)
			self._cursor = self._conn.cursor()
			# vérification du nom de la table
			self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
			self.tableName = tableName
			listeTable = [k[0] for k in self.cursor.fetchall()]
			# si la table n'existe pas, on la crée
			if self.tableName not in listeTable:
				self.cursor.execute(f"CREATE TABLE IF NOT EXISTS '{BDD_TABLE}' ('id' TEXT PRIMARY KEY, 'heure_debut' TEXT, 'heure_fin' TEXT)")
			# enregistrement de la clef primaire
			self.primaryKey = None
			self.cursor.execute(f"PRAGMA table_info({self.tableName})")
			for k in self.cursor.fetchall():
				if k[-1]:
					self.primaryKey = k[1]
					self.primaryKeyIndex = k[0]
					break
			if self.primaryKey is None:
				raise Exit(f"[!] la table '{self.tableName}' de la base de données '{FULLPATH}' n'a pas de clef primaire")
		# le chemin spécifié ne renvois vers rien
		except sqlite3.OperationalError:
			raise Exit(f"[!] la base de donnée '{FULLPATH}' est introuvable") # jamais trigger car connect crée automatiquement un fichier

	# interaction possible avec un 'with'
	def __enter__(self):
		return self

	# interaction possible avec un 'with'
	def __exit__(self, exc_type, exc_val, exc_tb):
		self.save()
		self.close()

	# interaction entre les variables privée et les "getters"
	@property
	def connection(self):
		return self._conn
	@property
	def cursor(self):
		return self._cursor

	# récupere les noms des champs de la table
	def _namesColonnes(self):
		self.cursor.execute(f"PRAGMA table_info({self.tableName})")
		L = [k[1] for k in self.cursor.fetchall()]
		return L

	# renvois True si l'entrée de la clef primaire est bien présente dans la table
	def _verify(self, key, prefixe, suffixe):
		# si prefixe et suffixe valent False, la clef doit exactement etre présente
		if not prefixe and not suffixe:
			self.cursor.execute(f"SELECT {self.primaryKey} FROM {self.tableName} WHERE {self.primaryKey} LIKE '{key}'")
		# si seul prefixe vaut True, la clef doit seulement commencer pareil
		elif prefixe and not suffixe:
			self.cursor.execute(f"SELECT {self.primaryKey} FROM {self.tableName} WHERE {self.primaryKey} LIKE '{key}%'")
		# si seul suffixe vaut True, la clef doit seulement finir pareil
		elif not prefixe and suffixe:
			self.cursor.execute(f"SELECT {self.primaryKey} FROM {self.tableName} WHERE {self.primaryKey} LIKE '%{key}'")
		# si prefixe et suffixe valent True, la clef doit etre contenue
		else:
			self.cursor.execute(f"SELECT {self.primaryKey} FROM {self.tableName} WHERE {self.primaryKey} LIKE '%{key}%'")

		# resultat
		if self.cursor.fetchall() == []:
			return False
		else:
			return True

	# recuperer les infos pour une entrée de clef (primaire par défaut) donnée. Si c'est "all", renvoit la totalité des données de la table
	def getDatas(self, key, keyname=None, order="id"):
		if not keyname:
			keyname = self.primaryKey
		if key == "all":
			self.cursor.execute(f"SELECT * FROM {self.tableName} ORDER BY {order} ASC")
			return self.cursor.fetchall()
		else:
			self.cursor.execute(f"SELECT * FROM {self.tableName} WHERE {keyname} LIKE '{key}' ORDER BY {order} ASC")
			return self.cursor.fetchone()

	# ajoute une nouvelle entrée dans la base de données
	def create(self, valeurs, lower=True):
		nomsColonnes = self._namesColonnes()
		if len(valeurs) != len(nomsColonnes):
			raise Exit(f"[!] les arguments {valeurs} ne correspondent pas au colonnes {nomsColonnes}")
		# on vérifie que l'entrée n'existe pas déja
		if not self._verify(valeurs[self.primaryKeyIndex], False, False):
			text = f"INSERT INTO {self.tableName}("
			for k in nomsColonnes:
				text += f"{k},"
			text = f"{text[:-1]}) VALUES("
			for k in valeurs:
				if k == "NULL":
					text += "NULL,"
				elif lower:
					text += f"'{str(k).lower()}',"
				else:
					text += f"'{k}',"
			text = f"{text[:-1]})"
			try:
				self.cursor.execute(text)
			except sqlite3.OperationalError as e:
				raise Exit(f"[!] erreur dans l'opération : {e}")
		else:
			raise Exit(f"[!] {self.primaryKey} = {valeurs[self.primaryKeyIndex]}, cette entrée existe déjà")

	# supprime une entrée en la selectionnant avec la clef primaire
	def delete(self, key):
		# on vérifie que l'entrée existe
		if self._verify(key, False, False):
			self.cursor.execute(f"DELETE FROM {self.tableName} WHERE {self.primaryKey}='{key}'")
		else:
			raise Exit(f"[!] {self.primaryKey} = {key}, pas d'entrée corespondante")

	# modifie une entrée en la selectionnant avec la clef primaire (dans le champ valeurs)
	def modify(self, valeurs, lower):
		nomsColonnes = self._namesColonnes()
		if len(valeurs) != len(nomsColonnes):
			raise Exit(f"[!] les arguments {valeurs} ne correspondent pas au colonnes {nomsColonnes}")
		# on vérifie que l'entrée existe
		if self._verify(valeurs[self.primaryKeyIndex], False, False):
			text = f"UPDATE {self.tableName} SET"
			for k in range(len(nomsColonnes)):
				if lower:
					text += f" {nomsColonnes[k]}='{str(valeurs[k]).lower()}',"
				else:
					text += f" {nomsColonnes[k]}='{valeurs[k]}',"
			text = f"{text[:-1]} WHERE {self.primaryKey} = '{valeurs[self.primaryKeyIndex]}'"
			try:
				self.cursor.execute(text)
			except sqlite3.OperationalError as e:
				raise Exit(f"[!] erreur dans l'opération : {e}")
		else:
			raise Exit(f"[!] {self.primaryKey} = {valeurs[self.primaryKeyIndex]}, pas d'entrée correspondante")

	# sauvegarde la base de donnée
	def save(self):
		self.connection.commit()

	# ferme la base de donnée
	def close(self):
		self.cursor.close()
		self.connection.close()


## ~~~~~~~~~~~~~~~~~~~~~~~~~~    HARDWARE RASPBERRY     ~~~~~~~~~~~~~~~~~~~~~~~~~~ ##

# renvoit True si la plateformee st un raspberry pi
def is_raspberrypi():
    try:
        with io.open('/sys/firmware/devicetree/base/model', 'r') as m:
            if 'raspberry pi' in m.read().lower(): return True
    except Exception: pass
    return False

# envoit à tous les utilisateurs actifs un message
def send_alerts(func, liste_ids, message, now, horaires):
    send = False
    # si on envoit tout le temps des alertes
    if horaires[0] == horaires[1]:
        send = True

    # si le 1er argument est plus petit que le 2ème, la période est donc dans le bon sens
    elif horaires[0] < horaires[1]:
        if horaires[0] < now.time() and now.time() < horaires[1]:
            send = True
    # sinon on compare par rapport à minuit
    else:
        temp_horaire_0 = datetime(
            year=now.year, month=now.month, day=now.day,
            hour=horaires[0].hour, minute=horaires[0].minute)
        temp_horaire_1 = datetime(
            year=now.year, month=now.month, day=now.day,
            hour=horaires[1].hour, minute=horaires[1].minute) + timedelta(days=1)
        if temp_horaire_0 < now and now < temp_horaire_1:
            send = True

    # envoit les messages s'il le faut
    if send:
        for k in liste_ids:
            func(chat_id=k, text=message)
    # renvoit l'action réalisé (pour les tests)
    return send

# job qui vérifie l'état de la détection et envoi les alertes appropriées
def job_detection_ir(context, test_instant_state=None):
    # context.job.context est une liste qui contient les élements suivants
    # - 0 : authorized_accounts
    # - 1 : active_accounts
    # - 2 : horaires_alertes
    # - 3 : current_state
    # - 4 : time_rappel
    # - 5 : time_latence

    # test_instant_state est une variable de test, pour changer la valeur de instant_state
    # instant_state = 1 -> le capteur détecte une présence
    if test_instant_state is None:
        if not TESTING_MODE:
            instant_state = bool(GPIO.input(NUMERO_PIN_IR))
        else:
            with open(os.path.join(BASEPATH, "input.txt"), "r") as f:
                instant_state = bool(int(f.read()[0]))
    else:
        instant_state = test_instant_state
    # le temps actuel
    now = datetime.now()

    # si le capteur IR detecte du mouvement
    if instant_state:
        # si c'est un front montant
        if context.job.context[3] is False:
            # envoi du message d'alerte
            send_alerts(
                context.bot.send_message,
                context.job.context[1],
                "alerte !",
                now,
                context.job.context[2],
            )
            # enregistrement de l'alerte
            context.job.context[3] = [now, now, now]

        # si l'alerte est toujours en cours
        else:
            # met à jour le timestamp de la fin de l'alerte
            context.job.context[3][2] = now
            # si cela fait plus de time_rappel
            if now - context.job.context[3][1] > context.job.context[4]:
                send_alerts(
                    context.bot.send_message,
                    context.job.context[1],
                    f"mouvement détectés depuis {str(now - context.job.context[3][0])[:-7]}",
                    now,
                    context.job.context[2]
                )
                context.job.context[3][1] = now

    # si le capteur IR ne détecte pas du mouvement
    else:
        # si il y a une alerte en cours
        if context.job.context[3] is not False:
            # si cela fait plus de time_latence
            if now - context.job.context[3][2] > context.job.context[5]:
                send_alerts(
                    context.bot.send_message,
                    context.job.context[1],
                    f"fin de l'alerte",
                    now,
                    context.job.context[2]
                )
                # sauvegarde de l'alerte
                with obj_bdd(BDD_PATH, BDD_TABLE) as temp_bdd:
    				temp_bdd.create([
                        md5(f"{context.job.context[3][0]}_{context.job.context[3][1]}_{context.job.context[3][2]}"),
                        context.job.context[3][0],
                        context.job.context[3][2],
                    ])
                context.job.context[3] = False
    # renvoit l'action réalisé (pour les tests)
    return context.job.context


## ~~~~~~~~~~~~~~~~~~~~~~~~~~   FONCTIONS UTLITAIRES    ~~~~~~~~~~~~~~~~~~~~~~~~~~ ##

# renvoit la liste des utilsateurs autorisés
def load_authorized_accounts():
    with open(os.path.join(BASEPATH, "authorized_accounts.yml"), "r") as f:
        data = yaml_load(f, Loader=yaml_FullLoader)
    return data

# renvoit les horaires pour l'envoit des alertes
def load_horaires_alertes():
    with open(os.path.join(BASEPATH, "horaires_alertes.yml"), "r") as f:
        data = yaml_load(f, Loader=yaml_FullLoader)
    # transforme les str en time
    data = [datetime.strptime(k, "%H:%M").time() for k in data]
    return data

# nettoie la base de donnée
def job_netttoyage_bdd(context):
    with obj_bdd(BDD_PATH, BDD_TABLE) as temp_bdd:
        data = temp_bdd.getDatas()

## ~~~~~~~~~~~~~~~~~~~~~~~~~~       COMMANDES BOT       ~~~~~~~~~~~~~~~~~~~~~~~~~~ ##

# décorateur ne répondant que si l'utilisateur est autorisé
def verify_user(func):
    def inner(*args, **kwargs):
        # avec le 'partial' de functools, les arguments 'args' sont
        # - authorized_accounts
        # - active_accounts
        # - Update
        # - CallbackContext

        # vérifie le status
        if not args[2].effective_user.username in args[0]:
            # envoi le message de blocage
            args[2].message.reply_text("accès non autorisé")
        else:
            # les fonctions de commandes ont comme argument : Update, CallbackContext, authorized_accounts, active_accounts
            func(args[2], args[3], auth_acc=args[0], acti_acc=args[1])
    return inner

# fonction lancée par la commande '/start'
@verify_user
def start(update, context, auth_acc=[], acti_acc=[]):
    print("start", acti_acc)
    # envoi le message de bienvenue
    update.message.reply_text("Coucou !\nAppuis sur '/' pour voir les commandes disponibles")
    # enregistre l'utilisateur pour la réception des alertes
    register(auth_acc, acti_acc, update, context)
    # les arguments sont mis dans le même ordre que lors d'un appel avec 'partial'

# fonction lancé par la commande '/register'
@verify_user
def register(update, context, auth_acc=[], acti_acc=[]):
    if update.effective_user.id not in acti_acc:
        acti_acc.append(update.effective_user.id)
    update.message.reply_text("alertes activées")

# fonction lancé par la commande '/unregister'
@verify_user
def unregister(update, context, auth_acc=[], acti_acc=[]):
    if update.effective_user.id in acti_acc:
        acti_acc.remove(update.effective_user.id)
    update.message.reply_text("alertes désactivées")

# fonction lancée par la commande '/ping'
@verify_user
def ping(update, context, auth_acc=[], acti_acc=[]):
    # renvoit le message de statuts correct
    update.message.reply_text("pong")

# fonction lancée par la commande '/photo'
@verify_user
def photo(update, context, auth_acc=[], acti_acc=[]):
    # renvoit le récapitulatif
    update.message.reply_text(f"photo du {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    # renvoit la photo
    pass

# fonction lancée par la commande '/recap'
@verify_user
def recap(update, context, auth_acc=[], acti_acc=[]):
    # renvoit le récapitulatif
    update.message.reply_text("récapitulatif des dernières 24h")
    # renvoit l'image
    pass

# fonction lancée par la commande '/reload'
@verify_user
def reload(update, context, auth_acc=[], acti_acc=[]):
    # fichiers de configurations
    auth_acc = load_authorized_accounts()
    hora_ale = load_horaires_alertes()
    # renvoit la confirmation
    update.message.reply_text("fichiers de configurations rechargées")
    # stoppe le job de détection actuel
    context.job_queue.get_jobs_by_name("_job_detection_ir")[0].schedule_removal()
    # relance le job avec les nouveaux paramètres, le niveau d'alerte est réinitialisé
    context.job_queue.run_repeating(
        job_detection_ir,
        first=3,
        interval=TIMEOUT,
        name="_job_detection_ir",
        context=[auth_acc, acti_acc, hora_ale, False, TIMERAPPEL, TIMELATENCE],
    )

# affiche l'aide
@verify_user
def help(update, context):
    update.message.reply_text("""\
Commandes disponibles:
/register : active les alertes par message
/unregister : désactive les alertes par message
/ping : vérifie que le bot est en ligne et fonctionnel
/photo : envoi une photo
/recap : envoi le récapitulatif des dernières 24 heures
/reload : recharge les configurations (.yml)
/help : affiche l'aide""")

# affiche les erreurs rencontrés par le programme
def error(update, context):
    print(f"Update '{update}' \ncaused error '{context.error}'")


## ~~~~~~~~~~~~~~~~~~~~~~~~~~    FONCTION PRINCIPALE    ~~~~~~~~~~~~~~~~~~~~~~~~~~ ##

# la fonction principale du bot
def main():
    ##~~~ plateforme physique
    global TESTING_MODE
    if is_raspberrypi():
        # si la plateforme est un raspberry
        import RPi.GPIO as GPIO
        TESTING_MODE = False
        # numero du pin physique pour la detection infrarouge
        NUMERO_PIN_IR = 18
    else:
        print("\033[91m[!] PROGRAMME EN MODE TEST\033[00m")
        TESTING_MODE = True

    ##~~~ configurations du bot
    # récupere le token d'identitification dans le .env
    if os.path.isfile(os.path.join(BASEPATH, ".env")):
        with open(os.path.join(BASEPATH, ".env"), "r") as f:
            try:
                # création du bot avec son token d'authentification (retire le 'token=' du début)
                bot = Updater(REGEX_TOKEN.findall(f.read())[0][6:], use_context=True)
            except Exception as e:
                raise e
    else:
        raise Exit("[!] le fichier .env contenant le token d'identitification n'existe pas")
    # dialogue avec le détecteur IR
    if not TESTING_MODE:
        # utilisation de numeros de pins logiques
        GPIO.setmode(GPIO.BCM)
        # pas d'avertissement d'erreur en console
        GPIO.setwarnings(False)
        #initialisation du pin
        GPIO.setup(NUMERO_PIN_IR, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    # si mode de test, création du fichier de simulation de l'entrée RPI
    else:
        if not os.path.isfile(os.path.join(BASEPATH, "input.txt")):
            with open(os.path.join(BASEPATH, "input.txt"), "w+") as f:
                f.write("0")
    # fichier de configuration des comptes autorisés
    authorized_accounts = load_authorized_accounts()
    # fichier de configuration des horaires d'alertes
    horaires_alertes = load_horaires_alertes()

    ##~~~ constantes du runtime
    # les comptes actifs
    active_accounts = []
    # le stade courant de la détection IR
    #   qui vaut soit False s'il ne se passe rien
    #   soit [datetime début, datetime dernier rappel, datetime fin]
    current_state = False

    ##~~~ ajout des gestionnaires de jobs
    # la détection infrarouge
    bot.job_queue.run_repeating(
        job_detection_ir,
        first=0,
        interval=TIMEOUT,
        name="_job_detection_ir",
        context=[authorized_accounts, active_accounts, horaires_alertes, current_state, TIMERAPPEL, TIMELATENCE],
    )
    # le nettoyage de la base de donnée
    bot.job_queue.run_daily(
        job_netttoyage_bdd,
        name="_job_nettoyage_bdd",
    )

    ##~~~ ajout des gestionnaires de commande par ordre d'importance
    # la commande /start
    bot.dispatcher.add_handler(CommandHandler("start", partial(start, authorized_accounts, active_accounts)))
    # la commande /register
    bot.dispatcher.add_handler(CommandHandler("register", partial(register, authorized_accounts, active_accounts)))
    # la commande /unregister
    bot.dispatcher.add_handler(CommandHandler("unregister", partial(unregister, authorized_accounts, active_accounts)))
    # la commande /ping
    bot.dispatcher.add_handler(CommandHandler("ping", partial(ping, authorized_accounts, active_accounts)))
    # la commande /photo
    bot.dispatcher.add_handler(CommandHandler("photo", partial(photo, authorized_accounts, active_accounts)))
    # la commande /recap
    bot.dispatcher.add_handler(CommandHandler("recap", partial(recap, authorized_accounts, active_accounts)))
    # la commande /reload
    bot.dispatcher.add_handler(CommandHandler("reload", partial(reload, authorized_accounts, active_accounts)))
    # la commande /help
    bot.dispatcher.add_handler(CommandHandler("help", help))
    # gestion des erreurs
    bot.dispatcher.add_error_handler(error)

    # lance le bot
    bot.start_polling()
    # continue le programme jusqu'à la réception d'un signal de fin (par ex: CTRL-C)
    bot.idle()

# lance la fonction principale
if __name__ == "__main__":
    main()


# fin
