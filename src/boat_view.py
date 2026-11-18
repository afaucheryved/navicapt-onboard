"""Dessin Tkinter partagé entre simulation et mesures USB réelles."""
import math


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

