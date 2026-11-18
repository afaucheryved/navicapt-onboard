"""Trames USB lisibles par le visualiseur PC et conservées dans la console Thonny."""
import json

PREFIX = 'NAVICAPT '


def encode(state):
    return PREFIX + json.dumps({'type': 'navicapt', 'version': 1, 'etat': state})


def decode(line):
    """Ignore les messages console, données tronquées ou non finies."""
    import math
    if not line.startswith(PREFIX):
        return None
    try:
        frame = json.loads(line[len(PREFIX):])
        if frame.get('type') != 'navicapt' or frame.get('version') != 1:
            return None
        state = frame['etat']
        if state['etat'] not in ('attente', 'calibration', 'fonctionnement', 'defaut'):
            return None
        if any(type(state[k]) is not bool for k in ('risque', 'son', 'mesures_valides')):
            return None
        measures = state.get('mesures')
        if measures is not None:
            for key in ('cap_deg', 'gite_deg', 'bome_deg', 'bome_brute_deg'):
                value = measures.get(key)
                if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
                    return None
        return state
    except (ValueError, KeyError, TypeError, AttributeError):
        return None
