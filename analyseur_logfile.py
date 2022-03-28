#!/n'importe ou/python
# -*-coding:utf-8 -*
## ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ##
##                                                                                       ##
##  ----  ----  ----               analyseur de log file               ----  ----  ----  ##
##                                                                                       ##
## ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ##

# analyseur de fichier log de la Fee FeeClochette_v2
## version 1, compiled 31/03/2019
## created by MGL 12.7 An 217

# NOM DU FICHIER A ANALYSER
name = "OLDlogFile24h"

## ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~        PARAMETRES       ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ##

# modules complementaires
import matplotlib.pyplot as plt
import numpy as np

# le dossier racine du programme
path = "/home/margoulin/Documents/FeeClochette_v2"
#path = "/home/margoulin/Bureau"

# dictionnaire principal de toutes les heures de la journee
dictHoraires = {}

# buffer des horaires issu du fichier
buffer = []

# creation de tous les dictionnaires d'heures
for k in range(24):
    dictHoraires["h"+str(k)] = {}
    for i in range(4):
        dictHoraires["h"+str(k)][i] = 0

#les listes pour tracer le diagramme
Abcisse = []
Valeur = []

## ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~   IMPORTER LE LOGFILE   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ##

# on importe le logfile dans une grande liste
file = open(path+"/"+name+".txt","r")
for lignes in file:#
    if lignes[:1] == "/":
        titreDuGraphe = lignes[1:-1]
    elif lignes[:1] != "#" and lignes != "\n":
        buffer.append([lignes[:5],lignes[7:-1]])
file.close()

## ~~~~~~~~~~~~~~~~~~~~~~~~~~~ REMPLISSAGE DU DICTIONNAIRE ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ##

# on importe tous les elements du buffer dans le dictionnaire dictHoraires
for i in buffer:
    #initialisation des increment avec les heures et minutes de debut
    incrementHeure = int(i[0][:2])
    incrementMinute = int(i[0][3:])

    while incrementHeure <= int(i[1][:2]) and incrementMinute <= int(i[1][3:]):

        # on incremente les valeurs du dico si la valeur en cours est dans le 1/4h correspondant
        if incrementMinute < 15:
            dictHoraires["h"+str(incrementHeure)][0] += 1
        elif incrementMinute < 30:
            dictHoraires["h"+str(incrementHeure)][1] += 1
        elif incrementMinute < 45:
            dictHoraires["h"+str(incrementHeure)][2] += 1
        else:
            dictHoraires["h"+str(incrementHeure)][3] += 1

        #on passe à la minute suivante
        if incrementMinute < 59:
            incrementMinute += 1
        else:
            incrementMinute = 0
            incrementHeure += 1

## ~~~~~~~~~~~~~~~~~~~~~~~~~~~         HISTOGRAMME         ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ##

# remplissage des listes de tracage
for k in range(24):
    for i in range(4):
        Abcisse.append(k + float(i)/4)
        Valeur.append(dictHoraires["h"+str(k)][i])

# dessin du graphe
for h in range(0,96,4):
    #si nombre pair, on trace en bleu
    if Abcisse[h]%2 == 0:
        plt.bar(Abcisse[h:h+4], Valeur[h:h+4], width=0.25, color="r", align='edge')
    #si nombre impair, on trace en bleu
    else:
        plt.bar(Abcisse[h:h+4], Valeur[h:h+4], width=0.25, color="b", align='edge')

# les titres des axes, legendes, etc
plt.xlabel("heures")
plt.xlim(0,24)
plt.xticks([k for k in range(25)],[str(k) for k in range(25)])
plt.ylabel("activite en minute")
plt.ylim(0,15)
plt.yticks([k for k in range(16)],[str(k) for k in range(16)])
plt.title("activite detecte par la Fee Clochette au cours de la journee")
plt.show()
