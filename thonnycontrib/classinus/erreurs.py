"""Erreur du plugin portant une cle de texte (traduisible), jamais un message brut.

`detail` est un complement technique court (code HTTP, nature de la panne), affiche a la suite du texte.
"""


class ErreurClassinus(Exception):
    def __init__(self, cle_texte, detail=""):
        super().__init__(cle_texte)
        self.cle_texte = cle_texte
        self.detail = detail
