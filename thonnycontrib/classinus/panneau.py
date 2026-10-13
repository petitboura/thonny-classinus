"""Panneau Classinus dans Thonny : historique, zone de saisie, envoyer / arreter."""

import queue
import threading
import tkinter as tk
from tkinter import ttk

from . import connexion, mise_en_forme
from .erreurs import ErreurClassinus
from .flux import EchangeEnCours
from .textes import t

IMAGES_ATTENTE = "\u280b\u2819\u2839\u2838\u283c\u2834\u2826\u2827\u2807\u280f"


class VueClassinus(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self._file = queue.Queue()
        self._echange = None
        self._historique = []
        self._question = ""
        self._reponse = ""
        self._statut_outil = ""
        self._occupe = False
        self._connexion_en_cours = False
        self._annule_connexion = False
        self._image = 0
        self._construire()
        self._maj_etat_connexion()
        self.after(40, self._lire_file)
        self.after(120, self._animer)

    # ---------- construction ----------
    def _construire(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        haut = ttk.Frame(self)
        haut.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 2))
        haut.columnconfigure(0, weight=1)
        self._lbl_etat = ttk.Label(haut, text="")
        self._lbl_etat.grid(row=0, column=0, sticky="w")
        self._btn_connexion = ttk.Button(haut, command=self._basculer_connexion)
        self._btn_connexion.grid(row=0, column=1, sticky="e")

        zone = ttk.Frame(self)
        zone.grid(row=1, column=0, sticky="nsew", padx=6)
        zone.columnconfigure(0, weight=1)
        zone.rowconfigure(0, weight=1)
        self._historique_txt = tk.Text(zone, wrap="word", state="disabled", height=10, width=36, borderwidth=0, padx=6, pady=6)
        defil = ttk.Scrollbar(zone, command=self._historique_txt.yview)
        self._historique_txt.configure(yscrollcommand=defil.set)
        self._historique_txt.grid(row=0, column=0, sticky="nsew")
        defil.grid(row=0, column=1, sticky="ns")
        mise_en_forme.preparer_tags(self._historique_txt)
        self._historique_txt.tag_configure("qui", font=self._historique_txt._polices_classinus[0], spacing1=8)
        self._historique_txt.tag_configure("erreur", foreground="#b00020")
        self._historique_txt.tag_configure("info", foreground="#666666")

        self._lbl_statut = ttk.Label(self, text="", foreground="#666666")
        self._lbl_statut.grid(row=2, column=0, sticky="w", padx=8)

        bas = ttk.Frame(self)
        bas.grid(row=3, column=0, sticky="ew", padx=6, pady=(2, 6))
        bas.columnconfigure(0, weight=1)
        self._saisie = tk.Text(bas, height=3, width=30, wrap="word", padx=4, pady=4)
        self._saisie.grid(row=0, column=0, sticky="ew")
        self._btn_envoyer = ttk.Button(bas, command=self._envoyer_ou_arreter)
        self._btn_envoyer.grid(row=0, column=1, sticky="ns", padx=(6, 0))
        self._saisie.bind("<Return>", self._sur_entree)
        self._saisie.bind("<FocusIn>", self._saisie_focus)
        self._saisie.bind("<FocusOut>", self._saisie_perd_focus)
        self._afficher_placeholder()
        self._maj_boutons()

    # ---------- saisie ----------
    def _afficher_placeholder(self):
        if not self._saisie.get("1.0", "end-1c") and self.focus_get() is not self._saisie:
            self._saisie.insert("1.0", t("placeholder"), ("indice",))
            self._saisie.tag_configure("indice", foreground="#888888")

    def _saisie_focus(self, _):
        if self._saisie.tag_ranges("indice"):
            self._saisie.delete("1.0", "end")

    def _saisie_perd_focus(self, _):
        self._afficher_placeholder()

    def _texte_saisi(self):
        if self._saisie.tag_ranges("indice"):
            return ""
        return self._saisie.get("1.0", "end-1c").strip()

    def _sur_entree(self, event):
        if event.state & 0x1:  # Maj+Entree : retour a la ligne
            return None
        if not self._occupe:
            self._envoyer()
        return "break"

    # ---------- affichage ----------
    def _ecrire(self, texte, *tags):
        w = self._historique_txt
        bas = w.yview()[1] >= 0.99
        w.configure(state="normal")
        w.insert(tk.END, texte, tags)
        w.configure(state="disabled")
        if bas:
            w.see(tk.END)

    def _maj_boutons(self):
        self._btn_envoyer.configure(text=t("arreter") if self._occupe else t("envoyer"))
        self._btn_connexion.configure(
            text=t("se_deconnecter") if connexion.est_connecte() else t("se_connecter"),
            state="disabled" if self._occupe else "normal",
        )

    def _maj_etat_connexion(self):
        if self._connexion_en_cours:
            self._lbl_etat.configure(text=t("connexion_en_cours"))
        else:
            self._lbl_etat.configure(text=t("connecte") if connexion.est_connecte() else t("non_connecte"))
        self._maj_boutons()

    def _animer(self):
        if self._occupe and not self._reponse:
            self._image = (self._image + 1) % len(IMAGES_ATTENTE)
            base = self._statut_outil or t("reflechit")
            self._lbl_statut.configure(text="%s %s" % (IMAGES_ATTENTE[self._image], base))
        elif self._connexion_en_cours:
            self._image = (self._image + 1) % len(IMAGES_ATTENTE)
            self._lbl_statut.configure(text="%s %s" % (IMAGES_ATTENTE[self._image], t("connexion_en_cours")))
        else:
            self._lbl_statut.configure(text="")
        self.after(120, self._animer)

    # ---------- connexion ----------
    def _basculer_connexion(self):
        if connexion.est_connecte():
            connexion.se_deconnecter()
            self._ecrire(t("deconnecte_ok") + "\n", "info")
            self._maj_etat_connexion()
            return
        if self._connexion_en_cours:
            self._annule_connexion = True
            return
        self._connexion_en_cours = True
        self._annule_connexion = False
        self._maj_etat_connexion()

        def tache():
            try:
                connexion.se_connecter(annule=lambda: self._annule_connexion)
                self._file.put(("connexion_ok", None))
            except ErreurClassinus as e:
                self._file.put(("connexion_erreur", e.cle_texte))
            except Exception:
                self._file.put(("connexion_erreur", "err_connexion_echec"))

        threading.Thread(target=tache, daemon=True).start()

    # ---------- envoi ----------
    def _envoyer_ou_arreter(self):
        if self._occupe:
            self._arreter()
        else:
            self._envoyer()

    def _envoyer(self):
        message = self._texte_saisi()
        if not message:
            return
        if not connexion.est_connecte():
            self._ecrire(t("err_connexion_requise") + "\n", "erreur")
            return
        self._saisie.delete("1.0", "end")
        self._question = message
        self._reponse = ""
        self._statut_outil = ""
        self._ecrire("\n" + t("toi") + "\n", "qui")
        self._ecrire(message + "\n", "utilisateur")
        self._ecrire(t("classinus") + "\n", "qui")
        self._historique_txt.mark_set("debut_reponse", "end-1c")
        self._historique_txt.mark_gravity("debut_reponse", "left")
        self._occupe = True
        self._maj_boutons()
        self._echange = EchangeEnCours(self._file)
        self._echange.demarrer(message, list(self._historique))

    def _arreter(self):
        if self._echange is not None:
            self._echange.arreter()
        self._terminer(arrete=True)

    def _terminer(self, arrete=False):
        if not self._occupe:
            return
        self._occupe = False
        self._statut_outil = ""
        if self._reponse:
            self._mettre_en_forme_reponse()
            self._historique.append({"role": "user", "content": self._question})
            self._historique.append({"role": "assistant", "content": self._reponse})
        if arrete:
            self._ecrire("\n" + t("arrete") + "\n", "info")
        self._reponse = ""
        self._echange = None
        self._maj_etat_connexion()

    def _mettre_en_forme_reponse(self):
        w = self._historique_txt
        w.configure(state="normal")
        w.delete("debut_reponse", "end-1c")
        mise_en_forme.inserer(w, self._reponse, "assistant")
        w.configure(state="disabled")
        w.see(tk.END)

    # ---------- lecture de la file (jamais d'interface depuis un autre fil) ----------
    def _lire_file(self):
        try:
            while True:
                kind, valeur = self._file.get_nowait()
                self._traiter(kind, valeur)
        except queue.Empty:
            pass
        self.after(40, self._lire_file)

    def _traiter(self, kind, valeur):
        if kind == "texte":
            if self._occupe:
                self._reponse += valeur
                self._ecrire(valeur, "assistant")
        elif kind == "statut":
            self._statut_outil = valeur
        elif kind == "statut_fin":
            self._statut_outil = ""
        elif kind == "confirmation":
            self._ecrire("\n" + t("err_confirmation") + "\n", "info")
        elif kind == "erreur":
            self._ecrire("\n" + t(valeur) + "\n", "erreur")
            if valeur in ("err_session_expiree", "err_connexion_requise"):
                self._maj_etat_connexion()
        elif kind == "fin":
            self._terminer()
        elif kind == "connexion_ok":
            self._connexion_en_cours = False
            self._ecrire(t("connecte_ok") + "\n", "info")
            self._maj_etat_connexion()
        elif kind == "connexion_erreur":
            self._connexion_en_cours = False
            self._ecrire(t(valeur) + "\n", "erreur")
            self._maj_etat_connexion()
