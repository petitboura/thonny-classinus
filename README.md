# thonny-classinus

Plugin Thonny qui ajoute un panneau Classinus a droite de l'editeur.

Etape 1 : connexion au compte Classinus (via le navigateur), puis une question
tapee dans le panneau et une reponse qui s'affiche au fil de l'eau.

Les adresses (serveur Classinus, service de connexion) ne sont jamais ecrites
dans le code : elles viennent de `defauts.json`, de la page de reglages
Classinus de Thonny, ou des variables d'environnement `CLASSINUS_BACKEND_URL`
et `CLASSINUS_SUPABASE_URL`.
