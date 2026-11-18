"""Génère un dossier embarqué et son ZIP à partir des sources, sans Tkinter ni photos."""
from pathlib import Path
import shutil

racine = Path(__file__).resolve().parents[1]
cible = racine / 'thonny_pico'
cible.mkdir(exist_ok=True)
shutil.copytree(racine / 'src', cible / 'src', dirs_exist_ok=True,
                ignore=shutil.ignore_patterns('__pycache__', 'simulator_gui.py', 'simulation.py', 'pico_viewer.py', 'boat_view.py'))
for nom in ('main.py', 'diagnostic_i2c.py', 'diagnostic_boutons.py', 'diagnostic_axes.py'):
    shutil.copy2(racine / nom, cible / nom)
p = cible / 'src' / 'config.py'
p.write_text(p.read_text().replace('SIMULATION = True', 'SIMULATION = False'))
(cible / 'LIRE_AVANT_TRANSFERT.txt').write_text(
    'Dans Thonny : choisir MicroPython (Raspberry Pi Pico).\n'
    'Transférer le CONTENU de thonny_pico à la racine du Pico : main.py, diagnostic_i2c.py et src/.\n'
    'src/config.py configuré : MPU Grove1, bôme Grove2, bateau Grove3, audio GP27, bouton GP20.\n'
    'Prochain essai : diagnostic_boutons.py (GP20/21/22), puis main.py à plat + GP20.\n'
    'Bouton externe normalement ouvert : RUN vers GND ; il redémarre main.py.\n'
    'log.txt est créé sur le Pico automatiquement ; ne pas remplacer les logs existants.\n'
    'Pour les mesures graphiques réelles : visualiseur_pico.py sur le PC, voir README.\n'
    'Météo embarquée désactivée par défaut.\n'
    'Voir le README du projet pour Wi-Fi et calibration. Tkinter reste sur le PC.\n')
shutil.make_archive(str(racine / 'thonny_pico'), 'zip', cible)
print('Dossier :', cible)
print('Archive :', racine / 'thonny_pico.zip')
