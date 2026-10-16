"""Mises a jour du plugin : on demande a PyPI la derniere version publiee.

La verification ne part jamais plus d'une fois par intervalle (reglage `mise_a_jour_intervalle_heures`),
elle tourne dans un fil a part et reste muette au moindre souci (hors ligne, reponse inattendue).
L'adresse interrogee et l'intervalle viennent de `defauts.json`.
"""

import json
import re
import time
import urllib.request

from . import identite, reglages

DELAI_RESEAU = 5
INTERVALLE_REPLI_HEURES = 24  # seulement si defauts.json est illisible
_VERSION_VALIDE = re.compile(r"^[0-9][0-9A-Za-z.+\-]{0,30}$")


def _chiffres(version):
    """(1, 2, 3) pour "1.2.3", None si le debut n'est pas un nombre. Les suffixes (rc1, dev0) sont ignores."""
    morceaux = []
    for partie in str(version).split("."):
        nombre = re.match(r"\d+", partie)
        if not nombre:
            break
        morceaux.append(int(nombre.group()))
        if nombre.end() != len(partie):
            break
    return tuple(morceaux) or None


def est_plus_recente(candidate, installee):
    """Vrai si `candidate` est strictement plus recente que `installee`, faux si l'une des deux est illisible."""
    a, b = _chiffres(candidate), _chiffres(installee)
    if a is None or b is None:
        return False
    longueur = max(len(a), len(b))
    a += (0,) * (longueur - len(a))
    b += (0,) * (longueur - len(b))
    return a > b


def interroger():
    """La derniere version publiee sur PyPI, ou None au moindre souci."""
    adresse = reglages.lire("mise_a_jour_url")
    if not adresse.lower().startswith("https://"):
        return None
    requete = urllib.request.Request(adresse, headers={"Accept": "application/json", "User-Agent": identite.agent_utilisateur()})
    try:
        with urllib.request.urlopen(requete, timeout=DELAI_RESEAU) as reponse:
            version = json.loads(reponse.read().decode("utf-8"))["info"]["version"]
    except Exception:  # verification de confort : aucune panne ne doit se voir
        return None
    if isinstance(version, str) and _VERSION_VALIDE.match(version):
        return version
    return None


def verification_due():
    """Vrai si la derniere verification reussie date de plus d'un intervalle (ou n'a jamais eu lieu)."""
    try:
        derniere = float(reglages.lire("derniere_verification_maj") or 0)
    except ValueError:
        derniere = 0
    try:
        heures = float(reglages.lire("mise_a_jour_intervalle_heures") or INTERVALLE_REPLI_HEURES)
    except ValueError:
        heures = INTERVALLE_REPLI_HEURES
    ecoule = time.time() - derniere
    return not 0 <= ecoule < heures * 3600


def retenir(version):
    """Garde la derniere version vue et l'heure de la verification."""
    reglages.ecrire("derniere_verification_maj", str(int(time.time())))
    reglages.ecrire("version_connue", version)


def version_a_proposer(version=None):
    """La version a annoncer, ou None (rien de plus recent installe, ou annonce deja fermee par l'eleve)."""
    version = version or reglages.lire("version_connue")
    if not version or not est_plus_recente(version, identite.version_installee()):
        return None
    if version == reglages.lire("version_ignoree"):
        return None
    return version


def ignorer(version):
    """L'eleve ferme l'annonce : on ne la remontre pas pour cette version, une plus recente la reaffichera."""
    reglages.ecrire("version_ignoree", version)
