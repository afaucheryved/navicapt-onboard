# NaviCapt

Prototype de surveillance d’un voilier sur **Raspberry Pi Pico W** : deux boussoles mesurent le cap du bateau et l’angle relatif de la bôme ; un MPU6050 estime la gîte. Le programme affiche les mesures, journalise les runs et commande une alerte sonore selon la gîte.

Pour le développement, une **extension Thonny incluse dans le dépôt** ouvre une fenêtre Tkinter à partir des mesures de la console : garder MicroPython sélectionné et faire **F5 sur le Pico**. Un simulateur PC avec curseurs et une vraie requête météo Open-Meteo est également disponible.

## Démarrer

Depuis la racine du dépôt, avec Python 3.11+ et Tkinter :

```sh
python3 main.py --simulation
```

Pour le montage réel, suivre le [guide d’installation](agent/setup.md) :

```sh
python3 tools/preparer_thonny.py
# Avec le Python qui contient Thonny :
python3 tools/installer_extension_thonny.py
```

Téléverser le contenu de `thonny_pico/` à la racine du Pico, redémarrer Thonny après installation de l’extension, puis lancer `main.py` côté Pico. Poser la centrale à plat, aligner la bôme et appuyer sur **GP20** pour armer la surveillance.

## Se repérer

- `src/` : acquisition, calculs, alertes, journal et interfaces PC.
- `thonny_plugin/` et `tools/` : extension Thonny, installation et préparation du paquet Pico.
- `tests/` : vérifications sans carte ; certains tests graphiques nécessitent un écran.
- [Guide complet](agent/setup.md) : câblage, installation, diagnostics, logs et tests.
- [AGENTS.md](AGENTS.md) : consignes de prise en main pour les agents de l’équipe.

**Prototype à valider sur le bateau.** Les seuils d’alerte sont des valeurs de démonstration ; les caps ne sont pas compensés en inclinaison. Les secrets Wi-Fi, journaux, environnements Python et paquets générés restent locaux.
