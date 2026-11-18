"""Journal JSON par ligne, borné à deux fichiers ; compatible MicroPython."""
import json
import os
import random
from .compat import ticks_ms, ticks_diff


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
        record = dict(data)
        record.update(run_id=self.run_id, evenement=event,
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
            self.event('etat' if key != self.previous else 'mesure', etat=state)
            self.previous = key
            self.last_sample = now
