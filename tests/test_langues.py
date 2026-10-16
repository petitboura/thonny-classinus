"""Verifie que toutes les langues ont les memes textes : `python -m unittest discover tests`."""

import os
import re
import sys
import types
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

try:
    import thonny  # noqa: F401
except ImportError:  # le test n'a pas besoin de Thonny, seulement du paquet
    faux = types.ModuleType("thonny")
    faux.get_workbench = lambda: None
    sys.modules["thonny"] = faux

from thonnycontrib.classinus import textes  # noqa: E402

DOSSIER_PLUGIN = os.path.join(RACINE, "thonnycontrib", "classinus")
APPEL_T = re.compile(r"\bt\(\s*[\"']([A-Za-z0-9_]+)[\"']\s*\)")


class TestLangues(unittest.TestCase):
    def test_au_moins_francais_et_anglais(self):
        self.assertIn("fr", textes.langues_disponibles())
        self.assertIn("en", textes.langues_disponibles())

    def test_memes_textes_dans_toutes_les_langues(self):
        self.assertEqual([], textes.verifier())

    def test_chaque_langue_a_un_nom(self):
        for code in textes.langues_disponibles():
            self.assertTrue(textes.nom_langue(code).strip(), code)

    def test_les_textes_utilises_dans_le_code_existent_partout(self):
        manquants = []
        for nom in sorted(os.listdir(DOSSIER_PLUGIN)):
            if not nom.endswith(".py") or nom == "textes.py":
                continue
            with open(os.path.join(DOSSIER_PLUGIN, nom), encoding="utf-8") as f:
                for cle in APPEL_T.findall(f.read()):
                    for code in textes.langues_disponibles():
                        if cle not in textes.TEXTES[code]:
                            manquants.append("%s : %s (%s)" % (nom, cle, code))
        self.assertEqual([], manquants)


if __name__ == "__main__":
    unittest.main()
