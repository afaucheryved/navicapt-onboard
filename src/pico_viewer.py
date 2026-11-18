"""Interface PC de mesures réelles ; USB non bloquant, sans exécuter de code sur le Pico."""
import math
import os
import time
import tkinter as tk
from tkinter import ttk
from .telemetry import decode
from .boat_view import dessiner_navire


class PicoViewer:
    def __init__(self, root, serial_factory=None, port_list=None):
        self.root = root
        if serial_factory is None:
            import serial
            from serial.tools.list_ports import comports
            serial_factory, port_list = serial.Serial, comports
        self.serial_factory = serial_factory
        self.port_list = port_list or (lambda: [])
        self.serial = None
        self.buffer = b''
        self.discard_line = False
        self.state = None
        self.received = None
        self.retry_at = 0
        self.wanted = False
        self.closed = False
        self.after_id = None
        root.title('NaviCapt — mesures réelles du Pico')
        root.geometry('1050x820')
        root.minsize(900, 800)
        root.configure(bg='#102534')
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('TFrame', background='#102534')
        style.configure('TLabel', background='#102534', foreground='#e9f3f8', font=('Sans', 11))
        frame = ttk.Frame(root, padding=18)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='NaviCapt / Mesures réelles', font=('Sans', 23, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='MPU6050 + deux QMC5883P • GP20 : calibration • RUN–GND : redémarrage').pack(anchor='w', pady=8)
        connection = ttk.Frame(frame)
        connection.pack(fill='x', pady=8)
        self.port = tk.StringVar(value='/dev/ttyACM0' if os.name == 'posix' else '')
        self.port_box = ttk.Combobox(connection, textvariable=self.port, width=28)
        self.port_box.pack(side='left')
        ttk.Button(connection, text='Ports USB', command=self.refresh_ports).pack(side='left', padx=6)
        ttk.Button(connection, text='Connecter', command=self.connect).pack(side='left', padx=6)
        ttk.Button(connection, text='Déconnecter', command=self.disconnect).pack(side='left')
        self.connection_text = ttk.Label(frame, text='Libérer le port dans Thonny, puis connecter et appuyer sur RUN.')
        self.connection_text.pack(anchor='w', pady=5)
        self.banner = tk.Label(frame, text='AUCUNE MESURE', bg='#5c5662', fg='white',
                               font=('Sans', 13, 'bold'), pady=10, wraplength=970)
        self.banner.pack(fill='x', pady=8)
        self.values = ttk.Label(frame, text='Cap : —    Gîte : —    Bôme : —', wraplength=970)
        self.values.pack(anchor='w', pady=6)
        self.details = ttk.Label(frame, text='Les angles avant calibration sont non validés.', wraplength=970)
        self.details.pack(anchor='w', pady=6)
        self.canvas = tk.Canvas(frame, bg='#163747', highlightthickness=0, width=800, height=400)
        self.canvas.pack(fill='both', expand=True)
        ttk.Label(frame, text='Les mesures et alertes sont calculées sur le Pico. '
                  'Cette fenêtre ne commande ni les sorties ni la calibration.', wraplength=970).pack(anchor='w', pady=6)
        self.refresh_ports()
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.tick()

    def refresh_ports(self):
        ports = [p.device for p in self.port_list()]
        self.port_box['values'] = ports
        if ports and self.port.get() not in ports:
            self.port.set(ports[0])

    def connect(self):
        self.disconnect()
        self.wanted = True
        self._open()

    def _open(self):
        try:
            options = dict(port=self.port.get(), baudrate=115200, timeout=0)
            if os.name == 'posix':
                options['exclusive'] = True
            self.serial = self.serial_factory(**options)
            self.buffer = b''
            self.discard_line = False
            self.connection_text.config(text='Port ouvert — en attente des trames ; appuyer sur RUN si nécessaire.')
        except OSError as error:
            self.serial = None
            self.connection_text.config(text='USB : %s. Libérer le port dans Thonny ou vérifier les permissions.' % error)
        self.retry_at = time.monotonic() + 1

    def _close_port(self):
        if self.serial is not None:
            try:
                self.serial.close()
            except OSError:
                pass
            self.serial = None

    def disconnect(self):
        self.wanted = False
        self._close_port()
        self.received = None
        self.state = None
        self.connection_text.config(text='Déconnecté — aucune mesure en direct.')

    def feed(self, data):
        """Assembler les trames fragmentées et borner la mémoire en cas de flux corrompu."""
        chunks = data.split(b'\n')
        for index, chunk in enumerate(chunks):
            ended = index < len(chunks) - 1
            if not self.discard_line:
                self.buffer += chunk
                if len(self.buffer) > 16384:
                    self.buffer = b''
                    self.discard_line = True
            if ended:
                if not self.discard_line:
                    state = decode(self.buffer.decode('utf-8', errors='replace').strip())
                    if state is not None:
                        self.state = state
                        self.received = time.monotonic()
                self.buffer = b''
                self.discard_line = False

    def render(self):
        fresh = self.received is not None and time.monotonic() - self.received < 1.5
        state = self.state
        if not fresh or state is None:
            self.banner.config(text='AUCUNE MESURE RÉCENTE — liaison interrompue ou Pico en redémarrage', bg='#5c5662')
            self.values.config(text='Cap : —    Gîte : —    Bôme : —')
            self.details.config(text='Les anciennes mesures sont masquées. Attendre le Pico, ou appuyer sur RUN.')
            self.canvas.delete('all')
            return
        m = state.get('mesures') or {}
        valid = state['mesures_valides']
        labels = {'attente': 'ATTENTE — poser à plat, aligner la bôme puis appuyer sur GP20',
                  'calibration': 'CALIBRATION — rester immobile',
                  'fonctionnement': 'SURVEILLANCE ACTIVE',
                  'defaut': 'DÉFAUT — ' + (state.get('erreur') or 'capteur à vérifier')}
        alarm = state['risque'] or state['etat'] == 'defaut'
        self.banner.config(text='ALERTE — RISQUE DE DESSALEMENT' if state['risque'] else labels[state['etat']],
                           bg='#ab3346' if alarm else '#24556b')
        def angle(key):
            value = m.get(key)
            return '—' if value is None else '%.1f°' % value
        self.values.config(text='Cap : %s    Gîte : %s    Bôme après zéro : %s    Appuis GP20 : %s' % (
            angle('cap_deg'), angle('gite_deg'), angle('bome_deg'), state.get('appuis', 0)))
        self.details.config(text='%s · bôme brute : %s · son : %s%s' % (
            'Mesures validées' if valid else 'MESURES NON VALIDÉES', angle('bome_brute_deg'),
            'BIP' if state['son'] else 'silence',
            ' · journal : ' + state['erreur_log'] if state.get('erreur_log') else ''))
        self.connection_text.config(text='USB connecté — dernière trame il y a %.1f s' % (time.monotonic()-self.received))
        cap, gite = m.get('cap_deg'), m.get('gite_deg')
        boom = m.get('bome_deg') if valid else m.get('bome_brute_deg')
        if cap is None or gite is None or boom is None or state['etat'] == 'defaut':
            self.canvas.delete('all')
            self.canvas.create_text(30, 50, anchor='w', text='Dessin indisponible : mesures non exploitables.', fill='white')
        else:
            dessiner_navire(self.canvas, cap, gite, boom, state,
                            'Bôme : angle calibré' if valid else 'Bôme brute — avant calibration')

    def tick(self):
        if self.closed:
            return
        now = time.monotonic()
        if self.wanted and self.serial is None and now >= self.retry_at:
            self._open()
        if self.serial is not None:
            try:
                count = min(self.serial.in_waiting, 8192)
                if count:
                    self.feed(self.serial.read(count))
            except OSError as error:
                self._close_port()
                self.received = None
                self.connection_text.config(text='USB déconnecté : %s ; reconnexion automatique…' % error)
                self.retry_at = now + 1
        self.render()
        self.after_id = self.root.after(50, self.tick)

    def close(self):
        self.closed = True
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
        self._close_port()
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        PicoViewer(root)
    except ImportError:
        from tkinter import messagebox
        messagebox.showerror('pyserial requis', 'Installer pyserial dans Python PC : python3 -m pip install pyserial')
        root.destroy()
        return
    root.mainloop()
