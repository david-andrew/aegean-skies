"""Step 4: pack the announcer for the game.

  python pack.py --corpus ANALYSIS.npz PHONES.json [--corpus ...] --fit FIT.json \
                 --repo REPO --out ANNOUNCER.z [--report OUT.json]

Writes:
  ANNOUNCER.z              raw-deflate tables: phone set, diphone trajectories (int8 mel-cepstra,
                           8-bit aperiodicity/voicing), pronunciation lexicon, letter-to-sound rules.
                           Kept OUTSIDE the repository (scratch) until a final voice is chosen; the
                           game reads it from the AEGEAN_VOICE_DATA environment variable.
                           Its last section is the fitted prosody model (durations, intonation,
                           microprosody, effort, fricative caps, pauses) as named number lists.

The lexicon comes from CMUdict (Carnegie Mellon University; licence in CMUDICT-LICENSE.txt,
which must accompany any distributed copy of the tables).

Only derived numbers leave the scratch analysis: averaged 5 ms spectral-envelope trajectories
(no phase, no pitch, no waveform), and aggregate duration/F0 statistics.
"""
import argparse, glob, json, math, os, re, struct, zlib
import numpy as np
import build_units as bu
import world_analysis as wa
import lts

PHONES = ['pau', 'AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY', 'IH', 'IY', 'OW', 'OY', 'UH', 'UW',
          'B', 'CH', 'D', 'DH', 'F', 'G', 'HH', 'JH', 'K', 'L', 'M', 'N', 'NG', 'P', 'R', 'S', 'SH', 'T',
          'TH', 'V', 'W', 'Y', 'Z', 'ZH', 'AX', 'IX', 'AXR', 'IYX']

