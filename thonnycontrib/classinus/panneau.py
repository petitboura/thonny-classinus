"""Panneau Classinus dans Thonny : historique, zone de saisie, envoyer / arreter."""

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import connexion, contexte, editeur, mise_en_forme
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
        self._blocs = []
        self._erreur_affichee = False
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

        actions = ttk.Frame(self)
        actions.grid(row=3, column=0, sticky="ew", padx=6, pady=(2, 0))
        actions.columnconfigure((0, 1), weight=1, uniform="actions")
        self._btn_code = ttk.Button(actions, command=self._envoyer_code)
        self._btn_erreur = ttk.Button(actions, command=self._expliquer_erreur)
        self._btn_inserer = ttk.Button(actions, command=self._inserer)
        self._btn_lancer = ttk.Button(actions, command=self._lancer)
        for i, bouton in enumerate((self._btn_code, self._btn_erreur, self._btn_inserer, self._btn_lancer)):
            bouton.grid(row=i // 2, column=i % 2, sticky="ew", padx=1, pady=1)

        bas = ttk.Frame(self)
        bas.grid(row=4, column=0, sticky="ew", padx=6, pady=(2, 6))
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
        libre = "disabled" if self._occupe else "normal"
        self._btn_code.configure(text=t("envoyer_code"), state=libre)
        self._btn_erreur.configure(text=t("expliquer_erreur"), state=libre)
        self._btn_lancer.configure(text=t("lancer"), state=libre)
        self._btn_inserer.configure(text=t("inserer"), state="normal" if self._blocs and not self._occupe else "disabled")
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
        question = self._texte_saisi()
        if question:
            self._lancer_echange(question, None, True)

    def _envoyer_code(self):
        ctx = contexte.lire()
        if not ctx.a_du_code():
            self._ecrire(t("aucun_code") + "\n", "info")
            return
        question = self._texte_saisi()
        self._lancer_echange(question or t("question_code"), ctx, bool(question))

    def _expliquer_erreur(self):
        ctx = contexte.lire()
        if not ctx.erreur:
            self._ecrire(t("aucune_erreur") + "\n", "info")
            return
        self._lancer_echange(t("question_erreur"), ctx, False)

    def _lancer_echange(self, message, ctx, vider_saisie):
        if not connexion.est_connecte():
            self._ecrire(t("err_connexion_requise") + "\n", "erreur")
            return
        if vider_saisie:
            self._saisie.delete("1.0", "end")
        self._question = message
        self._reponse = ""
        self._blocs = []
        self._erreur_affichee = False
        self._statut_outil = ""
        self._ecrire("\n" + t("toi") + "\n", "qui")
        self._ecrire(message + "\n", "utilisateur")
        if ctx is not None:
            self._ecrire(t("code_envoye") % (ctx.nom or t("sans_nom")) + "\n", "info")
        self._ecrire(t("classinus") + "\n", "qui")
        self._historique_txt.mark_set("debut_reponse", "end-1c")
        self._historique_txt.mark_gravity("debut_reponse", "left")
        self._occupe = True
        self._maj_boutons()
        self._echange = EchangeEnCours(self._file)
        self._echange.demarrer(contexte.construire_message(message, ctx), list(self._historique))

    # ---------- actions dans Thonny (toujours sur clic de l'eleve) ----------
    def _inserer(self):
        if len(self._blocs) == 1:
            self._confirmer_insertion(self._blocs[0])
        elif self._blocs:
            menu = tk.Menu(self, tearoff=False)
            for i, bloc in enumerate(self._blocs, 1):
                premiere = bloc.strip().split("\n")[0][:40]
                menu.add_command(label="%s : %s" % (t("bloc_n") % i, premiere), command=lambda b=bloc: self._confirmer_insertion(b))
            menu.tk_popup(self._btn_inserer.winfo_rootx(), self._btn_inserer.winfo_rooty() + self._btn_inserer.winfo_height())

    def _confirmer_insertion(self, code):
        lignes = code.split("\n")
        apercu = "\n".join(lignes[:12]) + ("\n..." if len(lignes) > 12 else "")
        question = t("inserer_question") % apercu
        if editeur.a_selection():
            question += "\n\n" + t("inserer_remplace")
        if not messagebox.askyesno(t("inserer_titre"), question, parent=self):
            return
        try:
            editeur.inserer(code)
            self._ecrire(t("inserer_ok") + "\n", "info")
        except ErreurClassinus as e:
            self._ecrire(t(e.cle_texte) + "\n", "erreur")

    def _lancer(self):
        try:
            editeur.lancer_script()
        except ErreurClassinus as e:
            self._ecrire(t(e.cle_texte) + "\n", "erreur")

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
            self._blocs = editeur.extraire_blocs(self._reponse)
            self._mettre_en_forme_reponse()
            self._historique.append({"role": "user", "content": self._question})
            self._historique.append({"role": "assistant", "content": self._reponse})
        if arrete:
            self._ecrire("\n" + t("arrete") + "\n", "info")
        elif not self._reponse and not self._erreur_affichee:
            self._ecrire("\n" + t("err_aucune_reponse") + "\n", "erreur")
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
            self._erreur_affichee = True
            self._ecrire("\n" + t("err_confirmation") + "\n", "info")
        elif kind == "erreur":
            cle, detail = valeur
            self._erreur_affichee = True
            self._ecrire("\n" + t(cle) + (" " + t("detail_technique") % detail if detail else "") + "\n", "erreur")
            if cle in ("err_session_expiree", "err_connexion_requise"):
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
