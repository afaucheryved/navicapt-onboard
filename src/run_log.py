"""Journal JSON par ligne, borné à deux fichiers ; compatible MicroPython."""
import json
import os
import random
from .compat import ticks_ms, ticks_diff


def resume_etat(state):
    """Champs de premier niveau, unités explicites et état conservé comme texte."""
    measures = state.get('mesures') or {}
    return {'etat': state.get('etat'), 'gite_deg': measures.get('gite_deg'),
            'bome_deg': measures.get('bome_deg'), 'risque': state.get('risque'),
            'erreur': state.get('erreur'), 'son': state.get('son'),
            'cap_bateau_deg': measures.get('cap_deg'),
            'cap_bome_deg': measures.get('cap_bome_deg'),
            'bome_zero_deg': measures.get('bome_zero_deg'),
            'mesure_ms': measures.get('mesure_ms'),
            'mesures_valides': state.get('mesures_valides', False),
            'appuis': state.get('appuis'), 'bouton': state.get('bouton'),
            'erreur_log': state.get('erreur_log')}


class RunLogger:
    def __init__(self, path='log.txt', period_ms=5000, max_bytes=131072, clock=ticks_ms):
        self.path = path
        self.period_ms = period_ms
        self.max_bytes = max_bytes
        self.clock = clock
        self.started = clock()
        self.run_id = '%08x' % random.getrandbits(32)
        self.previous = None
        self.last_sample = None
        self.error = None

    def event(self, event, **data):
        """Ferme chaque écriture ; une panne du journal ne coupe pas la surveillance."""
        if self.error is not None:
            return
        snapshot = data.pop('instantane', None)
        record = resume_etat(snapshot or {})
        record.update(data)
        record.update(format_version=2, run_id=self.run_id, evenement=event,
                      depuis_debut_ms=ticks_diff(self.clock(), self.started))
        try:
            line = json.dumps(record) + '\n'
            try:
                size = os.stat(self.path)[6]
            except OSError:
                size = 0
            if size + len(line.encode('utf-8')) > self.max_bytes:
                try:
                    os.remove(self.path + '.1')
                except OSError:
                    pass
                if size:
                    os.rename(self.path, self.path + '.1')
            with open(self.path, 'a') as stream:
                stream.write(line)
        except OSError as error:
            self.error = str(error)
            print('Journal indisponible : ' + self.error)

    def observe(self, state):
        key = (state['etat'], state['risque'], state['erreur'], state.get('appuis', 0))
        now = self.clock()
        if key != self.previous or self.last_sample is None or ticks_diff(now, self.last_sample) >= self.period_ms:
            self.event('etat' if key != self.previous else 'mesure', instantane=state)
            self.previous = key
            self.last_sample = now
