"""Fenetre « Historique » : la liste des conversations, comme sur le site (Epingles, puis groupes par date)."""

import queue
import threading
import tkinter as tk
from tkinter import ttk

from . import historique
from .erreurs import ErreurClassinus
from .textes import t


class FenetreHistorique(tk.Toplevel):
    """`au_choix(cle, messages)` est appelee, dans le fil de l'interface, quand une conversation est ouverte."""

    def __init__(self, master, au_choix):
        super().__init__(master)
        self.title(t("historique_titre"))
        self.geometry("380x500")
        self.minsize(280, 260)
        self.transient(master.winfo_toplevel())
        self._au_choix = au_choix
        self._file = queue.Queue()
        self._epingles, self._fils, self._suivant = [], [], None
        self._cles = {}  # identifiant de ligne -> cle de conversation
        self._ouvert = {"epingles": False}  # les groupes de date sont ouverts par defaut, les epingles repliees
        self._occupe = False

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self._arbre = ttk.Treeview(self, show="tree", selectmode="browse")
        defil = ttk.Scrollbar(self, command=self._arbre.yview)
        self._arbre.configure(yscrollcommand=defil.set)
        self._arbre.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        defil.grid(row=0, column=1, sticky="ns", pady=6)
        self._statut = ttk.Label(self, text="", foreground="#666666")
        self._statut.grid(row=1, column=0, columnspan=2, sticky="w", padx=8)
        self._btn_plus = ttk.Button(self, text=t("historique_charger_plus"), command=self._page_suivante)
        self._btn_plus.grid(row=2, column=0, columnspan=2, pady=(2, 6))
        self._btn_plus.grid_remove()

        self._arbre.bind("<ButtonRelease-1>", self._sur_clic)
        self._arbre.bind("<Return>", self._sur_clic)
        self._arbre.bind("<<TreeviewOpen>>", lambda _e: self._retenir_etat(True))
        self._arbre.bind("<<TreeviewClose>>", lambda _e: self._retenir_etat(False))
        self.bind("<Escape>", lambda _e: self.destroy())
        self._charger(None)
        self.after(50, self._lire_file)

    # ---------- chargement (reseau dans un fil a part, jamais d'interface depuis ce fil) ----------
    def _charger(self, curseur):
        self._statut.configure(text=t("historique_chargement"))
        self._btn_plus.configure(state="disabled")

        def tache():
            try:
                self._file.put(("page", historique.page_de_fils(curseur), curseur is None))
            except ErreurClassinus as e:
                self._file.put(("erreur", t(e.cle_texte)))
            except Exception:
                self._file.put(("erreur", t("historique_erreur")))

        threading.Thread(target=tache, daemon=True).start()

    def _page_suivante(self):
        if self._suivant:
            self._charger(self._suivant)

    def _ouvrir(self, cle):
        if self._occupe:
            return
        self._occupe = True
        self._statut.configure(text=t("historique_chargement"))

        def tache():
            try:
                self._file.put(("fil", cle, historique.messages_du_fil(cle)))
            except ErreurClassinus as e:
                self._file.put(("erreur_fil", t(e.cle_texte)))
            except Exception:
                self._file.put(("erreur_fil", t("historique_ouverture_erreur")))

        threading.Thread(target=tache, daemon=True).start()

    def _lire_file(self):
        if not self.winfo_exists():
            return
        try:
            while True:
                self._traiter(*self._file.get_nowait())
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(50, self._lire_file)

    def _traiter(self, kind, *valeur):
        if kind == "page":
            page, premiere = valeur
            if premiere:
                self._epingles = page["epingles"]
            self._fils += page["fils"]
            self._suivant = page["suivant"]
            self._statut.configure(text="" if self._epingles or self._fils else t("historique_vide"))
            self._btn_plus.configure(state="normal")
            if self._suivant:
                self._btn_plus.grid()
            else:
                self._btn_plus.grid_remove()
            self._reconstruire()
        elif kind == "erreur":
            self._statut.configure(text=valeur[0])
            self._btn_plus.configure(state="normal")
        elif kind == "fil":
            cle, messages = valeur
            self._occupe = False
            self._au_choix(cle, messages)
            self.destroy()
        elif kind == "erreur_fil":
            self._occupe = False
            self._statut.configure(text=valeur[0])

    # ---------- liste ----------
    def _retenir_etat(self, ouvert):
        ligne = self._arbre.focus()
        if ligne.startswith("g:"):
            self._ouvert[ligne[2:]] = ouvert

    def _reconstruire(self):
        self._arbre.delete(*self._arbre.get_children())
        self._cles = {}
        if self._epingles:
            titre = "%s (%d)" % (t("historique_epingles"), len(self._epingles))
            self._arbre.insert("", "end", "g:epingles", text=titre, open=self._ouvert.get("epingles", False))
            for fil in self._epingles:
                self._ajouter_fil("g:epingles", "p:", fil)
        recents = [fil for fil in self._fils if not fil.get("epingle")]
        for cle, libelle, fils in historique.regrouper_par_date(recents):
            self._arbre.insert("", "end", "g:" + cle, text=libelle, open=self._ouvert.get(cle, True))
            for fil in fils:
                self._ajouter_fil("g:" + cle, "f:", fil)

    def _ajouter_fil(self, parent, prefixe, fil):
        ligne = prefixe + fil["cle"]
        if self._arbre.exists(ligne):
            return
        self._arbre.insert(parent, "end", ligne, text=fil.get("titre") or "")
        self._cles[ligne] = fil["cle"]

    def _sur_clic(self, _evt=None):
        cle = self._cles.get(self._arbre.focus())
        if cle:
            self._ouvrir(cle)
