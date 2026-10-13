"""Envoi d'une question au serveur Classinus et lecture de la reponse en continu.

Tout se passe dans un fil a part. Le fil ne touche jamais a l'interface de
Thonny : il depose des messages dans une file, que le panneau lit regulierement.
Messages deposes : ("texte", str), ("statut", str), ("statut_fin", str),
("confirmation", None), ("fin", None), ("erreur", cle_texte).
"""

import json
import threading
import urllib.error
import urllib.request

from . import connexion, reglages
from .erreurs import ErreurClassinus


class EchangeEnCours:
    def __init__(self, file_messages):
        self.file = file_messages
        self._arret = threading.Event()
        self._reponse = None

    def demarrer(self, message, historique):
        threading.Thread(target=self._executer, args=(message, historique), daemon=True).start()

    def arreter(self):
        self._arret.set()
        reponse = self._reponse
        if reponse is not None:
            try:
                reponse.close()
            except Exception:
                pass
        threading.Thread(target=_prevenir_arret, daemon=True).start()

    def _executer(self, message, historique):
        try:
            base = reglages.lire("backend_url")
            if not base:
                raise ErreurClassinus("err_adresse_manquante")
            corps = json.dumps(
                {
                    "message": message,
                    "agent_id": reglages.lire_defaut("agent_id", "clovis"),
                    "historique": historique,
                    "longueur_reponse": "moyenne",
                }
            ).encode("utf-8")
            req = urllib.request.Request(
                base + "/api/chat",
                data=corps,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                    "Authorization": "Bearer " + connexion.jeton_valide(),
                },
            )
            try:
                self._reponse = urllib.request.urlopen(req, timeout=90)
            except urllib.error.HTTPError as e:
                raise ErreurClassinus(_cle_pour_code(e.code), "HTTP %s" % e.code)
            except (urllib.error.URLError, OSError) as e:
                raise ErreurClassinus("err_reseau", _resume(getattr(e, "reason", None) or e))
            self._lire_flux()
        except ErreurClassinus as e:
            if not self._arret.is_set():
                self.file.put(("erreur", (e.cle_texte, e.detail)))
        except Exception as e:
            if not self._arret.is_set():
                self.file.put(("erreur", ("err_reseau", _resume(e))))
        finally:
            self.file.put(("fin", None))

    def _lire_flux(self):
        for ligne in self._reponse:
            if self._arret.is_set():
                return
            ligne = ligne.decode("utf-8", errors="replace").strip()
            if not ligne.startswith("data:"):
                continue
            donnee = ligne[5:].strip()
            if donnee == "[DONE]":
                return
            try:
                evt = json.loads(donnee)
            except ValueError:
                continue
            kind = evt.get("type")
            if kind == "reponse" and evt.get("texte"):
                self.file.put(("texte", evt["texte"]))
            elif kind == "statut":
                self.file.put(("statut", evt.get("texte", "")))
            elif kind == "statut_termine":
                self.file.put(("statut_fin", evt.get("texte", "")))
            elif kind == "confirmation_requise":
                self.file.put(("confirmation", None))
                return


def _resume(erreur):
    """Nature courte de la panne, pour aider a comprendre sans ouvrir un journal."""
    return ("%s: %s" % (type(erreur).__name__, erreur))[:160]


def _cle_pour_code(code):
    if code == 401:
        return "err_session_expiree"
    if code == 429:
        return "err_trop_de_messages"
    if code >= 500:
        return "err_serveur"
    return "err_generique"


def _prevenir_arret():
    """Dit au serveur d'arreter vraiment le travail en cours (bouton Arreter)."""
    try:
        base = reglages.lire("backend_url")
        req = urllib.request.Request(
            base + "/api/chat/arreter",
            data=b"",
            method="POST",
            headers={"Authorization": "Bearer " + connexion.jeton_valide()},
        )
        urllib.request.urlopen(req, timeout=10).close()
    except Exception:
        pass
