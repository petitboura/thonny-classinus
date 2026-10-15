"""Mise en forme de la conversation dans un widget Text : bulles, titres, gras, code colore, liens, lignes.

Les liens et les numeros de ligne sont cliquables ; ce module ne fait rien lui-meme au clic,
il appelle les fonctions donnees a `preparer_tags` (le panneau demande confirmation avant d'ouvrir un site).
"""

import re
import tkinter as tk
import tkinter.font as tkfont

from . import adresses, coloration, couleurs, tableaux

_GRAS = re.compile(r"\*\*(.+?)\*\*")
_CODE = re.compile(r"`([^`\n]+)`")
_LIEN = re.compile(r"\[([^\]\n]+)\]\((https?://[^\s)]+)\)")
_ADRESSE = re.compile(r"https?://[^\s<>\"')\]]+")
_LIGNE = re.compile(r"\b(?:lignes?|lines?)\s+(\d+)", re.IGNORECASE)
# Pour surligner : « lignes 3 a 5 », « lines 3-5 » (suite) ou « lignes 3 et 5 » (deux lignes).
_LIGNES_CITEES = re.compile(r"\b(?:lignes?|lines?)\s+(\d+)(?:\s*(-|–|à|to|et|and)\s*(\d+))?", re.IGNORECASE)
_BLOC_CODE = re.compile(r"```.*?(?:```|\Z)", re.DOTALL)
_MAX_SUITE_LIGNES = 40
_MOTIFS = ((_GRAS, "gras"), (_CODE, "code"), (_LIEN, "lien"), (_ADRESSE, "adresse"), (_LIGNE, "ligne"))
_PONCTUATION_FINALE = ".,;:!?"
_LONGUEUR_ADRESSE_AFFICHEE = 50
_MARGE_BULLE = 36


def preparer_tags(w, ouvrir_lien=None, aller_ligne=None, curseur_lien="hand2"):
    base = tkfont.nametofont("TkDefaultFont")
    gras = base.copy()
    gras.configure(weight="bold")
    titre = base.copy()
    titre.configure(weight="bold", size=base.cget("size") + 2)
    mono = tkfont.nametofont("TkFixedFont")
    mono_gras = mono.copy()
    mono_gras.configure(weight="bold")
    w._polices_classinus = (gras, titre, mono_gras)
    w._actions_classinus = {}
    w._compteur_classinus = 0

    # Les bulles et les infos d'abord : les tags crees ensuite ont la priorite.
    w.tag_configure("utilisateur", justify="right", lmargin1=_MARGE_BULLE, lmargin2=_MARGE_BULLE, rmargin=6, background=couleurs.bulle(w))
    w.tag_configure("assistant", lmargin1=6, lmargin2=6, rmargin=_MARGE_BULLE)
    w.tag_configure("info", foreground=couleurs.attenue(w))
    w.tag_configure("info_droite", foreground=couleurs.attenue(w), justify="right", lmargin1=_MARGE_BULLE, lmargin2=_MARGE_BULLE, rmargin=6)
    w.tag_configure("erreur", foreground=couleurs.erreur(w))

    w.tag_configure("gras", font=gras)
    w.tag_configure("titre", font=titre)
    w.tag_configure("code", font=mono, background=couleurs.nuance(w))
    # Tableaux : jamais coupes a la largeur du panneau (la barre de defilement horizontale apparait si besoin).
    w.tag_configure("tableau", font=mono, wrap="none", background=couleurs.nuance(w), lmargin1=6, lmargin2=6)
    w.tag_configure("tableau_titre", font=mono_gras)
    w.tag_configure("bloc_code", font=mono, background=couleurs.nuance(w), lmargin1=12, lmargin2=12)
    for genre, couleur in coloration.couleurs().items():
        w.tag_configure("py_" + genre, foreground=couleur)

    w.tag_configure("lien", foreground=couleurs.lien(w), underline=True)
    # « ligne N » cliquable : plus visible qu'un lien, meme jaune que la ligne surlignee dans l'editeur.
    w.tag_configure("ligne_citee", font=gras, background=couleurs.ligne_citee(w))
    curseur_normal = w.cget("cursor")
    w.tag_bind("lien", "<Button-1>", lambda evt: _clic(w, evt, ouvrir_lien, aller_ligne))
    w.tag_bind("lien", "<Enter>", lambda evt: w.configure(cursor=curseur_lien))
    w.tag_bind("lien", "<Leave>", lambda evt: w.configure(cursor=curseur_normal))


def vider(w):
    w.configure(state="normal")
    w.delete("1.0", tk.END)
    w.configure(state="disabled")
    w._actions_classinus.clear()


def _clic(w, evt, ouvrir_lien, aller_ligne):
    for nom in w.tag_names("@%d,%d" % (evt.x, evt.y)):
        action = w._actions_classinus.get(nom)
        if action is None:
            continue
        genre, valeur = action
        if genre == "lien" and ouvrir_lien is not None:
            ouvrir_lien(valeur)
        elif genre == "ligne" and aller_ligne is not None:
            aller_ligne(valeur)
        return "break"
    return None


