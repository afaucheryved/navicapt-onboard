# Navi'Capt — Test du haut-parleur Grove
# Carte : Raspberry Pi Pico (MicroPython)
# Branchement : haut-parleur sur Grove 4 -> signal sur GP18
# (si rien ne sort, essaie PIN_HP = 19)

from machine import Pin, PWM
import time

PIN_HP = 18
VOLUME = 32768  # rapport cyclique 50 % (max 65535) = son le plus fort

hp = PWM(Pin(PIN_HP))
hp.duty_u16(0)


def son(freq, duree_ms):
    hp.freq(freq)
    hp.duty_u16(VOLUME)
    time.sleep_ms(duree_ms)
    hp.duty_u16(0)


def bip(freq, duree_ms):
    son(freq, duree_ms)
    time.sleep_ms(int(duree_ms * 0.3))


# --- Signaux Navi'Capt ---
def cap_correct():
    bip(1500, 120)
    bip(1500, 120)

def corriger_gauche():
    bip(400, 250)

def corriger_droite():
    bip(1200, 500)

def alerte():
    hp.duty_u16(VOLUME)
    for _ in range(3):
        for f in range(600, 1401, 20):
            hp.freq(f)
            time.sleep_ms(4)
        for f in range(1400, 599, -20):
            hp.freq(f)
            time.sleep_ms(4)
    hp.duty_u16(0)


GAMME = [523, 587, 659, 698, 784, 880, 988, 1047]  # do -> do


def test():
    print("=== Test haut-parleur Navi'Capt (GP%d) ===" % PIN_HP)

    print("1. Bip 1 kHz")
    bip(1000, 300)
    time.sleep_ms(800)

    print("2. Gamme do-re-mi-fa-sol-la-si-do")
    for f in GAMME:
        bip(f, 200)
    time.sleep_ms(800)

    print("3. Balayage 200 Hz -> 4 kHz")
    hp.duty_u16(VOLUME)
    for f in range(200, 4001, 50):
        hp.freq(f)
        time.sleep_ms(15)
    hp.duty_u16(0)
    time.sleep_ms(800)

    print("4. Signaux Navi'Capt")
    print("   cap correct");      cap_correct();     time.sleep_ms(600)
    print("   corriger gauche");  corriger_gauche(); time.sleep_ms(600)
    print("   corriger droite");  corriger_droite(); time.sleep_ms(600)
    print("   alerte");           alerte()


try:
    while True:
        test()
        print("--- Fin du cycle, reprise dans 3 s ---\n")
        time.sleep(3)
except KeyboardInterrupt:
    pass
finally:
    hp.duty_u16(0)
    hp.deinit()
    print("Haut-parleur coupé.")