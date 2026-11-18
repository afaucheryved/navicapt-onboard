"""Simulateur Tkinter PC : mêmes acquisition, calibration et alertes que sur Pico."""

import asyncio
import math
import tkinter as tk
from tkinter import ttk
from . import config
from .compat import ticks_ms, ticks_diff
from .drivers.simulation import InteractiveSensors, SimulatedOutput
from .onboard_system import OnBoardSystem
from .weather import OpenMeteo


class Simulator:
    def __init__(self, root, meteo=None):
        self.root = root
        self.closed = False
        self.sensors = InteractiveSensors()
        self.output = SimulatedOutput()
        self.system = OnBoardSystem(self.sensors, self.output, meteo or OpenMeteo())
        self.loop = asyncio.new_event_loop()
        self.weather_task = None
        self.demo_start = None
        self.next_weather = ticks_ms()
        self.after_id = None
        root.title('NaviCapt — simulateur de navigation')
        root.geometry('1080x900')
        root.minsize(900, 850)
        root.configure(bg='#102534')
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('TFrame', background='#102534')
        style.configure('TLabel', background='#102534', foreground='#e9f3f8', font=('Sans', 11))
        style.configure('Title.TLabel', font=('Sans', 23, 'bold'))
        style.configure('TCheckbutton', background='#102534', foreground='#e9f3f8')
        outer = ttk.Frame(root, padding=22)
        outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='NaviCapt / Poste de simulation', style='Title.TLabel').pack(anchor='w')
        ttk.Label(outer, text='Capteurs simulés • météo réelle Open-Meteo • aucune commande matérielle').pack(anchor='w', pady=(4, 16))
        self.status = tk.Label(outer, text='ATTENTE — aligner la bôme puis appuyer sur le bouton',
                               bg='#24556b', fg='white', font=('Sans', 13, 'bold'), pady=12, wraplength=960)
        self.status.pack(fill='x')
        body = ttk.Frame(outer)
        body.pack(fill='both', expand=True, pady=6)
        controls = ttk.Frame(body, width=280)
        controls.pack(side='left', fill='y', padx=(0, 20))
        self.cap = tk.DoubleVar(value=0)
        self.bome = tk.DoubleVar(value=0)
        self.gite = tk.DoubleVar(value=0)
        for label, var, low, high in [('Cap du bateau (°)', self.cap, 0, 359),
                                       ('Bôme / axe arrière (°)', self.bome, -150, 150),
                                       ('Gîte (°)', self.gite, -85, 85)]:
            ttk.Label(controls, text=label).pack(anchor='w', pady=(4, 0))
            tk.Scale(controls, variable=var, from_=low, to=high, orient='horizontal',
                     length=270, resolution=1, font=('Sans', 10), width=10, bg='#102534', fg='#e9f3f8',
                     troughcolor='#24556b', highlightthickness=0).pack(fill='x')
        self.button = ttk.Button(controls, text='Bouton : armer / refaire le zéro', command=self.press_button)
        self.button.pack(fill='x', pady=(8, 4))
        ttk.Label(controls, text='Bôme à 0°, gîte < 15° ; maintenir\nimmobile pendant la calibration.').pack(anchor='w')
        self.fault = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls, text='Débrancher un capteur', variable=self.fault).pack(anchor='w', pady=6)
        self.sound = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls, text='Bip sonore PC', variable=self.sound).pack(anchor='w')
        ttk.Button(controls, text='Scénario automatique / manuel', command=self.toggle_demo).pack(fill='x', pady=6)
        self.readings = ttk.Label(controls, text='', justify='left')
        self.readings.pack(anchor='w', pady=4)
        self.canvas = tk.Canvas(body, bg='#163747', highlightthickness=0, width=640, height=440)
        self.canvas.pack(side='left', fill='both', expand=True)
        weather = ttk.Frame(outer)
        weather.pack(fill='x')
        ttk.Label(weather, text='MÉTÉO RÉELLE — %.2f, %.2f (coordonnées dans config.py)' %
                  (config.LATITUDE, config.LONGITUDE)).pack(anchor='w')
        self.weather_text = ttk.Label(weather, text='Requête HTTPS en cours…', wraplength=980)
        self.weather_text.pack(anchor='w', pady=6)
        self.weather_button = ttk.Button(weather, text='Actualiser la météo', command=self.request_weather)
        self.weather_button.pack(anchor='w')
        ttk.Label(outer, text='Seuils de démonstration : alerte à |gîte| ≥ 40°, arrêt à ≤ 30°. '
                  'La météo ne déclenche pas l’alarme.', wraplength=980).pack(anchor='w', pady=(4, 0))
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.system.initialize()
        self.request_weather()
        self.tick()

    def press_button(self):
        self.sensors.button = True
        self.root.after(200, self.release_button)

    def release_button(self):
        self.sensors.button = False

    def toggle_demo(self):
        if self.demo_start is None:
            self.demo_start = ticks_ms()
            self.fault.set(False)
            self.cap.set(0)
            self.bome.set(0)
            self.gite.set(0)
            self.press_button()
        else:
            self.demo_start = None

    def request_weather(self):
        if self.weather_task is None or self.weather_task.done():
            self.next_weather = ticks_ms() + config.METEO_PERIODE_MS
            self.weather_task = self.loop.create_task(self.system.update_weather())
            self.weather_button.state(['disabled'])

    def draw(self, state):
        from .boat_view import dessiner_navire
        dessiner_navire(self.canvas, self.sensors.cap, self.sensors.gite,
                        self.sensors.bome, state)

    def tick(self):
        if self.closed:
            return
        if self.demo_start is not None:
            t = ticks_diff(ticks_ms(), self.demo_start) / 1000
            self.bome.set(25 if t >= 2 else 0)
            self.gite.set(55 if 3 <= t < 6 else 0)
            if t >= 9:
                self.demo_start = None
        self.sensors.cap = self.cap.get()
        self.sensors.bome = self.bome.get()
        self.sensors.gite = self.gite.get()
        self.sensors.failure = self.fault.get()
        previous_sound = self.output.active
        self.system.step(ticks_ms())
        # Une itération asyncio entre deux rafraîchissements Tk ; HTTPS reste dans son travailleur.
        self.loop.call_soon(self.loop.stop)
        self.loop.run_forever()
        state = self.system.snapshot()
        labels = {'attente': 'ATTENTE — aligner la bôme puis armer',
                  'calibration': 'CALIBRATION — maintenir le bateau et la bôme immobiles',
                  'fonctionnement': 'SURVEILLANCE ACTIVE', 'defaut': 'DÉFAUT — ' + (state['erreur'] or '')}
        text = 'ALERTE — RISQUE DE DESSALEMENT' if state['risque'] else labels[state['etat']]
        self.status.config(text=text, bg='#ab3346' if state['risque'] or state['etat'] == 'defaut' else '#24556b')
        m = state['mesures'] or {}
        boom = m.get('bome_deg')
        self.readings.config(text='Mesures : %s\nCap : %.1f°\nGîte filtrée : %.1f°\nBôme / bateau : %s' % (
            'valides' if state['mesures_valides'] else 'non validées', m.get('cap_deg', 0),
            m.get('gite_deg', 0), '—' if boom is None else '%.1f°' % boom))
        weather = state['meteo']
        message = 'En attente de la réponse Open-Meteo…'
        if weather:
            age = ticks_diff(ticks_ms(), self.system.meteo_ms) // 1000
            message = ('Open-Meteo · %.1f °C · vent %.1f m/s · venant de %.0f° · '
                       'source %s UTC · reçu il y a %ss%s') % (
                weather['temperature_c'], weather['vent_ms'], weather['direction_vent_deg'],
                weather['date_source'], age, ' · PÉRIMÉ' if state['meteo_perimee'] else '')
        if state['erreur_meteo']:
            message += '\nÉchec météo : ' + state['erreur_meteo']
        self.weather_text.config(text=message)
        if self.weather_task.done():
            self.weather_button.state(['!disabled'])
            if ticks_diff(ticks_ms(), self.next_weather) >= 0:
                self.request_weather()
        self.draw(state)
        if self.sound.get() and self.output.active and not previous_sound:
            self.root.bell()
        self.after_id = self.root.after(config.PERIODE_MS, self.tick)

    def close(self):
        self.closed = True
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
        for task in asyncio.all_tasks(self.loop):
            task.cancel()
        self.loop.run_until_complete(asyncio.sleep(0))
        self.output.close()
        self.loop.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    Simulator(root)
    root.mainloop()
