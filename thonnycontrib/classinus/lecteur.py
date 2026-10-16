"""Lecture a voix haute d'une reponse avec la voix de l'ordinateur : rien a installer sur Windows et Mac.

Windows : PowerShell (System.Speech). Mac : la commande `say`. Linux : espeak-ng ou espeak, si l'un des deux est installe.
Le texte passe par l'entree standard du programme, jamais par la ligne de commande (aucun souci de guillemets).
Il n'y a pas de vraie pause : on arrete, et une nouvelle lecture reprend au debut.
"""

import re
import shutil
import subprocess
import sys
import threading

_BLOC_CODE = re.compile(r"```.*?(?:```|\Z)", re.DOTALL)
_TABLEAU = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)
_LIEN = re.compile(r"\[([^\]\n]+)\]\(https?://[^\s)]+\)")
_ADRESSE = re.compile(r"https?://\S+")
_CODE_EN_LIGNE = re.compile(r"`([^`\n]*)`")
_DEBUT_LIGNE = re.compile(r"^\s*(?:#+\s*|[-*\u2022]\s+)", re.MULTILINE)
_ETOILES_DE_MISE_EN_FORME = re.compile(r"\*+(?=\S)|(?<=\S)\*+")
_LIGNES_VIDES = re.compile(r"\n(?:[ \t]*\n)+")

_SCRIPT_WINDOWS = (
    "[Console]::InputEncoding = [System.Text.Encoding]::UTF8; "
    "Add-Type -AssemblyName System.Speech; "
    "$voix = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
    "$voix.Speak([Console]::In.ReadToEnd())"
)


def texte_a_lire(texte):
    """La reponse sans ce qui se lit mal : blocs de code, tableaux, adresses, signes de mise en forme."""
    texte = _BLOC_CODE.sub(" ", texte)
    texte = _TABLEAU.sub(" ", texte)
    texte = _LIEN.sub(r"\1", texte)
    texte = _ADRESSE.sub(" ", texte)
    texte = _CODE_EN_LIGNE.sub(r"\1", texte)
    texte = _DEBUT_LIGNE.sub("", texte)
    texte = _ETOILES_DE_MISE_EN_FORME.sub("", texte)
    return _LIGNES_VIDES.sub("\n", texte).strip()


def _commande():
    """La commande qui lit le texte recu sur son entree standard, ou None si l'ordinateur n'en a pas."""
    if sys.platform.startswith("win"):
        programme = shutil.which("powershell") or shutil.which("pwsh")
        return [programme, "-NoProfile", "-NonInteractive", "-Command", _SCRIPT_WINDOWS] if programme else None
    if sys.platform == "darwin":
        programme = shutil.which("say")
        return [programme] if programme else None
    for nom in ("espeak-ng", "espeak"):
        programme = shutil.which(nom)
        if programme:
            return [programme, "--stdin"]
    return None


class Lecteur:
    def __init__(self):
        self._processus = None
        self._verrou = threading.Lock()

    def en_cours(self):
        with self._verrou:
            processus = self._processus
        return processus is not None and processus.poll() is None

    def lire(self, texte, fin=None):
        """Lance la lecture (la precedente s'arrete). `fin(processus)` est appelee dans un autre fil quand le processus se termine.

        Renvoie False quand la voix de l'ordinateur est introuvable ou n'a pas pu demarrer.
        """
        self.arreter()
        commande = _commande()
        if commande is None or not texte.strip():
            return False
        try:
            processus = subprocess.Popen(
                commande,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError:
            return False
        with self._verrou:
            self._processus = processus

        def attendre():
            try:
                processus.communicate(texte.encode("utf-8"))
            except Exception:
                pass
            if fin is not None:
                fin(processus)

        threading.Thread(target=attendre, daemon=True).start()
        return True

    def arreter(self):
        with self._verrou:
            processus, self._processus = self._processus, None
        if processus is not None and processus.poll() is None:
            try:
                processus.terminate()
            except OSError:
                pass
