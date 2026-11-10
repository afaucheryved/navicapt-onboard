# Système embarqué

- `get_functions.py` : capteurs, filtrage, grandeurs physiques et météo.
- `determine_actions.py` : décisions à partir des mesures fournies.
- `do_actions.py` : commandes des sorties sans attente bloquante.
- `OnBoardSystem` : bouton, calibration, états et boucle acquisition → décision → action.
- `main.py` : point d'entrée sur l'ESP32 sous MicroPython.

Lire chaque capteur une fois par cycle. Angles en degrés, temps en ms ; partager les mêmes repères entre modules. Garder la météo dans un cache daté sans bloquer la surveillance.

Installer le firmware MicroPython adapté, puis transférer `main.py`, `src/` et les pilotes compatibles avec `mpremote`. Le `venv` reste sur l'ordinateur. Les fichiers sont uniquement des squelettes à implémenter.

Idée générale du code, pour rappel :

![Idée générale de l’architecture du système embarqué](r%C3%A9flexions%20architecture%20code.png)
