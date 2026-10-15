"""Les deux boutons a menu du panneau : « Modele » (en haut) et « Reglages » (en bas).

Meme contenu que la barre de saisie du site : le modele a part, puis dans Reglages la longueur de
reponse, l'effort, le mode pedagogique et les modes ressources.
"""

import tkinter as tk
from tkinter import ttk

from . import conversation, reglages
from .icones import Icones
from .textes import langue, t

LONGUEUR_MAX_MODELE = 22
ORDRE_DISTRIBUTEURS = ("claude", "gpt", "gemini", "deepseek")
NOMS_DISTRIBUTEURS = {"claude": "Claude", "gpt": "GPT", "gemini": "Gemini", "deepseek": "DeepSeek"}

EFFORTS = ("none", "low", "high", "max")
EFFORT_PAR_DEFAUT = "low"  # le meme que celui du serveur et du site
PERSONAS = ("socratique", "professeur", "tuteur", "examinateur")
MODES_SOURCE = ("recherche", "sur_pieces")


class BoutonModele(ttk.Menubutton):
    """Choix du modele, avec les memes regles que le bouton du haut du site.

    - Le bouton n'existe que si le serveur propose au moins un modele (le panneau le cache sinon).
    - La liste est groupee par fournisseur, dans l'ordre fixe de ORDRE_DISTRIBUTEURS, seulement
      pour les fournisseurs presents.
    - Le modele actif est le dernier choix de l'eleve s'il est encore dans la liste ; sinon le
      modele par defaut (DeepSeek Flash, voir defauts.json). Il n'y a pas de mode « Auto ».
    - Le serveur revalide de toute facon le modele recu.
    """

    def __init__(self, master, style):
        super().__init__(master, style=style, direction="below")
        self._icones = Icones(self)
        self._modeles = []
        self._bientot = []
        self._variable = tk.StringVar()
        self._menu = tk.Menu(self, tearoff=False)
        self.configure(menu=self._menu)

    def definir_modeles(self, modeles, bientot=()):
        self._modeles = [m for m in modeles if m.get("modele_id")]
        self._bientot = [m for m in bientot if m.get("modele_id")] if self._modeles else []
        self._construire_menu()
        self._variable.set(self.identifiant() or "")
        self._maj_bouton()

    def a_des_modeles(self):
        return bool(self._modeles)

    def identifiant(self):
        """Le modele a envoyer au serveur, ou None quand le serveur n'en propose aucun."""
        if not self._modeles:
            return None
        garde = reglages.lire("modele")
        if any(m["modele_id"] == garde for m in self._modeles):
            return garde
        return self._par_defaut()["modele_id"]

    def _par_defaut(self):
        voulu = reglages.lire_defaut("modele_par_defaut")
        distributeur = reglages.lire_defaut("distributeur_par_defaut")
        for critere in (lambda m: m["modele_id"] == voulu, lambda m: m["distributeur"] == distributeur):
            trouve = next((m for m in self._modeles if critere(m)), None)
            if trouve:
                return trouve
        return self._modeles[0]

    def _modele_actif(self):
        identifiant = self.identifiant()
        return next((m for m in self._modeles if m["modele_id"] == identifiant), None)

    def _construire_menu(self):
        self._menu.delete(0, "end")
        for distributeur in ORDRE_DISTRIBUTEURS:
            du_distributeur = [m for m in self._modeles if m["distributeur"] == distributeur]
            a_venir = [m for m in self._bientot if m["distributeur"] == distributeur]
            if not du_distributeur and not a_venir:
                continue
            if self._menu.index("end") is not None:
                self._menu.add_separator()
            self._menu.add_command(label=NOMS_DISTRIBUTEURS[distributeur], state="disabled")
            for modele in du_distributeur:
                self._menu.add_radiobutton(
                    label=modele["label"], image=self._icones.obtenir(distributeur), compound="left",
                    variable=self._variable, value=modele["modele_id"], command=self._choisir,
                )
            for modele in a_venir:  # grises, jamais choisissables
                self._menu.add_command(
                    label="%s  (%s)" % (modele["label"], self._mot_bientot(modele)),
                    image=self._icones.obtenir(distributeur), compound="left", state="disabled",
                )

    @staticmethod
    def _mot_bientot(modele):
        """Le mot « Bientot » dans la langue du panneau, tel que reglé dans Supabase."""
        mots = modele.get("libelles_bientot") or {}
        return mots.get(langue()) or mots.get("fr") or next(iter(mots.values()), "Bientôt")

    def _choisir(self):
        reglages.ecrire("modele", self._variable.get())
        self._maj_bouton()

    def _maj_bouton(self):
        modele = self._modele_actif()
        if modele is None:
            return
        texte = modele["label"]
        if len(texte) > LONGUEUR_MAX_MODELE:
            texte = texte[: LONGUEUR_MAX_MODELE - 1] + "\u2026"
        self.configure(text=texte, image=self._icones.obtenir(modele["distributeur"]), compound="left")

    def activer(self, actif):
        self.configure(state="normal" if actif else "disabled")


class BoutonReglages(ttk.Menubutton):
    """Longueur de reponse, effort, mode pedagogique et modes ressources."""

    def __init__(self, master, style, au_changement_conversation):
        """`au_changement_conversation(genre, valeur)` est appele pour les deux choix rattaches a la conversation."""
        super().__init__(master, style=style, direction="above", text=t("reglages"))
        self._au_changement = au_changement_conversation
        self._longueur = tk.StringVar(value=self._valeur_gardee("longueur", conversation.LONGUEURS, "moyenne"))
        self._effort = tk.StringVar(value=self._valeur_gardee("effort", EFFORTS, EFFORT_PAR_DEFAUT))
        self._persona = tk.StringVar(value="")
        self._source = tk.StringVar(value="")
        menu = tk.Menu(self, tearoff=False)
        self.configure(menu=menu)
        self._ligne(menu, "reglage_longueur", self._longueur, [(v, t("longueur_" + v)) for v in conversation.LONGUEURS],
                    lambda: reglages.ecrire("longueur", self._longueur.get()))
        self._ligne(menu, "reglage_effort", self._effort, [(v, t("effort_" + v)) for v in EFFORTS],
                    lambda: reglages.ecrire("effort", self._effort.get()))
        self._ligne(menu, "reglage_persona", self._persona,
                    [("", t("persona_aucun"))] + [(v, t("persona_" + v)) for v in PERSONAS],
                    lambda: self._au_changement("persona", self._persona.get() or None))
        self._ligne(menu, "reglage_source", self._source,
                    [("", t("source_aucun"))] + [(v, t("source_" + v)) for v in MODES_SOURCE],
                    lambda: self._au_changement("mode_source", self._source.get() or None))

    @staticmethod
    def _valeur_gardee(cle, valides, defaut):
        garde = reglages.lire(cle)
        return garde if garde in valides else defaut

    @staticmethod
    def _ligne(menu, cle_titre, variable, choix, commande):
        sous = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label=t(cle_titre), menu=sous)
        for valeur, libelle in choix:
            sous.add_radiobutton(label=libelle, variable=variable, value=valeur, command=commande)

    def longueur(self):
        return self._longueur.get()

    def effort(self):
        return self._effort.get()

    def nouvelle_conversation(self):
        """Le mode pedagogique et les modes ressources sont propres a une conversation : on repart de « Aucun »."""
        self._persona.set("")
        self._source.set("")

    def activer(self, actif):
        self.configure(state="normal" if actif else "disabled")
