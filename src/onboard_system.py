# Coordonne acquisition, décision et sorties sans bloquer la surveillance.
# États prévus : attente, calibration, fonctionnement, défaut.
# Conserve les références, filtres, alertes, anti-rebond et cache météo daté.

# ne pas oublier de faire les importations des fonctions!


class OnBoardSystem:
    """Orchestre le fonctionnement du système embarqué."""

    def __init__(self) -> None:
        """Prépare l'état interne et les composants du système."""

    def initialize(self) -> None:
        """Initialise le matériel et passe en attente du bouton."""

    def calibrate(self) -> None:
        """Enregistre le zéro de la bôme dans une position connue."""

    def update_button(self, appuye: bool, maintenant_ms: int) -> None:
        """Détecte un nouvel appui avec anti-rebond et demande la calibration."""

    def step(self, maintenant_ms: int) -> None:
        """Lit une fois chaque capteur, calcule, décide et commande les sorties."""

    async def update_weather(self) -> None:
        """Actualise le cache météo daté et gère les erreurs réseau."""

    async def run(self) -> None:
        """Planifie la surveillance, le bouton et les mises à jour météo."""
