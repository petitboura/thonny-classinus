"""Fenetre « Fichier Classinus » : que faire d'un fichier venu du serveur Classinus.

L'eleve ne voit jamais l'adresse brute du serveur. Selon le type du fichier, la fenetre propose :
ouvrir dans Thonny (texte et code, dans un nouvel onglet non enregistre), enregistrer sur
l'ordinateur (toujours), ouvrir dans le navigateur (PDF et images). Les types sont dans
defauts.json (`extensions_texte`, `extensions_navigateur`, `taille_max_texte`).

Le telechargement se fait dans un fil a part ; la fenetre lit ses messages dans une file,
jamais d'interface touchee depuis un autre fil. Les fichiers de Classinus se telechargent sans
connexion (leur adresse est celle que le site donne lui-meme), mais Cloudflare exige l'en-tete
du plugin (voir identite.py).
"""

import os
import queue
import threading
import tkinter as tk
import urllib.request
import webbrowser
from tkinter import filedialog, ttk

from . import adresses, editeur, identite, reglages
from .erreurs import ErreurClassinus
from .textes import t

_TAILLE_MORCEAU = 64 * 1024
_TIMEOUT_S = 30
_DELAI_LECTURE_MS = 60
_LARGEUR_TEXTE = 380


def _extension(nom):
    return os.path.splitext(nom)[1].lower()


def peut_ouvrir_dans_thonny(nom):
    return _extension(nom) in reglages.lire_defaut("extensions_texte", [])


def peut_ouvrir_dans_navigateur(nom):
    return _extension(nom) in reglages.lire_defaut("extensions_navigateur", [])


def _telecharger(adresse, destination, limite, file):
    """Fil a part. Depose ("texte", octets), ("enregistre", chemin) ou ("erreur", cle_texte) dans `file`."""
    requete = urllib.request.Request(adresse, headers={"User-Agent": identite.agent_utilisateur()})
    try:
        with urllib.request.urlopen(requete, timeout=_TIMEOUT_S) as reponse:
            if destination is None:
                contenu = reponse.read(limite + 1)
                if len(contenu) > limite:
                    file.put(("erreur", "err_fichier_trop_gros"))
                else:
                    file.put(("texte", contenu))
                return
            with open(destination, "wb") as sortie:
                while True:
                    morceau = reponse.read(_TAILLE_MORCEAU)
                    if not morceau:
                        break
                    sortie.write(morceau)
        file.put(("enregistre", destination))
    except Exception:
        if destination is not None:
            try:
                os.remove(destination)  # pas de fichier a moitie ecrit
            except OSError:
                pass
        file.put(("erreur", "err_fichier_telechargement"))


class FenetreFichier(tk.Toplevel):
    def __init__(self, parent, adresse, titre, informer):
        """`informer(texte)` : ecrit une info dans le panneau (fichier ouvert ou enregistre)."""
        super().__init__(parent)
        self._adresse = adresse
        self._nom = adresses.nom_fichier(adresse, titre, t("fichier_sans_nom"))
        self._informer = informer
        self._file = queue.Queue()
        self._occupe = False
        self._ferme = False
        self._tache = None
        self._boutons = []

        self.title(t("fichier_titre"))
        self.transient(parent)
        self.resizable(False, False)
        cadre = ttk.Frame(self, padding=14)
        cadre.pack(fill="both", expand=True)
        ttk.Label(cadre, text=t("fichier_titre_nom") % self._nom, wraplength=_LARGEUR_TEXTE, justify="left").pack(anchor="w")
        self._statut = ttk.Label(cadre, text="", wraplength=_LARGEUR_TEXTE, justify="left")
        self._statut.pack(anchor="w", pady=(8, 0))

        if peut_ouvrir_dans_thonny(self._nom):
            self._ajouter_bouton(cadre, "fichier_ouvrir_thonny", self._ouvrir_dans_thonny)
        self._ajouter_bouton(cadre, "fichier_enregistrer", self._enregistrer)
        if peut_ouvrir_dans_navigateur(self._nom):
            self._ajouter_bouton(cadre, "fichier_ouvrir_navigateur", self._ouvrir_dans_navigateur)
        ttk.Button(cadre, text=t("fichier_annuler"), command=self.destroy).pack(fill="x", pady=(10, 0))
        self.bind("<Escape>", lambda _evt: self.destroy())

        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass  # fenetre fermee ou pas encore affichable : la fenetre reste utilisable sans blocage
        self._tache = self.after(_DELAI_LECTURE_MS, self._lire_file)

    def _ajouter_bouton(self, cadre, cle_texte, commande):
        bouton = ttk.Button(cadre, text=t(cle_texte), command=commande)
        bouton.pack(fill="x", pady=(10, 0))
        self._boutons.append(bouton)

    def destroy(self):
        self._ferme = True
        if self._tache is not None:
            try:
                self.after_cancel(self._tache)
            except tk.TclError:
                pass
        super().destroy()

    def _occuper(self, occupe):
        self._occupe = occupe
        for bouton in self._boutons:
            bouton.configure(state="disabled" if occupe else "normal")
        if occupe:
            self._statut.configure(text=t("fichier_telechargement"), foreground="")

    def _lancer(self, destination, limite):
        if self._occupe:
            return
        self._occuper(True)
        threading.Thread(target=_telecharger, args=(self._adresse, destination, limite, self._file), daemon=True).start()

    def _ouvrir_dans_thonny(self):
        self._lancer(None, int(reglages.lire_defaut("taille_max_texte", 1000000)))

    def _enregistrer(self):
        chemin = filedialog.asksaveasfilename(parent=self, initialfile=adresses.nom_sur_disque(self._nom))
        if chemin:
            self._lancer(chemin, 0)

    def _ouvrir_dans_navigateur(self):
        webbrowser.open(self._adresse)
        self.destroy()

    def _lire_file(self):
        if self._ferme:
            return
        try:
            while True:
                kind, valeur = self._file.get_nowait()
                self._traiter(kind, valeur)
                if self._ferme:
                    return
        except queue.Empty:
            pass
        except tk.TclError:
            return  # la fenetre a ete fermee pendant le traitement
        self._tache = self.after(_DELAI_LECTURE_MS, self._lire_file)

    def _traiter(self, kind, valeur):
        if kind == "texte":
            try:
                code = valeur.decode("utf-8").replace("\r\n", "\n")
            except UnicodeDecodeError:
                self._erreur("err_fichier_pas_du_texte")
                return
            try:
                editeur.ouvrir_dans_onglet(code)
            except ErreurClassinus as e:
                self._erreur(e.cle_texte)
                return
            self._informer(t("onglet_ok"))
            self.destroy()
        elif kind == "enregistre":
            self._informer(t("fichier_enregistre") % valeur)
            self.destroy()
        else:
            self._erreur(valeur)

    def _erreur(self, cle_texte):
        self._occuper(False)
        self._statut.configure(text=t(cle_texte), foreground="#c0392b")


def proposer(parent, adresse, titre, informer):
    FenetreFichier(parent, adresse, titre, informer)
