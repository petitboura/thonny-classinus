"""Tous les textes affiches, par langue. Aucune chaine visible ailleurs."""

TEXTES = {
    "fr": {
        "titre_panneau": "Classinus",
        "non_connecte": "Non connecté",
        "connecte": "Connecté",
        "se_connecter": "Se connecter",
        "se_deconnecter": "Se déconnecter",
        "connexion_en_cours": "Connexion en cours, termine dans ton navigateur...",
        "envoyer": "Envoyer",
        "arreter": "Arrêter",
        "placeholder": "Pose ta question à Classinus (Entrée pour envoyer, Maj+Entrée pour un retour à la ligne)",
        "toi": "Toi",
        "classinus": "Classinus",
        "reflechit": "Classinus réfléchit",
        "arrete": "Réponse arrêtée.",
        "connecte_ok": "Tu es connecté à Classinus.",
        "deconnecte_ok": "Tu es déconnecté.",
        "titre_reglages": "Classinus",
        "reglage_backend": "Adresse du serveur Classinus",
        "reglage_supabase": "Adresse du service de connexion",
        "reglage_langue": "Langue du panneau (auto, fr, en)",
        "reglage_info": "Laisse vide pour garder les valeurs par défaut du plugin.",
        "navigateur_titre": "Classinus",
        "navigateur_ok": "Connexion réussie. Tu peux fermer cet onglet et revenir dans Thonny.",
        "navigateur_echec": "La connexion a échoué. Reviens dans Thonny et réessaie.",
        "err_adresse_manquante": "L'adresse du serveur Classinus n'est pas réglée. Ouvre Outils > Options > Classinus.",
        "err_connexion_requise": "Connecte-toi d'abord à Classinus avec le bouton en haut du panneau.",
        "err_session_expiree": "Ta connexion a expiré. Clique sur Se connecter pour recommencer.",
        "err_reseau": "Impossible de joindre Classinus. Vérifie ta connexion internet puis réessaie.",
        "err_trop_de_messages": "Tu envoies trop de messages à la suite. Attends une minute puis réessaie.",
        "err_serveur": "Classinus a un souci en ce moment. Réessaie dans un instant.",
        "err_connexion_echec": "La connexion à Classinus a échoué. Réessaie.",
        "err_connexion_delai": "Le délai de connexion est dépassé. Clique sur Se connecter pour recommencer.",
        "err_service_connexion": "Le service de connexion de Classinus ne répond pas comme prévu. Réessaie plus tard.",
        "err_confirmation": "Classinus demande une confirmation pour une action. Ouvre Classinus sur le site pour la valider.",
        "err_generique": "Une erreur est survenue. Réessaie.",
    },
    "en": {
        "titre_panneau": "Classinus",
        "non_connecte": "Not signed in",
        "connecte": "Signed in",
        "se_connecter": "Sign in",
        "se_deconnecter": "Sign out",
        "connexion_en_cours": "Signing in, finish in your browser...",
        "envoyer": "Send",
        "arreter": "Stop",
        "placeholder": "Ask Classinus a question (Enter to send, Shift+Enter for a new line)",
        "toi": "You",
        "classinus": "Classinus",
        "reflechit": "Classinus is thinking",
        "arrete": "Answer stopped.",
        "connecte_ok": "You are signed in to Classinus.",
        "deconnecte_ok": "You are signed out.",
        "titre_reglages": "Classinus",
        "reglage_backend": "Classinus server address",
        "reglage_supabase": "Sign-in service address",
        "reglage_langue": "Panel language (auto, fr, en)",
        "reglage_info": "Leave empty to keep the plugin defaults.",
        "navigateur_titre": "Classinus",
        "navigateur_ok": "Signed in. You can close this tab and go back to Thonny.",
        "navigateur_echec": "Sign-in failed. Go back to Thonny and try again.",
        "err_adresse_manquante": "The Classinus server address is not set. Open Tools > Options > Classinus.",
        "err_connexion_requise": "Sign in to Classinus first with the button at the top of the panel.",
        "err_session_expiree": "Your session has expired. Click Sign in to start again.",
        "err_reseau": "Cannot reach Classinus. Check your internet connection and try again.",
        "err_trop_de_messages": "You are sending too many messages in a row. Wait a minute and try again.",
        "err_serveur": "Classinus has a problem right now. Try again in a moment.",
        "err_connexion_echec": "Signing in to Classinus failed. Try again.",
        "err_connexion_delai": "Sign-in timed out. Click Sign in to start again.",
        "err_service_connexion": "The Classinus sign-in service is not answering as expected. Try again later.",
        "err_confirmation": "Classinus needs a confirmation for an action. Open Classinus on the website to approve it.",
        "err_generique": "Something went wrong. Try again.",
    },
}

_langue = "fr"


def definir_langue(choix, langue_thonny=""):
    """choix: 'auto', 'fr', 'en' ou vide. En auto on suit la langue de Thonny."""
    global _langue
    brut = (choix or "").strip().lower()
    if brut in TEXTES:
        _langue = brut
        return
    code = (langue_thonny or "").lower()[:2]
    _langue = code if code in TEXTES else "fr"


def t(cle):
    return TEXTES.get(_langue, TEXTES["fr"]).get(cle) or TEXTES["fr"].get(cle, cle)
