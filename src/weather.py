"""Météo Open-Meteo (modèle Météo-France AROME) : un seul travailleur réseau,
hors boucle de surveillance.

Sur Pico W, la requête HTTPS est écrite directement avec des sockets (repris de
test_api.py) : pas de dépendance à `requests`, et le port 443 évite les proxys
des opérateurs mobiles qui interceptent le HTTP. Le Pico passe par le partage de
connexion du téléphone. Le certificat n'est pas vérifié côté Pico : suffisant
pour un prototype. Sur PC, urllib vérifie le certificat normalement.
"""

import sys
import json
import math
import _thread
from .compat import ticks_ms, ticks_diff, sleep_ms

HOTE = 'api.open-meteo.com'
TAILLE_MAX = 16384


def chemin_meteo(latitude: float, longitude: float) -> str:
    """Construit la requête vent actuel, en nœuds, modèle Météo-France."""
    return ('/v1/meteofrance?latitude=%s&longitude=%s'
            '&current=wind_speed_10m,wind_direction_10m,wind_gusts_10m'
            '&wind_speed_unit=kn&timezone=UTC') % (latitude, longitude)


def beaufort(kn: float) -> int:
    """Force Beaufort correspondant à une vitesse en nœuds."""
    seuils = (1, 4, 7, 11, 17, 22, 28, 34, 41, 48, 56, 64)
    return sum(1 for s in seuils if kn >= s)


def angle_relatif(dir_vent: float, cap_bateau: float) -> float:
    """Angle d'où vient le vent par rapport à l'axe du bateau, dans ]-180, 180].
    > 0 : vent venant de tribord, < 0 : de bâbord, 0 : vent de face."""
    a = (dir_vent - cap_bateau) % 360
    return a - 360 if a > 180 else a


def _nombre(valeur) -> bool:
    return isinstance(valeur, (int, float)) and not isinstance(valeur, bool) and math.isfinite(valeur)


def normaliser_meteo(donnees: dict) -> dict:
    """Vérifie et normalise les unités demandées à Open-Meteo."""
    actuel = donnees['current']
    unites = donnees['current_units']
    champs = (('wind_speed_10m', 'kn', 'vent_kn'),
              ('wind_direction_10m', '°', 'direction_vent_deg'))
    resultat = {'source': 'Open-Meteo (Météo-France)', 'date_source': actuel['time']}
    for cle, unite, cible in champs:
        valeur = actuel[cle]
        if unites[cle] != unite or not _nombre(valeur):
            raise ValueError('Donnée météo invalide : ' + cle)
        resultat[cible] = valeur
    # Les rafales peuvent manquer ponctuellement (null) sans invalider le vent moyen.
    rafales = actuel.get('wind_gusts_10m')
    if rafales is not None and (unites.get('wind_gusts_10m') != 'kn' or not _nombre(rafales)):
        raise ValueError('Donnée météo invalide : wind_gusts_10m')
    resultat['rafales_kn'] = rafales
    resultat['beaufort'] = beaufort(resultat['vent_kn'])
    return resultat


def http_get_json(hote: str, chemin: str, timeout_ms: int) -> dict:
    """GET HTTPS par sockets (MicroPython), lit au plus 16 Kio, ferme toujours."""
    import socket
    import ssl
    etape = 'DNS'
    s = None
    try:
        addr = socket.getaddrinfo(hote, 443)[0][-1]
        etape = 'connexion TCP à %s' % (addr,)
        s = socket.socket()
        s.settimeout(timeout_ms / 1000)
        s.connect(addr)
        etape = 'négociation TLS'
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        if hasattr(ctx, 'check_hostname'):
            ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        s = ctx.wrap_socket(s, server_hostname=hote)
        f = s if hasattr(s, 'readline') else s.makefile('rwb')

        etape = 'envoi de la requête'
        f.write((('GET %s HTTP/1.0\r\nHost: %s\r\nUser-Agent: NaviCapt-PicoW\r\n'
                 'Accept: application/json\r\nConnection: close\r\n\r\n')
                % (chemin, hote)).encode())
        if hasattr(f, 'flush'):
            f.flush()

        etape = 'attente de la réponse'
        statut = f.readline()
        longueur = None
        while True:  # en-têtes
            ligne = f.readline()
            if not ligne or ligne == b'\r\n':
                break
            if ligne.lower().startswith(b'content-length:'):
                longueur = int(ligne.split(b':')[1])

        etape = 'lecture du contenu'
        corps = f.read(min(longueur, TAILLE_MAX + 1) if longueur else TAILLE_MAX + 1)
    except OSError as e:
        raise OSError('%s pendant : %s' % (e, etape))
    finally:
        if s:
            s.close()

    if b' 200 ' not in statut:
        raise OSError('HTTP météo : %s | %s' % (statut, corps[:150]))
    if len(corps) > TAILLE_MAX:
        raise ValueError('Réponse météo trop volumineuse')
    return json.loads(corps)


