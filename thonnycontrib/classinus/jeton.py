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


def lire():
    coffre = _coffre()
    if coffre is not None:
        try:
            brut = coffre.get_password(SERVICE, UTILISATEUR)
            if brut:
                return json.loads(brut)
        except Exception:
            pass
    try:
        with open(_fichier(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def ecrire(donnees):
    brut = json.dumps(donnees)
    coffre = _coffre()
    if coffre is not None:
        try:
            coffre.set_password(SERVICE, UTILISATEUR, brut)
            _supprimer_fichier()
            return
        except Exception:
            pass
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
