"""Page Classinus dans Outils > Options de Thonny."""

from tkinter import ttk

from thonny import get_workbench

from . import reglages
from .textes import definir_langue, langues_disponibles, t


class PageReglages(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.columnconfigure(1, weight=1)
        self._champs = {}
        lignes = (("backend_url", "reglage_backend"), ("supabase_url", "reglage_supabase"), ("langue", "reglage_langue"))
        for i, (cle, libelle) in enumerate(lignes):
            texte = t(libelle) % ", ".join(("auto",) + langues_disponibles()) if cle == "langue" else t(libelle)
            ttk.Label(self, text=texte).grid(row=i, column=0, sticky="w", padx=6, pady=4)
            champ = ttk.Entry(self, width=40)
            champ.insert(0, get_workbench().get_option("classinus." + cle) or "")
            champ.grid(row=i, column=1, sticky="ew", padx=6, pady=4)
            self._champs[cle] = champ
        ttk.Label(self, text=t("reglage_info"), foreground="#666666").grid(row=len(lignes), column=0, columnspan=2, sticky="w", padx=6, pady=8)

    def apply(self):
        for cle, champ in self._champs.items():
            reglages.ecrire(cle, champ.get())
        definir_langue(reglages.lire("langue"), get_workbench().get_option("general.language") or "")
        return True
