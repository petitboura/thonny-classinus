"""Tous les textes affiches, par langue. Aucune chaine visible ailleurs.

Chaque langue est un fichier du dossier `langues/` (`fr.py`, `en.py`...) qui donne `NOM` et `TEXTES`.
Les langues sont decouvertes toutes seules : ajouter un fichier suffit, rien d'autre a declarer.
Toute langue doit avoir exactement les memes cles que les autres (verifie par `tests/test_langues.py`),
jamais une langue seule : le francais ne sert de repli que si une cle manque par accident.
"""

import importlib
import pkgutil
import re

from . import langues as _paquet_langues

LANGUE_REPLI = "fr"


def _charger():
    textes, noms = {}, {}
    for info in pkgutil.iter_modules(_paquet_langues.__path__):
        module = importlib.import_module("%s.%s" % (_paquet_langues.__name__, info.name))
        textes[info.name] = module.TEXTES
        noms[info.name] = getattr(module, "NOM", info.name)
    return textes, noms


TEXTES, NOMS_LANGUES = _charger()
_langue = LANGUE_REPLI


def langues_disponibles():
    """Les codes des langues installees, dans l'ordre alphabetique (fr, en...)."""
    return tuple(sorted(TEXTES))


def nom_langue(code):
    """Le nom d'une langue, ecrit dans cette langue (Français, English...)."""
    return NOMS_LANGUES.get(code, code)


def definir_langue(choix, langue_thonny=""):
    """choix: 'auto', un code de langue installee ou vide. En auto on suit la langue de Thonny."""
    global _langue
    brut = (choix or "").strip().lower()
    if brut in TEXTES:
        _langue = brut
        return
    code = (langue_thonny or "").lower()[:2]
    _langue = code if code in TEXTES else LANGUE_REPLI


def langue():
    """Le code de la langue active du panneau."""
    return _langue


def t(cle):
    return TEXTES.get(_langue, TEXTES[LANGUE_REPLI]).get(cle) or TEXTES[LANGUE_REPLI].get(cle, cle)


def _marqueurs(texte):
    return sorted(re.findall(r"%[sd]", texte))


def verifier():
    """Liste les problemes de traduction (vide si tout est bon) : cle absente, texte vide, marqueurs %s ou %d differents."""
    problemes = []
    toutes = set().union(*(set(d) for d in TEXTES.values()))
    for code in langues_disponibles():
        textes = TEXTES[code]
        for cle in sorted(toutes - set(textes)):
            problemes.append("%s : la cle %s manque" % (code, cle))
        for cle, valeur in textes.items():
            if not str(valeur).strip():
                problemes.append("%s : la cle %s est vide" % (code, cle))
            reference = TEXTES[LANGUE_REPLI].get(cle)
            if reference is not None and _marqueurs(str(valeur)) != _marqueurs(str(reference)):
                problemes.append("%s : la cle %s n'a pas les memes %%s ou %%d que %s" % (code, cle, LANGUE_REPLI))
    return problemes
