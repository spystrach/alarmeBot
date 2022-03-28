#!/usr/bin/env python
# -*- coding: utf-8 -*-
## ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ##
##																				   ##
##  ----  ----  ----             TESTS BOT TELEGRAM              ----  ----  ----  ##
##																				   ##
## ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ##

## programme de test du bot telegram

## ~~~~~~~~~~~~~~~~~~~~~~~~~~        PARAMETRES         ~~~~~~~~~~~~~~~~~~~~~~~~~~ ##

# modules complémentaires
import os
import sys
import unittest
import datetime
from uuid import uuid4

# fonctions a tester
from alarmeBot import send_alerts, job_detection_ir, obj_bdd, job_nettoyage_bdd, Exit

# dossiers du projet
BASEPATH = os.path.realpath(os.path.dirname(sys.argv[0]))

# base de donnée de test
TEST_DB_PATH = os.path.join(BASEPATH, "test_data.db")
TEST_DB_NAME = "alertes"

# simule un CallbackContext
class MockContext:
    def __init__(self, test_db_path, test_db_name):
        # partie bot
        class MockBot:
            # MockUp de la fonction context.bot.send_message
            def mock_send_message(*args, **kwargs):
                pass
            send_message = mock_send_message
        self.bot = MockBot()
        # partie job
        class MockJob:
            context = [
                ["authorized_accounts"],        # authorized_accounts
                ["active_accounts"],            # active_accounts
                ["00:00", "00:00"],             # horaires_alertes
                False,  # current_state
                datetime.timedelta(minutes=2),  # time_rappel
                datetime.timedelta(minutes=5),  # time_latence
                (test_db_path, test_db_name),
            ]
        self.job = MockJob()

## ~~~~~~~~~~~~~~~~~~~~~~~~~~~   CLASSES DE TESTS    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ##

# tests des envois des alertes
class TestSendAlerts(unittest.TestCase):
    # initialisation de la classe de test
    @classmethod
    def setUpClass(self):
        # MockUp de la fonction context.bot.send_message
        def mock_send_message(*args, **kwargs):
            pass
        self.mock_send_message = mock_send_message
        # temp présent du test jour/mois/année, 17h 44
        now = datetime.datetime.now()
        self.now = datetime.datetime(
            year=now.year, month=now.month, day=now.day, hour=17, minute=44)
    # horaires d'alerte dans le sens croissant, doit envoyer une alerte
    def test_horaire_toujours(self):
        # horaires : tout le temps
        horaires = [datetime.time(hour=0), datetime.time(hour=0, minute=0)]
        self.assertIs(
            send_alerts(
                self.mock_send_message,
                [""],
                "super texte",
                self.now,
                horaires,
            ),
            True,
        )
    # horaires d'alerte dans le sens croissant, doit envoyer une alerte
    def test_horaire_croissant_inside(self):
        # horaires de 16h à 20h 30
        horaires = [datetime.time(hour=16), datetime.time(hour=20, minute=30)]
        self.assertIs(
            send_alerts(
                self.mock_send_message,
                [""],
                "super texte",
                self.now,
                horaires,
            ),
            True,
        )
    # horaires d'alerte dans le sens croissant, ne doit pas envoyer une alerte
    def test_horaire_croissant_outside(self):
        # horaires de 10h à 16h 30
        horaires = [datetime.time(hour=10), datetime.time(hour=16, minute=30)]
        self.assertIs(
            send_alerts(
                self.mock_send_message,
                [""],
                "super texte",
                self.now,
                horaires,
            ),
            False,
        )
    # horaires d'alerte dans le sens décroissant, doit envoyer une alerte
    def test_horaire_decroissant_inside(self):
        # horaires de 16h à 7h 30
        horaires = [datetime.time(hour=16), datetime.time(hour=7, minute=30)]
        self.assertIs(
            send_alerts(
                self.mock_send_message,
                [""],
                "super texte",
                self.now,
                horaires,
            ),
            True,
        )
    # horaires d'alerte dans le sens décroissant, ne doit pas envoyer une alerte
    def test_horaire_decroissant_outside(self):
        # horaires de 19h à 7h 30
        horaires = [datetime.time(hour=19), datetime.time(hour=7, minute=30)]
        self.assertIs(
            send_alerts(
                self.mock_send_message,
                [""],
                "super texte",
                self.now,
                horaires,
            ),
            False,
        )

