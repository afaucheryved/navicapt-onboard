"""Textes du bandeau vent : calculs purs, sans fenêtre."""
import unittest
from src.boat_view import (allure, angle_vent_relatif, point_cardinal, textes_vent,
                           vent_valide)

METEO = {'source': 'Open-Meteo (Météo-France)', 'date_source': '2026-11-25T16:00',
         'vent_kn': 11.6, 'direction_vent_deg': 184, 'rafales_kn': 18.1, 'beaufort': 4}


class WindDisplayTests(unittest.TestCase):
    def test_cardinal_and_relative_angle(self):
        self.assertEqual(point_cardinal(0), 'N')
        self.assertEqual(point_cardinal(184), 'S')
        self.assertEqual(point_cardinal(225), 'SO')
        self.assertEqual(point_cardinal(350), 'N')
        self.assertEqual(angle_vent_relatif(184, 68), 116)
        self.assertEqual(angle_vent_relatif(10, 350), 20)
        self.assertEqual(angle_vent_relatif(300, 0), -60)
        self.assertEqual(allure(20), 'face au vent')
        self.assertEqual(allure(-60), 'au près')
        self.assertEqual(allure(90), 'vent de travers')
        self.assertEqual(allure(130), 'au largue')
        self.assertEqual(allure(-170), 'vent arrière')

    def test_texts_with_heading(self):
        state = {'meteo': METEO, 'meteo_perimee': False, 'erreur_meteo': None,
                 'meteo_age_ms': 240000}
        titre, detail, couleur = textes_vent(state, 68)
        self.assertIn('12 kn', titre)
        self.assertIn('force 4', titre)
        self.assertIn('rafales 18 kn', titre)
        self.assertIn('du S (184°)', titre)
        self.assertIn('Au largue : 116° tribord', detail)
        self.assertIn('16:00 UTC', detail)
        self.assertIn('4 min', detail)
        self.assertNotIn('PÉRIMÉE', detail)

    def test_waiting_error_and_stale(self):
        self.assertIn('en attente', textes_vent({'meteo': None})[0])
        titre, detail, _ = textes_vent({'meteo': None, 'erreur_meteo': 'Wi-Fi : mot de passe incorrect'})
        self.assertIn('indisponible', titre)
        self.assertIn('mot de passe incorrect', detail)
        meteo = dict(METEO, rafales_kn=None)
        titre, detail, couleur = textes_vent({'meteo': meteo, 'meteo_perimee': True}, None)
        self.assertNotIn('rafales', titre)
        self.assertIn('PÉRIMÉE', detail)
        self.assertNotIn('largue', detail)  # pas de cap : pas d'allure

    def test_invalid_frame_values_ignored(self):
        self.assertIsNone(vent_valide({'vent_kn': 'x', 'direction_vent_deg': 10}))
        self.assertIsNone(vent_valide({'vent_kn': float('nan'), 'direction_vent_deg': 10}))
        self.assertIsNone(vent_valide([1, 2]))
        self.assertIn('en attente', textes_vent({'meteo': {'vent_kn': True}})[0])


if __name__ == '__main__':
    unittest.main()
