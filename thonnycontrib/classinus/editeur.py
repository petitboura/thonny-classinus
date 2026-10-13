"""Actions dans Thonny : trouver le code propose, l'inserer dans l'editeur, lancer le script.

Chaque action est declenchee par un clic de l'eleve ; l'insertion demande en plus sa validation
(voir panneau.py) et se defait avec Annuler (Ctrl+Z).
"""

import re

from thonny import get_workbench

from .erreurs import ErreurClassinus

_BLOC = re.compile(r"^[ \t]*```([^\n]*)\n(.*?)^[ \t]*```[ \t]*$", re.S | re.M)
_LANGAGES_PYTHON = ("", "python", "py", "python3")


def extraire_blocs(reponse):
    """Les blocs de code Python d'une reponse, dans l'ordre."""
    blocs = []
    for langage, code in _BLOC.findall(reponse):
        if langage.strip().lower() in _LANGAGES_PYTHON and code.strip():
            blocs.append(code.rstrip("\n"))
    return blocs


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


def lancer_script():
    runner = get_workbench().get_runner()
    if runner is None or not runner.cmd_run_current_script_enabled():
        raise ErreurClassinus("err_lancer_indisponible")
    runner.cmd_run_current_script()
