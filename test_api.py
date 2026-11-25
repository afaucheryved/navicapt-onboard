# Navi'Capt - getapi.py : récupération du vent via Open-Meteo (modèle Météo-France AROME)
# Cible : Raspberry Pi Pico W (MicroPython, firmware "Pico W").
# Le Pico W se connecte au partage de connexion du téléphone, qui sert de passerelle Internet.
# Requête HTTP(S) écrite directement avec des sockets, avec un message à chaque étape.
import json
import network
import rp2
import socket
import ssl
import time

# --- Partage de connexion du téléphone ---
SSID = "Xiaomi 13T"          # nom de l'iPhone après renommage (sans apostrophe)
PASSWORD = ""    # à remplacer par le vrai mot de passe

# Plan d'eau : la Garonne à Bordeaux (au niveau du pont de pierre)
LAT, LON = 44.84, -0.565

HOST = "api.open-meteo.com"
PATH = ("/v1/meteofrance?latitude={}&longitude={}"
        "&current=wind_speed_10m,wind_direction_10m,wind_gusts_10m"
        "&wind_speed_unit=kn").format(LAT, LON)

# HTTPS (port 443) évite les proxys des opérateurs mobiles qui interceptent
# le HTTP (port 80). Le certificat n'est pas vérifié : suffisant pour un prototype.
USE_HTTPS = True

REFRESH_S = 15 * 60  # le modèle est au pas de 15 min
TIMEOUT_S = 20

rp2.country("FR")
wlan = network.WLAN(network.STA_IF)

STATUTS = {
    0: "inactif",
    1: "connexion en cours",
    -1: "échec de connexion",
    -2: "réseau introuvable (partage coupé, ou en 5 GHz ?)",
    -3: "mot de passe incorrect",
    3: "connecté",
}


def connect_wifi(timeout_s=20):
    if wlan.isconnected():
        return
    wlan.active(True)
    wlan.config(pm=0xa11140)  # désactive l'économie d'énergie Wi-Fi (plus fiable)
    print("Connexion à", SSID, "...")
    wlan.connect(SSID, PASSWORD)
    for _ in range(timeout_s):
        s = wlan.status()
        if s == 3 or s < 0:
            break
        time.sleep(1)
    s = wlan.status()
    if s != 3:
        raise RuntimeError("Wi-Fi : " + STATUTS.get(s, str(s)))
    print("Connecté, IP du Pico :", wlan.ifconfig()[0])


def http_get_json(host, path):
    port = 443 if USE_HTTPS else 80
    etape = "DNS"
    s = None
    try:
        addr = socket.getaddrinfo(host, port)[0][-1]
        etape = "connexion TCP à {}".format(addr)
        s = socket.socket()
        s.settimeout(TIMEOUT_S)
        s.connect(addr)
        if USE_HTTPS:
            etape = "négociation TLS"
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            if hasattr(ctx, "check_hostname"):
                ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            s = ctx.wrap_socket(s, server_hostname=host)
        f = s if hasattr(s, "readline") else s.makefile("rwb")

        etape = "envoi de la requête"
        f.write(("GET {} HTTP/1.0\r\nHost: {}\r\nUser-Agent: NaviCapt-PicoW\r\n"
                 "Accept: application/json\r\nConnection: close\r\n\r\n")
                .format(path, host).encode())
        if hasattr(f, "flush"):
            f.flush()

        etape = "attente de la réponse"
        statut = f.readline()
        longueur = None
        while True:  # en-têtes
            ligne = f.readline()
            if not ligne or ligne == b"\r\n":
                break
            if ligne.lower().startswith(b"content-length:"):
                longueur = int(ligne.split(b":")[1])

        etape = "lecture du contenu"
        corps = f.read(longueur) if longueur else f.read()
    except OSError as e:
        raise RuntimeError("{} pendant : {}".format(e, etape))
    finally:
        if s:
            s.close()

    if b" 200 " not in statut:
        raise RuntimeError("API : {} | {}".format(statut, corps[:150]))
    return json.loads(corps)


def get_wind():
    """Renvoie (vitesse_kn, direction_deg, rafales_kn, heure UTC)."""
    print("Requête à Open-Meteo ({})...".format("HTTPS" if USE_HTTPS else "HTTP"))
    c = http_get_json(HOST, PATH)["current"]
    return (c["wind_speed_10m"], c["wind_direction_10m"],
            c["wind_gusts_10m"], c["time"])


def beaufort(kn):
    seuils = (1, 4, 7, 11, 17, 22, 28, 34, 41, 48, 56, 64)
    return sum(1 for s in seuils if kn >= s)


def angle_relatif(dir_vent, cap_bateau):
    """Angle d'où vient le vent par rapport à l'axe du bateau, dans ]-180, 180].
    > 0 : vent venant de tribord, < 0 : de bâbord, 0 : vent de face."""
    a = (dir_vent - cap_bateau) % 360
    return a - 360 if a > 180 else a


def main():
    while True:
        try:
            connect_wifi()  # se reconnecte tout seul si le téléphone a coupé
            v, d, raf, t = get_wind()
            print("{} UTC | {:.1f} kn (F{}) | du {:.0f}° | rafales {:.1f} kn"
                  .format(t, v, beaufort(v), d, raf))
            # cap = lire_boussole()
            # print(angle_relatif(d, cap))
            time.sleep(REFRESH_S)
        except Exception as e:
            print("Erreur :", e)
            time.sleep(10)  # on réessaie vite en cas de problème


main()