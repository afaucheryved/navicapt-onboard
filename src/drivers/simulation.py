"""Scénario reproductible sans capteurs ni connexion Internet."""

import math
from ..compat import ticks_ms, ticks_diff, sleep_ms


class SimulatedSensors:
    """Simule un appui, une gîte dangereuse puis un retour à plat."""

    def __init__(self, horloge: object = ticks_ms) -> None:
        """Choisit une horloge réelle ou contrôlée par les tests."""
        self.horloge = horloge
        self.debut = horloge()
        self.t = 0.0
        self.inclinaison = 0.0

    def initialize(self) -> None:
        """Remet le scénario au début."""
        self.debut = self.horloge()

    def refresh(self) -> None:
        """Fige les données du cycle courant."""
        self.t = ticks_diff(self.horloge(), self.debut) / 1000
        self.inclinaison = 55.0 if 3 <= self.t < 6 else 5.0

    def read_bateau(self) -> tuple:
        """Renvoie un cap fixe de 350°."""
        angle = math.radians(350)
        return (30 * math.cos(angle), 30 * math.sin(angle), 5.0)

    def read_bome(self) -> tuple:
        """Simule une bôme alignée au zéro puis décalée de 25°."""
        angle = math.radians(10 + (25 if self.t >= 2 else 0))
        return (30 * math.cos(angle), 30 * math.sin(angle), 5.0)

    def read_acceleration(self) -> tuple:
        """Renvoie le vecteur de pesanteur correspondant à la gîte."""
        angle = math.radians(self.inclinaison)
        return (0.0, 9.80665 * math.sin(angle), 9.80665 * math.cos(angle))

    def read_button(self) -> bool:
        """Simule un appui entre 0,2 et 0,5 seconde."""
        return 0.2 <= self.t < 0.5


class SimulatedOutput:
    """Mémorise la commande audio pour inspection."""

    def __init__(self) -> None:
        """Prépare une sortie silencieuse."""
        self.active = False
        self.frequence = 0

    def set_tone(self, active: bool, frequence: int) -> None:
        """Mémorise le son demandé."""
        self.active = active
        self.frequence = frequence

    def close(self) -> None:
        """Coupe la sortie simulée."""
        self.active = False


class SimulatedWeather:
    """Fournit des données explicitement simulées."""

    async def fetch(self, latitude: float, longitude: float, timeout_ms: int) -> dict:
        """Renvoie une météo fictive sans accès réseau."""
        await sleep_ms(1)
        return {"source": "simulation", "temperature_c": 18.0,
                "vent_ms": 4.0, "direction_vent_deg": 270.0}
