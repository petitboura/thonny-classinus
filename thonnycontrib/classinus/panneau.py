"""Panneau Classinus dans Thonny : conversation, boutons d'aide, zone de saisie."""

import os
import queue
import threading
import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from tkinter import filedialog, messagebox, ttk

from . import adresses, connexion, contexte, conversation, editeur, mise_en_forme, parametres_conversation, pieces_jointes
from .erreurs import ErreurClassinus
from .flux import EchangeEnCours
from .menus import BoutonModele, BoutonReglages
from .textes import t

IMAGES_ATTENTE = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
STYLE_BOUTON = "Classinus.TButton"
STYLE_BOUTON_LARGE = "Classinus.Large.TButton"
STYLE_MENU = "Classinus.TMenubutton"
DUREE_COPIE_MS = 1500
LONGUEUR_APERCU_ADRESSE = 200


def _curseur_lien():
    try:
        from thonny.ui_utils import get_hyperlink_cursor

        return get_hyperlink_cursor()
    except Exception:
        return "hand2"


class VueClassinus(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self._file = queue.Queue()
        self._echange = None
        self._historique = []
        self._question = ""
        self._contexte_envoye = None  # le code montre avec la derniere question : les « ligne N » de la reponse le visent
        self._reponse = ""
        self._erreur_affichee = False
        self._statut_outil = ""
        self._occupe = False
        self._connexion_en_cours = False
        self._annule_connexion = False
        self._image = 0
        self._colonnes_actions = 0
        self._fil = conversation.Fil()
        self._pieces = []
        self._texte_pieces = ""
        self._en_attente = {}  # choix de la conversation pas encore enregistres sur le serveur
        self._construire()
        self._maj_etat_connexion()
        threading.Thread(target=self._charger_modeles, daemon=True).start()
        self.after(40, self._lire_file)
        self.after(120, self._animer)

    # ---------- construction ----------
    def _construire(self):
        police_petite = tkfont.nametofont("TkDefaultFont").copy()
        taille = police_petite.cget("size")
        police_petite.configure(size=taille + 1 if taille < 0 else max(7, taille - 1))
        self._police_petite = police_petite
        style = ttk.Style(self)
        style.configure(STYLE_BOUTON, padding=(4, 1), font=police_petite)
        style.configure(STYLE_BOUTON_LARGE, padding=(8, 3), font=police_petite)
        style.configure(STYLE_MENU, padding=(6, 2), font=police_petite)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        haut = ttk.Frame(self)
        haut.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 2))
        haut.columnconfigure(0, weight=1)
        self._lbl_etat = ttk.Label(haut, text="")
        self._lbl_etat.grid(row=0, column=0, sticky="w")
        self._btn_connexion = ttk.Button(haut, style=STYLE_BOUTON, command=self._basculer_connexion)
        self._btn_connexion.grid(row=0, column=1, sticky="e")
        self._btn_modele = BoutonModele(haut, STYLE_MENU)
        self._btn_modele.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self._btn_modele.grid_remove()  # visible seulement quand le serveur propose des modeles

        zone = ttk.Frame(self)
        zone.grid(row=1, column=0, sticky="nsew", padx=6)
        zone.columnconfigure(0, weight=1)
        zone.rowconfigure(0, weight=1)
        self._historique_txt = tk.Text(zone, wrap="word", state="disabled", height=10, width=36, borderwidth=0, padx=6, pady=6)
        defil = ttk.Scrollbar(zone, command=self._historique_txt.yview)
        self._defil_x = ttk.Scrollbar(zone, orient="horizontal", command=self._historique_txt.xview)
        self._historique_txt.configure(yscrollcommand=defil.set, xscrollcommand=self._defiler_x)
        self._historique_txt.grid(row=0, column=0, sticky="nsew")
        defil.grid(row=0, column=1, sticky="ns")
        mise_en_forme.preparer_tags(
            self._historique_txt,
            ouvrir_lien=self._ouvrir_lien,
            aller_ligne=self._aller_ligne,
            curseur_lien=_curseur_lien(),
        )

        self._lbl_statut = ttk.Label(self, text="", foreground="#666666")
        self._lbl_statut.grid(row=2, column=0, sticky="w", padx=8)

        self._actions = ttk.Frame(self)
        self._actions.grid(row=3, column=0, sticky="ew", padx=6, pady=(2, 0))
        self._boutons_action = [
            ttk.Button(self._actions, style=STYLE_BOUTON, command=commande)
            for commande in (
                self._envoyer_code,
                self._corriger_code,
                self._expliquer_erreur,
                self._expliquer_selection,
                self._nouvelle_conversation,
            )
        ]
        (self._btn_code, self._btn_correction, self._btn_erreur, self._btn_selection, self._btn_nouvelle) = self._boutons_action
        self._actions.bind("<Configure>", self._reorganiser_actions)

        options = ttk.Frame(self)
        options.grid(row=4, column=0, sticky="ew", padx=6, pady=(4, 0))
        options.columnconfigure(1, weight=1)
        self._btn_joindre = ttk.Button(options, style=STYLE_BOUTON_LARGE, command=self._joindre)
        self._btn_joindre.grid(row=0, column=0, sticky="w")
        self._btn_reglages = BoutonReglages(options, STYLE_MENU, self._choix_conversation)
        self._btn_reglages.grid(row=0, column=1, sticky="e")
        self._cadre_pieces = ttk.Frame(self)
        self._cadre_pieces.grid(row=5, column=0, sticky="ew", padx=6)

        bas = ttk.Frame(self)
        bas.grid(row=6, column=0, sticky="ew", padx=6, pady=(2, 6))
        bas.columnconfigure(0, weight=1)
        self._saisie = tk.Text(bas, height=3, width=30, wrap="word", padx=4, pady=4)
        self._saisie.grid(row=0, column=0, sticky="ew")
        self._btn_envoyer = ttk.Button(bas, style=STYLE_BOUTON, command=self._envoyer_ou_arreter)
        self._btn_envoyer.grid(row=0, column=1, sticky="ns", padx=(6, 0))
        self._saisie.bind("<Return>", self._sur_entree)
        self._saisie.bind("<FocusIn>", self._saisie_focus)
        self._saisie.bind("<FocusOut>", self._saisie_perd_focus)
        self._afficher_placeholder()
        self._maj_boutons()

    def _defiler_x(self, debut, fin):
        """Barre de defilement horizontale : visible seulement quand un tableau depasse le panneau."""
        self._defil_x.set(debut, fin)
        if float(debut) <= 0.0 and float(fin) >= 1.0:
            self._defil_x.grid_remove()
        else:
            self._defil_x.grid(row=1, column=0, sticky="ew")

    def _reorganiser_actions(self, _evt=None):
        """Les boutons se rangent sur autant de colonnes que la largeur du panneau le permet."""
        largeur = self._actions.winfo_width()
        pas = max(b.winfo_reqwidth() for b in self._boutons_action) + 4
        colonnes = max(1, min(len(self._boutons_action), largeur // pas)) if largeur > 1 else 2
        if colonnes == self._colonnes_actions:
            return
        self._colonnes_actions = colonnes
        for i in range(len(self._boutons_action)):
            self._actions.columnconfigure(i, weight=1 if i < colonnes else 0, uniform="actions" if i < colonnes else "")
        for i, bouton in enumerate(self._boutons_action):
            bouton.grid(row=i // colonnes, column=i % colonnes, sticky="ew", padx=1, pady=1)

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
        for bouton, cle in zip(
            self._boutons_action,
            ("envoyer_code", "corriger_code", "expliquer_erreur", "expliquer_selection", "nouvelle_conversation"),
        ):
            bouton.configure(text=t(cle), state=libre)
        self._btn_connexion.configure(
            text=t("se_deconnecter") if connexion.est_connecte() else t("se_connecter"),
            state="disabled" if self._occupe else "normal",
        )
        self._btn_joindre.configure(text=t("joindre"), state=libre)
        self._btn_reglages.activer(not self._occupe)
        self._btn_modele.activer(not self._occupe)
        self.after_idle(self._reorganiser_actions)

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
        if not question and self._pieces:
            question = t("question_fichier")
        if question:
            self._lancer_echange(question, None, True)

    def _avec_code(self):
        ctx = contexte.lire()
        if not ctx.a_du_code():
            self._ecrire(t("aucun_code") + "\n", "info")
            return None
        return ctx

    def _envoyer_code(self):
        ctx = self._avec_code()
        if ctx is not None:
            saisi = self._texte_saisi()
            self._lancer_echange(saisi or t("question_code"), ctx, bool(saisi), saisi or t("envoyer_code"))

    def _corriger_code(self):
        ctx = self._avec_code()
        if ctx is not None:
            saisi = self._texte_saisi()
            complement = "\n" + saisi if saisi else ""
            self._lancer_echange(t("question_correction") + complement, ctx, bool(saisi), t("corriger_code") + complement)

    def _expliquer_erreur(self):
        ctx = contexte.lire()
        if not ctx.erreur:
            self._ecrire(t("aucune_erreur") + "\n", "info")
            return
        self._lancer_echange(t("question_erreur"), ctx, False, t("expliquer_erreur"))

    def _expliquer_selection(self):
        ctx = contexte.lire()
        if not ctx.selection.strip():
            self._ecrire(t("aucune_selection") + "\n", "info")
            return
        self._lancer_echange(t("question_selection"), ctx.seulement_selection(), False, t("expliquer_selection"))

    def _nouvelle_conversation(self):
        self._historique = []
        self._question = ""
        self._contexte_envoye = None
        self._reponse = ""
        self._texte_pieces = ""
        self._pieces = []
        self._afficher_pieces()
        self._fil.nouveau()
        self._en_attente = {}
        self._btn_reglages.nouvelle_conversation()
        mise_en_forme.vider(self._historique_txt)

    def _lancer_echange(self, message, ctx, vider_saisie, affichage=None):
        if not connexion.est_connecte():
            self._ecrire(t("err_connexion_requise") + "\n", "erreur")
            return
        if vider_saisie:
            self._saisie.delete("1.0", "end")
        chemins = list(self._pieces)
        self._pieces = []
        self._afficher_pieces()
        self._question = message
        self._contexte_envoye = ctx
        try:
            editeur.effacer_surlignage()
        except tk.TclError:
            pass  # l'onglet a ete ferme entre temps
        self._texte_pieces = ""
        self._reponse = ""
        self._erreur_affichee = False
        self._statut_outil = ""
        self._ecrire("\n")
        self._ecrire((affichage or message) + "\n", "utilisateur")
        if ctx is not None:
            self._ecrire(t("code_envoye") % (ctx.nom or t("sans_nom")) + "\n", "info_droite")
        for chemin in chemins:
            self._ecrire(os.path.basename(chemin) + "\n", "info_droite")
        self._historique_txt.mark_set("debut_reponse", "end-1c")
        self._historique_txt.mark_gravity("debut_reponse", "left")
        self._occupe = True
        self._maj_boutons()
        champs = {
            "longueur_reponse": self._btn_reglages.longueur(),
            "modele": self._btn_modele.identifiant(),
            "effort_reflexion": self._btn_reglages.effort(),
            "message_enregistre": message,
            "client": "thonny",
            "libelles_client": contexte.libelles_boutons(),
        }
        champs.update(self._fil.champs())
        self._echange = EchangeEnCours(self._file)
        en_attente, conversation_id = dict(self._en_attente), self._fil.identifiant
        self._echange.demarrer(
            contexte.construire_message(message, ctx), list(self._historique), champs, chemins,
            avant=lambda: self._enregistrer_choix(conversation_id, en_attente),
        )

    # ---------- fichiers joints ----------
    def _joindre(self):
        if len(self._pieces) >= pieces_jointes.MAX_PIECES:
            self._ecrire(t("err_trop_de_pieces") + "\n", "erreur")
            return
        choix = filedialog.askopenfilenames(parent=self, title=t("choisir_fichier"))
        if not choix:
            return
        for chemin in self.tk.splitlist(choix):
            if len(self._pieces) >= pieces_jointes.MAX_PIECES:
                self._ecrire(t("err_trop_de_pieces") + "\n", "erreur")
                break
            try:
                pieces_jointes.verifier(chemin)
            except ErreurClassinus as e:
                self._ecrire(t(e.cle_texte) % e.detail + "\n", "erreur")
                continue
            if chemin not in self._pieces:
                self._pieces.append(chemin)
        self._afficher_pieces()

    def _retirer_piece(self, chemin):
        if chemin in self._pieces:
            self._pieces.remove(chemin)
        self._afficher_pieces()

    def _afficher_pieces(self):
        for enfant in self._cadre_pieces.winfo_children():
            enfant.destroy()
        for chemin in self._pieces:
            nom = os.path.basename(chemin)
            libelle = "%s  \u00d7" % (nom if len(nom) <= 28 else nom[:27] + "\u2026")
            ttk.Button(self._cadre_pieces, text=libelle, style=STYLE_BOUTON, command=lambda c=chemin: self._retirer_piece(c)).pack(anchor="w", pady=1)

    # ---------- modele et reglages ----------
    def _charger_modeles(self):
        self._file.put(("modeles", conversation.modeles_disponibles()))

    def _choix_conversation(self, genre, valeur):
        """Mode pedagogique ou mode ressources choisi : enregistre sur le serveur, sinon a la prochaine question."""
        self._en_attente[genre] = valeur
        if connexion.est_connecte():
            conversation_id = self._fil.identifiant
            threading.Thread(target=self._enregistrer_choix, args=(conversation_id, {genre: valeur}), daemon=True).start()

    def _enregistrer_choix(self, conversation_id, choix):
        """Dans un fil a part. Les choix bien enregistres sont signales au panneau, qui ne les renverra plus."""
        for genre, valeur in choix.items():
            if parametres_conversation.definir(genre, conversation_id, valeur):
                self._file.put(("choix_enregistre", (conversation_id, genre, valeur)))

    # ---------- actions dans Thonny (toujours sur clic de l'eleve) ----------
    def _boutons_bloc(self, w, code, langage):
        """Les boutons sous un bloc de code de la reponse."""
        cadre = ttk.Frame(w)
        copier = ttk.Button(cadre, text=t("copier"), style=STYLE_BOUTON)
        copier.configure(command=lambda: self._copier(code, copier))
        copier.grid(row=0, column=0, padx=(0, 2))
        if editeur.est_python(langage, code):
            ttk.Button(cadre, text=t("inserer"), style=STYLE_BOUTON, command=lambda: self._confirmer_insertion(code)).grid(row=0, column=1, padx=2)
            ttk.Button(cadre, text=t("nouvel_onglet"), style=STYLE_BOUTON, command=lambda: self._ouvrir_onglet(code)).grid(row=0, column=2, padx=2)
        return cadre

    def _copier(self, code, bouton):
        self.clipboard_clear()
        self.clipboard_append(code)
        bouton.configure(text=t("copie"))

        def restaurer():
            try:
                bouton.configure(text=t("copier"))
            except tk.TclError:
                pass  # la conversation a ete effacee entre temps

        self.after(DUREE_COPIE_MS, restaurer)

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

    def _ouvrir_onglet(self, code):
        try:
            editeur.ouvrir_dans_onglet(code)
            self._ecrire(t("onglet_ok") + "\n", "info")
        except ErreurClassinus as e:
            self._ecrire(t(e.cle_texte) + "\n", "erreur")

    def _aller_ligne(self, numero):
        try:
            editeur.surligner_ligne(numero)
        except ErreurClassinus as e:
            self._ecrire(t(e.cle_texte) + "\n", "erreur")

    def _ouvrir_lien(self, adresse):
        """Annonce le vrai site et n'ouvre le navigateur qu'apres accord de l'eleve."""
        site = adresses.domaine(adresse)
        if site is None:
            return
        apercu = adresse if len(adresse) <= LONGUEUR_APERCU_ADRESSE else adresse[: LONGUEUR_APERCU_ADRESSE - 3] + "..."
        if messagebox.askyesno(t("lien_titre"), t("lien_question") % (site, apercu), parent=self):
            webbrowser.open(adresse)

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
            self._surligner_lignes_citees()
            self._historique.append({"role": "user", "content": self._question + self._texte_pieces})
            self._historique.append({"role": "assistant", "content": self._reponse})
        if arrete:
            self._ecrire("\n" + t("arrete") + "\n", "info")
        elif not self._reponse and not self._erreur_affichee:
            self._ecrire("\n" + t("err_aucune_reponse") + "\n", "erreur")
        self._reponse = ""
        self._echange = None
        self._maj_etat_connexion()

    def _surligner_lignes_citees(self):
        """Surligne dans l'editeur les lignes que la reponse cite, si l'eleve a envoye ce fichier et ne l'a pas change."""
        ctx = self._contexte_envoye
        if ctx is None or not ctx.code.strip():
            return
        numeros = mise_en_forme.lignes_citees(self._reponse)
        if not numeros:
            return
        try:
            editeur.surligner_lignes_citees(numeros, ctx.nom, ctx.code)
        except (ErreurClassinus, tk.TclError):
            pass  # rien a montrer : l'eleve garde les « ligne N » cliquables dans le panneau

    def _mettre_en_forme_reponse(self):
        w = self._historique_txt
        w.configure(state="normal")
        w.delete("debut_reponse", "end-1c")
        mise_en_forme.inserer(w, self._reponse, "assistant", self._boutons_bloc)
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
        elif kind == "meta":
            self._fil.retenir(valeur)
        elif kind == "pieces":
            self._texte_pieces = valeur
        elif kind == "modeles":
            self._btn_modele.definir_modeles(valeur)
            if self._btn_modele.a_des_modeles():
                self._btn_modele.grid()
            else:
                self._btn_modele.grid_remove()
        elif kind == "choix_enregistre":
            conversation_id, genre, enregistre = valeur
            if conversation_id == self._fil.identifiant and self._en_attente.get(genre, enregistre) == enregistre:
                self._en_attente.pop(genre, None)
        elif kind == "confirmation":
            self._erreur_affichee = True
            self._ecrire("\n" + t("err_confirmation") + "\n", "info")
        elif kind == "erreur":
            cle, detail = valeur
            self._erreur_affichee = True
            texte = t(cle)
            if "%s" in texte:
                texte, detail = texte % detail, ""
            self._ecrire("\n" + texte + (" " + t("detail_technique") % detail if detail else "") + "\n", "erreur")
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
