"""Teste la voix gardee prete (protocole ligne base64 -> FIN) avec un faux programme de voix, sans Windows : `python -m unittest discover tests`."""

import os
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest import mock

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

try:
    import thonny  # noqa: F401
except ImportError:
    faux = types.ModuleType("thonny")
    faux.get_workbench = lambda: None
    sys.modules["thonny"] = faux

from thonnycontrib.classinus import lecteur  # noqa: E402

FAUSSE_VOIX = (
    "import sys, base64, time\n"
    "sys.stdout.write('PRET\\n'); sys.stdout.flush()\n"
    "for ligne in sys.stdin:\n"
    "    t = base64.b64decode(ligne.strip()).decode('utf-8')\n"
    "    open(sys.argv[1], 'a', encoding='utf-8').write(t + '\\n')\n"
    "    time.sleep(0.6 if 'long' in t else 0.05)\n"
    "    sys.stdout.write('FIN\\r\\n'); sys.stdout.flush()\n"
)


def _attendre(condition, delai=5):
    fin = time.time() + delai
    while time.time() < fin:
        if condition():
            return True
        time.sleep(0.02)
    return False


class TestLecteur(unittest.TestCase):
    def setUp(self):
        self._dossier = tempfile.TemporaryDirectory()
        self.addCleanup(self._dossier.cleanup)
        self.journal = os.path.join(self._dossier.name, "lu.txt")
        script = os.path.join(self._dossier.name, "voix.py")
        with open(script, "w") as f:
            f.write(FAUSSE_VOIX)
        self.demarrages = []

        patch = mock.patch.object(lecteur, "_commande_chaude", lambda: [sys.executable, script, self.journal])
        patch.start()
        self.addCleanup(patch.stop)

        vrai_popen = subprocess.Popen

        def popen(*args, **kwargs):
            self.demarrages.append(1)  # un vrai programme lance
            return vrai_popen(*args, **kwargs)

        patch2 = mock.patch.object(lecteur.subprocess, "Popen", popen)
        patch2.start()
        self.addCleanup(patch2.stop)
        self.voix = lecteur.Lecteur()
        self.addCleanup(self.voix.fermer)

    def _lu(self):
        with open(self.journal, encoding="utf-8") as f:
            return f.read()

    def test_lecture_avec_voix_prete_et_accents(self):
        self.voix.prechauffer()
        self.assertTrue(_attendre(lambda: self.voix._chaud is not None))
        fini = threading.Event()
        self.assertTrue(self.voix.lire("Voilà l'été, ça marche\nsur deux lignes", lambda p: fini.set()))
        self.assertTrue(self.voix.en_cours())
        self.assertTrue(fini.wait(5))
        self.assertFalse(self.voix.en_cours())
        self.assertEqual(self._lu().strip(), "Voilà l'été, ça marche\nsur deux lignes")
        # la voix reste chargee : une seconde lecture ne relance pas de programme
        self.assertTrue(_attendre(lambda: self.voix._chaud is not None))
        fini.clear()
        self.assertTrue(self.voix.lire("deuxieme", lambda p: fini.set()))
        self.assertTrue(fini.wait(5))
        self.assertEqual(len(self.demarrages), 1)

    def test_arreter_puis_relire(self):
        self.voix.prechauffer()
        self.assertTrue(_attendre(lambda: self.voix._chaud is not None))
        fini = threading.Event()
        self.assertTrue(self.voix.lire("un texte long", lambda p: fini.set()))
        time.sleep(0.2)
        self.assertTrue(self.voix.en_cours())
        self.voix.arreter()
        self.assertFalse(self.voix.en_cours())
        self.assertTrue(fini.wait(5))  # le panneau est prevenu aussi quand on arrete
        self.assertTrue(_attendre(lambda: self.voix._chaud is not None))  # une nouvelle voix est preparee
        fini.clear()
        self.assertTrue(self.voix.lire("apres arret", lambda p: fini.set()))
        self.assertTrue(fini.wait(5))
        self.assertIn("apres arret", self._lu())
        self.assertEqual(len(self.demarrages), 2)

    def test_clic_avant_la_fin_du_chargement(self):
        self.voix._demarrer_chaud()
        fini = threading.Event()
        self.assertTrue(self.voix.lire("tout de suite", lambda p: fini.set()))
        self.assertTrue(fini.wait(5))
        self.assertIn("tout de suite", self._lu())

    def test_sans_voix_prete_retombe_sur_lancien_mode(self):
        with mock.patch.object(lecteur, "_commande_chaude", lambda: None), mock.patch.object(lecteur, "_commande", lambda: None):
            voix = lecteur.Lecteur()
            voix.prechauffer()
            self.assertFalse(voix.lire("bonjour"))
            self.assertFalse(voix.lire("   "))
            voix.fermer()


if __name__ == "__main__":
    unittest.main()
