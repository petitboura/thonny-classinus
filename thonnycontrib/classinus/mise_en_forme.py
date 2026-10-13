"""Mise en forme de base d'une reponse dans un widget Text : titres, gras, code."""

import re
import tkinter as tk
import tkinter.font as tkfont

_GRAS = re.compile(r"\*\*(.+?)\*\*")
_CODE = re.compile(r"`([^`\n]+)`")


def preparer_tags(texte_widget):
    base = tkfont.nametofont("TkDefaultFont")
    gras = base.copy()
    gras.configure(weight="bold")
    titre = base.copy()
    titre.configure(weight="bold", size=base.cget("size") + 2)
    mono = tkfont.nametofont("TkFixedFont")
    texte_widget.tag_configure("gras", font=gras)
    texte_widget.tag_configure("titre", font=titre)
    texte_widget.tag_configure("code", font=mono, background="#eeeeee")
    texte_widget.tag_configure("bloc_code", font=mono, background="#eeeeee", lmargin1=12, lmargin2=12)
    texte_widget._polices_classinus = (gras, titre)


def inserer(texte_widget, texte, tag_base):
    """Insere `texte` a la fin du widget avec la mise en forme de base."""
    dans_bloc = False
    for ligne in texte.split("\n"):
        if ligne.strip().startswith("```"):
            dans_bloc = not dans_bloc
            continue
        if dans_bloc:
            texte_widget.insert(tk.END, ligne + "\n", (tag_base, "bloc_code"))
            continue
        if ligne.startswith("#"):
            texte_widget.insert(tk.END, ligne.lstrip("# ").strip() + "\n", (tag_base, "titre"))
            continue
        if ligne.startswith(("- ", "* ")):
            ligne = "\u2022 " + ligne[2:]
        _inserer_ligne(texte_widget, ligne, tag_base)
        texte_widget.insert(tk.END, "\n", (tag_base,))


def _inserer_ligne(w, ligne, tag_base):
    morceaux = []
    pos = 0
    for m in sorted(list(_GRAS.finditer(ligne)) + list(_CODE.finditer(ligne)), key=lambda x: x.start()):
        if m.start() < pos:
            continue
        morceaux.append((ligne[pos : m.start()], ()))
        morceaux.append((m.group(1), ("gras",) if m.re is _GRAS else ("code",)))
        pos = m.end()
    morceaux.append((ligne[pos:], ()))
    for contenu, tags in morceaux:
        if contenu:
            w.insert(tk.END, contenu, (tag_base,) + tags)
