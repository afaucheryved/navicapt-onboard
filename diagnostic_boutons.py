"""Prochain essai dans Thonny : GP20/21/22, sans capteurs ni haut-parleur."""
from machine import Pin
from src.compat import ticks_ms, ticks_diff
from src.run_log import RunLogger
import time

pins = {n: Pin(n, Pin.IN, Pin.PULL_UP) for n in (20, 21, 22)}
stable = {n: p.value() for n, p in pins.items()}
brut = dict(stable)
change = {n: ticks_ms() for n in pins}
log = RunLogger()
log.event('test_boutons_debut')
print('TEST 30 s : appuyer sur GP20, puis GP21, puis GP22. 0 = appuyé ; 1 = relâché.')
print('RUN-GND : reset matériel ; au relâchement, main.py repart (le test sera interrompu).')
print('Le bouton externe doit être normalement ouvert ; aucune connexion à 3V3.')
print('État initial :', stable)
debut = ticks_ms()
try:
    while ticks_diff(ticks_ms(), debut) < 30000:
        now = ticks_ms()
        for n, p in pins.items():
            value = p.value()
            if value != brut[n]:
                brut[n] = value
                change[n] = now
            if value != stable[n] and ticks_diff(now, change[n]) >= 50:
                stable[n] = value
                print('GP%s : %s' % (n, 'APPUYÉ' if value == 0 else 'RELÂCHÉ'))
                log.event('bouton', gpio=n, appuye=value == 0)
        time.sleep_ms(10)
finally:
    log.event('test_boutons_fin')
    print('Fin du test ; événements enregistrés dans log.txt.')
