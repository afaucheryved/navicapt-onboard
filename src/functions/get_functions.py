"""Acquisition et calculs physiques ; les pilotes sont fournis en paramètres."""

import math


def vecteur_valide(valeur: tuple) -> tuple:
    """Vérifie les trois composantes finies d'une mesure."""
    if len(valeur) != 3 or not all(math.isfinite(v) for v in valeur):
        raise ValueError("Vecteur capteur invalide")
    return tuple(valeur)


def get_boussole_bateau_data(capteurs: object) -> tuple:
    """Lit le champ magnétique du bateau en µT."""
    return vecteur_valide(capteurs.read_bateau())


def get_boussole_bome_data(capteurs: object) -> tuple:
    """Lit le champ magnétique de la bôme en µT."""
    return vecteur_valide(capteurs.read_bome())


def get_accelerometre_data(capteurs: object) -> tuple:
    """Lit l'accélération (x, y, z) en m/s²."""
    return vecteur_valide(capteurs.read_acceleration())


def get_bouton_data(capteurs: object) -> bool:
    """Lit l'appui brut avant anti-rebond."""
    return bool(capteurs.read_button())


def get_bateau_cap(champ_magnetique: tuple) -> float:
    """Calcule le cap magnétique horizontal entre 0° et 360° exclus."""
    x, y, _ = vecteur_valide(champ_magnetique)
    if x * x + y * y < 1e-12:
        raise ValueError("Champ magnétique horizontal nul")
    return math.degrees(math.atan2(y, x)) % 360


def get_bome_cap(champ_magnetique: tuple) -> float:
    """Calcule le cap magnétique horizontal de la bôme."""
    return get_bateau_cap(champ_magnetique)


def get_bome_angle(cap_bateau: float, cap_bome: float, offset: float) -> float:
    """Calcule l'angle relatif dans [-180°, 180°[."""
    if not all(math.isfinite(v) for v in (cap_bateau, cap_bome, offset)):
        raise ValueError("Cap ou référence invalide")
    return (cap_bome - cap_bateau - offset + 180) % 360 - 180


def get_inclinaison(acceleration: tuple) -> float:
    """Estime la gîte signée autour de l'axe x, en degrés."""
    x, y, z = vecteur_valide(acceleration)
    if x * x + y * y + z * z < 1e-6 or y * y + z * z < 1e-12:
        raise ValueError("Accélération inexploitable pour la gîte")
    return math.degrees(math.atan2(y, z))


def filtrer_passe_bas(valeur: float, precedente: float, alpha: float) -> float:
    """Applique un lissage exponentiel, avec alpha dans ]0, 1]."""
    if not 0 < alpha <= 1 or not all(math.isfinite(v) for v in (valeur, precedente)):
        raise ValueError("Paramètres du filtre invalides")
    return precedente + alpha * (valeur - precedente)


async def get_meteo_data(
    latitude: float, longitude: float, timeout_ms: int, fournisseur: object
) -> dict:
    """Récupère la météo depuis le fournisseur configuré."""
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180 or timeout_ms <= 0:
        raise ValueError("Coordonnées ou délai météo invalides")
    return await fournisseur.fetch(latitude, longitude, timeout_ms)
