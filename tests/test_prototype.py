"""Vérifications métier et contrats matériels, sans carte ni réseau."""
import asyncio
import math
import json
import struct
import time
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from src import config
from src.onboard_system import OnBoardSystem
from src.drivers.simulation import SimulatedSensors, SimulatedOutput
from src.drivers.hardware import SEN0694, MMC5603
from src.functions.get_functions import get_bome_angle, get_bateau_cap, get_inclinaison
from src.functions.determine_actions import risque_dessalement, mesure_perimee
from src.functions.do_actions import (
    AlerteSonore, bips_demarrage, bip_calibration_reussie,
)
from src.weather import OpenMeteo, normaliser_meteo, chemin_meteo, angle_relatif


class Clock:
    now = 0
    def __call__(self):
        return self.now


class Sensors(SimulatedSensors):
    button = False
    roll = 0
    boom = 20
    failure = False
    delay = 0
    reads = 0
    def refresh(self):
        self.reads += 1
        self.horloge.now += self.delay
        if self.failure:
            raise OSError('capteur débranché')
        self.inclinaison = self.roll
    def read_bome(self):
        angle = math.radians(self.boom)
        return (30*math.cos(angle), 30*math.sin(angle), 0)
    def read_button(self):
        return self.button


def settings(**changes):
    values = {k: v for k, v in vars(config).items() if k.isupper()}
    values.update(changes)
    return SimpleNamespace(**values)


class Calculations(unittest.TestCase):
    def test_angles(self):
        self.assertEqual(get_bome_angle(350, 10, 0), 20)
        self.assertEqual(get_bome_angle(10, 350, 0), -20)
        self.assertEqual(get_bome_angle(350, 10, 20), 0)
        self.assertEqual(get_bateau_cap((0, -30, 0)), 270)
        self.assertAlmostEqual(get_inclinaison((0, -1, 1)), -45)
    def test_invalid_vectors(self):
        for v in ((0, 0, 0), (float('nan'), 1, 1)):
            with self.assertRaises(ValueError):
                get_inclinaison(v)
        with self.assertRaises(ValueError):
            get_bateau_cap((0, 0, 1))
    def test_hysteresis(self):
        state = False
        results = []
        for angle in (39, 40, 35, -31, -30):
            state = risque_dessalement(angle, state, 40, 30)
            results.append(state)
        self.assertEqual(results, [False, True, True, True, False])
    def test_expiry_and_wrap(self):
        self.assertFalse(mesure_perimee(100, 600, 500))
        self.assertTrue(mesure_perimee(100, 601, 500))
        with patch('src.functions.determine_actions.ticks_diff', return_value=40):
            self.assertFalse(mesure_perimee(1020, 36, 50))
    def test_pulsed_audio(self):
        output = SimulatedOutput()
        alarm = AlerteSonore(output, 150, 350, 2000)
        alarm.set_active(True)
        alarm.update(0)
        self.assertTrue(output.active)
        alarm.set_active(True)
        alarm.update(200)
        self.assertFalse(output.active)
        alarm.update(500)
        self.assertTrue(output.active)
        alarm.set_active(False)
        self.assertFalse(output.active)


class StartupAudioTests(unittest.IsolatedAsyncioTestCase):
    async def test_three_bips_and_silence(self):
        commands = []
        waits = []

        class Output:
            def set_tone(self, active, frequence):
                commands.append((active, frequence))

        async def wait(duration):
            waits.append(duration)

        await bips_demarrage(Output(), 2000, wait)
        self.assertEqual(commands, [(True, 2000), (False, 2000)] * 3)
        self.assertFalse(commands[-1][0])
        self.assertEqual(waits, [150] * 5)

    async def test_long_bip_only_after_success(self):
        commands = []
        waits = []

        class Output:
            def set_tone(self, active, frequence):
                commands.append((active, frequence))

        async def wait(duration):
            waits.append(duration)

        await bip_calibration_reussie(Output(), 2000, wait)
        self.assertEqual(commands, [(True, 2000), (False, 2000)])
        self.assertEqual(waits, [600])


class SystemTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.sensors = Sensors(self.clock)
        self.output = SimulatedOutput()
        self.system = OnBoardSystem(self.sensors, self.output,
                                    config=settings(ALPHA=1, LECTURE_TOLERANCE_MS=250),
                                    horloge=self.clock)
        self.system.initialize()
    def tick(self, now):
        self.clock.now = now
        self.system.step(now)
    def calibrate(self):
        self.system.calibrate()
        for i in range(10):
            self.tick(100 + i*50)
        self.assertEqual(self.system.etat, 'fonctionnement')
    def test_button_debounce_and_hold(self):
        self.sensors.button = True
        self.tick(0)
        self.sensors.button = False
        self.tick(20)
        self.sensors.button = True
        self.tick(40)
        self.tick(70)
        self.assertEqual(self.system.etat, 'attente')
        for now in range(100, 1200, 50):
            self.tick(now)
        self.assertEqual(self.system.etat, 'fonctionnement')
        self.assertEqual(self.system._calibration, [])
    def test_zero_alarm_and_single_refresh(self):
        self.calibrate()
        self.sensors.boom = 45
        self.sensors.roll = 50
        reads = self.sensors.reads
        self.tick(700)
        self.assertEqual(self.sensors.reads, reads + 1)
        self.assertTrue(self.system.risque)
        self.assertTrue(self.output.active)
        self.assertAlmostEqual(self.system.mesures['bome_deg'], 55)
        self.assertAlmostEqual(self.system.mesures['bome_zero_deg'], 25)
        self.sensors.roll = 35
        self.tick(750)
        self.assertTrue(self.system.risque)
        self.sensors.roll = 29
        self.tick(800)
        self.assertFalse(self.system.risque)
        self.assertFalse(self.output.active)
    def test_fault_requires_recalibration(self):
        self.calibrate()
        self.sensors.failure = True
        self.tick(700)
        self.assertEqual(self.system.etat, 'fonctionnement')  # raté encore toléré
        self.tick(950)
        self.assertEqual(self.system.etat, 'defaut')
        self.assertTrue(self.output.active)
        self.assertFalse(self.system.snapshot()['mesures_valides'])
        self.sensors.failure = False
        self.tick(800)
        self.assertEqual(self.system.etat, 'defaut')
        self.calibrate()
        self.assertFalse(self.output.active)
    def test_transient_i2c_error_tolerated(self):
        self.calibrate()
        mesures = dict(self.system.mesures)
        self.sensors.failure = True
        self.tick(700)
        self.tick(750)
        self.assertEqual(self.system.etat, 'fonctionnement')
        self.assertEqual(self.system.mesures, mesures)  # dernières mesures conservées
        self.assertFalse(self.output.active)
        self.assertEqual(self.system.snapshot()['lectures_ratees'], 2)
        self.sensors.failure = False
        self.tick(800)
        self.assertEqual(self.system.etat, 'fonctionnement')
        self.assertTrue(self.system.snapshot()['mesures_valides'])
        # Nouvelle série d'échecs : la tolérance repart de zéro.
        self.sensors.failure = True
        self.tick(1000)
        self.assertEqual(self.system.etat, 'fonctionnement')
        self.tick(1200)
        self.assertEqual(self.system.etat, 'fonctionnement')
        self.tick(1250)
        self.assertEqual(self.system.etat, 'defaut')
    def test_stale_and_slow(self):
        self.calibrate()
        self.clock.now = 2000
        self.assertFalse(self.system.snapshot()['mesures_valides'])
        self.sensors.delay = 600
        self.tick(2100)
        self.assertEqual(self.system.etat, 'defaut')
    def test_unstable_calibration(self):
        self.system.calibrate()
        self.tick(100)
        self.sensors.boom += 10
        self.tick(150)
        self.assertEqual(self.system.etat, 'defaut')
    def test_tilted_calibration_rejected(self):
        self.sensors.roll = 55
        self.system.calibrate()
        self.tick(100)
        self.assertEqual(self.system.etat, 'defaut')
        self.assertIsNone(self.system.offset_bome)
    def test_circular_calibration(self):
        self.system.calibrate()
        for i in range(10):
            self.sensors.boom = 169.8 if i % 2 else 170.2
            self.tick(100 + i*50)
        self.assertEqual(self.system.etat, 'fonctionnement')
        self.assertAlmostEqual(abs(self.system.offset_bome), 180)
    def test_recalibration_preserves_alarm(self):
        self.calibrate()
        self.sensors.roll = 55
        self.tick(700)
        self.system.calibrate()
        self.assertEqual(self.system.etat, 'fonctionnement')
        self.assertTrue(self.system.risque)


