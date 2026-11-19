"""Commandes non bloquantes ; un objet distinct conserve chaque motif sonore."""

from ..compat import ticks_diff, sleep_ms


class AlerteSonore:
    """Pilote un signal pulsé sans attente bloquante."""

    def __init__(self, sortie: object, on_ms: int, off_ms: int, frequence: int) -> None:
        """Associe une sortie et les durées du motif."""
        if on_ms <= 0 or off_ms <= 0 or frequence <= 0:
            raise ValueError("Motif sonore invalide")
        self.sortie = sortie
        self.on_ms = on_ms
        self.off_ms = off_ms
        self.frequence = frequence
        self.active = False
        self.debut_ms = None
        self.son = False

    def set_active(self, active: bool) -> None:
        """Change l'activation sans redémarrer un motif déjà actif."""
        if active != self.active:
            self.active = active
            self.debut_ms = None
        if not active:
            self.sortie.set_tone(False, self.frequence)
            self.son = False

    def update(self, maintenant_ms: int) -> None:
        """Actualise la phase sonore à partir du temps écoulé."""
        if not self.active:
            return
        if self.debut_ms is None:
            self.debut_ms = maintenant_ms
        phase = ticks_diff(maintenant_ms, self.debut_ms)
        if phase >= self.on_ms + self.off_ms or phase < 0:
            self.debut_ms = maintenant_ms
            phase = 0
        self.son = phase < self.on_ms
        self.sortie.set_tone(self.son, self.frequence)


def set_alerte_dessalement(active: bool, alerte: AlerteSonore) -> None:
    """Active ou arrête le motif d'alerte."""
    alerte.set_active(active)


async def bips_demarrage(sortie: object, frequence: int, attendre=sleep_ms) -> None:
    """Émet trois bips courts pour tester la sortie audio au démarrage."""
    actif = False
    try:
        for numero in range(3):
            sortie.set_tone(True, frequence)
            actif = True
            await attendre(150)
            sortie.set_tone(False, frequence)
            actif = False
            if numero < 2:
                await attendre(150)
    finally:
        if actif:
            sortie.set_tone(False, frequence)


async def bip_calibration_reussie(sortie: object, frequence: int,
                                  attendre=sleep_ms) -> None:
    """Confirme le passage en fonctionnement par un bip long unique."""
    sortie.set_tone(True, frequence)
    try:
        await attendre(600)
    finally:
        sortie.set_tone(False, frequence)


def instructions_sonores() -> None:
    """Prévoit le guidage sonore pour border la voile, à implémenter."""


def update_alerte_sonore(maintenant_ms: int, alerte: AlerteSonore) -> None:
    """Fait avancer le motif sonore sans bloquer."""
    alerte.update(maintenant_ms)


def arreter_sorties(alerte: AlerteSonore) -> None:
    """Coupe le son et libère la sortie."""
    alerte.set_active(False)
    alerte.sortie.close()
