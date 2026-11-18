"""Le dossier distribué doit être autonome pour F5 local, même hors du dépôt."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Écran requis pour le test du paquet Tkinter')
class PackageTests(unittest.TestCase):
    def test_packaged_main_opens_gui_without_repo_sources(self):
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / 'projet'
            project.mkdir()
            shutil.copytree(source / 'src', project / 'src', ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copytree(source / 'tools', project / 'tools')
            for name in ('main.py', 'diagnostic_i2c.py', 'diagnostic_axes.py', 'diagnostic_boutons.py'):
                shutil.copy2(source / name, project / name)
            subprocess.run([sys.executable, str(project / 'tools/preparer_thonny.py')],
                           check=True, capture_output=True, timeout=15)
            package = Path(temp) / 'dossier_telecharge'
            shutil.copytree(project / 'thonny_pico', package)
            shutil.rmtree(project)  # Aucun repli vers les sources du dépôt n'est possible.
            script = '''
import sys
from src import config
from src import pico_viewer
import serial.tools.list_ports
serial.tools.list_ports.comports = lambda: []  # Aucun accès au vrai Pico pendant ce test.
assert config.SIMULATION is False
original = pico_viewer.PicoViewer
opened = []
def open_viewer(root, **kwargs):
    viewer = original(root, **kwargs)
    opened.append(viewer)
    root.after(100, viewer.close)
    return viewer
pico_viewer.PicoViewer = open_viewer
import main
sys.argv = ['main.py']
main.main()
assert len(opened) == 1 and opened[0].closed
print('GUI_PACKAGE_OK')
'''
            result = subprocess.run([sys.executable, '-c', script], cwd=package,
                                    check=True, capture_output=True, text=True, timeout=15)
            self.assertIn('GUI_PACKAGE_OK', result.stdout)
