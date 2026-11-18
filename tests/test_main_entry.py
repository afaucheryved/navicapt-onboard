"""F5 doit lancer le vrai visualiseur sur PC, quel que soit le réglage embarqué."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from src import config

spec = importlib.util.spec_from_file_location('navicapt_entry', Path(__file__).resolve().parents[1] / 'main.py')
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)


class MainEntryTests(unittest.TestCase):
    def test_pc_default_opens_real_viewer_even_with_hardware_config(self):
        start = Mock()
        with patch.object(sys, 'argv', ['main.py']), patch.object(config, 'SIMULATION', False), \
             patch.dict(sys.modules, {'src.pico_viewer': SimpleNamespace(main=start)}):
            entry.main()
        start.assert_called_once_with()
    def test_pc_simulation_requires_explicit_option(self):
        start = Mock()
        with patch.object(sys, 'argv', ['main.py', '--simulation']), \
             patch.dict(sys.modules, {'src.simulator_gui': SimpleNamespace(main=start)}):
            entry.main()
        start.assert_called_once_with()
