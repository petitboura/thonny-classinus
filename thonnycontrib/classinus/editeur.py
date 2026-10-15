"""Actions dans Thonny : inserer du code, ouvrir du code dans un onglet, montrer une ligne.

Chaque action est declenchee par un clic de l'eleve ; l'insertion demande en plus sa validation
(voir panneau.py) et se defait avec Annuler (Ctrl+Z). Seul le surlignage des lignes citees par la
reponse se fait tout seul : il ne change ni le texte ni le curseur du fichier.
"""

import ast
import os
import tkinter as tk

from thonny import get_workbench

from . import couleurs
from .erreurs import ErreurClassinus

_TAG_LIGNE = "classinus_ligne"
DUREE_SURLIGNAGE_MS = 8000
DUREE_SURLIGNAGE_AUTO_MS = 30000  # lignes surlignees toutes seules : l'eleve peut ne pas regarder tout de suite
_LANGAGES_PYTHON = ("python", "py", "python3")


def est_python(langage, code=""):
    """Vrai pour un bloc python ; sans langage indique, vrai si le code est du Python valide."""
    if langage in _LANGAGES_PYTHON:
        return True
    if langage:
        return False
    try:
        ast.parse(code)
    except Exception:
        return False
    return True


def _editeur_courant():
    editeur = get_workbench().get_editor_notebook().get_current_editor()
    if editeur is None:
        raise ErreurClassinus("err_aucun_editeur")
    return editeur


def a_selection():
    editeur = get_workbench().get_editor_notebook().get_current_editor()
    return editeur is not None and bool(editeur.get_text_widget().tag_ranges("sel"))


def inserer(code):
    """Ecrit `code` a la place de la selection, ou au curseur, en un seul pas d'annulation."""
    texte = _editeur_courant().get_text_widget()
    texte.edit_separator()
    if texte.tag_ranges("sel"):
        position = texte.index("sel.first")
        texte.delete("sel.first", "sel.last")
    else:
        position = texte.index("insert")
    texte.insert(position, code)
    texte.edit_separator()
    texte.see(position)
    texte.focus_set()


def ouvrir_dans_onglet(code):
    """Ouvre `code` dans un nouvel onglet non enregistre : aucun fichier de l'eleve n'est touche."""
    carnet = get_workbench().get_editor_notebook()
    carnet.open_new_file()
    texte = carnet.get_current_editor().get_text_widget()
    texte.insert("1.0", code + "\n")
    texte.mark_set("insert", "1.0")
    texte.see("1.0")


def surligner_ligne(numero):
    """Montre la ligne `numero` du fichier ouvert (surlignage temporaire)."""
    texte = _editeur_courant().get_text_widget()
    derniere = int(texte.index("end-1c").split(".")[0])
    if numero < 1 or numero > derniere:
        raise ErreurClassinus("err_ligne_introuvable")
    debut = "%d.0" % numero
    texte.tag_configure(_TAG_LIGNE, background=couleurs.surlignage(texte))
    texte.tag_remove(_TAG_LIGNE, "1.0", tk.END)
    texte.tag_add(_TAG_LIGNE, debut, "%d.0 lineend + 1c" % numero)
    texte.mark_set("insert", debut)
    texte.see(debut)
    _programmer_retrait(texte, DUREE_SURLIGNAGE_MS)


def surligner_lignes_citees(numeros, nom_attendu, code_attendu):
    """Surligne toutes seules les lignes citees par la reponse, sans bouger le curseur ni le texte.

    Seulement si le fichier ouvert est encore exactement celui que l'eleve a envoye : sinon les
    numeros ne correspondraient plus et on montrerait une mauvaise ligne. Renvoie vrai si surligne.
    """
    editeur = get_workbench().get_editor_notebook().get_current_editor()
    if editeur is None or os.path.basename(editeur.get_filename() or "") != nom_attendu:
        return False
    texte = editeur.get_text_widget()
    if texte.get("1.0", "end-1c").rstrip() != code_attendu.rstrip():
        return False
    derniere = int(texte.index("end-1c").split(".")[0])
    valides = sorted({n for n in numeros if 1 <= n <= derniere})
    if not valides:
        return False
    texte.tag_configure(_TAG_LIGNE, background=couleurs.surlignage(texte))
    texte.tag_remove(_TAG_LIGNE, "1.0", tk.END)
    for numero in valides:
        texte.tag_add(_TAG_LIGNE, "%d.0" % numero, "%d.0 lineend + 1c" % numero)
    texte.see("%d.0" % valides[0])  # ne defile que si la premiere ligne n'est pas deja visible
    _programmer_retrait(texte, DUREE_SURLIGNAGE_AUTO_MS)
    return True


def effacer_surlignage():
    """Retire le surlignage du fichier ouvert (a l'envoi d'une nouvelle question)."""
    editeur = get_workbench().get_editor_notebook().get_current_editor()
    if editeur is not None:
        _retirer_surlignage(editeur.get_text_widget())


def _programmer_retrait(texte, duree_ms):
    ancien = getattr(texte, "_classinus_retrait", None)
    if ancien is not None:
        texte.after_cancel(ancien)
    texte._classinus_retrait = texte.after(duree_ms, lambda: _retirer_surlignage(texte))


def _retirer_surlignage(texte):
    try:
        texte.tag_remove(_TAG_LIGNE, "1.0", tk.END)
    except tk.TclError:
        pass  # l'onglet a ete ferme entre temps
