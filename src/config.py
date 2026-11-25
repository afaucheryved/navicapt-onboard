"""Réglages du prototype ; seuils de démonstration à valider sur le bateau."""

SIMULATION = True  # main.py détecte PC/Pico ; --simulation lance la démo PC.
PERIODE_MS = 50
ANTI_REBOND_MS = 50
SEUIL_ACTIVATION = 40.0
SEUIL_ARRET = 30.0
ALPHA = 0.25
AGE_MESURE_MAX_MS = 500
# Ratés de lecture I2C tolérés (câble qui bouge, [Errno 110]) avant défaut : 1 s.
# Au-delà de AGE_MESURE_MAX_MS, mesures_valides passe à False pendant la coupure.
LECTURE_TOLERANCE_MS = 1000
CALIBRATION_ECHANTILLONS = 10
CALIBRATION_ECART_MAX_DEG = 3.0
CALIBRATION_GITE_MAX_DEG = 15.0
BIP_ON_MS = 150
BIP_OFF_MS = 350
FREQUENCE_HZ = 2000

# Photos : Pico W sur Maker Pi Pico, GY-271 et centrale 8 broches.
# Connecteurs confirmés par l’utilisateur ; SDA/SCL selon brochage Maker Pi Pico.
CABLAGE_CONFIRME = True
SDA_BATEAU = 4  # Grove 3, boussole bateau
SCL_BATEAU = 5
SDA_BOME = 2  # Grove 2, boussole bôme
SCL_BOME = 3
SDA_IMU = 0  # Grove 1, MPU6050.
SCL_IMU = 1
BOUTON_PIN = 20  # Bouton de calibration câblé entre GP20 et GND.
AUDIO_PIN = 18  # Haut-parleur sur Grove 4 (signal GP18), validé par test_haut_parleur.py.
VOLUME_DUTY = 32768  # Rapport cyclique PWM : 50 % = son le plus fort (max 65535).
IMU_MODELE = 'MPU6050'  # 'SEN0694' ou 'MPU6050'
ADRESSE_IMU = 0x68  # MPU6050 : 0x68 ou 0x69 ; SEN0694 : 0x4A.
ADRESSE_BOME = None  # Auto : QMC5883P 0x2C (montage réel), QMC5883L 0x0D, HMC5883L 0x1E.
# Le MPU6050 utilise la seconde boussole pour le cap du bateau.
ADRESSE_MAG_BATEAU = 'auto'  # Seconde GY-271 sur Grove 3 ; None si absente.
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

# Météo : Open-Meteo, modèle Météo-France AROME (pas de 15 min), vent en nœuds.
# Le Pico W passe par le partage de connexion du téléphone (2,4 GHz).
METEO_ACTIVE = True
LATITUDE = 44.84  # Garonne à Bordeaux (pont de pierre), à remplacer par le plan d'eau.
LONGITUDE = -0.565
METEO_PERIODE_MS = 900000  # Le modèle AROME est au pas de 15 min.
METEO_REESSAI_MS = 3000  # Tant que le Wi-Fi/la requête échoue : nouvel essai toutes les 3 s.
METEO_AGE_MAX_MS = 1800000  # Périmée après deux rafraîchissements manqués.
METEO_TIMEOUT_MS = 20000  # Wi-Fi puis DNS + TLS sur partage mobile : 20 s comme test_api.py.
# Partage de connexion du téléphone ; secrets.py (ignoré par Git) prime s'il existe.
WIFI_SSID = 'Xiaomi 13T'
WIFI_PASSWORD = ''

# Sur Pico : journal persistant, rotation log.txt -> log.txt.1 (128 Kio chacun).
LOG_ACTIF = True
LOG_PERIODE_MS = 5000
LOG_TAILLE_MAX = 131072
TELEMETRIE_USB = True  # Trames NAVICAPT pour visualiseur_pico.py sur PC.
