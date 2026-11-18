# Installer et développer NaviCapt

Ce guide sert aux équipiers et à leurs agents. Toutes les commandes partent de la **racine du dépôt cloné**, celle qui contient `main.py`, `src/` et `tools/`. Il n’est pas nécessaire de recréer un dossier parent nommé `code`.

## 1. Prérequis et choix du mode

- PC : Python **3.11 ou plus récent**, avec Tkinter. Utiliser `python3` dans les exemples ; sous Windows, adapter à l’exécutable Python installé, par exemple `py -3`.
- Montage réel : Thonny, câble USB de données et **Pico W avec MicroPython** (version observée sur le montage : 1.24.0).
- Simulation : aucun paquet Python tiers, mais Internet pour la météo réelle. Sur Debian/Ubuntu, Tkinter peut être fourni par `python3-tk`.
- Affichage USB indépendant : paquet `pyserial` dans le Python PC. L’extension Thonny n’en a pas besoin directement : Thonny gère la connexion.
- Tests graphiques complets : Tkinter, Thonny importable, `pyserial`, Pillow et un écran ; sous Linux, Xvfb permet un écran virtuel. Voir la section Tests.

Les modes ont des rôles distincts :

- **Conseillé : MicroPython dans Thonny + extension NaviCapt**. F5 exécute le programme sur le Pico et les sorties de console alimentent la fenêtre PC.
- **Python PC + `main.py`** : fenêtre qui lit directement le port USB ; Thonny doit alors libérer ce port.
- **Python PC + `main.py --simulation`** : capteurs simulés, sans Pico.

## 2. Matériel et câblage

Montage actuel : Pico W sur **Cytron Maker Pi Pico**, MPU6050 et deux modules GY-271 contenant des **QMC5883P**. Les numéros GP ci-dessous sont ceux des GPIO, pas les numéros physiques du connecteur.

- **Grove 1, MPU6050** : SDA → GP0 ; SCL → GP1 ; VCC → 3V3 ; GND → GND. Adresse attendue `0x68` (`0x69` si AD0 impose cette adresse).
- **Grove 2, boussole de bôme** : SDA → GP2 ; SCL → GP3 ; VCC → 3V3 ; GND → GND.
- **Grove 3, boussole du bateau** : SDA → GP4 ; SCL → GP5 ; VCC → 3V3 ; GND → GND.
- **Haut-parleur amplifié Keyes** : signal S → GP27 ; alimentation adaptée au module ; masse commune. GP27 fournit le signal PWM, pas l’alimentation du haut-parleur.
- **GP20 intégré** : bouton d’armement et de calibration, actif bas. `BOUTON_PIN` permet de choisir GP21 ou GP22.
- **Bouton externe normalement ouvert** : entre RUN et GND uniquement. Sur le connecteur 3V3/GND/RUN, laisser 3V3 libre. L’appui maintient le Pico en reset ; le relâchement relance `main.py` enregistré à sa racine.

Les trois paires utilisent des bus `SoftI2C` distincts : les deux boussoles peuvent ainsi partager la même adresse. Les QMC5883P répondent à `0x2C` et leur identifiant au registre `0x00` doit être `0x80`. Le pilote prend aussi en charge QMC5883L (`0x0D`) et HMC5883L (`0x1E`). Le marquage GY-271 ne suffit pas à identifier la puce. Le pilote SEN0694 de l’ancien montage est conservé, mais n’est pas sélectionné.

Le câblage et les repères sont réglés dans `src/config.py`. Vérifier le raccordement réel SDA/SCL, sans se fier seulement aux couleurs des fils. Ne pas modifier les GPIO pour résoudre un simple problème d’interpréteur ou d’onglet Thonny.

## 3. Préparer et transférer le programme sur le Pico

```sh
python3 tools/preparer_thonny.py
```

Ce script crée **`thonny_pico/` et `thonny_pico.zip`**, ignorés par Git. Modifier les sources à la racine, puis régénérer ce paquet après chaque changement destiné au Pico.

Dans Thonny :

