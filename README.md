# NaviCapt — Pico et simulateur Tkinter

Le PC simule les capteurs du navire avec Tkinter et interroge **réellement Open-Meteo en HTTPS**. Le Pico utilise les capteurs et le haut-parleur. Les deux modes partagent la même calibration, le même filtre et les mêmes décisions d’alerte.

## Lancer le simulateur sur le PC (y compris dans Thonny)

Ouvrir le dossier **`code/`**, choisir l’interpréteur **Python 3 de l’ordinateur**, puis exécuter `main.py` (F5 dans Thonny), ou :

```sh
python3 main.py
```

Tkinter est fourni avec les installations habituelles de Python/Thonny. Sous Debian/Ubuntu, s’il manque : `sudo apt install python3-tk`. Aucun paquet Python supplémentaire n’est requis pour la simulation et la requête météo.

1. Laisser bôme et gîte à 0°, puis cliquer sur **Bouton : armer / refaire le zéro**. La calibration prend 10 mesures stables.
2. Déplacer les curseurs : cap du navire, angle physique de bôme et gîte. La coque et la bôme tournent dans la vue de dessus ; la coupe arrière montre la gîte.
3. La valeur « bôme après zéro » est la mesure relative calibrée. La bôme orange montre l’entrée physique, même avant calibration ; « non validées » indique que les mesures ne sont pas utilisables.
4. À |gîte filtrée| ≥ 40°, l’alerte s’allume et le son est pulsé ; elle s’arrête à ≤ 30°. Le lissage introduit un petit délai. Cocher « Bip sonore PC » pour entendre la sonnerie système (selon les réglages audio du PC).
5. « Débrancher un capteur » provoque un défaut. Décocher, remettre à plat et réappuyer pour reprendre. « Scénario automatique / manuel » lance une séquence de 9 secondes, ou rend la main aux curseurs.

La simulation démarre une vraie requête météo, renouvelée toutes les 5 minutes, avec un bouton d’actualisation. La fenêtre reste réactive pendant le réseau. La source, sa date UTC, l’âge de réception et les erreurs sont affichés ; une panne conserve la dernière réponse, signalée périmée après 15 minutes. Les données actuelles Open-Meteo sont des données de modèle pour les coordonnées configurées, pas celles d’un capteur à bord. Elles ne pilotent pas l’alarme.

Coordonnées par défaut : Bordeaux, `44.84, -0.58`. Modifier `LATITUDE` et `LONGITUDE` dans `src/config.py` pour le lieu souhaité. Aucun remplacement par une météo inventée en cas d’échec réseau.

Le scénario console reste disponible : `python3 main.py --console 9`.

## Afficher les capteurs réels dans Tkinter, avec Thonny

Le fichier **`visualiseur_pico.py`** affiche les vrais angles reçus du Pico par USB : vue de dessus, gîte, bôme brute avant zéro / calibrée après zéro, état, alertes et nombre d’appuis GP20. Il ne simule pas les mesures et ne commande pas le bateau. Le programme embarqué reste `main.py` sur le Pico. Une coupure de données de plus de 1,5 s masque les anciennes mesures et signale la perte de liaison ; après un reset RUN, le visualiseur retente la connexion au même port.

1. Téléverser la nouvelle version de **`main.py` et `src/`** depuis `thonny_pico/` à la racine du Pico. Les trames USB sont activées par `TELEMETRIE_USB = True`.
2. Dans Thonny, sélectionner **Python 3 de l’ordinateur**, ce qui libère le port MicroPython. Le port USB doit être utilisé par le visualiseur seul. Si le port reste occupé, fermer Thonny et lancer le visualiseur depuis un terminal.
3. Installer **pyserial dans le Python PC** s’il manque : dans Thonny, **Outils → Gérer les paquets**, chercher `pyserial` et l’installer. Tkinter est aussi nécessaire. Le simulateur seul n’a pas besoin de pyserial.
4. Ouvrir le fichier local **`code/visualiseur_pico.py`**, puis **F5**. Choisir `/dev/ttyACM0` et cliquer **Connecter**.
5. Appuyer puis relâcher le bouton **RUN–GND** pour démarrer `main.py` si le programme a été arrêté. Le port USB peut disparaître brièvement pendant le reset ; le visualiseur retente la connexion. Si le système attribue un autre nom de port, choisir ce nouveau port et reconnecter.
6. Mettre le capteur à plat, aligner la bôme et appuyer sur **GP20** pour calibrer. La fenêtre montre « mesures non validées » jusqu’au succès de la calibration. Un défaut masque le dessin ; les valeurs numériques restantes sont explicitement non validées.

