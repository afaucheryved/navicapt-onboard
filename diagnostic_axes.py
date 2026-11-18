"""Mesures brutes du MPU6050 pour distinguer montage latéral et défaut de lecture."""
from machine import Pin, SoftI2C
from src import config
from src.drivers.hardware import MPU6050, remap
from src.functions.get_functions import get_inclinaison
import math
import time

bus = SoftI2C(sda=Pin(config.SDA_IMU), scl=Pin(config.SCL_IMU), freq=100000)
imu = MPU6050(bus, config.ADRESSE_IMU)
print('Poser la centrale à plat, composants vers le haut, puis incliner autour de son axe X.')
for _ in range(20):
    raw = imu.read_acceleration()
    mapped = remap(raw, config.AXES_ACCEL, config.SIGNES_ACCEL, (0, 0, 0))
    print('brut x/y/z=%s m/s² ; norme=%.2f ; gîte configurée=%.1f°' % (
        raw, math.sqrt(sum(v*v for v in raw)), get_inclinaison(mapped)))
    time.sleep_ms(500)