class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_confirmation_only_on_calibration_success(self):
        for result, expected in (('fonctionnement', 1), ('defaut', 0)):
            clock = Clock()
            system = OnBoardSystem(Sensors(clock), SimulatedOutput(),
                                   config=settings(SIMULATION=False), horloge=clock)
            def initialize():
                system.etat = 'calibration'
            def step(now):
                system.etat = result
                clock.now += 50
            system.initialize = initialize
            system.step = step
            with patch('src.onboard_system.bips_demarrage', new_callable=AsyncMock), \
                    patch('src.onboard_system.bip_calibration_reussie',
                          new_callable=AsyncMock) as confirmation, \
                    patch('src.onboard_system.sleep_ms', new_callable=AsyncMock):
                await system.run(150)
                self.assertEqual(confirmation.await_count, expected)

    async def test_startup_bips_only_on_pico(self):
        for simulation, expected in ((False, 1), (True, 0)):
            clock = Clock()
            system = OnBoardSystem(Sensors(clock), SimulatedOutput(),
                                   config=settings(SIMULATION=simulation), horloge=clock)
            with patch('src.onboard_system.bips_demarrage', new_callable=AsyncMock) as bips:
                await system.run(0)
                self.assertEqual(bips.await_count, expected)

    async def test_weather_retries_quickly_after_failure(self):
        class FlakyWeather:
            calls = 0
            async def fetch(self, *args):
                FlakyWeather.calls += 1
                if FlakyWeather.calls == 1:
                    raise OSError('Wi-Fi : réseau introuvable')
                return {'source': 'test'}
        clock = Clock()
        system = OnBoardSystem(Sensors(clock), SimulatedOutput(), FlakyWeather(),
                               config=settings(METEO_PERIODE_MS=900000, METEO_REESSAI_MS=30000),
                               horloge=clock)
        waits = []
        async def fake_sleep(ms):
            waits.append(ms)
            if len(waits) == 2:
                raise asyncio.CancelledError
        with patch('src.onboard_system.sleep_ms', fake_sleep):
            with self.assertRaises(asyncio.CancelledError):
                await system._weather_loop()
        self.assertEqual(waits, [30000, 900000])
        self.assertEqual(system.cache_meteo, {'source': 'test'})
    async def test_weather_failure_preserves_cache(self):
        class BrokenWeather:
            async def fetch(self, *args):
                raise OSError('hors ligne')
        clock = Clock()
        system = OnBoardSystem(Sensors(clock), SimulatedOutput(), BrokenWeather(), horloge=clock)
        system.cache_meteo = {'source': 'dernier résultat'}
        system.meteo_ms = 0
        await system.update_weather()
        self.assertEqual(system.cache_meteo['source'], 'dernier résultat')
        self.assertIsNotNone(system.erreur_meteo)
        clock.now = config.METEO_AGE_MAX_MS + 1
        self.assertTrue(system.snapshot()['meteo_perimee'])
    async def test_network_timeout_and_heartbeat(self):
        provider = OpenMeteo()
        calls, beats = [], []
        def slow(*args):
            calls.append(1)
            time.sleep(0.15)
            return {'source': 'test'}
        provider._request = slow
        async def heartbeat():
            for _ in range(8):
                beats.append(1)
                await asyncio.sleep(0.01)
        async def fetch():
            with self.assertRaises(OSError):
                await provider.fetch(44, -0.5, 30)
            with self.assertRaises(OSError):
                await provider.fetch(44, -0.5, 30)
        await asyncio.gather(fetch(), heartbeat())
        self.assertEqual((len(beats), len(calls)), (8, 1))
        await asyncio.sleep(0.12)
        self.assertFalse(provider.verrou.locked())
    async def test_cancellation_stops_audio(self):
        output = SimulatedOutput()
        system = OnBoardSystem(SimulatedSensors(), output)
        task = asyncio.create_task(system.run())
        await asyncio.sleep(0.01)
        system.alerte.set_active(True)
        system.alerte.update(0)
        self.assertTrue(output.active)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertFalse(output.active)
    async def test_observer_error_stops_audio(self):
        output = SimulatedOutput()
        system = OnBoardSystem(SimulatedSensors(), output)
        def observer(state):
            raise RuntimeError('afficheur débranché')
        with self.assertRaises(RuntimeError):
            await system.run(100, observer)
        self.assertFalse(output.active)


