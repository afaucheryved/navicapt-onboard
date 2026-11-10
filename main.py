"""Prototype NaviCapt : simulation sur PC ou matériel ESP32 selon config.py."""

import sys
import asyncio
from src import config
from src.onboard_system import OnBoardSystem


def afficher(etat: dict) -> None:
    """Affiche les mesures et les alertes à cadence limitée."""
    mesures = etat['mesures'] or {}
    print('état=%s gîte=%s° bôme=%s° risque=%s son=%s erreur=%s' % (
        etat['etat'], mesures.get('gite_deg'), mesures.get('bome_deg'),
        etat['risque'], etat['son'], etat['erreur']))


def main() -> None:
    """Construit les pilotes et lance la boucle du prototype."""
    if config.SIMULATION:
        from src.drivers.simulation import SimulatedSensors, SimulatedOutput, SimulatedWeather
        capteurs, sortie, meteo = SimulatedSensors(), SimulatedOutput(), SimulatedWeather()
        duree_ms = int(float(sys.argv[1]) * 1000) if len(sys.argv) > 1 else 9000
        if duree_ms <= 0:
            raise ValueError('La durée de simulation doit être positive')
        print('SIMULATION : appui automatique, zéro, gîte à 55° puis retour à plat.')
    else:
        if sys.implementation.name != 'micropython':
            raise RuntimeError('Le mode matériel nécessite MicroPython sur ESP32')
        from src.drivers.hardware import HardwareSensors, HardwareOutput
        from src.weather import OpenMeteo
        capteurs, sortie, meteo = HardwareSensors(config), HardwareOutput(config.AUDIO_PIN), OpenMeteo()
        duree_ms = None
        print('ESP32 : placer la bôme dans l’axe puis appuyer sur le bouton.')
    systeme = OnBoardSystem(capteurs, sortie, meteo)
    try:
        asyncio.run(systeme.run(duree_ms, afficher))
    except KeyboardInterrupt:
        print('Système arrêté.')


if __name__ == '__main__':
    main()
