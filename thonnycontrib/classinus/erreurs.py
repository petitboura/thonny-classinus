"""Erreur du plugin portant une cle de texte (traduisible), jamais un message brut."""


class ErreurClassinus(Exception):
    def __init__(self, cle_texte):
        super().__init__(cle_texte)
        self.cle_texte = cle_texte
