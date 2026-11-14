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
import argparse, glob, json, os, re, struct, zlib
import numpy as np
import build_units as bu
import world_analysis as wa
import lts

PHONES = ['pau', 'AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY', 'IH', 'IY', 'OW', 'OY', 'UH', 'UW',
          'B', 'CH', 'D', 'DH', 'F', 'G', 'HH', 'JH', 'K', 'L', 'M', 'N', 'NG', 'P', 'R', 'S', 'SH', 'T',
          'TH', 'V', 'W', 'Y', 'Z', 'ZH', 'AX', 'IX', 'AXR', 'IYX']

# Pronunciations the dictionary lacks or gets wrong for this world (stress digit on vowels).
MANUAL = {
    'kalyra': 'K AH0 L IY1 R AH0', 'kalyran': 'K AH0 L IY1 R AH0 N', 'kalyrans': 'K AH0 L IY1 R AH0 N Z',
    'kalyrassa': 'K AE2 L IH0 R AE1 S AH0', 'orenthia': 'AO0 R EH1 N TH IY0 AH0',
    'orenthian': 'AO0 R EH1 N TH IY0 AH0 N', 'orenthians': 'AO0 R EH1 N TH IY0 AH0 N Z',
    'orenthessa': 'AO2 R EH0 N TH EH1 S AH0', 'kalamos': 'K AA1 L AH0 M OW2 S', 'mikra': 'M IY1 K R AH0',
    'agios': 'AA1 Y IY0 OW2 S', 'nikolaos': 'N IY2 K OW0 L AA1 OW0 S', 'selene': 'S EH0 L IY1 N IY0',
    'kryfo': 'K R IY1 F OW0', 'vecchio': 'V EH1 K IY0 OW0', 'porto': 'P AO1 R T OW0',
    'seaplane': 'S IY1 P L EY2 N', 'seaplanes': 'S IY1 P L EY2 N Z', 'floatplane': 'F L OW1 T P L EY2 N',
    'aeroplane': 'EH1 R AH0 P L EY2 N', 'triplane': 'T R AY1 P L EY2 N', 'metres': 'M IY1 T ER0 Z',
    'metre': 'M IY1 T ER0', 'kilometres': 'K IH0 L AA1 M AH0 T ER0 Z', 'harbour': 'HH AA1 R B ER0',
    'archipelago': 'AA2 R K AH0 P EH1 L AH0 G OW2', 'meltemi': 'M EH0 L T EH1 M IY0', 'caique': 'K AY0 IY1 K',
    'windscreen': 'W IH1 N D S K R IY2 N', 'privateers': 'P R AY2 V AH0 T IH1 R Z', 'privateer': 'P R AY2 V AH0 T IH1 R',
    'telegraphist': 'T AH0 L EH1 G R AH0 F IH0 S T', 'carburettor': 'K AA1 R B Y ER0 EH2 T ER0',
}

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
        else:
            unknown.append(w)
    return out, unknown


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


def model_numbers(fit, superposition):
    """The fitted prosody as named number lists, in the order src/voice_model.jo expects."""
    d = fit['durations']
    m = {}
    m['duration_ms'] = [d['intercept_ms'].get(p, 0.0) for p in PHONES]
    m['duration_factors'] = [d['factors'][k] for k in DURATION_FACTORS]
    m['elasticity'] = [d['elasticity'][k] for k in ['stressed_vowel', 'unstressed_vowel', 'onset', 'coda']]
    m['reference_rate'] = [d['reference_rate']]
    caps = []
    fr = fit['fricatives']
    for kind in ['', '_wordend', '_final']:
        for p in PHONES:
            v = fr.get(p + kind) or fr.get(p + '_wordend') or fr.get(p)
            caps.append(v['p90_ms'] if (p in FRICATIVES and v) else 0.0)
    m['fricative_cap_ms'] = caps
    w = superposition['weights']
    for k in ['arc_stop', 'arc_other', 'accent_first', 'accent_middle', 'accent_nuclear', 'micro']:
        m[k] = w[k]
    m['accent_lags'] = [superposition['lags'][0], superposition['lags'][1] - superposition['lags'][0]]
    m['level'] = [fit['f0_st']['median'], superposition['level_spread']] + [superposition['level_by_index'][str(i)] for i in range(3)]
    m['effort'] = fit['effort']['vector']
    pz = fit['pauses']
    m['pauses'] = [pz['comma']['median_ms'] / 1000, pz['stop']['median_ms'] / 1000, pz['none']['median_ms'] / 1000]
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
    model = model_numbers(fit, fit['superposition'])
    raw, z, n = pack(units, lex, out, model)
    rep = dict(units=n, tokens=sum(len(v) for v in groups.values()), lexicon=len(lex), unknown=len(unknown),
               raw_bytes=raw, deflated_bytes=z, rules=len(lts.RULES))
    print(json.dumps(rep))
    if a.report:
        json.dump(dict(rep, unknown_words=unknown, counts={f'{k[0]}-{k[1]}': u['count'] for k, u in units.items()}),
                  open(a.report, 'w'), indent=1)


if __name__ == '__main__':
    main()