# Pronunciations the dictionary lacks or gets wrong for this world (stress digit on vowels).
# Place and personal names of this world, read Greek-style (the user's decision, 2026-11-15):
# a = ah, e = eh, i/y = ee, o = oh, ou = oo, no English reduction, stress on the penultimate
# syllable unless the name's Greek says otherwise (Kálamos, Nikólaos, Mikrá, Kryfó). Names not
# listed here are read by the same values from the letter-to-sound rules (lts.py).
NAMES = {
    'kalyra': 'K AA0 L IY1 R AA0', 'kalyran': 'K AA0 L IY1 R AA0 N', 'kalyrans': 'K AA0 L IY1 R AA0 N Z',
    'kalyrassa': 'K AA0 L IY0 R AA1 S AA0', 'orenthia': 'OW0 R EH0 N TH IY1 AA0',
    'orenthian': 'OW0 R EH0 N TH IY1 AA0 N', 'orenthians': 'OW0 R EH0 N TH IY1 AA0 N Z',
    'orenthessa': 'OW0 R EH0 N TH EH1 S AA0', 'kalamos': 'K AA1 L AA0 M OW0 S', 'mikra': 'M IY0 K R AA1',
    'agios': 'AA1 Y IY0 OW0 S', 'nikolaos': 'N IY0 K OW1 L AA0 OW0 S', 'selene': 'S EH0 L IY1 N EH0',
    'kryfo': 'K R IY0 F OW1', 'vecchio': 'V EH1 K IY0 OW0', 'porto': 'P OW1 R T OW0',
    'meltemi': 'M EH0 L T EH1 M IY0', 'lepta': 'L EH0 P T AA1',
    # Greek words whose stress is not on the penultimate syllable
    'tsipouro': 'T S IY1 P UW0 R OW0', 'laskaris': 'L AA1 S K AA0 R IY0 S', 'kleftiko': 'K L EH1 F T IY0 K OW0',
    'galaktoboureko': 'G AA0 L AA0 K T OW0 B UW1 R EH0 K OW0', 'tyrnavos': 'T IY1 R N AA0 V OW0 S',
    'ikariotikos': 'IY0 K AA0 R IY0 OW1 T IY0 K OW0 S', 'masticha': 'M AA1 S T IY0 K AA0', 'mastika': 'M AA1 S T IY0 K AA0',
    'faskomilo': 'F AA0 S K OW1 M IY0 L OW0', 'phoinikes': 'F IY1 N IY0 K EH0 S', 'rakomelo': 'R AA0 K OW1 M EH0 L OW0',
}
# Hand-written English entries the dictionary lacks or gets wrong (stress digit on vowels).
MANUAL = dict(NAMES, **{
    'wind': 'W IH1 N D', 'winds': 'W IH1 N D Z',
    'seaplane': 'S IY1 P L EY2 N', 'seaplanes': 'S IY1 P L EY2 N Z', 'floatplane': 'F L OW1 T P L EY2 N',
    'aeroplane': 'EH1 R AH0 P L EY2 N', 'triplane': 'T R AY1 P L EY2 N', 'metres': 'M IY1 T ER0 Z',
    'metre': 'M IY1 T ER0', 'kilometres': 'K IH0 L AA1 M AH0 T ER0 Z', 'harbour': 'HH AA1 R B ER0',
    'archipelago': 'AA2 R K AH0 P EH1 L AH0 G OW2', 'caique': 'K AY0 IY1 K',
    'windscreen': 'W IH1 N D S K R IY2 N', 'privateers': 'P R AY2 V AH0 T IH1 R Z', 'privateer': 'P R AY2 V AH0 T IH1 R',
    'telegraphist': 'T AH0 L EH1 G R AH0 F IH0 S T', 'carburettor': 'K AA1 R B Y ER0 EH2 T ER0',
    'treacle': 'T R IY1 K AH0 L', 'scurvy': 'S K ER1 V IY0', 'kestrel': 'K EH1 S T R AH0 L', 'petrel': 'P EH1 T R AH0 L',
    'claret': 'K L AE1 R AH0 T', 'convalescents': 'K AA2 N V AH0 L EH1 S AH0 N T S', 'patronal': 'P AH0 T R OW1 N AH0 L',
    'cretans': 'K R IY1 T AH0 N Z', 'malmsey': 'M AA1 M Z IY0', 'lychee': 'L IY1 CH IY0', 'practising': 'P R AE1 K T IH0 S IH0 NG',
    'tsars': 'Z AA1 R Z', 'aperitifs': 'AH0 P EH2 R IH0 T IY1 F S', 'courgette': 'K UH0 R ZH EH1 T',
})

NUMBER_WORDS = ('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen '
                'fifteen sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty '
                'ninety hundred thousand million first second third fourth fifth sixth seventh eighth ninth '
                'tenth point minus o clock oclock half quarter past noon midnight').split()


def harvest(repo):
    words = set()
    for f in glob.glob(os.path.join(repo, 'src', '*.jo')):
        t = open(f, errors='ignore').read()
        for s in re.findall(r'"((?:[^"\\]|\\.)*)"', t):
            s = re.sub(r'\{[^}]*\}', ' ', s)
            if len(s) < 3 or not re.search('[a-z] [a-z]|^[A-Z][a-z]+$', s):
                continue
            for w in re.findall(r"[A-Za-z][A-Za-z']*", s):
                words.add(w.lower().strip("'"))
    return words


def lexicon(repo, extra_text=''):
    import cmudict
    D = cmudict.dict()
    words = harvest(repo) | set(NUMBER_WORDS) | set(MANUAL)
    for w in re.findall(r"[A-Za-z][A-Za-z']*", extra_text):
        words.add(w.lower())
    out = {}
    unknown = []
    for w in sorted(words):
        if w in MANUAL:
            out[w] = MANUAL[w].split()
        elif w in D:
            out[w] = D[w][0]
        elif derive(w, D):
            out[w] = derive(w, D)
        else:
            unknown.append(w)
    return out, unknown


