"""Pilotes I2C minimaux SEN0694 et MMC5603, à valider sur la carte réelle.

Protocoles : DFRobot/DFRobot_Multi_DOF_IMU (src/) et fiche MMC5603NJ.
Les registres I2C du SEN0694 diffèrent des adresses Modbus UART.
"""

import struct
import time
from ..compat import ticks_ms, ticks_diff


def pause_ms(duree: int) -> None:
    """Attend brièvement pendant une transaction matérielle."""
    time.sleep_ms(duree)


def remap(valeur: tuple, axes: tuple, signes: tuple, offset: tuple) -> tuple:
    """Applique la correction magnétique puis le repère de montage."""
    return tuple((valeur[axes[i]] - offset[axes[i]]) * signes[i] for i in range(3))


class SEN0694:
    """Lit l'accélération et le champ magnétique de la centrale DFRobot."""

    def __init__(self, bus: object, adresse: int) -> None:
        """Vérifie l'identité et impose le mode normal, ±8 g."""
        self.bus = bus
        self.adresse = adresse
        if struct.unpack('<H', self.read(0, 2))[0] != 0x3343:
            raise OSError('SEN0694 : fabricant inattendu')
        if struct.unpack('<H', self.read(1, 2))[0] != 9:
            raise OSError('SEN0694 : modèle inattendu')
        self.write(5, 2)
        self.write(6, 2)
        pause_ms(50)

    def read(self, registre: int, taille: int) -> bytes:
        """Lit après sélection d'une adresse 16 bits little-endian."""
        self.bus.writeto(self.adresse, struct.pack('<H', registre))
        pause_ms(10)
        valeur = self.bus.readfrom(self.adresse, taille)
        if len(valeur) != taille:
            raise OSError('SEN0694 : lecture incomplète')
        return valeur

    def write(self, registre: int, valeur: int) -> None:
        """Écrit un mot de configuration little-endian."""
        self.bus.writeto(self.adresse, struct.pack('<HH', registre, valeur))
        pause_ms(10)

    def read_sample(self) -> tuple:
        """Renvoie accélération en m/s² et champ en µT."""
        acceleration = struct.unpack('<hhh', self.read(0x10, 6))
        magnetisme = struct.unpack('<iii', self.read(0x16, 12))
        return (tuple(v * 9.80665 / 4096 for v in acceleration),
                tuple(v * 0.01 for v in magnetisme))


class MMC5603:
    """Lit le magnétomètre de bôme en mode mesure à la demande."""

    def __init__(self, bus: object, adresse: int) -> None:
        """Vérifie l'identité, réinitialise et active l'auto set/reset."""
        self.bus = bus
        self.adresse = adresse
        if self.bus.readfrom_mem(adresse, 0x39, 1)[0] != 0x10:
            raise OSError('MMC5603 : identifiant inattendu')
        self.bus.writeto_mem(adresse, 0x1C, b'\x80')
        pause_ms(20)
        self.bus.writeto_mem(adresse, 0x1B, b'\x20')

    def read_sample(self) -> tuple:
        """Déclenche une mesure et attend au plus 30 ms."""
        self.bus.writeto_mem(self.adresse, 0x1B, b'\x21')
        debut = ticks_ms()
        while not self.bus.readfrom_mem(self.adresse, 0x18, 1)[0] & 0x40:
            if ticks_diff(ticks_ms(), debut) >= 30:
                raise OSError('MMC5603 : mesure expirée')
            pause_ms(1)
        donnees = self.bus.readfrom_mem(self.adresse, 0, 9)
        return tuple((((donnees[2*i] << 12) | (donnees[2*i+1] << 4)
                       | (donnees[6+i] >> 4)) - 524288) * 0.00625 for i in range(3))


class HardwareSensors:
    """Expose le même contrat que le simulateur sur ESP32."""

    def __init__(self, config: object) -> None:
        """Prépare le bouton GPIO27 avec résistance de rappel."""
        from machine import Pin
        self.config = config
        self.bouton = Pin(config.BOUTON_PIN, Pin.IN, Pin.PULL_UP)

    def initialize(self) -> None:
        """Configure les deux bus et vérifie les capteurs."""
        from machine import I2C, Pin
        c = self.config
        bus0 = I2C(0, sda=Pin(c.SDA_BATEAU), scl=Pin(c.SCL_BATEAU), freq=100000)
        bus1 = I2C(1, sda=Pin(c.SDA_BOME), scl=Pin(c.SCL_BOME), freq=100000)
        self.imu = SEN0694(bus0, c.ADRESSE_IMU)
        self.bome = MMC5603(bus1, c.ADRESSE_BOME)

    def refresh(self) -> None:
        """Acquiert un seul échantillon par capteur et par cycle."""
        c = self.config
        acceleration, bateau = self.imu.read_sample()
        self.acceleration = remap(acceleration, c.AXES_ACCEL, c.SIGNES_ACCEL, (0, 0, 0))
        self.bateau = remap(bateau, c.AXES_MAG_BATEAU, c.SIGNES_MAG_BATEAU,
                            c.OFFSET_MAG_BATEAU)
        self.champ_bome = remap(self.bome.read_sample(), c.AXES_MAG_BOME,
                                c.SIGNES_MAG_BOME, c.OFFSET_MAG_BOME)

    def read_bateau(self) -> tuple:
        """Renvoie le champ du bateau acquis pendant ce cycle."""
        return self.bateau

    def read_bome(self) -> tuple:
        """Renvoie le champ de bôme acquis pendant ce cycle."""
        return self.champ_bome

    def read_acceleration(self) -> tuple:
        """Renvoie l'accélération acquise pendant ce cycle."""
        return self.acceleration

    def read_button(self) -> bool:
        """Indique un appui actif à l'état bas."""
        return self.bouton.value() == 0


class HardwareOutput:
    """Produit une tonalité PWM vers l'étage d'amplification du haut-parleur."""

    def __init__(self, pin: int) -> None:
        """Prépare la sortie audio silencieuse."""
        from machine import PWM, Pin
        self.pwm = PWM(Pin(pin), freq=2000, duty_u16=0)
        self.active = False
        self.closed = False

    def set_tone(self, active: bool, frequence: int) -> None:
        """Commande une onde carrée, pas une sinusoïde."""
        if not self.closed:
            self.pwm.freq(frequence)
            self.pwm.duty_u16(16384 if active else 0)
        self.active = active and not self.closed

    def close(self) -> None:
        """Coupe la sortie puis libère le PWM."""
        if not self.closed:
            self.pwm.duty_u16(0)
            self.pwm.deinit()
            self.closed = True
        self.active = False
