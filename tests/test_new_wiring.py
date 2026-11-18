"""Contrats des nouveaux capteurs et du câblage Pico."""
import math
import struct
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from src import config
from src.drivers.hardware import GY271, MPU6050, HardwareSensors, valider_cablage
from src.drivers.simulation import InteractiveSensors
from src.functions.get_functions import get_bateau_cap, get_bome_angle


def settings(**changes):
    values = {k: v for k, v in vars(config).items() if k.isupper()}
    values.update(changes)
    return SimpleNamespace(**values)


class Bus:
    def __init__(self, address):
        self.address = address
        self.writes = []
        self.status = 1
        self.identity = b'H43'
    def scan(self):
        return [self.address]
    def writeto_mem(self, *args):
        self.writes.append(args)
    def readfrom_mem(self, address, reg, size):
        if reg == 0x75:
            return b'\x68'
        if reg == 0x3B:
            return struct.pack('>hhh', 0, -16384, 16384)
        if reg == 0x0A:
            return self.identity
        if reg in (0x06, 0x09):
            return bytes([self.status])
        if self.address == 0x0D:
            return struct.pack('<hhh', 3000, -6000, 1500)
        return struct.pack('>hhh', 1090, 980, -2180)  # X,Z,Y


class QMC5883PBus(Bus):
    """Double fidèle aux adresses du QMC5883P (distinctes du QMC5883L)."""
    def __init__(self):
        super().__init__(0x2C)
        self.chip_id = 0x80
        self.reads = []
    def readfrom_mem(self, address, reg, size):
        self.reads.append((address, reg, size))
        if reg == 0x00 and size == 1:
            return bytes([self.chip_id])
        if reg == 0x09 and size == 1:
            return bytes([self.status])
        if reg == 0x01 and size == 6:
            return struct.pack('<hhh', 3750, -7500, 1875)
        raise AssertionError('Registre QMC5883P incorrect : %s' % ((reg, size),))


class NewWiringTests(unittest.TestCase):
    def test_grove_mapping_and_gpio_conflicts(self):
        self.assertEqual((config.SDA_IMU, config.SCL_IMU), (0, 1))
        self.assertEqual((config.SDA_BOME, config.SCL_BOME), (2, 3))
        self.assertEqual((config.SDA_BATEAU, config.SCL_BATEAU), (4, 5))
        valider_cablage(config)
        for changes in ({'CABLAGE_CONFIRME': False}, {'AUDIO_PIN': 3},
                        {'SDA_IMU': None}, {'SDA_BOME': 4}, {'BOUTON_PIN': 27}):
            with self.assertRaises(ValueError):
                valider_cablage(settings(**changes))
    @patch('src.drivers.hardware.pause_ms')
    def test_qmc_auto_decoding_and_overflow(self, pause):
        bus = Bus(0x0D)
        driver = GY271(bus, 'auto')
        self.assertEqual(driver.read_sample(), (100, -200, 50))
        self.assertIn((0x0D, 9, b'\x15'), bus.writes)
        bus.status = 3
        with self.assertRaisesRegex(OSError, 'saturation'):
            driver.read_sample()
    @patch('src.drivers.hardware.pause_ms')
    def test_hmc_axis_order_and_identity(self, pause):
        bus = Bus(0x1E)
        driver = GY271(bus)
        for actual, expected in zip(driver.read_sample(), (100, -200, 100)):
            self.assertAlmostEqual(actual, expected)
        bus.identity = b'???'
        with self.assertRaises(OSError):
            GY271(bus)
    @patch('src.drivers.hardware.pause_ms')
    def test_qmc5883p_identity_configuration_and_signed_decoding(self, pause):
        bus = QMC5883PBus()
        driver = GY271(bus)
        self.assertEqual(driver.modele, 'QMC5883P')
        self.assertEqual(bus.writes, [(0x2C, 0x0B, b'\x80'),
                                     (0x2C, 0x0B, b'\x08'), (0x2C, 0x0A, b'\x05')])
        self.assertEqual(driver.read_sample(), (100, -200, 50))
        self.assertEqual(bus.reads[-2:], [(0x2C, 0x09, 1), (0x2C, 0x01, 6)])
    @patch('src.drivers.hardware.pause_ms')
    def test_qmc5883p_wrong_identity_never_configured(self, pause):
        bus = QMC5883PBus()
        bus.chip_id = 0x00
        with self.assertRaisesRegex(OSError, 'identité'):
            GY271(bus)
        self.assertEqual(bus.writes, [])
    @patch('src.drivers.hardware.pause_ms')
    def test_qmc5883p_saturation_and_timeout(self, pause):
        bus = QMC5883PBus()
        driver = GY271(bus, 0x2C)
        bus.status = 3
        with self.assertRaisesRegex(OSError, 'saturation'):
            driver.read_sample()
        bus.status = 0
        with patch('src.drivers.hardware.ticks_ms', side_effect=[0, 151]):
            with self.assertRaisesRegex(OSError, 'expirée'):
                driver.read_sample()
    def test_compass_missing_or_ambiguous(self):
        bus = Bus(0x30)
        with self.assertRaises(OSError):
            GY271(bus)
        bus.scan = lambda: [0x0D, 0x1E]
        with self.assertRaises(OSError):
            GY271(bus)
    @patch('src.drivers.hardware.pause_ms')
    def test_compass_timeout(self, pause):
        driver = GY271(Bus(0x0D))
        driver.bus.status = 0
        with patch('src.drivers.hardware.ticks_ms', side_effect=[0, 151]):
            with self.assertRaises(OSError):
                driver.read_sample()
    @patch('src.drivers.hardware.pause_ms')
    def test_mpu_acceleration(self, pause):
        driver = MPU6050(Bus(0x68), 0x68)
        self.assertEqual(driver.read_acceleration(), (0, -9.80665, 9.80665))
    def test_interactive_boom_relative_to_rotating_boat(self):
        sensors = InteractiveSensors()
        sensors.bome = -35
        for cap in (0, 150, 350):
            sensors.cap = cap
            self.assertAlmostEqual(get_bome_angle(get_bateau_cap(sensors.read_bateau()),
                get_bateau_cap(sensors.read_bome()), 0), -35)
    @patch('src.drivers.hardware.pause_ms')
    def test_three_separate_buses_and_two_compasses(self, pause):
        buses = {}
        class Pin:
            IN, PULL_UP = 0, 1
            def __init__(self, number, *args): self.number = number
        def soft_i2c(sda, scl, freq):
            bus = Bus(0x68) if sda.number == 0 else QMC5883PBus()
            buses[sda.number] = bus
            return bus
        import sys
        machine = SimpleNamespace(Pin=Pin, SoftI2C=soft_i2c)
        with patch.dict(sys.modules, {'machine': machine}):
            sensors = HardwareSensors(config)
            sensors.initialize()
            sensors.refresh()
        self.assertEqual(set(buses), {0, 2, 4})
        self.assertIsNot(sensors.bome.bus, sensors.mag_bateau.bus)
        self.assertEqual(sensors.read_bateau(), (100, -200, 50))