BRITISH = [(r'our(s?|ed|ing)$', r'or\1'), (r'([^aeiou])re(s?)$', r'\1er\2'), (r'lled$', 'led'), (r'lling$', 'ling'), (r'is(e|es|ed|ing)$', r'iz\1'),
           (r'ys(e|es|ed|ing)$', r'yz\1'), (r'ogue$', 'og'), (r'oghurt$', 'ogurt'), (r'^aero', 'air')]


def derive(w, D):
    """An English word the dictionary has under another form: an American spelling, un-/re- on a
    known word, two known words run together, -y/-ed/-ing on a known stem. Keeps ordinary words
    out of the letter-to-sound rules, which read names (Greek-style)."""
    L = lambda x: MANUAL[x].split() if x in MANUAL else D[x][0] if x in D else None
    for a, b in BRITISH:
        v = re.sub(a, b, w)
        if v != w and L(v):
            return L(v)
    if w.endswith('s') and len(w) > 4 and L(w[:-1]):
        stem = L(w[:-1]); last = re.sub(r'\d', '', stem[-1])
        return stem + (['S'] if last in ('P', 'T', 'K', 'F', 'TH') else ['Z'])
    for suf, add in (('y', ['IY0']), ('ing', ['IH0', 'NG'])):
        if w.endswith(suf) and L(w[:-len(suf)]):
            return L(w[:-len(suf)]) + add
    if w.endswith('ed') and (L(w[:-2]) or L(w[:-1])):
        stem = L(w[:-2]) or L(w[:-1])
        last = re.sub(r'\d', '', stem[-1])
        return stem + (['IH0', 'D'] if last in ('T', 'D') else ['T'] if last in ('P', 'K', 'F', 'S', 'SH', 'CH', 'TH') else ['D'])
    for pre, ph in (('un', ['AH0', 'N']), ('re', ['R', 'IY0'])):
        if w.startswith(pre) and len(w) > len(pre) + 3:
            rest = w[len(pre):]
            r = L(rest) or derive(rest, D)
            if r:
                return ph + r
    for i in range(3, len(w) - 2):
        if L(w[:i]) and L(w[i:]):
            return L(w[:i]) + [p[:-1] + '2' if p.endswith('1') else p for p in L(w[i:])]
    return None


def quantise_units(units):
    keys = sorted(units, key=lambda k: (PHONES.index(k[0]), PHONES.index(k[1])))
    M = wa.ORDER + 1
    B = len(wa.BANDS)
    allm = np.concatenate([units[k]['frames'][:, :M] for k in keys])
    scale = np.maximum(np.abs(allm).max(0), 1e-6) / 127.0
    blob = bytearray()
    for k in keys:
        u = units[k]
        f = u['frames']
        blob += struct.pack('<BBHHH', PHONES.index(k[0]), PHONES.index(k[1]), min(u['count'], 65535),
                            int(round(u['left'] * 1000)), int(round(u['right'] * 1000)))
        q = np.clip(np.round(f[:, :M] / scale), -127, 127).astype(np.int8)
        a = np.clip(np.round(f[:, M:M + B] * 255), 0, 255).astype(np.uint8)
        v = np.clip(np.round(f[:, M + B] * 255), 0, 255).astype(np.uint8)
        for j in range(f.shape[0]):
            blob += q[j].tobytes() + a[j].tobytes() + bytes([v[j]])
    return keys, scale, bytes(blob)


def phone_code(p):
    base = p.rstrip('012')
    stress = int(p[-1]) if p[-1].isdigit() else 0
    return PHONES.index(base) | (stress << 6)