class OpenMeteo:
    """Isole DNS, HTTPS et lecture JSON dans un travailleur borné."""

    def __init__(self) -> None:
        """Empêche les requêtes concurrentes, même après expiration."""
        self.verrou = _thread.allocate_lock()

    def _request(self, chemin: str, timeout_ms: int) -> dict:
        """Lit au plus 16 Kio et ferme toujours la réponse réseau."""
        if sys.implementation.name == 'micropython':
            return normaliser_meteo(http_get_json(HOTE, chemin, timeout_ms))
        from urllib.request import urlopen
        with urlopen('https://' + HOTE + chemin, timeout=timeout_ms / 1000) as reponse:
            contenu = reponse.read(TAILLE_MAX + 1)
        if len(contenu) > TAILLE_MAX:
            raise ValueError('Réponse météo trop volumineuse')
        return normaliser_meteo(json.loads(contenu))

    async def fetch(self, latitude: float, longitude: float, timeout_ms: int) -> dict:
        """Attend un résultat sans bloquer ni accumuler les travailleurs."""
        if not self.verrou.acquire(False):
            raise OSError('Requête météo précédente encore en cours')
        resultat = {}
        chemin = chemin_meteo(latitude, longitude)

        def travail() -> None:
            """Transmet uniquement un résultat ou une erreur à la boucle."""
            try:
                resultat['valeur'] = self._request(chemin, timeout_ms)
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


STATUTS_WIFI = {
    0: 'inactif',
    1: 'connexion en cours',
    -1: 'échec de connexion',
    -2: 'réseau introuvable (partage coupé, ou en 5 GHz ?)',
    -3: 'mot de passe incorrect',
    3: 'connecté',
}


def identifiants_wifi() -> tuple:
    """secrets.py (facultatif, hors Git) prime sur les valeurs de config.py."""
    from . import config
    try:
        from secrets import WIFI_SSID, WIFI_PASSWORD
        return WIFI_SSID, WIFI_PASSWORD
    except ImportError:
        return config.WIFI_SSID, config.WIFI_PASSWORD


async def connecter_wifi(timeout_ms: int) -> None:
    """Connecte le Pico W au partage de connexion du téléphone si nécessaire."""
    if sys.implementation.name != 'micropython':
        return
    try:
        import network
    except ImportError:
        raise OSError('Météo embarquée : Pico W requis (Pico sans Wi-Fi non compatible)')
    wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected():
        return
    try:
        import rp2
        rp2.country('FR')
    except (ImportError, AttributeError):
        pass
    ssid, mot_de_passe = identifiants_wifi()
    wlan.active(True)
    try:
        wlan.config(pm=0xa11140)  # désactive l'économie d'énergie Wi-Fi (plus fiable)
    except (ValueError, OSError):
        pass
    print('Connexion à', ssid, '...')
    wlan.connect(ssid, mot_de_passe)
    debut = ticks_ms()
    while True:
        statut = wlan.status()
        if statut == 3 or statut < 0:
            break
        if ticks_diff(ticks_ms(), debut) >= timeout_ms:
            break
        await sleep_ms(100)
    statut = wlan.status()
    if statut != 3:
        wlan.disconnect()
        raise OSError('Wi-Fi : ' + STATUTS_WIFI.get(statut, str(statut)))
    print('Connecté, IP du Pico :', wlan.ifconfig()[0])
