# Acquisition et calcul de grandeurs physiques, sans décision ni commande.
# Lire chaque capteur une fois par cycle, puis réutiliser ses données.
# Vecteurs : tuples (x, y, z) ; angles en degrés ; temps en millisecondes.
# Les erreurs de lecture doivent être signalées, jamais remplacées par zéro.


def get_boussole_bateau_data() -> tuple:
    """Lit le champ magnétique (x, y, z) de la boussole du bateau."""


def get_boussole_bome_data() -> tuple:
    """Lit le champ magnétique (x, y, z) de la boussole de la bôme."""


def get_accelerometre_data() -> tuple:
    """Lit l'accélération (x, y, z) en m/s² dans le repère du bateau."""


def get_bouton_data() -> bool:
    """Indique si le bouton est appuyé, avant anti-rebond."""


def get_bateau_cap(champ_magnetique: tuple) -> float:
    """Calcule le cap du bateau entre 0° inclus et 360° exclus."""


def get_bome_cap(champ_magnetique: tuple) -> float:
    """Calcule le cap de la bôme entre 0° inclus et 360° exclus."""


def get_bome_angle(cap_bateau: float, cap_bome: float, offset: float) -> float:
    """Calcule l'angle relatif de la bôme entre -180° inclus et 180° exclus."""


def get_inclinaison(acceleration: tuple) -> float:
    """Estime la gîte signée à partir de l'accélération mesurée."""


def filtrer_passe_bas(valeur: float, precedente: float, alpha: float) -> float:
    """Filtre une mesure avec un coefficient alpha compris entre 0 et 1."""


# Le zéro relatif ne remplace pas la calibration magnétique des boussoles.
# Prévoir la compensation d'inclinaison selon le montage et la précision visée.
# Utiliser des pilotes compatibles MicroPython pour les références réelles.
# La requête météo devra céder la main ; async seul ne suffit pas.


async def get_meteo_data(latitude: float, longitude: float, timeout_ms: int) -> dict:
    """Récupère la météo normalisée avec un délai réseau limité."""
