"""Adresses web : on n'ouvre que du http ou https, et on montre toujours le vrai site."""

import os
import re
from urllib.parse import unquote, urlsplit

from . import reglages

SCHEMAS_AUTORISES = ("http", "https")
NOM_SITE = "Classinus"  # ce que l'eleve lit a la place de l'adresse brute du serveur
_CARACTERES_INTERDITS_NOM = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def domaine(adresse):
    """Le vrai site d'une adresse (sans "www."), ou None si elle n'est pas ouvrable."""
    try:
        morceaux = urlsplit(adresse)
        site = morceaux.hostname
    except ValueError:
        return None
    if morceaux.scheme.lower() not in SCHEMAS_AUTORISES or not site:
        return None
    site = site.lower()
    return site[4:] if site.startswith("www.") else site


def _chemin(adresse):
    try:
        return urlsplit(adresse).path
    except ValueError:
        return ""


def genre_classinus(adresse):
    """"fichier" pour un fichier servi par Classinus, "page" pour une page du site Classinus, sinon None.

    Les adresses de reference viennent des reglages (backend_url, supabase_url, site_url), jamais ecrites ici.
    """
    site = domaine(adresse)
    if site is None:
        return None
    chemin = _chemin(adresse)
    if site == domaine(reglages.lire("backend_url")) and chemin.startswith("/fichiers/"):
        return "fichier"
    if site == domaine(reglages.lire("supabase_url")) and chemin.startswith("/storage/"):
        return "fichier"
    if site == domaine(reglages.lire("site_url")):
        return "page"
    return None


def nom_fichier(adresse, titre=None, repli="fichier"):
    """Le nom d'un fichier a montrer : le texte du lien s'il ressemble a un nom de fichier, sinon la fin de l'adresse."""
    fin = os.path.basename(unquote(_chemin(adresse)))
    for candidat in (titre, fin):
        nom = os.path.basename((candidat or "").replace("\\", "/")).strip()
        if nom and os.path.splitext(nom)[1]:
            return nom
    return fin or repli


def nom_sur_disque(nom):
    """Le meme nom, sans les caracteres qu'un systeme de fichiers refuse."""
    return _CARACTERES_INTERDITS_NOM.sub("_", nom).strip() or "fichier"