def pack(units, lex, path, model=None):
    M = wa.ORDER + 1
    B = len(wa.BANDS)
    H = bu.HALF
    keys, scale, ublob = quantise_units(units)
    b = bytearray(b'AVX1')
    b += struct.pack('<H', len(PHONES))
    for p in PHONES:
        b += bytes([len(p)]) + p.encode()
    b += struct.pack('<HHHf', M, B, H, wa.ALPHA)
    b += struct.pack('<%df' % M, *scale)
    b += struct.pack('<H', len(keys)) + ublob
    b += struct.pack('<I', len(lex))
    for w, pr in sorted(lex.items()):
        wb = w.encode()
        b += bytes([len(wb)]) + wb + bytes([len(pr)]) + bytes(phone_code(p) for p in pr)
    b += struct.pack('<H', len(lts.RULES))
    for left, mid, right, out in lts.RULES:
        ph = [PHONES.index(p) for p in out.split()]
        for s in (left, mid, right):
            b += bytes([len(s)]) + s.encode()
        b += bytes([len(ph)]) + bytes(ph)
    # The prosody model: named lists of numbers (src/voice_model.jo reads them by name).
    model = model or {}
    b += struct.pack('<H', len(model))
    for name, values in model.items():
        nb = name.encode()
        b += bytes([len(nb)]) + nb + struct.pack('<H', len(values)) + struct.pack('<%df' % len(values), *values)
    raw = bytes(b)
    z = zlib.compress(raw, 9, wbits=-15)
    open(path, 'wb').write(z)
    return len(raw), len(z), len(keys)


DURATION_FACTORS = ['function', 'word_final', 'word_initial', 'cluster', 'syl2', 'syl3', 'final_vowel', 'final_cons', 'stressed_full']
FRICATIVES = ['F', 'V', 'TH', 'DH', 'S', 'Z', 'SH', 'ZH', 'HH']


