"""Reglages : valeurs par defaut du paquet < reglages Thonny < variables d'environnement."""

import json
import os

from thonny import get_workbench

_CLES = ("backend_url", "supabase_url", "langue")


def _defauts_paquet():
    chemin = os.path.join(os.path.dirname(__file__), "defauts.json")
    try:
        with open(chemin, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


DEFAUTS = _defauts_paquet()


def declarer_defauts():
    wb = get_workbench()
    for cle in _CLES:
        wb.set_default("classinus." + cle, "")


def lire(cle):
    """Retourne la valeur effective d'un reglage."""
    if cle == "backend_url" and os.environ.get("CLASSINUS_BACKEND_URL"):
        return os.environ["CLASSINUS_BACKEND_URL"].rstrip("/")
    if cle == "supabase_url" and os.environ.get("CLASSINUS_SUPABASE_URL"):
        return os.environ["CLASSINUS_SUPABASE_URL"].rstrip("/")
    valeur = ""
    if cle in _CLES:
        valeur = (get_workbench().get_option("classinus." + cle) or "").strip()
    if not valeur:
        valeur = str(DEFAUTS.get(cle, "") or "")
    if cle.endswith("_url"):
        valeur = valeur.rstrip("/")
    return valeur


def lire_defaut(cle, repli=""):
    return DEFAUTS.get(cle, repli)


def ecrire(cle, valeur):
    get_workbench().set_option("classinus." + cle, (valeur or "").strip())
