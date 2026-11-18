"""Prototype NaviCapt : simulation sur PC ou matériel Pico selon config.py."""

import sys
import asyncio
from src import config
from src.onboard_system import OnBoardSystem


def afficher(etat: dict) -> None:
    """Affiche les mesures et les alertes à cadence limitée."""
    mesures = etat['mesures'] or {}
    print('état=%s gîte=%s° bôme=%s° risque=%s son=%s erreur=%s appuis=%s' % (
        etat['etat'], mesures.get('gite_deg'), mesures.get('bome_deg'),
        etat['risque'], etat['son'], etat['erreur'], etat.get('appuis', 0)))
    if config.TELEMETRIE_USB:
        from src.telemetry import encode
        print(encode(etat))


def main() -> None:
    """Construit les pilotes et lance la boucle du prototype."""
    if config.SIMULATION and '--console' not in sys.argv and len(sys.argv) == 1:
        from src.simulator_gui import main as lancer_interface
        lancer_interface()
        return
    logger = None
    if config.SIMULATION:
        from src.drivers.simulation import SimulatedSensors, SimulatedOutput
        from src.weather import OpenMeteo
        config.METEO_ACTIVE = True
        capteurs, sortie, meteo = SimulatedSensors(), SimulatedOutput(), OpenMeteo()
        args = [a for a in sys.argv[1:] if a != '--console']
        duree_ms = int(float(args[0]) * 1000) if args else 9000
        if duree_ms <= 0:
            raise ValueError('La durée de simulation doit être positive')
        print('SIMULATION : appui automatique, zéro, gîte à 55° puis retour à plat.')
    else:
        if sys.implementation.name != 'micropython':
            raise RuntimeError('Le mode matériel nécessite MicroPython sur Pico')
        from src.drivers.hardware import HardwareSensors, HardwareOutput, valider_cablage
        valider_cablage(config)
        from src.weather import OpenMeteo
        capteurs, sortie, meteo = HardwareSensors(config), HardwareOutput(config.AUDIO_PIN), OpenMeteo()
        duree_ms = None
        if config.LOG_ACTIF:
            from src.run_log import RunLogger
            logger = RunLogger(period_ms=config.LOG_PERIODE_MS, max_bytes=config.LOG_TAILLE_MAX)
        print('Pico : placer la bôme dans l’axe puis appuyer sur le bouton.')
    systeme = OnBoardSystem(capteurs, sortie, meteo, logger=logger)
    try:
        asyncio.run(systeme.run(duree_ms, afficher))
    except KeyboardInterrupt:
        print('Système arrêté.')


if __name__ == '__main__':
    main()
