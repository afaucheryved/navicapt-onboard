# Décisions à partir de valeurs fournies : aucun accès matériel ou réseau.
# Seuils et durées sont à définir et valider pour le bateau.


def risque_dessalement(
    inclinaison: float,
    alerte_active: bool,
    seuil_activation: float,
    seuil_arret: float,
) -> bool:
    """Détermine l'alerte"""


def mesure_perimee(
    mesure_ms: int, maintenant_ms: int, age_max_ms: int
) -> bool:
    """Indique si une mesure dépasse l'âge maximal autorisé."""
