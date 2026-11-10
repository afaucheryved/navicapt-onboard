# NaviCapt — prototype embarqué

Trois étapes : `get_functions.py` mesure, `determine_actions.py` décide, `do_actions.py` commande. `OnBoardSystem` gère les états, le bouton, le zéro et les défauts ; les pilotes sont dans `src/drivers/`.

**Démo PC, sans dépendance ni réseau :**
```sh
python3 main.py
python3 -m unittest discover -s tests -v
```
La démo dure 9 s : appui automatique, zéro de la bôme, décalage de 25°, gîte de 55° puis retour à plat. La console affiche l'état et le son simulé. Une durée différente peut être passée : `python3 main.py 15`.

**ESP32 + SEN0694 + MMC5603 :** installer MicroPython, mettre `SIMULATION = False` dans `src/config.py`, puis transférer :
```sh
mpremote fs cp -r src :
mpremote fs cp main.py :main.py
mpremote reset
```
Câblage : SEN0694 en mode I2C, adresse `0x4A`, SDA21/SCL22 ; MMC5603 `0x30`, SDA32/SCL33 ; bouton GPIO27→GND ; audio GPIO25→amplificateur→haut-parleur. Le signal PWM est carré et pulsé.

Vérifier les repères/signes dans `config.py` : gîte proche de 0° à plat. Bôme dans l'axe, appuyer puis maintenir l'ensemble immobile pendant 10 mesures. Un défaut déclenche aussi le son et exige un nouvel appui après correction. Les seuils 40°/30° sont des valeurs de démonstration.

**Météo facultative :** activer `METEO_ACTIVE`, régler les coordonnées, installer `requests` sur la carte (`import mip; mip.install("requests")`) et créer `secrets.py` avec `WIFI_SSID` et `WIFI_PASSWORD` (ignoré par Git). Open-Meteo est interrogé dans un travailleur séparé ; les résultats sont conservés dans un cache daté, même après une erreur. En simulation, le fournisseur météo retourne des données fictives.

**Limites :** tests exécutés sur PC, pilotes à valider sur la carte ; météo testée avec des réponses simulées, sans appel réseau réel. Gîte estimée par l'accéléromètre lissé, caps horizontaux sans compensation d'inclinaison ni correction magnétique complète. Le zéro relatif ne calibre pas les boussoles. Ne pas considérer ce prototype comme une alarme de navigation validée.

Protocoles de référence : [SEN0694 — fabricant](https://github.com/DFRobot/DFRobot_Multi_DOF_IMU/tree/master/src), [MMC5603 — Adafruit](https://github.com/adafruit/Adafruit_CircuitPython_MMC56x3), [API Open-Meteo](https://open-meteo.com/en/docs).

Idée générale du code, pour rappel :

![Idée générale de l’architecture du système embarqué](r%C3%A9flexions%20architecture%20code.png)
