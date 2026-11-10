# Commandes matérielles courtes : aucune attente bloquante ni décision de risque.
# Répéter une commande identique ne doit pas relancer le motif sonore.
# Le haut-parleur est commandé via un étage adapté, pas directement par le GPIO.


def set_alerte_dessalement(active: bool) -> None:
    """Active ou désactive le motif sonore d'alerte."""


def update_alerte_sonore(maintenant_ms: int) -> None:
    """Fait avancer le motif sonore pulsé sans bloquer le programme."""

def instructions_sonores()-> None
    """ Donne les instructions sonores pour vorder la voile """


def arreter_sorties() -> None:
    """Arrête les sorties lors de l'arrêt du système."""