class HardwareTests(unittest.TestCase):
    def test_sen0694_protocol(self):
        class Bus:
            def __init__(self):
                self.commands = []
            def writeto(self, address, payload):
                self.commands.append(payload)
                self.reg = struct.unpack('<H', payload[:2])[0]
            def readfrom(self, address, size):
                return {0: struct.pack('<H', 0x3343), 1: struct.pack('<H', 9),
                        0x10: struct.pack('<hhh', 0, -4096, 4096),
                        0x16: struct.pack('<iii', 1234, -200, 0)}[self.reg]
        bus = Bus()
        with patch('src.drivers.hardware.pause_ms'):
            driver = SEN0694(bus, 0x4A)
            acceleration, magnetic = driver.read_sample()
        self.assertAlmostEqual(acceleration[1], -9.80665)
        self.assertAlmostEqual(magnetic[0], 12.34)
        self.assertIn(b'\x06\x00\x02\x00', bus.commands)
        self.assertEqual(bus.commands[-2:], [b'\x10\x00', b'\x16\x00'])
    def test_mmc5603_decoding_and_timeout(self):
        class Bus:
            ready = True
            def readfrom_mem(self, address, reg, size):
                if reg == 0x39:
                    return b'\x10'
                if reg == 0x18:
                    return b'\x40' if self.ready else b'\x00'
                return b'\x80\x00\x80\x01\x7f\xff\x00\x00\xf0'
            def writeto_mem(self, *args):
                pass
        bus = Bus()
        with patch('src.drivers.hardware.pause_ms'):
            driver = MMC5603(bus, 0x30)
            self.assertEqual(driver.read_sample(), (0, 0.1, -0.00625))
            bus.ready = False
            with patch('src.drivers.hardware.ticks_ms', side_effect=[0, 31]):
                with self.assertRaises(OSError):
                    driver.read_sample()
    def test_weather_units(self):
        payload = {'current': {'time': '2026-11-10T12:00', 'wind_speed_10m': 3,
                               'wind_direction_10m': 270, 'wind_gusts_10m': 7.5},
                   'current_units': {'wind_speed_10m': 'kn', 'wind_direction_10m': '°',
                                     'wind_gusts_10m': 'kn'}}
        meteo = normaliser_meteo(payload)
        self.assertEqual((meteo['vent_kn'], meteo['rafales_kn'], meteo['beaufort']), (3, 7.5, 1))
        payload['current']['wind_gusts_10m'] = None
        self.assertIsNone(normaliser_meteo(payload)['rafales_kn'])
        payload['current_units']['wind_speed_10m'] = 'km/h'
        with self.assertRaises(ValueError):
            normaliser_meteo(payload)

    def test_weather_path_and_relative_angle(self):
        chemin = chemin_meteo(44.84, -0.565)
        self.assertTrue(chemin.startswith('/v1/meteofrance?latitude=44.84&longitude=-0.565'))
        self.assertIn('wind_speed_unit=kn', chemin)
        self.assertIn('wind_gusts_10m', chemin)
        self.assertEqual(angle_relatif(90, 0), 90)
        self.assertEqual(angle_relatif(10, 350), 20)
        self.assertEqual(angle_relatif(300, 0), -60)