def _num(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _pick(sources, keys, default):
    """The first finite number found at keys in the sources (a fit, then the prior), else default."""
    for src in sources:
        cur = src
        for k in keys:
            if not isinstance(cur, dict) or k not in cur:
                cur = None
                break
            cur = cur[k]
        v = _num(cur)
        if v is not None:
            return v
    return default


def _vector(sources, keys, n, default):
    """A list of n finite numbers at keys in the first source that has one, else default."""
    for src in sources:
        cur = src
        for k in keys:
            cur = cur.get(k) if isinstance(cur, dict) else None
        if isinstance(cur, (list, tuple)) and len(cur) == n and all(_num(x) is not None for x in cur):
            return [float(x) for x in cur]
    return list(default)


NEUTRAL_LEVELS = {'0': 0.0, '1': 0.0, '2': 0.0}


def model_numbers(fit, superposition, prior=None):
    """The fitted prosody as named number lists, in the order src/voice_model.jo expects. Any
    value the fit lacks (a class with no examples in a small pool, a non-finite estimate) comes
    from the prior fit if given, else a neutral default; a missing phrase-level class takes the
    mean of the classes that are present."""
    prior = prior or {}
    sp_prior = prior.get('superposition', {})
    fits = [fit, prior]
    m = {}
    m['duration_ms'] = [_pick(fits, ['durations', 'intercept_ms', p], 0.0) for p in PHONES]
    m['duration_factors'] = [_pick(fits, ['durations', 'factors', k], 1.0) for k in DURATION_FACTORS]
    m['elasticity'] = [_pick(fits, ['durations', 'elasticity', k], -0.5) for k in ['stressed_vowel', 'unstressed_vowel', 'onset', 'coda']]
    m['reference_rate'] = [_pick(fits, ['durations', 'reference_rate'], 5.5)]
    caps = []
    for kind in ['', '_wordend', '_final']:
        for p in PHONES:
            v = 0.0
            if p in FRICATIVES:
                for key in (p + kind, p + '_wordend', p):
                    v = _pick(fits, ['fricatives', key, 'p90_ms'], None)
                    if v is not None:
                        break
            caps.append(v or 0.0)
    m['fricative_cap_ms'] = caps
    sps = [superposition, sp_prior]
    for k, n in [('arc_stop', 10), ('arc_other', 10), ('accent_first', 13), ('accent_middle', 13), ('accent_nuclear', 13), ('micro', 3)]:
        m[k] = _vector(sps, ['weights', k], n, [0.0] * n)
    lags = _vector(sps, ['lags'], 13, [round(-0.2 + 0.05 * i, 2) for i in range(13)])
    m['accent_lags'] = [lags[0], lags[1] - lags[0]]
    present = {k: _num(v) for k, v in (superposition.get('level_by_index') or {}).items() if _num(v) is not None}
    mean_present = sum(present.values()) / len(present) if present else None
    levels = []
    for i in range(3):
        v = present.get(str(i))
        if v is None:
            v = _pick([sp_prior], ['level_by_index', str(i)], mean_present if mean_present is not None else 0.0)
        levels.append(v)
    m['level'] = [_pick(fits, ['f0_st', 'median'], 7.0), _pick(sps, ['level_spread'], 1.5)] + levels
    m['effort'] = _vector(fits, ['effort', 'vector'], len((fit.get('effort') or prior.get('effort') or {}).get('vector') or []) or 25, [0.0] * 25)
    m['pauses'] = [_pick(fits, ['pauses', k, 'median_ms'], d) / 1000 for k, d in (('comma', 150.0), ('stop', 450.0), ('none', 150.0))]
    # rendering numbers and genre deliveries calibrated to a speaker (tune_round.calibrate), when present
    if fit.get('shape'):
        m['shape'] = _vector([fit], ['shape'], 3, [1.6, 7.0, 0.5])
    tune = fit.get('tune')
    if tune and all(len(tune.get(k) or []) == 43 for k in ('pitch', 'slope')):
        m['tune_pitch'], m['tune_slope'] = [float(x) for x in tune['pitch']], [float(x) for x in tune['slope']]
        if len(tune.get('energy') or []) == 43 and len(tune.get('intrinsic') or []) == len(PHONES):
            m['tune_energy'], m['tune_intrinsic'] = [float(x) for x in tune['energy']], [float(x) for x in tune['intrinsic']]
    if _num(fit.get('sustain')) is not None:
        m['sustain'] = [float(fit['sustain'])]
    for g, v in sorted((fit.get('tilts') or {}).items()):
        if v and all(_num(x) is not None for x in v):
            m['tilt_' + g] = [float(x) for x in v]
    for g, v in sorted((fit.get('styles') or {}).items()):
        if v and len(v) == 4 and all(_num(x) is not None for x in v):
            m['style_' + g] = [float(x) for x in v]
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', nargs=2, action='append', required=True)
    ap.add_argument('--fit', required=True, help='prosody_fit.py output (durations, effort, fricatives, pauses, f0)')
    ap.add_argument('--repo', required=True)
    ap.add_argument('--out', required=True, help='announcer data file, outside the repository')
    ap.add_argument('--report')
    a = ap.parse_args()
    groups = {}
    meta = {}
    for npz, ph in a.corpus:
        phones = json.load(open(ph))['phones']
        tracks = bu.segment_tracks(npz)
        for x, y, f, m in bu.tokens(phones, tracks):
            groups.setdefault((x, y), []).append(f)
            meta.setdefault((x, y), []).append(m)
    units = {}
    for k, fs in groups.items():
        mean, n = bu.average(fs)
        units[k] = dict(frames=mean, count=n, left=float(np.median([m['left'] for m in meta[k]])),
                        right=float(np.median([m['right'] for m in meta[k]])))
    lex, unknown = lexicon(a.repo)
    out = os.path.abspath(a.out)
    if out.startswith(os.path.abspath(a.repo) + os.sep):
        raise SystemExit('--out must be outside the repository until the final voice is chosen')
    fit = json.load(open(a.fit))
    model = model_numbers(fit, fit['superposition'], fit)
    raw, z, n = pack(units, lex, out, model)
    rep = dict(units=n, tokens=sum(len(v) for v in groups.values()), lexicon=len(lex), unknown=len(unknown),
               raw_bytes=raw, deflated_bytes=z, rules=len(lts.RULES))
    print(json.dumps(rep))
    if a.report:
        json.dump(dict(rep, unknown_words=unknown, counts={f'{k[0]}-{k[1]}': u['count'] for k, u in units.items()}),
                  open(a.report, 'w'), indent=1)


if __name__ == '__main__':
    main()
