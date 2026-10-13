# thonny-classinus

Plugin Thonny qui ajoute un panneau Classinus a droite de l'editeur.

Etape 1 : connexion au compte Classinus (via le navigateur), puis une question
tapee dans le panneau et une reponse qui s'affiche au fil de l'eau.

Etape 2 : deux boutons, "Envoyer mon code" (fichier ouvert, partie selectionnee,
derniere erreur et sortie du programme) et "Expliquer cette erreur". Rien ne
part sans un clic de l'eleve. Le code est ajoute au message envoye a Classinus,
dans un bloc "Contexte Thonny" ; les tailles maximales sont dans `defauts.json`
(`max_code`, `max_sortie`).

Etape 3 : "Inserer dans l'editeur" propose le bloc de code Python de la derniere
reponse (l'eleve valide, puis Ctrl+Z annule) et "Lancer le script" lance le
fichier courant.

Les adresses (serveur Classinus, service de connexion) ne sont jamais ecrites
dans le code : elles viennent de `defauts.json`, de la page de reglages
Classinus de Thonny, ou des variables d'environnement `CLASSINUS_BACKEND_URL`
et `CLASSINUS_SUPABASE_URL`.
