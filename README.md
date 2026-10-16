# thonny-classinus

Plugin Thonny qui ajoute un panneau Classinus a droite de l'editeur.

Etape 1 : connexion au compte Classinus (via le navigateur), puis une question
tapee dans le panneau et une reponse qui s'affiche au fil de l'eau.

Etape 2 : deux boutons, "Envoyer mon code" (fichier ouvert, partie selectionnee,
derniere erreur et sortie du programme) et "Expliquer cette erreur". Rien ne
part sans un clic de l'eleve. Le code est ajoute au message envoye a Classinus ;
les tailles maximales sont dans `defauts.json` (`max_code`, `max_sortie`).

Les consignes propres a Thonny (ou est Classinus, ce que font les boutons, comment
repondre : texte simple, code Python dans un bloc python) ne sont plus dans le
plugin : le serveur les ajoute lui-meme (fichier `core/consignes_thonny.txt` du
backend) quand le plugin se declare client Thonny. Le plugin envoie seulement
`client` et le nom de ses boutons dans la langue de l'eleve (`libelles_client`).
Modifier ce fichier du serveur change le comportement de Classinus dans Thonny.

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

Tableaux : un tableau Markdown dans la reponse s'affiche en vrai tableau aligne
(`tableaux.py`), avec une barre de defilement horizontale si le panneau est trop
etroit. Les consignes Thonny du serveur autorisent les tableaux.

Boutons du bas et du haut du panneau : "Joindre un fichier" (sur sa ligne, texte entier) et
"Reglages" (longueur de reponse, effort, mode pedagogique, modes ressources, comme sur le site).
Le bouton "Modele" est en haut du panneau, avec les memes regles que sur le site : il n'apparait
que si le serveur propose des modeles, la liste est groupee par fournisseur, il n'y a pas de mode
"Auto". Le modele actif est le dernier choix de l'eleve s'il est encore propose, sinon DeepSeek Flash
(`modele_par_defaut` dans `defauts.json`). Les icones des fournisseurs sont les vrais logos (`logos_data.py`, bibliotheque libre
`@lobehub/icons-static-svg`, licence MIT), l'icone "Auto" est dessinee par le plugin (`icones.py`). Le mode pedagogique et les modes ressources sont enregistres
sur le serveur pour la conversation en cours (`parametres_conversation.py`), comme sur le site.

Lignes citees : quand la reponse cite des lignes du code envoye (« ligne 7 », « lignes 3 a 5 »),
elles sont surlignees toutes seules dans l'editeur a la fin de la reponse, sans bouger le curseur
ni le texte, et seulement si le fichier ouvert est encore exactement celui que l'eleve a envoye
(`editeur.surligner_lignes_citees`). Dans le panneau, « ligne N » reste cliquable et ressort en jaune.

Fichiers et pages de Classinus : un lien qui pointe vers un fichier servi par Classinus (serveur
ou stockage) n'affiche jamais l'adresse brute. Il est annonce « (Classinus) » et ouvre la fenetre
« Fichier Classinus » (`fichier_classinus.py`) : ouvrir dans Thonny (texte et code, nouvel onglet non
enregistre), enregistrer sur l'ordinateur, ouvrir dans le navigateur (PDF et images). Les types
proposes sont dans `defauts.json` (`extensions_texte`, `extensions_navigateur`, `taille_max_texte`),
les adresses reconnues viennent des reglages (`backend_url`, `supabase_url`, `site_url`). Un lien vers
une page du site Classinus s'ouvre dans le navigateur avec la fenetre de confirmation habituelle,
qui annonce « Classinus ».

Mises a jour : Thonny ne previent pas quand un plugin a une nouvelle version, c'est donc le plugin qui le
fait (`mise_a_jour.py`). Au demarrage, il interroge PyPI dans un fil a part (adresse et intervalle dans
`defauts.json` : `mise_a_jour_url`, `mise_a_jour_intervalle_heures`, 24 h par defaut) et affiche un bandeau
en haut du panneau si une version plus recente existe. Le bandeau se ferme avec "Fermer" et ne reparait pas
pour cette version, une version encore plus recente le fait reparaitre. Hors ligne ou en cas de reponse
inattendue, rien ne s'affiche. Seules les versions deja installees avec cette fonction peuvent l'utiliser :
elle n'existe pas dans les versions publiees avant elle.

Langues : chaque langue est un fichier du dossier `thonnycontrib/classinus/langues/` (`fr.py`, `en.py`) avec
`NOM` et `TEXTES`. Tout texte visible passe par `t("cle")` et existe dans toutes les langues, jamais dans une
seule. Pour ajouter une langue : copier `en.py` en `<code>.py` (par exemple `ar.py`), changer `NOM`, traduire
les valeurs sans toucher aux cles ni aux `%s`. La langue est decouverte toute seule (reglage "auto" ou son code
dans Outils > Options > Classinus). Le test `python -m unittest discover tests` echoue si une cle manque dans une
langue, si un texte est vide, si les `%s` different, ou si le code appelle une cle qui n'existe pas.
