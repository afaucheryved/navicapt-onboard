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


class GY271:
    """GY-271 : QMC5883L, QMC5883P ou HMC5883L selon adresse et identité."""

    def __init__(self, bus, adresse=None):
        self.bus = bus
        presents = bus.scan()
        candidats = [a for a in (0x0D, 0x1E, 0x2C) if a in presents]
        if adresse is None or adresse == 'auto':
            if len(candidats) != 1:
                raise OSError('GY-271 : adresse absente ou ambiguë : %s' % presents)
            adresse = candidats[0]
        if adresse not in candidats:
            raise OSError('GY-271 : attendu à 0x0D (QMC5883L), 0x1E (HMC5883L) ou 0x2C (QMC5883P)')
        self.adresse = adresse
        self.modele = {0x0D: 'QMC5883L', 0x1E: 'HMC5883L', 0x2C: 'QMC5883P'}[adresse]
        if adresse == 0x2C:
            identite = bus.readfrom_mem(adresse, 0x00, 1)[0]
            if identite != 0x80:
                raise OSError('QMC5883P : identité 0x%02X, attendu 0x80' % identite)
            # QST QMC5883P Rev E : CTRL2 reset, puis ±8 G et set/reset actif.
            bus.writeto_mem(adresse, 0x0B, b'\x80')
            pause_ms(50)
            bus.writeto_mem(adresse, 0x0B, b'\x08')
            bus.writeto_mem(adresse, 0x0A, b'\x05')  # Normal, 50 Hz, OSR1=8, OSR2=1.
        elif adresse == 0x0D:
            bus.writeto_mem(adresse, 0x0A, b'\x80')
            pause_ms(10)
            bus.writeto_mem(adresse, 0x0B, b'\x01')
            bus.writeto_mem(adresse, 0x09, b'\x15')  # 50 Hz, ±8 G, continu.
        else:
            if bus.readfrom_mem(adresse, 0x0A, 3) != b'H43':
                raise OSError('HMC5883L : identité incorrecte')
            bus.writeto_mem(adresse, 0x00, b'\x70')  # 8 moyennes, 15 Hz.
            bus.writeto_mem(adresse, 0x01, b'\x20')  # ±1,3 G.
            bus.writeto_mem(adresse, 0x02, b'\x00')
        pause_ms(80)

    def read_sample(self):
        debut = ticks_ms()
        qmc_l = self.adresse == 0x0D
        qmc_p = self.adresse == 0x2C
        qmc = qmc_l or qmc_p
        while True:
            status = self.bus.readfrom_mem(self.adresse, 0x06 if qmc_l else 0x09, 1)[0]
            if qmc and status & 2:
                raise OSError(self.modele + ' : saturation magnétique')
            if status & 1:
                break
            if ticks_diff(ticks_ms(), debut) >= 150:
                raise OSError('GY-271 : mesure expirée')
            pause_ms(2)
        data = self.bus.readfrom_mem(self.adresse, (0x00 if qmc_l else 0x01) if qmc else 0x03, 6)
        values = struct.unpack('<hhh' if qmc else '>hhh', data)
        if qmc:
            # QMC5883L : 3000 LSB/G ; QMC5883P : 3750 LSB/G en ±8 G.
            return tuple(v / (37.5 if qmc_p else 30.0) for v in values)
        if -4096 in values:
            raise OSError('HMC5883L : saturation magnétique')
        x, z, y = values
        return (x / 10.9, y / 10.9, z / 9.8)


class MPU6050:
    """Accéléromètre uniquement ; ce capteur ne fournit aucun cap magnétique."""

    def __init__(self, bus, adresse):
        self.bus, self.adresse = bus, adresse
        if bus.readfrom_mem(adresse, 0x75, 1)[0] != 0x68:
            raise OSError('MPU6050 : identité incorrecte')
        bus.writeto_mem(adresse, 0x6B, b'\x00')
        bus.writeto_mem(adresse, 0x1C, b'\x00')  # ±2 g.
        pause_ms(100)

    def read_acceleration(self):
        data = self.bus.readfrom_mem(self.adresse, 0x3B, 6)
        return tuple(v * 9.80665 / 16384 for v in struct.unpack('>hhh', data))


