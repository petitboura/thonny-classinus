"""Stockage du jeton de connexion sur l'ordinateur de l'eleve.

Premier choix : le coffre du systeme (Windows, macOS, Linux) via keyring.
Repli : un fichier reserve a l'utilisateur dans le dossier de Thonny.
"""

import json
import os
import time

SERVICE = "thonny-classinus"
UTILISATEUR = "jeton"


def _fichier():
    from thonny import THONNY_USER_DIR

    return os.path.join(THONNY_USER_DIR, "classinus_jeton.json")


def _coffre():
    try:
        import keyring

        return keyring
    except Exception:
        return None


def _lire_coffre():
    coffre = _coffre()
    if coffre is None:
        return None
    try:
        brut = coffre.get_password(SERVICE, UTILISATEUR)
        return json.loads(brut) if brut else None
    except Exception:
        return None


def _lire_fichier():
    try:
        with open(_fichier(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def lire():
    """Le contenu qui porte la session s'il y en a un, sinon ce qui reste (identifiants de client)."""
    trouves = [d for d in (_lire_coffre(), _lire_fichier()) if d]
    for donnees in trouves:
        if donnees.get("access_token"):
            return donnees
    return trouves[0] if trouves else None


def _vider_coffre(coffre):
    try:
        coffre.delete_password(SERVICE, UTILISATEUR)
    except Exception:
        pass


def ecrire(donnees):
    brut = json.dumps(donnees)
    coffre = _coffre()
    if coffre is not None:
        try:
            coffre.set_password(SERVICE, UTILISATEUR, brut)
            # Le coffre de Windows refuse ou coupe les contenus trop gros : on relit pour verifier.
            if coffre.get_password(SERVICE, UTILISATEUR) == brut:
                _supprimer_fichier()
                return
        except Exception:
            pass
        # Ecriture ratee : une ancienne entree du coffre ne doit pas masquer le fichier.
        _vider_coffre(coffre)
    chemin = _fichier()
    fd = os.open(chemin, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(brut)


def _supprimer_fichier():
    try:
        os.remove(_fichier())
    except OSError:
        pass


def effacer():
    coffre = _coffre()
    if coffre is not None:
        try:
            coffre.delete_password(SERVICE, UTILISATEUR)
        except Exception:
            pass
    _supprimer_fichier()


def est_expire(donnees, marge=60):
    return not donnees or time.time() >= float(donnees.get("expires_at", 0)) - marge
