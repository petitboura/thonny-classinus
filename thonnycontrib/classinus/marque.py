"""Icone de Classinus, posee a gauche de la premiere ligne de chaque reponse : elle marque ou la reponse commence.

Image PNG de 18 pixels tiree du logo du site (logo-classinus-sans-fond), en texte base64 : rien a telecharger.
"""

import tkinter as tk

ICONE_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAABIAAAASCAYAAABWzo5XAAACeElEQVR42p2TO0xTURzGv3NuL1cekkbE+Ijg4GDiBkwuhcREEk00"
    "kqohxsT4SBycXBhILnVSIwMxisRBQ9ShNdHBMOBA76IbiKW1CQ9fFKSX0tvae/s85+9ACZpAQb/pDP/zy+88PuAfQrrOyyumE3H8"
    "T4hWIdZnb2txpmU8P3FodMqPKiIwAGzbENLBE/M3DhbCbQlaaCb6upfiL9weACA/lG3qRRjzQVanwrdVd2qXdPIO0kIWsjgKAGgE"
    "41vbgDEWEPHI9X0qJb3yl0NISxUmeCIhtLW5rY2CHgUA6mS0w6UVaoUlZHGZeM6SsGwZB4BgcAsQAQzthhwYuKkVEslOZLIoWoLy"
    "mRKPxUsUMxECADMCclW0GfMojBmluTcTl1x5u6uw7MicXWKUlViKi+mhiB1ZPTpEZVDQkADD7nrrai05NaZZEFmbSObA4kl6Yhgo"
    "BfvgAlDaFER+rwJvQNpdnW1aJtq2MGvLlAVGRVLmYiL6MZZ9TAQGBlH5shvjjDFGPBfrlXaamyZJM0Fy5od0Vhy1zxdAJnAOnAEE"
    "ABsajY15XKzDKGVCx09oyejp0KecmP8JslJSTWVppWFPdVjX0zxchmxoRKTz9g5DJEl3q8kvQ5HxFRGaJrG4JNS0Q4vuevXMhf6l"
    "KQDw+SA3+3zc74UC7kL+/ZHXk/fraLBbo0fdGg1e3DHy6pa7GQD8XigVml224wqWRw4PT96to/6zVfSwW/vw/Ert+bW5ypDVBoO+"
    "nzww+7Jp5F1PTezeKfXO8LWdx9h6r5muV3gc0sGJwL69bWkNPW16NtpTcxmA+udMRYu/agAg8mB/gxfrG3QPXNsClPMbAKFIujc1"
    "VWAAAAAASUVORK5CYII="
)


def creer_image(master):
    """L'image Tk de l'icone ; l'appelant doit garder une reference dessus."""
    return tk.PhotoImage(master=master, data=ICONE_PNG_BASE64)


def poser(widget, image):
    """Pose l'icone puis une espace a la fin du texte : la reponse s'ecrit sur la meme ligne, a sa droite."""
    widget.image_create(tk.END, image=image, align="center")
    widget.insert(tk.END, " ", ("assistant",))
