"""Connexion au compte Classinus via le navigateur (OAuth 2.1 avec PKCE).

Le service de connexion est celui deja utilise par le connecteur de Classinus.
Le mot de passe de l'eleve n'est jamais saisi dans Thonny : il valide dans son
navigateur, Thonny recoit seulement un code, puis un jeton.
"""

import base64
import hashlib
import json
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import identite, jeton, reglages
from .erreurs import ErreurClassinus
from .textes import t

DELAI_RESEAU = 20
DELAI_VALIDATION = 180


def _requete_json(url, donnees=None, formulaire=None):
    corps = None
    entetes = {"Accept": "application/json", "User-Agent": identite.agent_utilisateur()}
    if donnees is not None:
        corps = json.dumps(donnees).encode("utf-8")
        entetes["Content-Type"] = "application/json"
    elif formulaire is not None:
        corps = urllib.parse.urlencode(formulaire).encode("utf-8")
        entetes["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=corps, headers=entetes, method="POST" if corps else "GET")
    try:
        with urllib.request.urlopen(req, timeout=DELAI_RESEAU) as rep:
            return json.loads(rep.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code in (400, 401):
            raise ErreurClassinus("err_session_expiree")
        raise ErreurClassinus("err_service_connexion")
    except (urllib.error.URLError, OSError, ValueError):
        raise ErreurClassinus("err_reseau")


def _decouvrir(base):
    """Adresses du service de connexion, lues dans sa fiche officielle."""
    for chemin in ("/.well-known/oauth-authorization-server/auth/v1", "/auth/v1/.well-known/oauth-authorization-server"):
        try:
            meta = _requete_json(base + chemin)
        except ErreurClassinus:
            continue
        if meta.get("authorization_endpoint") and meta.get("token_endpoint"):
            return meta
    raise ErreurClassinus("err_service_connexion")


def _pkce():
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    return verifier, challenge


class _Retour(BaseHTTPRequestHandler):
    resultat = None
    etat_attendu = ""
    # Les navigateurs ouvrent parfois une connexion sans rien envoyer : on la lache vite.
    timeout = 10

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        p = urllib.parse.parse_qs(url.query)
        ok = bool(p.get("code")) and p.get("state", [""])[0] == self.etat_attendu
        if ok:
            type(self).resultat = {"code": p["code"][0]}
        else:
            type(self).resultat = {"erreur": True}
        cle = "navigateur_ok" if ok else "navigateur_echec"
        page = "<!doctype html><meta charset=utf-8><title>%s</title><body style=\"font-family:sans-serif;padding:2rem\"><p>%s</p></body>" % (
            t("navigateur_titre"),
            t(cle),
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(page.encode("utf-8"))

    def log_message(self, *args):
        pass


def _ouvrir_serveur_retour(port_prefere, etat):
    """Petit serveur local, uniquement joignable depuis cet ordinateur.

    Une connexion par fil, pour qu'une connexion vide du navigateur ne bloque pas la vraie reponse.
    """
    classe = type("RetourLocal", (_Retour,), {"resultat": None, "etat_attendu": etat})
    for port in (port_prefere, 0):
        try:
            return ThreadingHTTPServer(("127.0.0.1", port), classe), classe
        except OSError:
            continue
    raise ErreurClassinus("err_connexion_echec")


def _client_id(meta, redirect_uri):
    """Un identifiant par adresse de retour, enregistre une seule fois puis garde."""
    donnees = jeton.lire() or {}
    clients = donnees.get("clients", {})
    if redirect_uri in clients:
        return clients[redirect_uri]
    if not meta.get("registration_endpoint"):
        raise ErreurClassinus("err_service_connexion")
    rep = _requete_json(
        meta["registration_endpoint"],
        donnees={
            "client_name": "Thonny (Classinus)",
            "redirect_uris": [redirect_uri],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        },
    )
    cid = rep.get("client_id")
    if not cid:
        raise ErreurClassinus("err_service_connexion")
    clients[redirect_uri] = cid
    donnees["clients"] = clients
    jeton.ecrire(donnees)
    return cid


def _enregistrer_jetons(rep, client_id, redirect_uri, ancien=None):
    if not rep.get("access_token"):
        raise ErreurClassinus("err_connexion_echec")
    donnees = dict(ancien or jeton.lire() or {})
    donnees.update(
        {
            "access_token": rep["access_token"],
            "refresh_token": rep.get("refresh_token") or donnees.get("refresh_token", ""),
            "expires_at": time.time() + int(rep.get("expires_in", 3600)),
            "client_id": client_id,
            "redirect_uri": redirect_uri,
        }
    )
    jeton.ecrire(donnees)
    return donnees


def se_connecter(annule=None):
    """Bloquant (a lancer dans un fil). Ouvre le navigateur et attend la validation."""
    base = reglages.lire("supabase_url")
    if not base:
        raise ErreurClassinus("err_service_connexion")
    meta = _decouvrir(base)
    etat = secrets.token_urlsafe(24)
    serveur, classe = _ouvrir_serveur_retour(int(reglages.lire_defaut("port_retour", 0) or 0), etat)
    try:
        redirect_uri = "http://127.0.0.1:%d/callback" % serveur.server_address[1]
        client_id = _client_id(meta, redirect_uri)
        verifier, challenge = _pkce()
        adresse = meta["authorization_endpoint"] + "?" + urllib.parse.urlencode(
            {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": reglages.lire_defaut("scope", "openid profile email"),
                "state": etat,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
        webbrowser.open(adresse)
        serveur.timeout = 0.5
        limite = time.time() + DELAI_VALIDATION
        while classe.resultat is None:
            if annule is not None and annule():
                raise ErreurClassinus("err_connexion_echec")
            if time.time() > limite:
                raise ErreurClassinus("err_connexion_delai")
            serveur.handle_request()
        if "code" not in classe.resultat:
            raise ErreurClassinus("err_connexion_echec")
        rep = _requete_json(
            meta["token_endpoint"],
            formulaire={
                "grant_type": "authorization_code",
                "code": classe.resultat["code"],
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "code_verifier": verifier,
            },
        )
        _enregistrer_jetons(rep, client_id, redirect_uri)
    finally:
        serveur.server_close()


_verrou = threading.Lock()


def jeton_valide():
    """Retourne un jeton d'acces valide, en le renouvelant si besoin. Leve ErreurClassinus sinon."""
    with _verrou:
        donnees = jeton.lire()
        if not donnees or not donnees.get("access_token"):
            raise ErreurClassinus("err_connexion_requise")
        if not jeton.est_expire(donnees):
            return donnees["access_token"]
        if not donnees.get("refresh_token"):
            raise ErreurClassinus("err_session_expiree")
        base = reglages.lire("supabase_url")
        meta = _decouvrir(base)
        try:
            rep = _requete_json(
                meta["token_endpoint"],
                formulaire={
                    "grant_type": "refresh_token",
                    "refresh_token": donnees["refresh_token"],
                    "client_id": donnees.get("client_id", ""),
                },
            )
        except ErreurClassinus as e:
            if e.cle_texte == "err_session_expiree":
                jeton.effacer()
            raise
        return _enregistrer_jetons(rep, donnees.get("client_id", ""), donnees.get("redirect_uri", ""), donnees)["access_token"]


def est_connecte():
    donnees = jeton.lire()
    return bool(donnees and donnees.get("access_token") and (donnees.get("refresh_token") or not jeton.est_expire(donnees)))


def se_deconnecter():
    donnees = jeton.lire() or {}
    # On garde les identifiants de client enregistres, on retire seulement la session.
    jeton.effacer()
    if donnees.get("clients"):
        jeton.ecrire({"clients": donnees["clients"]})
