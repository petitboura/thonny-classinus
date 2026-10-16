"""Lecture a voix haute d'une reponse avec la voix de l'ordinateur : rien a installer sur Windows et Mac.

Windows : PowerShell (System.Speech). Mac : la commande `say`. Linux : espeak-ng ou espeak, si l'un des deux est installe.
Le texte passe par l'entree standard du programme, jamais par la ligne de commande (aucun souci de guillemets).
Il n'y a pas de vraie pause : on arrete, et une nouvelle lecture reprend au debut.

Windows : charger la voix prend plusieurs secondes. On la charge donc une fois a l'avance (`prechauffer`, des l'ouverture
du panneau) dans un PowerShell qui reste ouvert : le clic envoie juste le texte (en base64, une ligne) et le programme
repond `FIN` quand la lecture est terminee. Arreter une lecture ferme ce programme, un nouveau est prepare aussitot.
"""

import base64
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

_SCRIPT_WINDOWS_CHAUD = (
    "[Console]::InputEncoding = [System.Text.Encoding]::UTF8; "
    "Add-Type -AssemblyName System.Speech; "
    "$voix = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
    "[Console]::Out.WriteLine('PRET'); [Console]::Out.Flush(); "
    "while (($ligne = [Console]::In.ReadLine()) -ne $null) { "
    "try { $voix.Speak([System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($ligne))) } catch { }; "
    "[Console]::Out.WriteLine('FIN'); [Console]::Out.Flush() }"
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


def _commande_chaude():
    """La commande de la voix gardee prete en arriere-plan (Windows seulement), ou None."""
    if not sys.platform.startswith("win"):
        return None
    programme = shutil.which("powershell") or shutil.which("pwsh")
    return [programme, "-NoProfile", "-NonInteractive", "-Command", _SCRIPT_WINDOWS_CHAUD] if programme else None


class Lecteur:
    def __init__(self):
        self._processus = None  # ce qui est en train de lire
        self._chaud = None  # la voix deja chargee, en attente d'un texte (Windows)
        self._lecture_chaude = None  # le processus en cours de lecture, s'il vient de la voix prechauffee
        self._verrou = threading.Lock()
        self._verrou_demarrage = threading.Lock()

    def prechauffer(self):
        """Charge la voix a l'avance, sans bloquer (rien ne se passe en dehors de Windows)."""
        if _commande_chaude() is None:
            return
        threading.Thread(target=self._demarrer_chaud, daemon=True).start()

    def _demarrer_chaud(self):
        with self._verrou_demarrage:
            with self._verrou:
                if self._chaud is not None and self._chaud.poll() is None:
                    return
            commande = _commande_chaude()
            if commande is None:
                return
            try:
                processus = subprocess.Popen(
                    commande,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except OSError:
                return
            with self._verrou:
                self._chaud = processus

    def fermer(self):
        """A la fermeture du panneau : arrete la lecture et ferme la voix gardee prete."""
        self.arreter()
        with self._verrou:
            chaud, self._chaud = self._chaud, None
        self._terminer(chaud)

    @staticmethod
    def _terminer(processus):
        if processus is not None and processus.poll() is None:
            try:
                processus.terminate()
            except OSError:
                pass

    def _lire_avec_voix_prete(self, texte, fin):
        """Envoie le texte a la voix deja chargee. False si elle n'est pas disponible (on lit alors a l'ancienne)."""
        with self._verrou:
            chaud, self._chaud = self._chaud, None
        if chaud is None:
            return False
        if chaud.poll() is not None:
            return False
        try:
            chaud.stdin.write(base64.b64encode(texte.encode("utf-8")) + b"\n")
            chaud.stdin.flush()
        except (OSError, ValueError):
            self._terminer(chaud)
            return False
        with self._verrou:
            self._processus = chaud
            self._lecture_chaude = chaud

        def attendre():
            termine = False
            try:
                for ligne in chaud.stdout:
                    if ligne.strip() == b"FIN":
                        termine = True
                        break
            except (OSError, ValueError):
                pass
            with self._verrou:
                if self._processus is chaud:
                    self._processus = None
                if self._lecture_chaude is chaud:
                    self._lecture_chaude = None
                # Lecture finie normalement : la voix reste chargee pour la prochaine fois.
                if termine and chaud.poll() is None and self._chaud is None:
                    self._chaud = chaud
                    chaud_reutilisable = True
                else:
                    chaud_reutilisable = False
            if not chaud_reutilisable:
                self._terminer(chaud)
                self.prechauffer()
            if fin is not None:
                fin(chaud)

        threading.Thread(target=attendre, daemon=True).start()
        return True

    def en_cours(self):
        with self._verrou:
            processus = self._processus
        return processus is not None and processus.poll() is None

    def lire(self, texte, fin=None):
        """Lance la lecture (la precedente s'arrete). `fin(processus)` est appelee dans un autre fil quand le processus se termine.

        Renvoie False quand la voix de l'ordinateur est introuvable ou n'a pas pu demarrer.
        """
        self.arreter()
        if not texte.strip():
            return False
        if self._lire_avec_voix_prete(texte, fin):
            return True
        commande = _commande()
        if commande is None:
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
            etait_chaud = processus is not None and processus is self._lecture_chaude
            if etait_chaud:
                self._lecture_chaude = None
        if processus is not None and processus.poll() is None:
            self._terminer(processus)
            if etait_chaud:
                self.prechauffer()  # la voix chargee est perdue avec le processus : on en prepare une autre
