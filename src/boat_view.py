"""Dessin Tkinter partagé entre simulation et mesures USB réelles."""
import math

VENT_COULEUR = '#7fd3ff'
POINTS_CARDINAUX = ('N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                    'S', 'SSO', 'SO', 'OSO', 'O', 'ONO', 'NO', 'NNO')


def _nombre(valeur):
    return (isinstance(valeur, (int, float)) and not isinstance(valeur, bool)
            and math.isfinite(valeur))


def point_cardinal(direction_deg):
    """Direction en degrés → point cardinal français sur 16 secteurs."""
    return POINTS_CARDINAUX[int((direction_deg % 360) / 22.5 + .5) % 16]


def angle_vent_relatif(direction_vent, cap_bateau):
    """D'où vient le vent par rapport à l'étrave, dans ]-180, 180] (> 0 : tribord)."""
    a = (direction_vent - cap_bateau) % 360
    return a - 360 if a > 180 else a


def allure(angle_relatif):
    """Nom de l'allure pour un angle de vent relatif."""
    a = abs(angle_relatif)
    if a < 40:
        return 'face au vent'
    if a < 70:
        return 'au près'
    if a < 110:
        return 'vent de travers'
    if a < 155:
        return 'au largue'
    return 'vent arrière'


def vent_valide(meteo):
    """Renvoie la météo si ses champs essentiels sont exploitables, sinon None."""
    if not isinstance(meteo, dict):
        return None
    if not _nombre(meteo.get('vent_kn')) or not _nombre(meteo.get('direction_vent_deg')):
        return None
    return meteo


def textes_vent(state, cap_deg=None):
    """(titre, détail, couleur) du bandeau vent, à partir d'un instantané."""
    meteo = vent_valide(state.get('meteo'))
    erreur = state.get('erreur_meteo')
    if meteo is None:
        if erreur:
            return ('VENT — indisponible', 'Échec météo : %s' % erreur, '#ffb46b')
        return ('VENT — en attente', 'Connexion au partage du téléphone puis requête Météo-France…',
                '#b9d5df')
    vitesse, direction = meteo['vent_kn'], meteo['direction_vent_deg']
    rafales = meteo.get('rafales_kn')
    force = meteo.get('beaufort')
    titre = 'VENT  %.0f kn' % vitesse
    if _nombre(force):
        titre += '  ·  force %d' % force
    if _nombre(rafales):
        titre += '  ·  rafales %.0f kn' % rafales
    titre += '  ·  du %s (%.0f°)' % (point_cardinal(direction), direction)
    morceaux = []
    if _nombre(cap_deg):
        relatif = angle_vent_relatif(direction, cap_deg)
        if abs(relatif) < 1 or abs(relatif) > 179:
            cote = ''
        else:
            cote = ' tribord' if relatif > 0 else ' bâbord'
        morceaux.append('%s : %.0f°%s' % (allure(relatif).capitalize(), abs(relatif), cote))
    age = state.get('meteo_age_ms')
    recu = '' if not _nombre(age) else ', reçu il y a %d min' % (age // 60000)
    morceaux.append('Météo-France %s UTC%s' % (str(meteo.get('date_source', '?'))[-5:], recu))
    couleur = VENT_COULEUR
    if state.get('meteo_perimee'):
        morceaux.append('DONNÉE PÉRIMÉE')
        couleur = '#ffb46b'
    if erreur:
        morceaux.append('dernier échec : %s' % erreur)
    return titre, '   ·   '.join(morceaux), couleur


def dessiner_vent(c, cx, cy, rayon, meteo, couleur=VENT_COULEUR, cap_deg=None):
    """Rose des vents : la flèche traverse le cercle dans le sens où souffle le vent
    (elle part du côté d'où il vient). Trait gris : axe du bateau."""
    meteo = vent_valide(meteo)
    if meteo is None:
        return
    c.create_oval(cx-rayon, cy-rayon, cx+rayon, cy+rayon, outline='#4d7484', width=2)
    for texte, angle in (('N', 0), ('E', 90), ('S', 180), ('O', 270)):
        r = math.radians(angle)
        c.create_text(cx + math.sin(r) * (rayon + 12), cy - math.cos(r) * (rayon + 12),
                      text=texte, fill='#b9d5df', font=('Sans', 10, 'bold'))
    if _nombre(cap_deg):
        r = math.radians(cap_deg)
        c.create_line(cx, cy, cx + math.sin(r) * rayon * .8, cy - math.cos(r) * rayon * .8,
                      fill='#d7e9ed', width=3)
    d = math.radians(meteo['direction_vent_deg'])
    ux, uy = math.sin(d), -math.cos(d)  # côté d'où vient le vent, à l'écran
    c.create_line(cx + ux * rayon, cy + uy * rayon, cx - ux * rayon * .75, cy - uy * rayon * .75,
                  fill=couleur, width=6, arrow='last', arrowshape=(16, 20, 8))
    c.create_text(cx, cy + rayon + 30, text='VENT %.0f kn' % meteo['vent_kn'], fill=couleur,
                  font=('Sans', 12, 'bold'))
    if _nombre(cap_deg):
        c.create_text(cx, cy + rayon + 48, text='trait blanc : axe du bateau',
                      fill='#b9d5df', font=('Sans', 9))


def dessiner_navire(c, cap_deg, gite_deg, bome_deg, state, legende='Bôme orange : entrée physique'):
    c.delete('all')
    w, h = max(c.winfo_width(), 520), max(c.winfo_height(), 400)
    cx, cy = w / 2, h * .32
    scale = min(w / 4, h / 4)
    cap = math.radians(cap_deg)

    def point(x, y):
        return (cx + (x * math.cos(cap) - y * math.sin(cap)) * scale,
                cy + (x * math.sin(cap) + y * math.cos(cap)) * scale)

    c.create_text(20, 22, anchor='w', text='VUE DE DESSUS · N ↑', fill='#b9d5df', font=('Sans', 12, 'bold'))
    c.create_polygon(*[v for xy in [(0, -1), (.38, -.3), (.36, .9), (-.36, .9), (-.38, -.3)]
                       for v in point(*xy)], fill='#d7e9ed', outline='#8baebd', width=2)
    c.create_line(*point(0, -.8), *point(0, 1), fill='#568495', dash=(5, 4))
    a = math.radians(bome_deg)
    c.create_line(*point(0, 0), *point(-math.sin(a), math.cos(a)), fill='#ffbd69', width=7)
    c.create_oval(cx-6, cy-6, cx+6, cy+6, fill='white', outline='')
    c.create_text(w-20, 22, anchor='e', text=legende, fill='#ffbd69')
    if vent_valide(state.get('meteo')) is not None:
        couleur = '#ffb46b' if state.get('meteo_perimee') else VENT_COULEUR
        rayon = min(48, h * .11)
        dessiner_vent(c, w - rayon - 40, 60 + rayon, rayon, state['meteo'], couleur, cap_deg)
    # Coupe arrière : coque, pont et mât tournent avec la gîte.
    cy = h * .78
    roll = math.radians(gite_deg)
    cap = roll
    c.create_text(20, h*.59, anchor='w', text='VUE ARRIÈRE · GÎTE', fill='#b9d5df', font=('Sans', 12, 'bold'))
    c.create_line(20, cy+20, w-20, cy+20, fill='#4fa8c5', width=2)
    c.create_polygon(*[v for xy in [(-.7, 0), (.7, 0), (.38, .32), (-.38, .32)]
                       for v in point(*xy)], fill='#d7e9ed', outline='#8baebd')
    c.create_line(*point(0, 0), *point(0, -.85), fill='#ffbd69', width=4)
    color = '#ff6a73' if state['risque'] or state['etat'] == 'defaut' else '#74d6b1'
    c.create_text(w-20, h-20, anchor='e', text='SON : ' + ('BIP' if state['son'] else 'silence'),
                  fill=color, font=('Sans', 13, 'bold'))
