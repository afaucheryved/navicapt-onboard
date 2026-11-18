"""Persistance des runs et contrat du flux USB, sans carte physique."""
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from src.run_log import RunLogger
from src.telemetry import encode, decode
from src.onboard_system import OnBoardSystem
from src.drivers.simulation import SimulatedOutput
from test_prototype import Clock, Sensors, settings


def state(**changes):
    value = dict(etat='attente', risque=False, erreur=None, son=False, mesures_valides=False,
                 mesures=dict(cap_deg=15, cap_bome_deg=37, gite_deg=0, bome_deg=22, bome_brute_deg=22), appuis=0)
    value.update(changes)
    return value


class LoggingTests(unittest.TestCase):
    def test_append_runs_periodic_samples_and_button_events(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'log.txt'
            clock = Clock()
            logger = RunLogger(str(path), period_ms=5000, clock=clock)
            logger.event('demarrage')
            logger.observe(state())
            clock.now = 100
            logger.observe(state())
            clock.now = 5000
            logger.observe(state())
            clock.now = 5100
            logger.observe(state(appuis=1, etat='calibration'))
            logger.event('arret')
            other = RunLogger(str(path), clock=clock)
            other.event('demarrage')
            records = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual([r['evenement'] for r in records],
                             ['demarrage', 'etat', 'mesure', 'etat', 'arret', 'demarrage'])
            self.assertEqual(records[3]['appuis'], 1)
            self.assertEqual(records[3]['etat'], 'calibration')
            self.assertEqual(records[3]['gite_deg'], 0)
            self.assertEqual(records[3]['bome_deg'], 22)
            self.assertFalse(records[3]['risque'])
            self.assertIsNone(records[3]['erreur'])
            self.assertEqual(records[3]['cap_bateau_deg'], 15)
            self.assertEqual(records[3]['cap_bome_deg'], 37)
            self.assertTrue(all(r['format_version'] == 2 for r in records))
            self.assertTrue(all('gite_deg' in r and 'bome_deg' in r and 'risque' in r and 'erreur' in r for r in records))
            self.assertEqual(records[3]['depuis_debut_ms'], 5100)
            self.assertNotEqual(records[0]['run_id'], records[-1]['run_id'])
    def test_flat_fault_record_retains_values_and_error(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'log.txt'
            logger = RunLogger(str(path))
            logger.observe(state(etat='defaut', risque=False, son=True, erreur='capteur débranché'))
            record = json.loads(path.read_text())
            self.assertEqual(record['etat'], 'defaut')
            self.assertEqual(record['erreur'], 'capteur débranché')
            self.assertEqual(record['bome_deg'], 22)
            self.assertTrue(record['son'])
            self.assertFalse(record['mesures_valides'])

    def test_rotation_keeps_two_bounded_files(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'log.txt'
            logger = RunLogger(str(path), max_bytes=600)
            for i in range(30):
                logger.event('mesure', index=i)
            for file in (path, Path(str(path) + '.1')):
                self.assertLessEqual(file.stat().st_size, 600)
                for line in file.read_text().splitlines():
                    json.loads(line)
            self.assertEqual(len(list(Path(temp).iterdir())), 2)
    def test_disk_failure_reported_without_crashing(self):
        logger = RunLogger('/unwritable/log.txt')
        with patch('builtins.open', side_effect=OSError('disque plein')):
            logger.event('demarrage')
        self.assertIn('disque plein', logger.error)
    def test_stream_roundtrip_and_reject_corrupt_frames(self):
        self.assertEqual(decode(encode(state())), state())
        for line in ('bonjour', 'NAVICAPT {', 'NAVICAPT []',
                     encode(state(mesures={'gite_deg': float('nan')})),
                     encode(state(etat='inconnu')), encode(state(son='non'))):
            self.assertIsNone(decode(line))
    def test_boom_raw_available_before_zero_and_button_count(self):
        clock = Clock()
        sensors = Sensors(clock)
        system = OnBoardSystem(sensors, SimulatedOutput(), config=settings(ALPHA=1), horloge=clock)
        system.initialize()
        system.step(0)
        self.assertAlmostEqual(system.snapshot()['mesures']['bome_deg'], 30)
        self.assertIsNone(system.snapshot()['mesures']['bome_zero_deg'])
        self.assertAlmostEqual(system.snapshot()['mesures']['cap_bome_deg'], 20)
        self.assertAlmostEqual(system.snapshot()['mesures']['bome_brute_deg'], 30)
        sensors.button = True
        system.step(0)
        clock.now = 60
        system.step(60)
        self.assertEqual(system.snapshot()['appuis'], 1)
        self.assertTrue(system.snapshot()['bouton'])
        clock.now = 120
        system.step(120)
        self.assertEqual(system.snapshot()['appuis'], 1)

    def test_boom_difference_wrap_and_optional_zero_are_distinct(self):
        from src.drivers.simulation import InteractiveSensors
        clock = Clock()
        sensors = InteractiveSensors(clock)
        sensors.cap, sensors.bome = 350, 25
        system = OnBoardSystem(sensors, SimulatedOutput(),
                               config=settings(CALIBRATION_ECHANTILLONS=2), horloge=clock)
        system.initialize()
        system.step(0)
        self.assertEqual(system.etat, 'attente')
        self.assertAlmostEqual(system.mesures['cap_bome_deg'], 15)
        self.assertAlmostEqual(system.mesures['bome_deg'], 25)
        system.calibrate()
        for now in (50, 100):
            clock.now = now
            system.step(now)
        self.assertEqual(system.etat, 'fonctionnement')
        self.assertAlmostEqual(system.mesures['bome_deg'], 25)
        self.assertAlmostEqual(system.mesures['bome_zero_deg'], 0)
        sensors.cap, sensors.bome = 10, -35
        clock.now = 150
        system.step(150)
        self.assertAlmostEqual(system.mesures['bome_deg'], -35)
        self.assertAlmostEqual(system.mesures['bome_zero_deg'], -60)


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_journal_preserves_start_and_stop(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'log.txt'
            logger = RunLogger(str(path))
            system = OnBoardSystem(Sensors(Clock()), SimulatedOutput(), logger=logger)
            await system.run(60)
            records = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(records[0]['evenement'], 'demarrage')
            self.assertEqual(records[-1]['evenement'], 'arret')
