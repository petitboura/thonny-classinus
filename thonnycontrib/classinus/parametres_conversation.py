"""Mode pedagogique et mode ressources : deux choix rattaches a la conversation, enregistres par le serveur.

Ce sont les memes routes que celles du site (une conversation, un choix). Ils ne partent donc pas
avec chaque message : le panneau les enregistre sur le serveur, avant l'envoi de la question.
Toute panne renvoie False, sans bruit : le panneau reessaiera a la prochaine question.
"""

import json
import urllib.request

from . import connexion, identite, reglages

# genre -> (fin de l'adresse, nom du champ envoye)
ROUTES = {
    "persona": ("persona-pedagogique", "persona"),
    "mode_source": ("mode-source", "mode_source"),
}
DELAI = 10


def definir(genre, conversation_id, valeur):
    """Enregistre le choix (None pour « aucun ») sur le serveur. Retourne True si c'est fait."""
    route = ROUTES.get(genre)
    base = reglages.lire("backend_url")
    if route is None or not base:
        return False
    adresse, champ = route
    try:
        req = urllib.request.Request(
            "%s/api/conversations/%s/%s" % (base, conversation_id, adresse),
            data=json.dumps({champ: valeur}).encode("utf-8"),
            method="PUT",
            headers={
                "Content-Type": "application/json",
                "User-Agent": identite.agent_utilisateur(),
                "Authorization": "Bearer " + connexion.jeton_valide(),
            },
        )
        with urllib.request.urlopen(req, timeout=DELAI):
            return True
    except Exception:
        return False
