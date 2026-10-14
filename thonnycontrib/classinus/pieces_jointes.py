"""Fichiers que l'eleve joint a sa question (photo, PDF, document) : verification, envoi au serveur,
et texte ajoute au message.

Le serveur fait le travail : une photo est decrite par son modele de vision, un document est lu
(texte extrait, OCR si besoin). Les blocs de texte ajoutes au message sont ceux du site Classinus
(« [Image jointe : ...] », « [Document joint : ...] ») : memes mots, meme comportement.
Rien n'est envoye avant que l'eleve ait clique sur Envoyer.
"""

import json
import mimetypes
import os
import urllib.error
import urllib.request
import uuid

from . import connexion, identite, reglages
from .erreurs import ErreurClassinus

MAX_PIECES = 5
TAILLE_MAX_IMAGE = 5 * 1024 * 1024
TAILLE_MAX_DOCUMENT = 15 * 1024 * 1024
DELAI_ENVOI = 180  # la lecture d'un PDF scanne peut etre longue

_IMAGES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
_NON_PRIS_EN_CHARGE = (
    ".zip", ".rar", ".7z", ".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac",
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".exe", ".dll", ".msi", ".iso",
)


def verifier(chemin):
    """Retourne ("image" ou "document", taille en octets) ou leve ErreurClassinus."""
    nom = os.path.basename(chemin)
    extension = os.path.splitext(nom)[1].lower()
    try:
        taille = os.path.getsize(chemin)
    except OSError:
        raise ErreurClassinus("err_piece_illisible", nom)
    if not os.path.isfile(chemin):
        raise ErreurClassinus("err_piece_illisible", nom)
    if taille == 0:
        raise ErreurClassinus("err_piece_vide", nom)
    if extension in _NON_PRIS_EN_CHARGE:
        raise ErreurClassinus("err_piece_type", nom)
    genre = "image" if extension in _IMAGES else "document"
    if taille > (TAILLE_MAX_IMAGE if genre == "image" else TAILLE_MAX_DOCUMENT):
        raise ErreurClassinus("err_piece_trop_lourde", nom)
    return genre, taille


def _corps_multipart(nom_fichier, contenu, type_mime):
    frontiere = "----classinus" + uuid.uuid4().hex
    sur = nom_fichier.replace('"', "_").replace("\r", " ").replace("\n", " ")
    tete = (
        '--%s\r\nContent-Disposition: form-data; name="fichier"; filename="%s"\r\nContent-Type: %s\r\n\r\n'
        % (frontiere, sur, type_mime)
    ).encode("utf-8")
    corps = tete + contenu + ("\r\n--%s--\r\n" % frontiere).encode("ascii")
    return corps, "multipart/form-data; boundary=" + frontiere


def _poster(chemin_api, nom_fichier, contenu, type_mime):
    base = reglages.lire("backend_url")
    if not base:
        raise ErreurClassinus("err_adresse_manquante")
    corps, type_contenu = _corps_multipart(nom_fichier, contenu, type_mime)
    req = urllib.request.Request(
        base + chemin_api,
        data=corps,
        method="POST",
        headers={
            "Content-Type": type_contenu,
            "User-Agent": identite.agent_utilisateur(),
            "Authorization": "Bearer " + connexion.jeton_valide(),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=DELAI_ENVOI) as reponse:
            return json.loads(reponse.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise ErreurClassinus("err_session_expiree", "HTTP 401")
        raise ErreurClassinus("err_piece_refusee", "%s : %s" % (nom_fichier, _message_serveur(e)))
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise ErreurClassinus("err_reseau", ("%s: %s" % (type(e).__name__, e))[:160])


def _message_serveur(erreur):
    """Le message lisible du serveur (en francais), ou le code HTTP a defaut."""
    try:
        detail = json.loads(erreur.read().decode("utf-8")).get("detail")
        if isinstance(detail, dict) and detail.get("message"):
            return str(detail["message"])[:200]
    except Exception:
        pass
    return "HTTP %s" % erreur.code


def envoyer(chemin):
    """Envoie un fichier. Retourne {"bloc": texte a ajouter au message, "image_url": adresse ou None}."""
    genre, _taille = verifier(chemin)
    nom = os.path.basename(chemin)
    with open(chemin, "rb") as f:
        contenu = f.read()
    if genre == "image":
        type_mime = _IMAGES[os.path.splitext(nom)[1].lower()]
        url = _poster("/api/uploads/image-chat", nom, contenu, type_mime)["url"]
        return {"bloc": "\n\n[Image jointe : %s]" % url, "image_url": url}
    type_mime = mimetypes.guess_type(nom)[0] or "application/octet-stream"
    rep = _poster("/api/uploads/document-chat", nom, contenu, type_mime)
    lien = "\n[Lien réel du fichier : %s]" % rep["url"] if rep.get("url") else ""
    apercu = "\n[Aperçu visuel du fichier (PDF) : %s]" % rep["url_apercu"] if rep.get("url_apercu") else ""
    if not rep.get("lisible"):
        return {
            "bloc": "\n\n[Document joint : %s (illisible)]\nLe contenu de ce fichier n'a pas pu être lu, seul son nom est connu.%s" % (nom, lien),
            "image_url": None,
        }
    tronque = " (tronqué)" if rep.get("tronque") else ""
    return {"bloc": "\n\n[Document joint : %s%s]\n%s%s%s" % (nom, tronque, rep.get("texte", ""), lien, apercu), "image_url": None}