def valider_cablage(config):
    """Refuse des broches supposées ou incompatibles avec un Pico."""
    if not config.CABLAGE_CONFIRME:
        raise ValueError('Confirmer les GPIO dans src/config.py avant le mode matériel')
    pairs = [(config.SDA_BATEAU, config.SCL_BATEAU),
             (config.SDA_BOME, config.SCL_BOME), (config.SDA_IMU, config.SCL_IMU)]
    pins = [p for pair in pairs for p in pair] + [config.BOUTON_PIN, config.AUDIO_PIN]
    if any(type(p) is not int or p < 0 or p > 28 or p in (23, 24, 25) for p in pins):
        raise ValueError('GPIO Pico absent, réservé ou invalide')
    for pair in pairs:
        if pair[0] == pair[1]:
            raise ValueError('SDA et SCL doivent être distincts')
        for other in pairs:
            if pair != other and set(pair) & set(other):
                raise ValueError('Partager les deux fils I2C, ou aucun')
    if pins[-2] == pins[-1] or set(pins[-2:]) & set(pins[:-2]):
        raise ValueError('Bouton/audio en conflit avec les autres GPIO')


class HardwareSensors:
    """Expose le même contrat que le simulateur sur Pico."""

    def __init__(self, config: object) -> None:
        """Prépare le bouton actif bas avec résistance de rappel."""
        from machine import Pin
        valider_cablage(config)
        self.config = config
        self.bouton = Pin(config.BOUTON_PIN, Pin.IN, Pin.PULL_UP)

    def initialize(self) -> None:
        """Configure les deux bus et vérifie les capteurs."""
        from machine import SoftI2C, Pin
        c = self.config
        bus0 = SoftI2C(sda=Pin(c.SDA_BATEAU), scl=Pin(c.SCL_BATEAU), freq=100000)
        bus1 = bus0 if (c.SDA_BATEAU, c.SCL_BATEAU) == (c.SDA_BOME, c.SCL_BOME) else SoftI2C(
            sda=Pin(c.SDA_BOME), scl=Pin(c.SCL_BOME), freq=100000)
        bus_imu = bus0 if (c.SDA_IMU, c.SCL_IMU) == (c.SDA_BATEAU, c.SCL_BATEAU) else (
            bus1 if (c.SDA_IMU, c.SCL_IMU) == (c.SDA_BOME, c.SCL_BOME) else SoftI2C(
                sda=Pin(c.SDA_IMU), scl=Pin(c.SCL_IMU), freq=100000))
        if c.IMU_MODELE == 'SEN0694':
            self.imu = SEN0694(bus_imu, c.ADRESSE_IMU)
            self.mag_bateau = None
        elif c.IMU_MODELE == 'MPU6050':
            if c.ADRESSE_MAG_BATEAU is None:
                raise ValueError('MPU6050 sans boussole bateau : cap et angle de bôme indisponibles')
            if bus0 is bus1 and c.ADRESSE_MAG_BATEAU != 'auto' and c.ADRESSE_MAG_BATEAU == c.ADRESSE_BOME:
                raise ValueError('Deux boussoles de même adresse : utiliser deux bus I2C')
            self.imu = MPU6050(bus_imu, c.ADRESSE_IMU)
            self.mag_bateau = GY271(bus0, c.ADRESSE_MAG_BATEAU)
        else:
            raise ValueError('Confirmer IMU_MODELE : SEN0694 ou MPU6050')
        self.bome = GY271(bus1, c.ADRESSE_BOME)
        if self.mag_bateau is not None and bus0 is bus1 and self.bome.adresse == self.mag_bateau.adresse:
            raise ValueError('Deux boussoles de même adresse : utiliser deux bus I2C')

    def refresh(self) -> None:
        """Acquiert un seul échantillon par capteur et par cycle."""
        c = self.config
        if self.mag_bateau is None:
            acceleration, bateau = self.imu.read_sample()
        else:
            acceleration = self.imu.read_acceleration()
            bateau = self.mag_bateau.read_sample()
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
