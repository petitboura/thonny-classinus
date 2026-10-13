"""Identite reseau du plugin.

Cloudflare, devant le serveur Classinus, refuse (erreur 1010) les requetes qui
portent l'en-tete par defaut de Python (« Python-urllib »). Toute requete du
plugin annonce donc son nom et sa version, lue dans le paquet installe.
"""

NOM = "Classinus-Thonny"


def _version():
    try:
        from importlib.metadata import version

        return version("thonny-classinus")
    except Exception:
        return "inconnue"


def agent_utilisateur():
    return "%s/%s" % (NOM, _version())
