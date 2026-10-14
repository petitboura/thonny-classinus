"""Couleurs du code Python : celles de l'editeur de Thonny (le theme de syntaxe choisi par l'eleve)."""

import builtins
import io
import keyword
import tokenize

GENRES = ("keyword", "string", "comment", "number", "builtin", "definition")
LANGAGES_COLORES = ("python", "py", "python3", "")

_REPLI = {
    "keyword": "#8959A8",
    "string": "#718C00",
    "comment": "#8E908C",
    "number": "#F5871F",
    "builtin": "#7f0055",
    "definition": "#00008B",
}
_NOMS_INTEGRES = frozenset(nom for nom in dir(builtins) if not nom.startswith("_"))
_CHAINES = {tokenize.STRING}
for _nom in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END"):
    if hasattr(tokenize, _nom):
        _CHAINES.add(getattr(tokenize, _nom))
_SANS_COULEUR = {tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER}


def couleurs():
    """Genre de mot -> couleur du texte, lue dans le theme de Thonny."""
    try:
        from thonny.codeview import get_syntax_options_for_tag
    except ImportError:
        return dict(_REPLI)
    return {genre: get_syntax_options_for_tag(genre).get("foreground") or _REPLI[genre] for genre in GENRES}


def _genre(jeton, precedent):
    if jeton.type == tokenize.COMMENT:
        return "comment"
    if jeton.type in _CHAINES:
        return "string"
    if jeton.type == tokenize.NUMBER:
        return "number"
    if jeton.type == tokenize.NAME:
        if keyword.iskeyword(jeton.string):
            return "keyword"
        if precedent is not None and precedent.string in ("def", "class"):
            return "definition"
        if jeton.string in _NOMS_INTEGRES:
            return "builtin"
    return None


def decouper(code):
    """Le code en morceaux (texte, genre) ; le genre vaut None pour le texte ordinaire."""
    debuts = [0]
    for ligne in code.splitlines(True):
        debuts.append(debuts[-1] + len(ligne))

    def position(rang_colonne):
        rang, colonne = rang_colonne
        return debuts[min(rang - 1, len(debuts) - 1)] + colonne

    zones = []
    precedent = None
    try:
        for jeton in tokenize.generate_tokens(io.StringIO(code).readline):
            genre = _genre(jeton, precedent)
            if jeton.type not in _SANS_COULEUR:
                precedent = jeton
            if genre:
                zones.append((position(jeton.start), position(jeton.end), genre))
    except (tokenize.TokenError, SyntaxError):
        pass  # code incomplet : on garde ce qui a deja ete reconnu

    morceaux = []
    place = 0
    for debut, fin, genre in zones:
        if debut < place or fin > len(code):
            continue
        if debut > place:
            morceaux.append((code[place:debut], None))
        morceaux.append((code[debut:fin], genre))
        place = fin
    if place < len(code):
        morceaux.append((code[place:], None))
    return morceaux