1. Connecter le Pico et sélectionner **MicroPython (Raspberry Pi Pico)** et son port USB. Installer MicroPython adapté au Pico W si la carte n’est pas encore configurée.
2. Afficher **Affichage → Fichiers**. Dans « Cet ordinateur », ouvrir `thonny_pico/`.
3. Téléverser **le contenu**, directement à la racine du Pico : `main.py`, `src/` et les scripts `diagnostic_i2c.py`, `diagnostic_axes.py`, `diagnostic_boutons.py`. Le Pico doit contenir `/main.py` et `/src/`, pas `/thonny_pico/main.py`.
4. Fermer les anciens onglets distants sans les réenregistrer avant de remplacer les fichiers ; les rouvrir ensuite depuis la partie « Raspberry Pi Pico ».
5. Lancer `diagnostic_i2c.py` côté Pico pour vérifier les trois modules. Ce diagnostic n’active pas l’audio.
6. Ouvrir `main.py` côté Pico et faire F5. La surveillance reste en `attente` jusqu’à l’appui GP20. Le Pico relance aussi ce fichier à son redémarrage.

Le paquet contient les modules PC pour permettre également son lancement local. Sur MicroPython, `main.py` choisit le programme embarqué sans importer Tkinter. Le booléen `SIMULATION` est adapté par le lanceur au mode d’exécution ; ce n’est pas le sélecteur à utiliser pour choisir l’interface dans Thonny.

## 4. Installer l’extension Thonny — méthode conseillée

Les sources versionnées sont dans `thonny_plugin/`. L’installateur ajoute une copie autonome dans le profil utilisateur Thonny de chaque équipier ; cette copie locale ne se partage pas via Git.

Exécuter avec **le Python qui contient Thonny** :

```sh
python3 -c "import thonny; print(thonny.__file__)"
python3 tools/installer_extension_thonny.py
```

Si le premier import échoue, choisir l’interpréteur de l’installation Thonny. Sur Debian/Ubuntu avec Thonny système, cela peut être `/usr/bin/python3`, même si un environnement virtuel est actif. Une installation autonome de Thonny peut utiliser un autre exécutable. Si un profil `THONNY_USER_DIR` personnalisé est employé, utiliser le même pour l’installateur.

**Fermer puis rouvrir Thonny**. Garder **MicroPython (Raspberry Pi Pico)** sélectionné, ouvrir `main.py` côté Pico, puis F5. La fenêtre apparaît à la première trame `NAVICAPT` valide ; `TELEMETRIE_USB` doit donc rester activé.

L’extension écoute passivement les événements `ProgramOutput`. Elle ne prend pas le port série et n’envoie pas de commande au Pico. La console conserve ses sorties et le journal embarqué continue à fonctionner. L’affichage montre bôme, caps, gîte, état, risque, son et erreurs.

- Fermer la fenêtre la masque ; elle réapparaît à réception des mesures du prochain run après F5.
- Pendant un run, la rouvrir via **Affichage → NaviCapt — mesures du Pico**.
- Une interruption du backend efface l’affichage ; après 1,5 s sans mesure, les anciennes valeurs sont masquées.
- Plusieurs F5 réutilisent une seule fenêtre. Les sorties ordinaires ou trames invalides restent sans effet sur le dessin.

**Après une modification de l’extension ou des modules graphiques partagés**, relancer l’installateur puis redémarrer Thonny. Il recopie aussi `pico_viewer.py`, `boat_view.py` et `telemetry.py` depuis les sources.

Pour désinstaller seulement NaviCapt :

```sh
python3 tools/installer_extension_thonny.py --uninstall
```

Redémarrer Thonny après désinstallation. Les autres extensions et les logs restent conservés.

## 5. Première calibration et sens des valeurs

Poser la centrale à plat et placer la bôme dans l’axe du bateau, puis appuyer sur **GP20 pendant au moins 0,1 seconde**. Maintenir les capteurs immobiles : 10 mesures stables sont demandées. La séquence normale est `attente → calibration → fonctionnement`. Une gîte supérieure à 15° ou une variation de bôme supérieure à 3° pendant la calibration provoque un défaut ; corriger puis réappuyer.

L’angle principal est disponible dès la première acquisition réussie :

```python
bome_deg = (cap_bome_deg - cap_deg + 180) % 360 - 180
```

`cap_deg` est le cap du bateau ; `cap_bome_deg` celui de la bôme. Exemple : bateau à 350°, bôme à 15° → **+25°**. Les deux boussoles doivent avoir des axes cohérents avec leur montage.

`bome_brute_deg` est un alias conservé pour compatibilité. `bome_zero_deg` retire le décalage enregistré à la calibration ; ce champ reste `None` avant celle-ci. Il ne remplace pas l’angle principal. L’armement reste nécessaire : `mesures_valides=False` avant le fonctionnement ou en défaut, même si des valeurs numériques sont affichées.

