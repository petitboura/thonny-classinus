# thonny-classinus

Plugin Thonny qui ajoute un panneau Classinus a droite de l'editeur.

Etape 1 : connexion au compte Classinus (via le navigateur), puis une question
tapee dans le panneau et une reponse qui s'affiche au fil de l'eau.

Etape 2 : deux boutons, "Envoyer mon code" (fichier ouvert, partie selectionnee,
derniere erreur et sortie du programme) et "Expliquer cette erreur". Rien ne
part sans un clic de l'eleve. Le code est ajoute au message envoye a Classinus ;
les tailles maximales sont dans `defauts.json` (`max_code`, `max_sortie`).

Chaque message envoye commence par les consignes de `consignes.txt` : elles
disent a Classinus qu'il est dans Thonny, ce que font les boutons et comment
repondre (texte simple, code Python dans un bloc python). Modifier ce fichier
change le comportement de Classinus dans Thonny, sans toucher au code.

Etape 3 : sous chaque bloc de code de la reponse, "Copier", "Inserer" (l'eleve
valide, puis Ctrl+Z annule) et "Nouvel onglet" (le code s'ouvre dans un onglet
non enregistre). Le lancement du script reste le bouton vert de Thonny.

Boutons du panneau : "Envoyer mon code", "Corriger mon code", "Expliquer cette
erreur", "Expliquer ma selection" (envoie seulement la partie selectionnee),
"Nouvelle conversation" (efface la discussion). Si l'eleve est dans le pas a pas
du debogueur, la ligne ou il en est est envoyee avec le code.

Affichage : la question de l'eleve a droite, la reponse a gauche. Les couleurs
du code sont celles du theme de Thonny, les fonds suivent son theme clair ou
sombre. Les liens `[texte](https://...)` sont cliquables, le vrai site est
affiche a cote du texte et une fenetre de confirmation l'annonce avant
d'ouvrir le navigateur (seulement http et https). Un passage "ligne 7" dans
une reponse est cliquable et surligne la ligne dans l'editeur.

Les adresses (serveur Classinus, service de connexion) ne sont jamais ecrites
dans le code : elles viennent de `defauts.json`, de la page de reglages
Classinus de Thonny, ou des variables d'environnement `CLASSINUS_BACKEND_URL`
et `CLASSINUS_SUPABASE_URL`.

Etape 5 : longueur de reponse (courte, moyenne, longue) et choix du modele quand
l'agent en propose, memes choix que le site. Bouton "Joindre un fichier" (photo
5 Mo max, document 15 Mo max, 5 fichiers) : envoi au serveur au moment de
Envoyer (`pieces_jointes.py`). Chaque conversation du panneau a son identifiant et
ses messages s'enchainent dans le meme fil de l'historique du site
(`conversation.py`).
