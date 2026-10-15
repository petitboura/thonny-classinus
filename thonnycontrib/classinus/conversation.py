"""Fil de conversation du panneau, relie a l'historique du site, et choix de modele.

Chaque conversation du panneau a un identifiant : le serveur y range les messages, ils
apparaissent donc dans l'historique du site. `dernier` est l'identifiant du dernier message de
Classinus : il est renvoye a chaque question pour que les messages s'enchainent dans le meme fil.
"""

import json
import urllib.request
import uuid

from . import identite, reglages

LONGUEURS = ("courte", "moyenne", "longue")


class Fil:
    def __init__(self):
        self.nouveau()

    def nouveau(self):
        self.identifiant = str(uuid.uuid4())
        self.dernier = None

    def retenir(self, meta):
        """Evenement « meta » du serveur : identifiant du dernier message de Classinus."""
        valeur = meta.get("message_id_assistant")
        if isinstance(valeur, int) and not isinstance(valeur, bool):
            self.dernier = valeur

    def champs(self):
        champs = {"conversation_id": self.identifiant}
        if self.dernier is not None:
            champs["parent_id"] = self.dernier
        return champs


def _modele(m):
    return {
        "modele_id": m["modele_id"],
        "label": m.get("label") or m["modele_id"],
        "distributeur": m.get("distributeur") or "",
        "libelles_bientot": m.get("libelles_bientot") if isinstance(m.get("libelles_bientot"), dict) else {},
    }


def modeles_selecteur():
    """Les modeles du selecteur : (utilisables, bientot), chacun une liste de {"modele_id", "label", "distributeur"}.

    Meme source que le selecteur du site : les modeles « bientot » (fournisseurs marques Bientot dans
    Supabase) arrivent avec le mot a afficher par langue (cle `libelles_bientot`) et ne sont jamais
    choisissables. Appel public, sans connexion. Toute panne donne deux listes vides : le panneau
    fonctionne alors avec le modele par defaut, comme avant.
    """
    base = reglages.lire("backend_url")
    if not base:
        return [], []
    try:
        req = urllib.request.Request(
            "%s/api/agents/%s" % (base, reglages.lire_defaut("agent_id", "clovis")),
            headers={"User-Agent": identite.agent_utilisateur(), "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as reponse:
            donnees = json.loads(reponse.read().decode("utf-8"))
        return tuple(
            [_modele(m) for m in donnees.get(cle) or [] if isinstance(m, dict) and m.get("modele_id")]
            for cle in ("modeles_disponibles", "modeles_bientot")
        )
    except Exception:
        return [], []