def lignes_citees(texte):
    """Les numeros de ligne cites par la reponse, hors blocs de code (ex. « lignes 3 a 5 » donne 3, 4, 5)."""
    numeros = set()
    for m in _LIGNES_CITEES.finditer(_BLOC_CODE.sub("", texte)):
        premier = int(m.group(1))
        numeros.add(premier)
        if m.group(3) is None:
            continue
        second = int(m.group(3))
        if m.group(2).lower() in ("-", "–", "à", "to"):
            if premier < second <= premier + _MAX_SUITE_LIGNES:
                numeros.update(range(premier, second + 1))
        else:
            numeros.add(second)
    return sorted(numeros)


def inserer(w, texte, tag_base, rappel_bloc=None):
    """Insere `texte` a la fin du widget avec la mise en forme.

    `rappel_bloc(w, code, langage)` peut renvoyer un widget (les boutons sous un bloc de code).
    """
    dans_bloc = False
    langage = ""
    lignes_code = []
    lignes = texte.split("\n")
    i = -1
    while i + 1 < len(lignes):
        i += 1
        ligne = lignes[i]
        if not dans_bloc and tableaux.commence_un_tableau(ligne, lignes[i + 1] if i + 1 < len(lignes) else None):
            fin = i + 2
            while fin < len(lignes) and tableaux.est_ligne_de_tableau(lignes[fin]):
                fin += 1
            en_tete, corps = tableaux.bloc_tableau(lignes[i:fin])
            w.insert(tk.END, en_tete, (tag_base, "tableau", "tableau_titre"))
            w.insert(tk.END, corps, (tag_base, "tableau"))
            i = fin - 1
            continue
        if ligne.strip().startswith("```"):
            if not dans_bloc:
                dans_bloc = True
                info = ligne.strip()[3:].strip()
                langage = info.split()[0].lower() if info else ""
                lignes_code = []
            else:
                dans_bloc = False
                _inserer_bloc(w, "\n".join(lignes_code), langage, tag_base, rappel_bloc)
            continue
        if dans_bloc:
            lignes_code.append(ligne)
            continue
        if ligne.startswith("#"):
            w.insert(tk.END, ligne.lstrip("# ").strip() + "\n", (tag_base, "titre"))
            continue
        if ligne.startswith(("- ", "* ")):
            ligne = "• " + ligne[2:]
        _inserer_texte(w, ligne, (tag_base,))
        w.insert(tk.END, "\n", (tag_base,))
    if dans_bloc and lignes_code:  # bloc jamais ferme (reponse coupee) : affiche sans boutons
        _inserer_bloc(w, "\n".join(lignes_code), langage, tag_base, None)


def _inserer_bloc(w, code, langage, tag_base, rappel_bloc):
    tags = (tag_base, "bloc_code")
    if langage in coloration.LANGAGES_COLORES:
        for morceau, genre in coloration.decouper(code):
            w.insert(tk.END, morceau, tags + (("py_" + genre,) if genre else ()))
    else:
        w.insert(tk.END, code, tags)
    w.insert(tk.END, "\n", tags)
    if rappel_bloc is not None and code.strip():
        cadre = rappel_bloc(w, code, langage)
        if cadre is not None:
            w.window_create(tk.END, window=cadre, padx=4, pady=2)
            w.insert(tk.END, "\n", (tag_base,))


def _inserer_brut(w, texte, tags):
    if texte:
        w.insert(tk.END, texte, tags)


def _inserer_texte(w, texte, tags):
    """Un texte courant : gras, code en ligne, liens, numeros de ligne."""
    trouves = sorted(
        ((m.start(), m, genre) for motif, genre in _MOTIFS for m in motif.finditer(texte)),
        key=lambda element: element[0],
    )
    place = 0
    for debut, m, genre in trouves:
        if debut < place:
            continue
        _inserer_brut(w, texte[place:debut], tags)
        place = m.end()
        if genre == "gras":
            _inserer_texte(w, m.group(1), tags + ("gras",))
        elif genre == "code":
            _inserer_brut(w, m.group(1), tags + ("code",))
        elif genre == "lien":
            _inserer_lien(w, m.group(1), m.group(2), tags, adresse_nue=False)
        elif genre == "adresse":
            adresse = m.group(0).rstrip(_PONCTUATION_FINALE)
            place = debut + len(adresse)
            affichee = adresse.split("://", 1)[1]
            if len(affichee) > _LONGUEUR_ADRESSE_AFFICHEE:
                affichee = affichee[: _LONGUEUR_ADRESSE_AFFICHEE - 1] + "…"
            _inserer_lien(w, affichee, adresse, tags, adresse_nue=True)
        else:
            _inserer_action(w, m.group(0), ("ligne", int(m.group(1))), tags)
    _inserer_brut(w, texte[place:], tags)


def _inserer_lien(w, texte, adresse, tags, adresse_nue):
    site = adresses.domaine(adresse)
    if site is None:
        _inserer_brut(w, texte, tags)
        return
    visible = texte if adresse_nue else "%s (%s)" % (texte, site)
    _inserer_action(w, visible, ("lien", adresse), tags)


def _inserer_action(w, visible, action, tags):
    nom = "action_%d" % w._compteur_classinus
    w._compteur_classinus += 1
    w._actions_classinus[nom] = action
    supplement = ("ligne_citee",) if action[0] == "ligne" else ()
    w.insert(tk.END, visible, tags + ("lien", nom) + supplement)