class WeatherHTTPTests(unittest.TestCase):
    def test_http_response_is_closed_and_normalised(self):
        payload = {'current': {'time': '2026-11-10T12:00', 'wind_speed_10m': 3,
                               'wind_direction_10m': 270, 'wind_gusts_10m': 7.5},
                   'current_units': {'wind_speed_10m': 'kn', 'wind_direction_10m': '°',
                                     'wind_gusts_10m': 'kn'}}
        from unittest.mock import MagicMock
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps(payload).encode()
        with patch('urllib.request.urlopen', return_value=response) as request:
            data = OpenMeteo()._request('/fixture', 5000)
        self.assertEqual(data['vent_kn'], 3)
        self.assertEqual(request.call_args.args[0], 'https://api.open-meteo.com/fixture')
        self.assertEqual(request.call_args.kwargs['timeout'], 5)
        response.__exit__.assert_called_once()

    def test_pico_socket_request(self):
        import io
        from unittest.mock import MagicMock
        from src.weather import http_get_json
        corps = b'{"current": {}}'
        class Flux(io.BytesIO):
            def __init__(self, data):
                super().__init__(data)
                self.envoye = b''
            def write(self, data):
                self.envoye += data
        flux = Flux(b'HTTP/1.0 200 OK\r\nContent-Length: %d\r\n\r\n' % len(corps) + corps)
        brut = MagicMock()
        ctx = MagicMock()
        ctx.wrap_socket.return_value = flux
        flux.close = MagicMock()
        with patch('socket.getaddrinfo', return_value=[(0, 0, 0, '', ('1.2.3.4', 443))]), \
                patch('socket.socket', return_value=brut), \
                patch('ssl.SSLContext', return_value=ctx):
            self.assertEqual(http_get_json('api.open-meteo.com', '/v1/x', 20000), {'current': {}})
        brut.settimeout.assert_called_once_with(20)
        brut.connect.assert_called_once_with(('1.2.3.4', 443))
        self.assertTrue(flux.envoye.startswith(b'GET /v1/x HTTP/1.0\r\nHost: api.open-meteo.com'))
        flux.close.assert_called_once()

    def test_pico_socket_http_error(self):
        import io
        from unittest.mock import MagicMock
        from src.weather import http_get_json
        flux = io.BytesIO(b'HTTP/1.0 400 Bad Request\r\n\r\n{"reason": "x"}')
        ctx = MagicMock()
        ctx.wrap_socket.return_value = flux
        with patch('socket.getaddrinfo', return_value=[(0, 0, 0, '', ('1.2.3.4', 443))]), \
                patch('socket.socket', return_value=MagicMock()), \
                patch('ssl.SSLContext', return_value=ctx):
            with self.assertRaises(OSError):
                http_get_json('api.open-meteo.com', '/v1/x', 20000)

    def test_oversized_http_response_rejected(self):
        from unittest.mock import MagicMock
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b'x' * 16385
        with patch('urllib.request.urlopen', return_value=response):
            with self.assertRaises(ValueError):
                OpenMeteo()._request('/fixture', 5000)
        response.__exit__.assert_called_once()
