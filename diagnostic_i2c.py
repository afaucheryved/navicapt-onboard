"""Exécuter dans Thonny sur Pico : scan sans configuration ni écriture des capteurs."""
from machine import Pin, SoftI2C
from src import config

for nom, sda, scl in [('bôme / Grove 2', config.SDA_BOME, config.SCL_BOME),
                       ('bateau / Grove 3', config.SDA_BATEAU, config.SCL_BATEAU),
                       ('centrale', config.SDA_IMU, config.SCL_IMU)]:
    if sda is None or scl is None:
        print(nom, ': GPIO à préciser dans src/config.py')
        continue
    try:
        bus = SoftI2C(sda=Pin(sda), scl=Pin(scl), freq=100000)
        adresses = bus.scan()
        print(nom, 'SDA GP%s / SCL GP%s :' % (sda, scl),
              ['0x%02X' % adresse for adresse in adresses])
        if 0x2C in adresses:
            identite = bus.readfrom_mem(0x2C, 0x00, 1)[0]
            print('  QMC5883P : ID 0x%02X (attendu 0x80) : %s' % (
                identite, 'OK' if identite == 0x80 else 'modèle à vérifier'))
    except OSError as erreur:
        print(nom, ':', erreur)
print('Attendus : GY-271 0x2C (QMC5883P), 0x0D (QMC5883L) ou 0x1E (HMC5883L) ; MPU6050 0x68/0x69 ; SEN0694 0x4A.')