# tests de la detection IR
class TestDetectionIr(unittest.TestCase):
    # initialisation de la classe de test
    @classmethod
    def setUpClass(self):
        self.mock_context = MockContext(TEST_DB_PATH, TEST_DB_NAME)
        # temp présent du test jour/mois/année, 17h 44
        self.now = datetime.datetime.now()
        with obj_bdd(TEST_DB_PATH, TEST_DB_NAME) as temp_bdd:
            pass
    # suppression de la base de test à la fin de la classe
    @classmethod
    def tearDownClass(self):
        os.remove(TEST_DB_PATH)
    # pas d'alerte courante ni instantané
    def test_instant_False_current_False(self):
        self.assertIs(
            job_detection_ir(
                self.mock_context,  # le faux contexte
                False,             # le faux état instantané
            )[3],
            False,
        )
    # pas d'alerte courante, alerte instantané, l'alerte courante est crée
    def test_instant_True_current_False(self):
        data = job_detection_ir(
            self.mock_context,  # le faux contexte
            True,             # le faux état instantané
        )
        self.assertIs(
            type(data[3]),
            list,
        )
        for k in data[3]:
            self.assertIs(
                type(k),
                datetime.datetime,
            )
    # alerte courante, alerte instantané, l'alerte courante est modifée mais pas de rappel envoyé
    def test_instant_True_current_True_modify_below_timerappel(self):
        temp_context = self.mock_context
        temp_context.job.context[3] = [
            self.now - temp_context.job.context[4]
            + datetime.timedelta(seconds=5),  # début
            # dernier rappel
            self.now - \
            temp_context.job.context[4] + datetime.timedelta(seconds=5),
            # dernier signal positif
            self.now - \
            temp_context.job.context[4] + datetime.timedelta(seconds=5),
        ]
        data = job_detection_ir(
            temp_context,   # le faux contexte
            True,           # le faux état instantané
        )
        self.assertIs(
            type(data[3]),
            list,
        )
        for k in data[3]:
            self.assertIs(
                type(k),
                datetime.datetime,
            )
        # la date du début et du dernier rappel sont inchangées mais pas la date du dernier signal positif
        self.assertEqual(
            self.now
            - temp_context.job.context[4] + datetime.timedelta(seconds=5),
            data[3][0],
        )
        self.assertEqual(
            self.now
            - temp_context.job.context[4] + datetime.timedelta(seconds=5),
            data[3][1],
        )
        self.assertNotEqual(
            self.now
            - temp_context.job.context[4] + datetime.timedelta(seconds=5),
            data[3][2],
        )
    # alerte courante, alerte instantané, l'alerte courante est modifée et un rappel envoyé
    def test_instant_True_current_True_modify_above_timerappel(self):
        temp_context = self.mock_context
        temp_context.job.context[3] = [
            self.now - temp_context.job.context[4]
            - datetime.timedelta(seconds=5),  # début
            # dernier rappel
            self.now - \
            temp_context.job.context[4] - datetime.timedelta(seconds=5),
            # dernier signal positif
            self.now - \
            temp_context.job.context[4] - datetime.timedelta(seconds=5),
        ]
        data = job_detection_ir(
            temp_context,   # le faux contexte
            True,           # le faux état instantané
        )
        self.assertIs(
            type(data[3]),
            list,
        )
        for k in data[3]:
            self.assertIs(
                type(k),
                datetime.datetime,
            )
        # la date du début est inchangée mais pas les dates du dernier rappel et du dernier signal positif
        self.assertEqual(
            self.now
            - temp_context.job.context[4] - datetime.timedelta(seconds=5),
            data[3][0],
        )
        self.assertNotEqual(
            self.now
            - temp_context.job.context[4] - datetime.timedelta(seconds=5),
            data[3][1],
        )
        self.assertNotEqual(
            self.now
            - temp_context.job.context[4] - datetime.timedelta(seconds=5),
            data[3][2],
        )
    # alerte courante, alerte instantané, l'alerte courante est maintenue
    def test_instant_False_current_True_modify_below_timelatence(self):
        temp_context = self.mock_context
        temp_context.job.context[3] = [
            self.now - temp_context.job.context[5]
            + datetime.timedelta(seconds=5),  # début
            # dernier rappel
            self.now - \
            temp_context.job.context[5] + datetime.timedelta(seconds=5),
            # dernier signal positif
            self.now - \
            temp_context.job.context[5] + datetime.timedelta(seconds=5),
        ]
        data = job_detection_ir(
            temp_context,   # le faux contexte
            False,           # le faux état instantané
        )
        self.assertIs(
            type(data[3]),
            list,
        )
        for k in data[3]:
            self.assertIs(
                type(k),
                datetime.datetime,
            )
        # toutes les dates sont inchangées
        self.assertEqual(
            self.now
            - temp_context.job.context[5] + datetime.timedelta(seconds=5),
            data[3][0],
        )
        self.assertEqual(
            self.now
            - temp_context.job.context[5] + datetime.timedelta(seconds=5),
            data[3][1],
        )
        self.assertEqual(
            self.now
            - temp_context.job.context[5] + datetime.timedelta(seconds=5),
            data[3][2],
        )
    # alerte courante, alerte instantané, l'alerte courante est annulée
    def test_instant_False_current_True_modify_above_timelatence(self):
        temp_context = self.mock_context
        temp_context.job.context[3] = [
            self.now - temp_context.job.context[5]
            - datetime.timedelta(seconds=5),  # début
            # dernier rappel
            self.now - \
            temp_context.job.context[5] - datetime.timedelta(seconds=5),
            # dernier signal positif
            self.now - \
            temp_context.job.context[5] - datetime.timedelta(seconds=5),
        ]
        data = job_detection_ir(
            temp_context,   # le faux contexte
            False,           # le faux état instantané
        )
        self.assertIs(
            data[3],
            False,
        )

