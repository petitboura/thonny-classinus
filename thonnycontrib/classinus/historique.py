"""Historique des conversations : la meme liste que celle du site (Epingles, puis groupes par date).

Les conversations viennent des memes routes que le site. Une page de conversations arrive du plus
recemment actif au plus ancien ; les epingles ne viennent qu'avec la premiere page.
"""

import datetime
import json
import urllib.parse
import urllib.request

from . import connexion, identite, reglages
from .textes import t

DELAI = 15
TAILLE_PAGE = 30


def _demander(chemin, parametres=None, methode="GET", corps=None):
    base = reglages.lire("backend_url")
    adresse = "%s%s" % (base, chemin)
    if parametres:
        adresse += "?" + urllib.parse.urlencode(parametres)
    entetes = {
        "User-Agent": identite.agent_utilisateur(),
        "Accept": "application/json",
        "Authorization": "Bearer " + connexion.jeton_valide(),
    }
    donnees = None
    if corps is not None:
        donnees = json.dumps(corps).encode("utf-8")
        entetes["Content-Type"] = "application/json"
    req = urllib.request.Request(adresse, data=donnees, method=methode, headers=entetes)
    with urllib.request.urlopen(req, timeout=DELAI) as reponse:
        brut = reponse.read().decode("utf-8")
    return json.loads(brut) if brut.strip() else None


def _adresse_fil(cle):
    return "/api/historique/%s/fils/%s" % (_agent(), urllib.parse.quote(cle, safe=""))


def epingler(cle, epingle):
    _demander(_adresse_fil(cle), methode="PATCH", corps={"epingle": bool(epingle)})


def renommer(cle, titre):
    _demander(_adresse_fil(cle), methode="PATCH", corps={"titre": titre})


def supprimer(cle):
    _demander(_adresse_fil(cle), methode="DELETE")


def _agent():
    return urllib.parse.quote(reglages.lire_defaut("agent_id", "clovis"), safe="")


def page_de_fils(curseur=None):
    """Une page de conversations : {"epingles": [...], "fils": [...], "suivant": curseur ou None}."""
    parametres = {"limite": TAILLE_PAGE}
    if curseur:
        parametres.update(curseur)
    donnees = _demander("/api/historique/%s/fils" % _agent(), parametres)
    return {
        "epingles": donnees.get("epingles") or [],
        "fils": donnees.get("fils") or [],
        "suivant": donnees.get("suivant"),
    }


def messages_du_fil(cle):
    """Les messages de la conversation, dans l'ordre, sur la branche la plus recente."""
    lignes = _demander("/api/historique/%s/conversations/%s" % (_agent(), urllib.parse.quote(cle, safe="")))
    return branche_recente([ligne for ligne in lignes if isinstance(ligne, dict)])


def branche_recente(lignes):
    """Le site garde toutes les versions d'un message : on suit la branche du message le plus recent."""
    par_id = {ligne["id"]: ligne for ligne in lignes if isinstance(ligne.get("id"), int)}
    if not par_id or len(par_id) != len(lignes):
        return lignes
    courant = max(lignes, key=lambda ligne: (ligne.get("created_at") or "", ligne["id"]))
    chemin, vus = [], set()
    while courant is not None and courant["id"] not in vus:
        vus.add(courant["id"])
        chemin.append(courant)
        courant = par_id.get(courant.get("parent_id"))
    return list(reversed(chemin))


# ---------- groupes par date, memes regles que le site ----------
def _jour(d):
    return datetime.date(d.year, d.month, d.day)


def _date(iso):
    try:
        d = datetime.datetime.fromisoformat((iso or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    return d.astimezone().replace(tzinfo=None) if d.tzinfo else d


def groupe_de_date(iso, maintenant):
    """(cle, libelle) du groupe d'un fil : jours recents, semaines, mois dernier, puis un groupe par mois."""
    d = _date(iso)
    if d is None:
        return "inconnu", t("histo_plus_ancien")
    ecart = max(0, (_jour(maintenant) - _jour(d)).days)
    if ecart == 0:
        return "aujourdhui", t("histo_aujourdhui")
    if ecart == 1:
        return "hier", t("histo_hier")
    if ecart == 2:
        return "avant-hier", t("histo_avant_hier")
    mois_prec = maintenant.month - 1 or 12
    annee_prec = maintenant.year - (1 if maintenant.month == 1 else 0)
    dernier_jour = (datetime.date(maintenant.year, maintenant.month, 1) - datetime.timedelta(days=1)).day
    meme_jour = datetime.date(annee_prec, mois_prec, min(maintenant.day, dernier_jour))
    if ecart <= (_jour(maintenant) - meme_jour).days:
        semaines = -(-ecart // 7)
        return "sem-%d" % semaines, t("histo_semaines") % semaines
    ecoules = (maintenant.year - d.year) * 12 + (maintenant.month - d.month)
    if ecoules == 1:
        return "mois-dernier", t("histo_mois_dernier")
    nom = t("histo_mois").split("|")[d.month - 1]
    libelle = nom if d.year == maintenant.year else "%s %d" % (nom, d.year)
    return "mois-%d-%d" % (d.year, d.month), libelle


def regrouper_par_date(fils, maintenant=None):
    """Fils deja tries du plus recent au plus ancien -> [(cle, libelle, [fils])] ; jamais de groupe vide."""
    maintenant = maintenant or datetime.datetime.now()
    groupes = []
    for fil in fils:
        cle, libelle = groupe_de_date(fil.get("derniere_activite"), maintenant)
        if groupes and groupes[-1][0] == cle:
            groupes[-1][2].append(fil)
        else:
            groupes.append((cle, libelle, [fil]))
    return groupes
