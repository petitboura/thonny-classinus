"""Icones des menus : vrais logos des fournisseurs (voir logos_data.py), et une icone grise simple pour un fournisseur sans logo.

Pas de fichier image a telecharger : les logos sont dans le paquet. Un fournisseur sans logo recoit un disque gris, calcule point par point puis transformee en image PNG que Tk sait afficher.
"""

import base64
import struct
import tkinter as tk
import zlib
from tkinter import ttk

from .logos_data import LOGOS

TAILLE = 16
SUR_ECHANTILLON = 4  # chaque pixel est calcule sur 4 x 4 points : bords lisses

def _disque(x, y, rayon, cx=0.0, cy=0.0):
    return (x - cx) ** 2 + (y - cy) ** 2 <= rayon ** 2


def _generique(x, y):
    return (122, 130, 150) if _disque(x, y, 0.95) else None


FORMES = {}


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
    """Vrai si le fond des panneaux de Thonny est sombre (les logos OpenAI et Grok sont noirs : il faut alors le blanc)."""
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
        if cle in ("gpt", "grok") and _theme_sombre(self._widget):
            cle += "_sombre"
        if cle not in self._images:
            if cle in LOGOS:
                donnees = LOGOS[cle].encode("ascii")
            else:
                donnees = base64.b64encode(_dessiner(FORMES.get(cle, _generique)))
            self._images[cle] = tk.PhotoImage(master=self._widget, data=donnees)
        return self._images[cle]