# tests du nettoyage de la base de donnée
class TestNettoyageBdd(unittest.TestCase):
    # initialisation de la classe de test
    @classmethod
    def setUpClass(self):
        self.mock_context = MockContext(TEST_DB_PATH, TEST_DB_NAME)
        with obj_bdd(TEST_DB_PATH, TEST_DB_NAME) as temp_bdd:
            pass
    # suppression de la base de test à la fin de la classe
    @classmethod
    def tearDownClass(self):
        os.remove(TEST_DB_PATH)
    # initialisation pour chaque test
    def setUp(self):
        temp_time = datetime.datetime.now()
        with obj_bdd(TEST_DB_PATH, TEST_DB_NAME) as temp_bdd:
            t = temp_time - datetime.timedelta(days=7, minutes=5)
            temp_bdd.create(["007", t, t+datetime.timedelta(minutes=5)])
            t = temp_time - datetime.timedelta(days=7) + datetime.timedelta(minutes=5)
            temp_bdd.create_random_pk([t, t+datetime.timedelta(minutes=5)])
            t = temp_time - datetime.timedelta(days=5, hours=3)
            temp_bdd.create_random_pk([t, t+datetime.timedelta(minutes=5)])
    # supprime les entrées vieilles de plus d'une semaine
    def test_delete_old_entries(self):
        deleted = job_nettoyage_bdd(self.mock_context)
        with obj_bdd(TEST_DB_PATH, TEST_DB_NAME) as temp_bdd:
            data = temp_bdd.getDatas("all")
        self.assertEqual(
            len(data),
            2,
        )
        self.assertEqual(
            deleted[0][0],
            "007",
        )

# fin
