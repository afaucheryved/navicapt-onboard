"""Décisions pures, sans lecture matérielle ni commande de sortie."""

import math
from ..compat import ticks_diff


def risque_dessalement(
    inclinaison: float, alerte_active: bool,
    seuil_activation: float, seuil_arret: float,
) -> bool:
    """Applique une hystérésis à la valeur absolue de la gîte."""
    if not (0 <= seuil_arret < seuil_activation <= 180):
        raise ValueError("Seuils d'alerte invalides")
    if not math.isfinite(inclinaison):
        raise ValueError("Inclinaison invalide")
    angle = abs(inclinaison)
    return angle > seuil_arret if alerte_active else angle >= seuil_activation


def mesure_perimee(mesure_ms: int, maintenant_ms: int, age_max_ms: int) -> bool:
    """Détecte une mesure trop ancienne, même au bouclage du compteur."""
    age = ticks_diff(maintenant_ms, mesure_ms)
    return age < 0 or age > age_max_ms
