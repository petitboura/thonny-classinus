"""Tableaux Markdown (| a | b |) d'une reponse : detection et mise en colonnes alignees.

Un tableau est une suite de lignes qui commencent par | dont la deuxieme est la ligne de
separation (|---|---|). `bloc_tableau` rend le texte aligne, avec des traits, pret a etre
affiche en police a chasse fixe.
"""

import re

_SEPARATEUR = re.compile(r"^\s*\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)*\|?\s*$")
_MARQUES = re.compile(r"\*\*|`")
MAX_COLONNES = 12
MAX_LARGEUR_CELLULE = 40


def _cellules(ligne):
    ligne = ligne.strip()
    if ligne.startswith("|"):
        ligne = ligne[1:]
    if ligne.endswith("|") and not ligne.endswith("\\|"):
        ligne = ligne[:-1]
    return [_MARQUES.sub("", c.replace("\\|", "|")).strip() for c in re.split(r"(?<!\\)\|", ligne)]


def commence_un_tableau(ligne, suivante):
    """Vrai si `ligne` est l'en-tete d'un tableau dont `suivante` est la ligne de separation."""
    return (
        ligne.strip().startswith("|")
        and suivante is not None
        and "|" in suivante
        and "-" in suivante
        and bool(_SEPARATEUR.match(suivante))
        and 1 < len(_cellules(ligne)) <= MAX_COLONNES
    )


def est_ligne_de_tableau(ligne):
    return ligne.strip().startswith("|")


def bloc_tableau(lignes):
    """(en-tete, corps) : deux textes alignes. `lignes` = en-tete, separation, puis les lignes de donnees."""
    en_tete = _cellules(lignes[0])
    nb = len(en_tete)
    donnees = []
    for ligne in lignes[2:]:
        c = _cellules(ligne)[:nb]
        donnees.append(c + [""] * (nb - len(c)))
    toutes = [en_tete] + donnees
    largeurs = [min(MAX_LARGEUR_CELLULE, max(len(r[i]) for r in toutes)) or 1 for i in range(nb)]

    def formater(r):
        morceaux = []
        for i, cellule in enumerate(r):
            if len(cellule) > largeurs[i]:
                cellule = cellule[: largeurs[i] - 1] + "\u2026"
            morceaux.append(" " + cellule.ljust(largeurs[i]) + " ")
        return "\u2502".join(morceaux)

    trait = "\u253c".join("\u2500" * (w + 2) for w in largeurs)
    return formater(en_tete) + "\n" + trait + "\n", "\n".join(formater(r) for r in donnees) + ("\n" if donnees else "")
