"""Dictee : le micro de l'ordinateur enregistre, puis le serveur transcrit l'enregistrement en un seul envoi.

La bibliotheque `sounddevice` donne acces au micro (elle est installee avec le plugin). L'enregistrement est
envoye une seule fois, quand l'eleve arrete : le texte arrive d'un coup et la bibliotheque de l'eleve ne recoit
qu'un seul fichier audio. Le serveur transcrit en francais.
"""

import io
import json
import threading
import urllib.error
import urllib.request
import wave

from . import connexion, identite, pieces_jointes, reglages
from .erreurs import ErreurClassinus

FREQUENCE = 16000  # 16 000 mesures par seconde, mono, 16 bits : la qualite attendue par la transcription
DUREE_MAX_SECONDES = 300  # 9,6 Mo d'audio, bien sous la limite de 20 Mo du serveur
DELAI_ENVOI = 120


class Dictee:
    def __init__(self):
        self._flux = None
        self._morceaux = []
        self._verrou = threading.Lock()

    def active(self):
        return self._flux is not None

    def demarrer(self):
        """Ouvre le micro. Leve ErreurClassinus si la bibliotheque ou le micro manque."""
        try:
            import sounddevice
        except Exception:  # bibliotheque absente, ou composant systeme manquant (PortAudio sous Linux)
            raise ErreurClassinus("err_dictee_bibliotheque")
        self._morceaux = []

        def recevoir(donnees, _images, _temps, _etat):
            with self._verrou:
                self._morceaux.append(bytes(donnees))

        try:
            flux = sounddevice.RawInputStream(samplerate=FREQUENCE, channels=1, dtype="int16", callback=recevoir)
            flux.start()
        except Exception:
            raise ErreurClassinus("err_dictee_micro")
        self._flux = flux

    def arreter(self):
        """Ferme le micro et rend l'enregistrement (fichier WAV en octets), ou None s'il est vide."""
        flux, self._flux = self._flux, None
        if flux is not None:
            try:
                flux.stop()
                flux.close()
            except Exception:
                pass
        with self._verrou:
            son = b"".join(self._morceaux)
            self._morceaux = []
        if not son:
            return None
        tampon = io.BytesIO()
        with wave.open(tampon, "wb") as fichier:
            fichier.setnchannels(1)
            fichier.setsampwidth(2)
            fichier.setframerate(FREQUENCE)
            fichier.writeframes(son)
        return tampon.getvalue()


def transcrire(wav):
    """Envoie l'enregistrement au serveur et rend le texte. Leve ErreurClassinus (a lancer dans un fil a part)."""
    base = reglages.lire("backend_url")
    if not base:
        raise ErreurClassinus("err_adresse_manquante")
    corps, type_contenu = pieces_jointes._corps_multipart("dictee.wav", wav, "audio/wav")
    req = urllib.request.Request(
        base + "/api/uploads/audio-chat",
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
            texte = (json.loads(reponse.read().decode("utf-8")).get("texte") or "").strip()
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise ErreurClassinus("err_session_expiree", "HTTP 401")
        raise ErreurClassinus("err_dictee_echec", pieces_jointes._message_serveur(e))
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise ErreurClassinus("err_reseau", ("%s: %s" % (type(e).__name__, e))[:160])
    if not texte:
        raise ErreurClassinus("err_dictee_rien_compris")
    return texte
