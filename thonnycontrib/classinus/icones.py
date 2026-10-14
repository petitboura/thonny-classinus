"""Icones des menus : vrais logos des fournisseurs (voir logos_data.py), et une icone dessinee pour « Auto ».

Pas de fichier image a telecharger : les logos sont dans le paquet. L'icone « Auto » n'a pas de
logo, elle est calculee point par point puis transformee en image PNG que Tk sait afficher.
"""

import base64
import struct
import tkinter as tk
import zlib
from tkinter import ttk

from .logos_data import LOGOS

TAILLE = 16
SUR_ECHANTILLON = 4  # chaque pixel est calcule sur 4 x 4 points : bords lisses

BLANC = (255, 255, 255)


def _disque(x, y, rayon, cx=0.0, cy=0.0):
    return (x - cx) ** 2 + (y - cy) ** 2 <= rayon ** 2


def _etoile(x, y, taille):
    """Etoile a quatre branches (aux cotes creux)."""
    return (abs(x) / taille) ** 0.7 + (abs(y) / taille) ** 0.7 <= 1


def _auto(x, y):
    if not _disque(x, y, 0.95):
        return None
    if _etoile(x, y, 0.55):
        return BLANC
    return (122, 130, 150)


def _generique(x, y):
    return (122, 130, 150) if _disque(x, y, 0.95) else None


FORMES = {"auto": _auto}


def _png(lignes):
    brut = b"".join(b"\x00" + bytes(octet for pixel in ligne for octet in pixel) for ligne in lignes)

    def bloc(nom, donnees):
        corps = nom + donnees
        return struct.pack(">I", len(donnees)) + corps + struct.pack(">I", zlib.crc32(corps) & 0xFFFFFFFF)

    entete = struct.pack(">IIBBBBB", TAILLE, TAILLE, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", entete) + bloc(b"IDAT", zlib.compress(brut)) + bloc(b"IEND", b"")


def _dessiner(forme):
    lignes = []
    for py in range(TAILLE):
        ligne = []
        for px in range(TAILLE):
            couleurs = []
            for sy in range(SUR_ECHANTILLON):
                for sx in range(SUR_ECHANTILLON):
                    x = ((px + (sx + 0.5) / SUR_ECHANTILLON) / TAILLE) * 2 - 1
                    y = ((py + (sy + 0.5) / SUR_ECHANTILLON) / TAILLE) * 2 - 1
                    couleur = forme(x, y)
                    if couleur is not None:
                        couleurs.append(couleur)
            total = SUR_ECHANTILLON ** 2
            if not couleurs:
                ligne.append((0, 0, 0, 0))
                continue
            moyenne = tuple(round(sum(c[i] for c in couleurs) / len(couleurs)) for i in range(3))
            ligne.append(moyenne + (round(255 * len(couleurs) / total),))
        lignes.append(ligne)
    return _png(lignes)


def _theme_sombre(widget):
    """Vrai si le fond des panneaux de Thonny est sombre (le logo OpenAI est noir : il faut alors le blanc)."""
    try:
        fond = ttk.Style(widget).lookup("TFrame", "background") or "#ffffff"
        rouge, vert, bleu = (c // 257 for c in widget.winfo_rgb(fond))
        return 0.299 * rouge + 0.587 * vert + 0.114 * bleu < 128
    except tk.TclError:
        return False


class Icones:
    """Garde les images en vie (Tk les efface sinon) et les cree a la demande."""

    def __init__(self, widget):
        self._widget = widget
        self._images = {}

    def obtenir(self, cle):
        if cle == "gpt" and _theme_sombre(self._widget):
            cle = "gpt_sombre"
        if cle not in self._images:
            if cle in LOGOS:
                donnees = LOGOS[cle].encode("ascii")
            else:
                donnees = base64.b64encode(_dessiner(FORMES.get(cle, _generique)))
            self._images[cle] = tk.PhotoImage(master=self._widget, data=donnees)
        return self._images[cle]
