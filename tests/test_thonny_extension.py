"""Extension testée avec l’événement réel de Thonny et une fenêtre Tk, sans accès USB."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from src.telemetry import encode
from test_logging_telemetry import state

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('install_navicapt', ROOT / 'tools/installer_extension_thonny.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def test_self_contained_install_and_targeted_uninstall(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            other = target / 'thonnycontrib/other_plugin'
            other.mkdir(parents=True)
            (other / 'keep').write_text('keep')
            dest = installer.install(target)
            for name in ('pico_viewer.py', 'boat_view.py', 'telemetry.py'):
                self.assertEqual((dest / 'runtime' / name).read_bytes(), (ROOT / 'src' / name).read_bytes())
            installer.install(target, uninstall=True)
            self.assertFalse(dest.exists())
            self.assertTrue((other / 'keep').exists())


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Écran Tk requis (xvfb-run)')
class ThonnyExtensionTests(unittest.TestCase):
    def test_console_events_f5_errors_interruptions_and_single_window(self):
        import tkinter as tk
        from tkinter import ttk
        from thonny.workbench import Workbench
        class TestWorkbench(tk.Tk):
            bind = Workbench.bind
            event_generate = Workbench.event_generate
            def __init__(self):
                self._event_handlers = {}
                self._closing = False
                self.commands = {}
                super().__init__()
            def _update_toolbar(self): pass
            def add_command(self, ident, menu, label, handler): self.commands[ident] = handler
            def report_exception(self, message): raise AssertionError(message)
        with tempfile.TemporaryDirectory() as temp:
            dest = installer.install(Path(temp))
            spec = importlib.util.spec_from_file_location('navicapt_installed_test', dest / '__init__.py',
                                                         submodule_search_locations=[str(dest)])
            plugin = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = plugin
            spec.loader.exec_module(plugin)
            wb = TestWorkbench()
            outputs = []
            wb.bind('ProgramOutput', lambda event: outputs.append(event.data), True)
            style = ttk.Style(wb)
            original_style = style.configure('TLabel')
            original_theme = style.theme_use()
            try:
                with patch('thonny.get_workbench', return_value=wb), \
                     patch('serial.Serial', side_effect=AssertionError('USB interdit dans extension')):
                    plugin.load_plugin()
                    plugin.load_plugin()  # Pas de double abonnement.
                    bridge = plugin._bridge
                    self.assertEqual(len(wb._event_handlers['ProgramOutput']), 2)
                    def emit(text, stream='stdout'):
                        wb.event_generate('ProgramOutput', data=text, stream_name=stream)
                        wb.update()
                    frame = encode(state()) + '\r\n'
                    emit('texte console\nNAVICAPT {invalide}\n')
                    self.assertIsNone(bridge.viewer)
                    emit(frame[:25])
                    self.assertIsNone(bridge.viewer)
                    emit(frame[25:])
                    viewer = bridge.viewer
                    self.assertIsNotNone(viewer)
                    self.assertTrue(viewer.console)
                    self.assertIsNone(viewer.serial)
                    self.assertIn('22.0°', viewer.values.cget('text'))
                    self.assertEqual(style.configure('TLabel'), original_style)
                    self.assertEqual(style.theme_use(), original_theme)
                    alarm = state(etat='fonctionnement', risque=True, son=True, mesures_valides=True)
                    emit(encode(alarm)+'\n')
                    self.assertIs(bridge.viewer, viewer)
                    self.assertIn('ALERTE', viewer.banner.cget('text'))
                    emit(encode(state(etat='defaut', erreur='capteur absent', son=True))+'\n')
                    self.assertIn('capteur absent', viewer.banner.cget('text'))
                    bridge.received = viewer.received = 0
                    viewer.render()
                    self.assertIn('AUCUNE MESURE', viewer.banner.cget('text'))
                    self.assertEqual(len(viewer.canvas.find_all()), 0)
                    bridge.hide()
                    emit(frame)
                    self.assertEqual(viewer.root.state(), 'withdrawn')
                    wb.event_generate('CommandAccepted', command=SimpleNamespace(name='Run'))
                    self.assertIsNone(viewer.state)
                    emit(frame)
                    self.assertEqual(viewer.root.state(), 'normal')
                    self.assertIs(bridge.viewer, viewer)
                    emit('x'*17000 + '\n' + frame)
                    self.assertEqual(bridge.buffer, '')
                    self.assertEqual(viewer.state['etat'], 'attente')
                    emit(encode(alarm)+'\n', 'stderr')
                    self.assertEqual(viewer.state['etat'], 'attente')
                    wb.event_generate('BackendTerminated')
                    self.assertIsNone(viewer.state)
                    self.assertIn('AUCUNE MESURE', viewer.banner.cget('text'))
                    self.assertIn(frame, ''.join(outputs))  # Console intacte.
                    self.assertEqual(len(wb.winfo_children()), 1)
            finally:
                if plugin._bridge.viewer:
                    plugin._bridge.viewer.close()
                wb.destroy()
                for name in list(sys.modules):
                    if name.startswith(spec.name): del sys.modules[name]
