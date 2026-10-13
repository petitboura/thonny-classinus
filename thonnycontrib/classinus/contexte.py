"""Ce que l'eleve a sous les yeux dans Thonny : fichier, selection, sortie et erreur du programme.

Rien n'est lu ni envoye tant que l'eleve n'a pas clique sur un bouton du panneau.
La sortie du programme est simplement gardee en memoire (jamais envoyee toute seule).
"""

import os

from thonny import get_workbench

from . import reglages
from .textes import t

_sortie = ""
_erreur = ""

_CLOTURE = "~~~~"
_DEBUT_COUPE = "[... debut coupe ...]\n"
_FIN_COUPEE = "\n[... suite coupee ...]"


class Contexte:
    def __init__(self, nom, code, selection, sortie, erreur):
        self.nom = nom
        self.code = code
        self.selection = selection
        self.sortie = sortie
        self.erreur = erreur

    def a_du_code(self):
        return bool(self.code.strip() or self.selection.strip())


def installer():
    wb = get_workbench()
    wb.bind("ProgramOutput", _sur_sortie, True)
    wb.bind("BackendRestart", _sur_redemarrage, True)
    wb.bind("ToplevelResponse", _sur_fin_execution, True)


def _limite(cle, repli):
    try:
        return int(reglages.lire_defaut(cle, repli))
    except (TypeError, ValueError):
        return repli


def _sur_sortie(msg):
    global _sortie, _erreur
    donnee = msg.get("data", "") or ""
    limite = _limite("max_sortie", 6000)
    if msg.get("stream_name", "stdout") == "stderr":
        _erreur = (_erreur + donnee)[-limite:]
    else:
        _sortie = (_sortie + donnee)[-limite:]


def _sur_fin_execution(msg):
    """Thonny envoie le texte d'une erreur Python ici, pas dans la sortie normale."""
    global _erreur
    exception = msg.get("user_exception")
    if exception:
        texte = "".join(element[0] for element in exception.get("items", []))
        _erreur = (_erreur + texte)[-_limite("max_sortie", 6000):]


def _sur_redemarrage(_msg=None):
    global _sortie, _erreur
    _sortie = ""
    _erreur = ""


def lire():
    """Photographie ce que l'eleve voit maintenant."""
    nom = code = selection = ""
    editeur = get_workbench().get_editor_notebook().get_current_editor()
    if editeur is not None:
        texte = editeur.get_text_widget()
        code = editeur.get_content()
        nom = os.path.basename(editeur.get_filename() or "")
        if texte.tag_ranges("sel"):
            selection = texte.get("sel.first", "sel.last")
    return Contexte(nom, code, selection, _sortie.strip(), _erreur.strip())


def _bloc(titre, contenu, garder_debut):
    limite = _limite("max_code" if garder_debut else "max_sortie", 20000 if garder_debut else 4000)
    if len(contenu) > limite:
        contenu = contenu[:limite] + _FIN_COUPEE if garder_debut else _DEBUT_COUPE + contenu[-limite:]
    return "%s :\n%s\n%s\n%s\n" % (titre, _CLOTURE, contenu, _CLOTURE)


def _consignes():
    """Explique a Classinus ou il se trouve et comment repondre (texte dans consignes.txt)."""
    chemin = os.path.join(os.path.dirname(__file__), "consignes.txt")
    try:
        with open(chemin, encoding="utf-8") as f:
            modele = f.read().strip()
    except OSError:
        return ""
    return modele.format(**{cle: t(cle) for cle in ("envoyer_code", "expliquer_erreur", "inserer", "lancer")})


def construire_message(question, ctx=None):
    """Le message envoye au serveur : les consignes Thonny, ce que l'eleve voit (s'il l'a envoye), sa question."""
    parties = [_consignes() + "\n"]
    if ctx is None:
        parties.append("[Fin des consignes]\n\nQuestion de l'élève : %s" % question)
        return "\n".join(parties)
    parties.append("[Ce que l'élève te montre]")
    if ctx.nom:
        parties.append("Fichier : %s" % ctx.nom)
    if ctx.code.strip():
        parties.append(_bloc("Code du fichier", ctx.code, True))
    if ctx.selection.strip():
        parties.append(_bloc("Partie sélectionnée par l'élève", ctx.selection, True))
    if ctx.erreur:
        parties.append(_bloc("Dernière erreur affichée", ctx.erreur, False))
    if ctx.sortie:
        parties.append(_bloc("Ce que le programme a affiché", ctx.sortie, False))
    parties.append("[Fin des consignes]\n\nQuestion de l'élève : %s" % question)
    return "\n".join(parties)
