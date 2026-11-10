"""Réglages du prototype ; seuils de démonstration à valider sur le bateau."""

SIMULATION = True  # Passer à False uniquement sur l'ESP32 câblé.
PERIODE_MS = 50
ANTI_REBOND_MS = 50
SEUIL_ACTIVATION = 40.0
SEUIL_ARRET = 30.0
ALPHA = 0.25
AGE_MESURE_MAX_MS = 500
CALIBRATION_ECHANTILLONS = 10
CALIBRATION_ECART_MAX_DEG = 3.0
CALIBRATION_GITE_MAX_DEG = 15.0
BIP_ON_MS = 150
BIP_OFF_MS = 350
FREQUENCE_HZ = 2000

SDA_BATEAU = 21
SCL_BATEAU = 22
SDA_BOME = 32
SCL_BOME = 33
ADRESSE_IMU = 0x4A
ADRESSE_BOME = 0x30
BOUTON_PIN = 27
AUDIO_PIN = 25
# Repère cible : x vers l'avant, y transversal, z vers le haut au repos.
# Adapter les signes et les permutations au montage réel des deux capteurs.
AXES_ACCEL = (0, 1, 2)
SIGNES_ACCEL = (1, 1, 1)
AXES_MAG_BATEAU = (0, 1, 2)
SIGNES_MAG_BATEAU = (1, 1, 1)
AXES_MAG_BOME = (0, 1, 2)
SIGNES_MAG_BOME = (1, 1, 1)
OFFSET_MAG_BATEAU = (0.0, 0.0, 0.0)
OFFSET_MAG_BOME = (0.0, 0.0, 0.0)

METEO_ACTIVE = False
LATITUDE = 44.84  # Position fixe d'exemple, à remplacer par celle du bateau.
LONGITUDE = -0.58
METEO_PERIODE_MS = 300000
METEO_AGE_MAX_MS = 900000
METEO_TIMEOUT_MS = 5000
# Identifiants facultatifs dans secrets.py, ignoré par Git : WIFI_SSID, WIFI_PASSWORD.