La gîte est estimée par l’accélération puis lissée. Les valeurs de démonstration déclenchent une alerte à **|gîte| ≥ 40°**, avec arrêt à **≤ 30°** ; la bôme et la météo ne déclenchent pas à elles seules l’alarme. Les défauts provoquent également un son. Un nouvel appui ne permet pas d’interrompre une alerte de risque en cours pour recalibrer.

## 6. Autres modes de développement

### Simulation sans carte

```sh
python3 main.py --simulation
# Variante console, durée en secondes :
python3 main.py --console 9
```

La fenêtre propose des curseurs de cap, bôme et gîte, une calibration simulée, une panne de capteur, un scénario automatique et un bip PC optionnel. La sonnerie dépend des réglages audio de l’ordinateur.

La simulation interroge **réellement Open-Meteo en HTTPS** aux coordonnées `LATITUDE`/`LONGITUDE` de la configuration (Bordeaux par défaut). Mise à jour toutes les 5 minutes, bouton d’actualisation et cache déclaré périmé après 15 minutes. Une panne conserve la dernière réponse avec son erreur ; aucune météo fictive ne la remplace. Ce sont des données de modèle, pas un capteur de vent embarqué.

### Affichage USB indépendant

Installer `pyserial` dans le Python PC, par exemple dans un environnement virtuel :

```sh
python3 -m venv .venv
# Linux/macOS :
. .venv/bin/activate
python -m pip install pyserial
python main.py
```

Sous Windows, activer `.venv\Scripts\Activate.ps1` dans PowerShell. Dans Thonny, on peut aussi sélectionner **Python 3 de l’ordinateur**, installer `pyserial` via **Outils → Gérer les paquets**, ouvrir le `main.py` local et faire F5.

Cette fenêtre ouvre directement le port USB : elle ne doit pas être connectée en même temps que Thonny MicroPython. Un unique Pico identifié peut être connecté automatiquement ; sinon, choisir le port puis **Connecter**. Appuyer sur RUN si le programme embarqué a été arrêté. Si le port change après reset, le sélectionner à nouveau. `visualiseur_pico.py` reste un autre lanceur de ce mode.

### Météo embarquée facultative

Désactivée par défaut. Sur Pico W, installer `requests` via le shell MicroPython :

```python
import mip
mip.install('requests')
```

Créer `secrets.py` à la racine du Pico avec `WIFI_SSID` et `WIFI_PASSWORD`, puis activer `METEO_ACTIVE` dans la configuration embarquée. Le Pico doit disposer d’une connexion Wi-Fi utilisable. Garder les identifiants hors du dépôt. La météo ne pilote pas l’alarme.

## 7. Journal et dépannage

`log.txt` est créé à la racine du Pico avec `LOG_ACTIF=True`. Il conserve les démarrages, appuis GP20, changements d’état/risque/défaut et un relevé toutes les 5 secondes. Chaque ligne JSON contient un `run_id` et `depuis_debut_ms` ; ce n’est pas une date civile.

Le format 2 expose directement `etat`, `gite_deg`, `bome_deg`, `risque`, `erreur`, les deux caps, `son`, `appuis`, `mesures_valides` et le zéro optionnel. Les valeurs encore inconnues au démarrage sont `null`. Les anciens enregistrements peuvent conserver leur ancien format imbriqué.

Rotation à 128 Kio : le fichier précédent devient `log.txt.1`, avec une seule archive. Un arrêt propre ajoute `arret` ; un reset ou une coupure peut interrompre le run et une ligne en cours. Une erreur du journal est exposée sans arrêter la surveillance. Les fichiers générés ne contiennent pas de journal vide à téléverser, afin de préserver les runs existants.

Pour récupérer les journaux, arrêter le programme puis utiliser le panneau **Raspberry Pi Pico → Télécharger** sur `log.txt` et éventuellement `log.txt.1`. Un onglet ouvert ne suit pas automatiquement les écritures : le fermer **sans enregistrer** puis le rouvrir. Ne pas remplacer le journal récent par une ancienne copie de l’éditeur.

