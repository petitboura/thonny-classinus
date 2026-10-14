"""Couleurs qui suivent le theme de Thonny : on part du fond reel du widget, jamais d'un fond fixe."""


def _rgb(widget, couleur):
    rouge, vert, bleu = widget.winfo_rgb(couleur)
    return rouge // 257, vert // 257, bleu // 257


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(c))) for c in rgb)


def _fond(widget):
    return _rgb(widget, widget.cget("background"))


def est_sombre(widget):
    rouge, vert, bleu = _fond(widget)
    return 0.299 * rouge + 0.587 * vert + 0.114 * bleu < 128


def melanger(widget, cible, ratio):
    """Le fond du widget, teinte de `ratio` vers la couleur `cible` (rouge, vert, bleu)."""
    return _hex(tuple(b + (c - b) * ratio for b, c in zip(_fond(widget), cible)))


def nuance(widget):
    """Un fond tres legerement different de celui du widget (code en ligne, blocs de code)."""
    if est_sombre(widget):
        return melanger(widget, (255, 255, 255), 0.10)
    return melanger(widget, (0, 0, 0), 0.06)


def bulle(widget):
    """Le fond de la bulle de l'eleve."""
    return melanger(widget, (70, 130, 230), 0.25 if est_sombre(widget) else 0.14)


def surlignage(widget):
    """Le fond d'une ligne montree dans l'editeur."""
    return melanger(widget, (255, 214, 0), 0.40)


def attenue(widget):
    """Un gris lisible sur le fond du widget (infos discretes)."""
    texte = _rgb(widget, widget.cget("foreground"))
    return _hex(tuple(b + (c - b) * 0.55 for b, c in zip(_fond(widget), texte)))


def erreur(widget):
    return "#ff6b6b" if est_sombre(widget) else "#b00020"


def lien(widget):
    return "#6cb6ff" if est_sombre(widget) else "#0b57d0"
