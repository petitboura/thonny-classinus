"""Les deux boutons a menu du panneau : « Modele » (en haut) et « Reglages » (en bas).

Meme contenu que la barre de saisie du site : le modele a part, puis dans Reglages la longueur de
reponse, l'effort, le mode pedagogique et les modes ressources.
"""

import tkinter as tk
from tkinter import ttk

from . import conversation, reglages
from .icones import Icones
from .textes import t

LONGUEUR_MAX_MODELE = 22
ORDRE_DISTRIBUTEURS = ("claude", "gpt", "gemini", "deepseek")
NOMS_DISTRIBUTEURS = {"claude": "Claude", "gpt": "GPT", "gemini": "Gemini", "deepseek": "DeepSeek"}
DISTRIBUTEUR_PAR_DEFAUT = "deepseek"
CHOIX_AUTO = "auto"  # valeur gardee dans les reglages de Thonny pour « Auto »

EFFORTS = ("none", "low", "high", "max")
EFFORT_PAR_DEFAUT = "low"  # le meme que celui du serveur et du site
PERSONAS = ("socratique", "professeur", "tuteur", "examinateur")
MODES_SOURCE = ("recherche", "sur_pieces")


class BoutonModele(ttk.Menubutton):
    """Choix du modele. « Auto » laisse Classinus choisir ; sans choix de l'eleve, c'est DeepSeek."""

    def __init__(self, master, style):
        super().__init__(master, style=style, direction="below")
        self._icones = Icones(self)
        self._modeles = []
        self._variable = tk.StringVar()
        self._menu = tk.Menu(self, tearoff=False)
        self.configure(menu=self._menu)
        self.definir_modeles([])

    def definir_modeles(self, modeles):
        self._modeles = list(modeles)
        self._construire_menu()
        self._variable.set(self._cle_choisie())
        self._maj_bouton()

    def identifiant(self):
        """Le modele a envoyer au serveur, ou None (Auto, ou aucun modele propose)."""
        cle = self._cle_choisie()
        return cle if any(m["modele_id"] == cle for m in self._modeles) else None

    def _par_defaut(self):
        for modele in self._modeles:
            if modele["distributeur"] == DISTRIBUTEUR_PAR_DEFAUT:
                return modele["modele_id"]
        return CHOIX_AUTO

    def _cle_choisie(self):
        """Le choix de l'eleve s'il est encore valable, sinon DeepSeek."""
        garde = reglages.lire("modele")
        if garde == CHOIX_AUTO:
            return CHOIX_AUTO
        if any(m["modele_id"] == garde for m in self._modeles):
            return garde
        return self._par_defaut()

    def _construire_menu(self):
        self._menu.delete(0, "end")
        if not self._modeles:
            return
        self._menu.add_radiobutton(
            label=t("modele_auto"), image=self._icones.obtenir("auto"), compound="left",
            variable=self._variable, value=CHOIX_AUTO, command=self._choisir,
        )
        for distributeur in ORDRE_DISTRIBUTEURS:
            du_distributeur = [m for m in self._modeles if m["distributeur"] == distributeur]
            if not du_distributeur:
                continue
            self._menu.add_separator()
            self._menu.add_command(label=NOMS_DISTRIBUTEURS[distributeur], state="disabled")
            for modele in du_distributeur:
                self._menu.add_radiobutton(
                    label=modele["label"], image=self._icones.obtenir(distributeur), compound="left",
                    variable=self._variable, value=modele["modele_id"], command=self._choisir,
                )

    def _choisir(self):
        reglages.ecrire("modele", self._variable.get())
        self._maj_bouton()

    def _maj_bouton(self):
        cle = self._cle_choisie()
        if not self._modeles:
            texte, icone = NOMS_DISTRIBUTEURS[DISTRIBUTEUR_PAR_DEFAUT], DISTRIBUTEUR_PAR_DEFAUT
        elif cle == CHOIX_AUTO:
            texte, icone = t("modele_auto"), "auto"
        else:
            modele = next((m for m in self._modeles if m["modele_id"] == cle), None)
            texte = modele["label"] if modele else NOMS_DISTRIBUTEURS[DISTRIBUTEUR_PAR_DEFAUT]
            icone = modele["distributeur"] if modele else DISTRIBUTEUR_PAR_DEFAUT
        if len(texte) > LONGUEUR_MAX_MODELE:
            texte = texte[: LONGUEUR_MAX_MODELE - 1] + "…"
        self.configure(text=texte, image=self._icones.obtenir(icone), compound="left")
        # Sans liste de modeles venue du serveur, rien a choisir : le bouton montre seulement le modele utilise.
        self.configure(state="normal" if self._modeles else "disabled")

    def activer(self, actif):
        self.configure(state="normal" if actif and self._modeles else "disabled")


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
