"""Adresses web : on n'ouvre que du http ou https, et on montre toujours le vrai site."""

from urllib.parse import urlsplit

SCHEMAS_AUTORISES = ("http", "https")


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
