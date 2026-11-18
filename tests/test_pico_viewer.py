"""Vraie fenêtre et vrai port série virtuel ; aucun accès au Pico de l'utilisateur."""
import os
import time
import unittest
from src.telemetry import encode
from test_logging_telemetry import state


@unittest.skipUnless(os.environ.get('DISPLAY') and os.name == 'posix', 'Écran et pseudo-terminal requis')
class ViewerTests(unittest.TestCase):
    def test_autoconnect_only_an_identified_single_pico(self):
        import tkinter as tk
        from types import SimpleNamespace
        from src.pico_viewer import PicoViewer
        master, slave = os.openpty()
        root = tk.Tk()
        port = SimpleNamespace(device=os.ttyname(slave), vid=0x2E8A)
        viewer = PicoViewer(root, port_list=lambda: [port], auto_connect=True)
        try:
            self.assertIsNotNone(viewer.serial)
            self.assertEqual(viewer.port.get(), port.device)
            viewer.disconnect()
            port.vid = 0x1234
            viewer.auto_connect_pico()
            self.assertIsNone(viewer.serial)
            self.assertFalse(viewer.wanted)
        finally:
            viewer.close()
            os.close(master)
            os.close(slave)

    def test_usb_stream_alert_stale_recovery_and_close(self):
        import tkinter as tk
        from src.pico_viewer import PicoViewer
        from PIL import ImageGrab
        master, slave = os.openpty()
        root = tk.Tk()
        viewer = PicoViewer(root)
        viewer.port.set(os.ttyname(slave))
        errors = []
        root.report_callback_exception = lambda *error: errors.append(error)
        def pump(duration=.12):
            end = time.monotonic() + duration
            while time.monotonic() < end:
                root.update()
                time.sleep(.01)
            self.assertEqual(errors, [])
        try:
            viewer.connect()
            pump()
            self.assertIsNotNone(viewer.serial)
            frame = encode(state()) + '\n'
            os.write(master, b'Pico demarrage\n' + frame[:30].encode())
            pump()
            self.assertIsNone(viewer.state)
            os.write(master, frame[30:].encode())
            pump()
            self.assertEqual(viewer.state['etat'], 'attente')
            self.assertIn('NON VALIDÉES', viewer.details.cget('text'))
            alarm = state(etat='fonctionnement', risque=True, son=True, mesures_valides=True, appuis=1,
                          mesures=dict(cap_deg=30, gite_deg=55, bome_deg=35, bome_brute_deg=35))
            os.write(master, (encode(alarm)+'\n').encode())
            pump()
            self.assertIn('ALERTE', viewer.banner.cget('text'))
            self.assertGreater(len(viewer.canvas.find_all()), 0)
            ImageGrab.grab().save('/tmp/navicapt-usb.png')
            viewer.received = time.monotonic() - 2
            viewer.render()
            self.assertIn('AUCUNE MESURE', viewer.banner.cget('text'))
            self.assertEqual(len(viewer.canvas.find_all()), 0)
            os.write(master, (encode(state())+'\n').encode())
            pump()
            self.assertIn('ATTENTE', viewer.banner.cget('text'))
            viewer.feed(b'x' * 20000 + b'\n' + frame.encode())
            self.assertEqual(viewer.buffer, b'')
            self.assertEqual(viewer.state['etat'], 'attente')
            viewer.disconnect()
            viewer.render()
            self.assertIn('AUCUNE MESURE', viewer.banner.cget('text'))
        finally:
            viewer.close()
            os.close(master)
            os.close(slave)
