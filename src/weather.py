"""Météo Open-Meteo : un seul travailleur réseau, hors boucle de surveillance."""

import sys
import json
import math
import _thread
from .compat import ticks_ms, ticks_diff, sleep_ms


def normaliser_meteo(donnees: dict) -> dict:
    """Vérifie et normalise les unités demandées à Open-Meteo."""
    actuel = donnees['current']
    unites = donnees['current_units']
    champs = (('temperature_2m', '°C', 'temperature_c'),
              ('wind_speed_10m', 'm/s', 'vent_ms'),
              ('wind_direction_10m', '°', 'direction_vent_deg'))
    resultat = {'source': 'Open-Meteo', 'date_source': actuel['time']}
    for cle, unite, cible in champs:
        valeur = actuel[cle]
        if unites[cle] != unite or not isinstance(valeur, (int, float)) or not math.isfinite(valeur):
            raise ValueError('Donnée météo invalide : ' + cle)
        resultat[cible] = valeur
    return resultat


class OpenMeteo:
    """Isole DNS, HTTPS et lecture JSON dans un travailleur borné."""

    def __init__(self) -> None:
        """Empêche les requêtes concurrentes, même après expiration."""
        self.verrou = _thread.allocate_lock()

    def _request(self, url: str, timeout_ms: int) -> dict:
        """Lit au plus 16 Kio et ferme toujours la réponse réseau."""
        if sys.implementation.name == 'micropython':
            import requests
            reponse = requests.get(url, timeout=timeout_ms / 1000)
            try:
                if reponse.status_code != 200:
                    raise OSError('HTTP météo : %s' % reponse.status_code)
                contenu = reponse.raw.read(16385)
            finally:
                reponse.close()
        else:
            from urllib.request import urlopen
            with urlopen(url, timeout=timeout_ms / 1000) as reponse:
                contenu = reponse.read(16385)
        if len(contenu) > 16384:
            raise ValueError('Réponse météo trop volumineuse')
        return normaliser_meteo(json.loads(contenu))

    async def fetch(self, latitude: float, longitude: float, timeout_ms: int) -> dict:
        """Attend un résultat sans bloquer ni accumuler les travailleurs."""
        if not self.verrou.acquire(False):
            raise OSError('Requête météo précédente encore en cours')
        resultat = {}
        url = ('https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s'
               '&current=temperature_2m,wind_speed_10m,wind_direction_10m'
               '&wind_speed_unit=ms&timezone=UTC') % (latitude, longitude)

        def travail() -> None:
            """Transmet uniquement un résultat ou une erreur à la boucle."""
            try:
                resultat['valeur'] = self._request(url, timeout_ms)
            except Exception as erreur:
                resultat['erreur'] = str(erreur)
            finally:
                self.verrou.release()
                resultat['termine'] = True

        try:
            _thread.start_new_thread(travail, ())
        except Exception:
            self.verrou.release()
            raise
        debut = ticks_ms()
        while not resultat.get('termine', False):
            if ticks_diff(ticks_ms(), debut) >= timeout_ms:
                # Le travailleur finira et libérera ses ressources ; aucun autre
                # ne sera créé tant qu'il reste actif (notamment si DNS bloque).
                raise OSError('Délai météo dépassé')
            await sleep_ms(20)
        if 'erreur' in resultat:
            raise OSError(resultat['erreur'])
        return resultat['valeur']


async def connecter_wifi(timeout_ms: int) -> None:
    """Connecte l'ESP32 avec les identifiants locaux si nécessaire."""
    if sys.implementation.name != 'micropython':
        return
    import network
    wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected():
        return
    try:
        from secrets import WIFI_SSID, WIFI_PASSWORD
    except ImportError:
        raise OSError('Créer secrets.py avec WIFI_SSID et WIFI_PASSWORD')
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    debut = ticks_ms()
    while not wlan.isconnected():
        if ticks_diff(ticks_ms(), debut) >= timeout_ms:
            wlan.disconnect()
            raise OSError('Connexion Wi-Fi expirée')
        await sleep_ms(100)