Depuis un terminal, le lancement est `python3 visualiseur_pico.py` (installer au préalable pyserial dans cet interpréteur). Les détails de la liaison sont fondés sur l’[API pySerial](https://pyserial.readthedocs.io/en/stable/pyserial_api.html). Le visualiseur ne transmet ni Ctrl-C ni commande au Pico ; il écoute les lignes `NAVICAPT {…}` du programme. Les lignes console ordinaires sont ignorées.

## Prochain run : essai des boutons

Téléverser **`diagnostic_boutons.py`**, **`diagnostic_axes.py`**, **`main.py`** et le dossier **`src/`** mis à jour depuis `thonny_pico/`. Fermer les anciens onglets distants sans les réenregistrer avant de remplacer les fichiers.

1. Dans Thonny connecté au Pico, ouvrir **`diagnostic_boutons.py` côté Pico**, puis F5. Pendant 30 secondes, appuyer sur les boutons intégrés **GP20, GP21, GP22** ; chaque appui/relâchement est affiché et ajouté à `log.txt`, avec anti-rebond. Ce test ne démarre ni l’audio ni les capteurs.
2. Le bouton externe à deux fils doit être **normalement ouvert**, relié entre **RUN et GND**. Sur le connecteur marqué **3V3 / GND / RUN**, utiliser seulement **GND et RUN**. Un appui maintient le Pico en reset ; le relâchement redémarre le programme `main.py` enregistré à sa racine. Ce bouton ne se déclare pas comme un GPIO et ne remplace pas le bouton de calibration GP20. Voir la [fiche Raspberry Pi Pico](https://datasheets.raspberrypi.org/pico/pico_datasheet.pdf).
3. Si on appuie sur RUN pendant le diagnostic, celui-ci est interrompu et `main.py` démarre à sa place. Pour un essai autonome, fermer la connexion MicroPython de Thonny avant le reset ; on peut suivre la reprise avec le visualiseur PC ou consulter ensuite `log.txt`.
4. Pour tester la surveillance, poser la centrale à plat, bôme dans l’axe, lancer **`main.py`**, puis appuyer **GP20** au moins 0,1 s. Le compteur `appuis` doit augmenter. Si la centrale est posée sur le côté, une valeur telle que 130° et le refus de calibration sont cohérents avec le repère actuel : remettre à plat puis réappuyer. Le code ne soustrait pas automatiquement 130°, ce qui masquerait une vraie inclinaison.
5. Si la gîte reste éloignée de zéro à plat, exécuter **`diagnostic_axes.py`** et communiquer les vecteurs bruts. La norme doit être proche de 9,81 m/s² au repos. Un montage latéral permanent nécessite de définir `AXES_ACCEL` et `SIGNES_ACCEL` d’après le sens de montage et l’axe avant du bateau.

`bome_deg=None` en attente signifie **zéro non calibré**. Le champ `bome_brute_deg` permet désormais d’observer la différence de cap avant la calibration, sans la déclarer valide.

## Journal des runs sur le Pico

Avec `LOG_ACTIF = True`, **`log.txt` est créé automatiquement à la racine du Pico** au démarrage de `main.py` ; il n’est pas inclus dans le paquet à téléverser pour préserver les runs existants. Chaque ligne JSON comporte un identifiant de run et le temps écoulé en millisecondes depuis son démarrage, sans prétendre fournir une date civile tant que l’horloge du Pico n’est pas réglée.

Le journal conserve le démarrage, les changements d’état/risque/défaut, les appuis stabilisés de GP20 et un échantillon toutes les 5 secondes. Un arrêt logiciel propre ajoute `arret`. Un reset RUN ou une coupure brutale interrompt le programme immédiatement : la fin du run précédent peut manquer ; le démarrage suivant ajoute un nouvel identifiant. Une écriture en cours peut être interrompue, donc une dernière ligne incomplète doit être ignorée lors d’une analyse.

`log.txt` est limité à **128 Kio** ; à la rotation, l’ancien contenu devient **`log.txt.1`**, remplaçant l’archive précédente. L’historique est donc borné à environ 256 Kio, et ne conserve pas tous les runs indéfiniment. Une erreur d’écriture est exposée sans arrêter la surveillance. Dans Thonny, utiliser le panneau **Raspberry Pi Pico**, puis clic droit **Télécharger** sur `log.txt` et éventuellement `log.txt.1` pour les récupérer.

## Câblage adapté aux photos et aux précisions fournies

Carte : **Raspberry Pi Pico W sur Cytron Maker Pi Pico**. Les numéros ci-dessous sont des **GP**, pas les numéros physiques du connecteur Pico.

- **MPU6050, Grove 1** : SDA → GP0 ; SCL → GP1 ; VCC → 3V3 ; GND → GND.
- **GY-271 de bôme, Grove 2** : SDA → GP2 ; SCL → GP3 ; VCC → 3V3 ; GND → GND.
- **GY-271 du bateau, Grove 3** : SDA → GP4 ; SCL → GP5 ; VCC → 3V3 ; GND → GND.
- **Haut-parleur amplifié Keyes** : S → **GP27**, VCC → alimentation du module, GND → masse commune. Le logiciel envoie du PWM à S ; le haut-parleur n’est pas alimenté par GP27.
- **Bouton intégré choisi : GP20**, actif bas avec résistance de rappel interne. Pour utiliser GP21 ou GP22, changer `BOUTON_PIN`.

Le brochage Grove est celui du [fabricant Cytron](https://github.com/CytronTechnologies/MAKER-PI-PICO). Vérifier que SDA et SCL des adaptateurs sont bien raccordés aux GP indiqués : la couleur d’un fil ne suffit pas à les identifier.

Les trois connecteurs ont des paires I2C distinctes. Le pilote utilise `SoftI2C`, ce qui permet ces trois bus sur le Pico et évite le conflit d’adresse entre les deux boussoles identiques. Le MPU6050 est configuré à `0x68` (modifier `ADRESSE_IMU` si AD0 impose `0x69`). Les GY-271 sont détectées indépendamment sur chaque bus : **QMC5883P à `0x2C`** (adresse relevée sur les deux boussoles du montage), **QMC5883L à `0x0D`** ou **HMC5883L à `0x1E`**. Le QMC5883P est vérifié par son identifiant `0x80` au registre `0x00` avant configuration. Le marquage GY-271 seul ne détermine pas la puce. Une adresse inconnue, ambiguë, une saturation ou une mesure expirée produit un défaut explicite.

Le MPU6050 donne l’accélération ; la seconde boussole fournit le cap du bateau. L’angle de bôme est la différence entre les caps des deux boussoles, corrigée par le zéro. Le pilote SEN0694 reste disponible pour l’ancien montage, mais n’est plus sélectionné.

## Dossier à transférer avec Thonny

Le dossier préparé est **`code/thonny_pico/`**, également disponible dans **`code/thonny_pico.zip`**. Pour le régénérer après une modification des sources :

```sh
cd code
python3 tools/preparer_thonny.py
```

Dans Thonny :

1. Connecter le Pico, installer MicroPython adapté au **Pico W** si nécessaire, puis sélectionner **MicroPython (Raspberry Pi Pico)** et le bon port USB.
2. Afficher **Affichage → Fichiers**. Ouvrir localement `code/thonny_pico/`.
3. Téléverser **le contenu** à la racine du Pico : **`main.py`**, **`diagnostic_i2c.py`**, **`diagnostic_boutons.py`**, **`diagnostic_axes.py`** et le dossier **`src/`**. Ne pas créer une racine `/thonny_pico/` sur la carte. Aucun besoin d’envoyer les photos, le venv ou les tests.
4. Lancer `diagnostic_i2c.py` pour relever les adresses sur les trois Grove. Ce script ne configure pas les capteurs et n’active pas l’audio.
5. Lancer `main.py`. Dans cette copie, `SIMULATION = False` ; l’application attend un appui sur **GP20** pour calibrer, bôme dans l’axe et bateau à plat. Le fichier `main.py` démarre aussi au redémarrage du Pico.

Tkinter fonctionne **sur l’ordinateur**, pas sur MicroPython. Le paquet embarqué l’exclut. Les fichiers sources PC gardent `SIMULATION = True`.

Pour la météo **sur le Pico W**, facultative et désactivée par défaut : installer `requests` via `import mip; mip.install('requests')` dans le shell MicroPython, créer à la racine un `secrets.py` contenant `WIFI_SSID` et `WIFI_PASSWORD`, puis passer `METEO_ACTIVE = True` dans le `src/config.py` de la carte. Ne pas partager `secrets.py`. Sur PC, la météo réelle est activée automatiquement, indépendamment de ce réglage embarqué.

## Vérification et limites

```sh
cd code
python3 -m unittest discover -s tests -v
# Test de fenêtre, si un écran est disponible (ou avec xvfb-run -a) :
python3 -m unittest discover -s tests -p 'test_gui.py' -v
```

Les tests contrôlent notamment le décodage des capteurs, les trois bus, les conflits de broches, l’angle relatif lors d’un changement de cap, la calibration, les défauts et les erreurs réseau. Un appel HTTPS réel a également été effectué pendant la mise à jour. Les tests unitaires météo restent indépendants du réseau.

Les pilotes et les repères doivent encore être validés **sur le montage physique**. Ajuster `AXES_*`, `SIGNES_*` et les offsets magnétiques après montage : gîte proche de 0° à plat, signe cohérent, angle correct quand on tourne la bôme. Le zéro relatif ne réalise pas une calibration magnétique complète. Les caps sont horizontaux, sans compensation d’inclinaison ; la gîte est estimée à partir de l’accélération. Les seuils 40°/30° sont des valeurs de démonstration, et l’angle de bôme est affiché sans déclencher à lui seul une alerte.

Références de protocole : [MPU6050 — TDK/InvenSense](https://invensense.tdk.com/wp-content/uploads/2015/02/MPU-6000-Register-Map.pdf), [QMC5883P — QST](https://www.qstcorp.com/upload/pdf/202512/2C939E5AA0704285BC3BE71132B8629B.pdf), [QMC5883L — QST](https://www.qstcorp.com/upload/pdf/202512/13-52-04%20QMC5883L%20Datasheet%20Rev.%20B.pdf), [HMC5883L — fiche Honeywell](https://cdn.sparkfun.com/datasheets/Sensors/Magneto/HMC5883L-FDS.pdf), [Open-Meteo](https://open-meteo.com/en/docs).
