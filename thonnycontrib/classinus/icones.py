"""Petites icones des fournisseurs de modeles, dessinees par le plugin lui-meme.

Ce ne sont pas les logos officiels : une simulation fidele aux couleurs et a la forme generale,
sans fichier image a telecharger ni a livrer. Chaque icone est calculee point par point puis
transformee en image PNG, que Tk sait afficher dans un menu ou sur un bouton.
"""

import base64
import math
import struct
import tkinter as tk
import zlib

TAILLE = 16
SUR_ECHANTILLON = 4  # chaque pixel est calcule sur 4 x 4 points : bords lisses

BLANC = (255, 255, 255)


def _disque(x, y, rayon, cx=0.0, cy=0.0):
    return (x - cx) ** 2 + (y - cy) ** 2 <= rayon ** 2


def _etoile(x, y, taille):
    """Etoile a quatre branches (aux cotes creux)."""
    return (abs(x) / taille) ** 0.7 + (abs(y) / taille) ** 0.7 <= 1


def _melanger(a, b, ratio):
    return tuple(round(ca + (cb - ca) * ratio) for ca, cb in zip(a, b))


def _deepseek(x, y):
    if not _disque(x, y, 0.95):
        return None
    if _disque(x, y, 0.6, -0.05, 0.0) and not _disque(x, y, 0.5, 0.2, -0.05):
        return BLANC
    return (77, 107, 254)


def _claude(x, y):
    if not _disque(x, y, 0.95):
        return None
    rayon = math.hypot(x, y)
    angle = math.atan2(y, x)
    if 0.1 < rayon < 0.72 and abs(math.cos(4 * angle)) > 0.86:
        return BLANC
    return (217, 119, 87)


def _gpt(x, y):
    if not _disque(x, y, 0.95):
        return None
    hexagone = max(abs(x * math.cos(a) + y * math.sin(a)) for a in (math.pi / 6, math.pi / 2, 5 * math.pi / 6))
    if 0.4 <= hexagone <= 0.62:
        return BLANC
    return (16, 163, 127)


def _gemini(x, y):
    if not _etoile(x, y, 0.95):
        return None
    return _melanger((66, 133, 244), (155, 114, 203), (x + y + 2) / 4)


def _auto(x, y):
    if not _disque(x, y, 0.95):
        return None
    if _etoile(x, y, 0.55):
        return BLANC
    return (122, 130, 150)


def _generique(x, y):
    return (122, 130, 150) if _disque(x, y, 0.95) else None


FORMES = {
    "deepseek": _deepseek,
    "claude": _claude,
    "gpt": _gpt,
    "gemini": _gemini,
    "auto": _auto,
}


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


class Icones:
    """Garde les images en vie (Tk les efface sinon) et les cree a la demande."""

    def __init__(self, widget):
        self._widget = widget
        self._images = {}

    def obtenir(self, cle):
        if cle not in self._images:
            png = _dessiner(FORMES.get(cle, _generique))
            self._images[cle] = tk.PhotoImage(master=self._widget, data=base64.b64encode(png))
        return self._images[cle]
