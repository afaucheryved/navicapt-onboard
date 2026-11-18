"""Test de la vraie fenêtre ; ignoré en l'absence d'écran (xvfb-run convient)."""
import asyncio
import os
import time
import unittest


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Écran requis : lancer avec xvfb-run -a')
class GuiTests(unittest.TestCase):
    def test_calibration_alarm_fault_recovery_and_layout(self):
        import tkinter as tk
        from src.simulator_gui import Simulator
        class Weather:
            async def fetch(self, *args):
                await asyncio.sleep(.01)
                return dict(source='Open-Meteo', temperature_c=15, vent_ms=3.26,
                            direction_vent_deg=162, date_source='2026-11-16T16:30')
        root = tk.Tk()
        gui = Simulator(root, Weather())
        errors = []
        root.report_callback_exception = lambda *error: errors.append(error)
        def pump(seconds):
            end = time.monotonic() + seconds
            while time.monotonic() < end:
                root.update()
                time.sleep(.01)
            self.assertEqual(errors, [])
        try:
            pump(.3)  # Laisser Tk afficher la fenêtre avant le premier appui.
            gui.press_button()
            pump(1.3)
            self.assertEqual(gui.system.etat, 'fonctionnement')
            gui.bome.set(35)
            gui.gite.set(55)
            pump(.8)
            self.assertTrue(gui.system.risque)
            self.assertAlmostEqual(gui.system.mesures['bome_deg'], 35)
            # Contrôle que la météo et les mesures restent à l'intérieur de la fenêtre.
            for widget in (gui.weather_button, gui.readings):
                self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(),
                                     root.winfo_rooty() + root.winfo_height())
            gui.fault.set(True)
            pump(.1)
            self.assertEqual(gui.system.etat, 'defaut')
            gui.fault.set(False)
            gui.gite.set(0)
            gui.bome.set(0)
            gui.press_button()
            pump(1.3)
            self.assertEqual(gui.system.etat, 'fonctionnement')
            self.assertFalse(gui.system.risque)
            self.assertIsNotNone(gui.system.cache_meteo)
        finally:
            gui.close()
        self.assertFalse(gui.output.active)