- **Pas de fenêtre après F5** : vérifier l’extension dans le bon profil Thonny, redémarrer Thonny, vérifier `TELEMETRIE_USB=True` et la présence de lignes `NAVICAPT`. Un diagnostic qui ne produit pas ces trames n’ouvre pas la fenêtre.
- **Port USB absent ou déconnecté** : RUN coupe temporairement la connexion. Relâcher le bouton, attendre puis sélectionner le port disponible. Vérifier aussi le câble et l’absence d’un autre lecteur série.
- **Permission refusée sous Linux** : vérifier les groupes du compte et les droits du port avec `id` et `ls -l /dev/ttyACM*`. Si le port appartient à `dialout`, l’ajout au groupe par l’administrateur nécessite une nouvelle connexion de session pour être pris en compte.
- **Bouton non détecté** : lancer `diagnostic_boutons.py` sur le Pico. Pendant 30 s, GP20/21/22 doivent chacun produire `APPUYÉ` et `RELÂCHÉ`. RUN interrompt ce test et relance `main.py` ; il ne s’agit pas d’un GPIO de calibration.
- **Gîte élevée à plat ou défaut de calibration** : lancer `diagnostic_axes.py`. Au repos, la norme de l’accélération doit être proche de 9,81 m/s². Vérifier le montage et les `AXES_ACCEL`/`SIGNES_ACCEL` ; ne pas soustraire arbitrairement un angle pour masquer le défaut.
- **Capteur absent ou doute sur sa variante** : lancer `diagnostic_i2c.py`, comparer les adresses et identifiants avec le câblage ci-dessus.
- **Ancien code après téléversement** : fermer les onglets distants avant de remplacer les fichiers et les rouvrir ; F5 exécute le contenu de l’éditeur.

## 8. Tests et préparation d’un changement

Tests métier, pilotes et journaux, sans carte ni écran :

```sh
python3 -m unittest discover -s tests -p 'test_prototype.py' -v
python3 -m unittest discover -s tests -p 'test_new_wiring.py' -v
python3 -m unittest discover -s tests -p 'test_logging_telemetry.py' -v
```

Pour la suite complète, choisir un Python qui dispose de Tkinter, Thonny, `pyserial` et Pillow. Dans un environnement virtuel de test, on peut installer les dépendances Python avec :

```sh
python -m pip install thonny pyserial Pillow
python -m unittest discover -s tests -v
# Linux avec Xvfb installé, pour exercer aussi les fenêtres sans écran physique :
xvfb-run -a python -m unittest discover -s tests -v
```

Sans `DISPLAY`, les tests graphiques concernés sont ignorés. Les tests du port série virtuel nécessitent aussi POSIX ; ils ne sont pas exercés sous Windows. Les tests météo utilisent des réponses contrôlées et n’exigent pas de requête Internet. Les tests d’extension installent des copies temporaires, sans utiliser le vrai Pico ni modifier le profil Thonny de l’utilisateur.

Après un changement embarqué, régénérer le paquet et retransférer les fichiers concernés. Après un changement d’extension ou de ses modules partagés, réinstaller l’extension dans le profil de développement et redémarrer Thonny.

Le dépôt doit contenir les sources `thonny_plugin/` et `tools/installer_extension_thonny.py`, ainsi que les sources principales et les tests. Les copies installées, environnements, caches, `secrets.py`, `.env`, journaux et paquets Pico générés restent locaux selon `.gitignore`. Avant publication, vérifier `git rev-parse --show-toplevel` et `git status --short` depuis cette racine pour ne pas utiliser un dépôt parent.

## 9. Limites et références

Ce prototype doit encore être validé sur le montage et sur le bateau. Les caps sont horizontaux, sans compensation d’inclinaison ni calibration magnétique complète ; le zéro utilisateur ne remplace pas cette calibration. Adapter les axes, signes et offsets au montage réel. La gîte basée sur l’accélération et les seuils de démonstration ne constituent pas une alarme de navigation validée.

Références : [Cytron Maker Pi Pico](https://github.com/CytronTechnologies/MAKER-PI-PICO), [MPU6050 — TDK/InvenSense](https://invensense.tdk.com/wp-content/uploads/2015/02/MPU-6000-Register-Map.pdf), [QMC5883P — QST](https://www.qstcorp.com/upload/pdf/202512/2C939E5AA0704285BC3BE71132B8629B.pdf), [QMC5883L — QST](https://www.qstcorp.com/upload/pdf/202512/13-52-04%20QMC5883L%20Datasheet%20Rev.%20B.pdf), [HMC5883L — Honeywell](https://cdn.sparkfun.com/datasheets/Sensors/Magneto/HMC5883L-FDS.pdf), [Open-Meteo](https://open-meteo.com/en/docs), [pySerial](https://pyserial.readthedocs.io/en/stable/pyserial_api.html).
