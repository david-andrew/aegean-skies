"""Step 4: pack the announcer for the game.

  python pack.py --corpus ANALYSIS.npz PHONES.json [--corpus ...] --prosody STATS.json \
                 --repo REPO [--report OUT.json]

Writes, inside REPO:
  data/voice/announcer.z   raw-deflate tables: phone set, diphone trajectories (int8 mel-cepstra,
                           8-bit aperiodicity/voicing), pronunciation lexicon, letter-to-sound rules
  src/voice_model.jo       the prosody numbers as readable constants, with their provenance

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
          'TH', 'V', 'W', 'Y', 'Z', 'ZH']

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


def pack(units, lex, path):
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
    raw = bytes(b)
    z = zlib.compress(raw, 9, wbits=-15)
    open(path, 'wb').write(z)
    return len(raw), len(z), len(keys)


MODEL_TEMPLATE = '''# Generated by tools/voice_world/pack.py from the announcer analysis; rebuild, do not edit.
# Provenance: aggregate statistics of phone-aligned narration analysed in scratch (never
# committed): {sources}. Durations are medians per phone (vowels by stress), in ms at the
# narrator's own pace; F0 numbers are semitones re 100 Hz. Delivery choices that are not
# measurements are marked "set".

const VOICE_SYLLABLES_PER_SECOND = {sps}     # measured speaking rate within phrases
const VOICE_F0_MEDIAN = {f0med}             # Hz, measured
const VOICE_F0_LOW = {f0lo}                 # Hz, 5th percentile, measured
const VOICE_F0_HIGH = {f0hi}                # Hz, 95th percentile, measured
const VOICE_PHRASE_START = {start}          # st, measured phrase baseline start (median)
const VOICE_PHRASE_SPREAD = {start_iqr}     # st, measured interquartile range of phrase starts
const VOICE_DECLINATION = {decl}            # st/s, set between the narrator ({decl_recap}) and the 1942 newsreel ({decl_castle})
const VOICE_ACCENT = {accent}               # st, measured accent rise over the baseline (median)
const VOICE_ACCENT_SPREAD = {accent_iqr}    # st, measured interquartile range of accent rises
const VOICE_ACCENT_PEAK = {peak}            # fraction of the vowel where the accent peaks, measured
const VOICE_FINAL_FALL = {final}            # st, measured: newsreel's terminal fall (narrator {final_recap})
const VOICE_CONTINUATION = {cont}           # st, measured continuation rise before a comma pause
const VOICE_PAUSE_COMMA = {pc}              # s, set between the narrator ({pc_recap}) and the 1942 newsreel ({pc_castle})
const VOICE_PAUSE_STOP = {ps}               # s, set between the narrator ({ps_recap}) and the 1942 newsreel ({ps_castle})
const VOICE_FINAL_LENGTHENING = {fl}        # set (measured median {fl_measured} on a 10 ms grid)

# (phone, median ms unstressed, median ms stressed); consonants repeat one value.
VOICE_DURATIONS: f64[] = [
{durations}
]
'''


def model_jo(stats, castle, path, sources):
    D = stats['duration_ms']
    rows = []
    for p in PHONES:
        if p == 'pau':
            rows.append('    0.0, 0.0,')
            continue
        if p in bu.VOWELS:
            s1 = D.get(p + '1') or D.get(p + '0') or 90.0
            s0 = D.get(p + '0') or s1 * 0.7
        else:
            s0 = s1 = D.get(p) or 60.0
        rows.append(f'    {s0:.1f}, {s1:.1f},    # {p}')
    mid = lambda a, b: round((a + b) / 2, 3)
    text = MODEL_TEMPLATE.format(
        sources=sources, sps=stats['syllables_per_second'], f0med=stats['f0_hz']['median'],
        f0lo=stats['f0_hz']['p5'], f0hi=stats['f0_hz']['p95'], start=stats['phrase_start_st']['median'],
        start_iqr=round(stats['phrase_start_st']['p75'] - stats['phrase_start_st']['p25'], 2),
        decl=mid(stats['declination_st_per_s']['median'], castle['declination_st_per_s']['median']),
        decl_recap=stats['declination_st_per_s']['median'], decl_castle=castle['declination_st_per_s']['median'],
        accent=stats['accent_rise_st']['median'],
        accent_iqr=round(stats['accent_rise_st']['p75'] - stats['accent_rise_st']['p25'], 2),
        peak=stats['accent_peak_position'], final=castle['final_fall_st']['median'],
        final_recap=stats['final_fall_st']['median'], cont=stats['continuation_st']['median'],
        pc=mid(stats['pause_ms']['comma']['median'], castle['pause_ms']['comma']['median']) / 1000,
        pc_recap=stats['pause_ms']['comma']['median'] / 1000, pc_castle=castle['pause_ms']['comma']['median'] / 1000,
        ps=mid(stats['pause_ms']['stop']['median'], castle['pause_ms']['stop']['median']) / 1000,
        ps_recap=stats['pause_ms']['stop']['median'] / 1000, ps_castle=castle['pause_ms']['stop']['median'] / 1000,
        fl=1.15, fl_measured=stats['final_lengthening'], durations='\n'.join(rows))
    open(path, 'w').write(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', nargs=2, action='append', required=True)
    ap.add_argument('--prosody', required=True)
    ap.add_argument('--castle', required=True)
    ap.add_argument('--repo', required=True)
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
    os.makedirs(os.path.join(a.repo, 'data/voice'), exist_ok=True)
    raw, z, n = pack(units, lex, os.path.join(a.repo, 'data/voice/announcer.z'))
    model_jo(json.load(open(a.prosody)), json.load(open(a.castle)), os.path.join(a.repo, 'src/voice_model.jo'),
             'a modern recap narrator who imitates the period newsreel delivery, and a 1942 newsreel narrator')
    rep = dict(units=n, tokens=sum(len(v) for v in groups.values()), lexicon=len(lex), unknown=len(unknown),
               raw_bytes=raw, deflated_bytes=z, rules=len(lts.RULES))
    print(json.dumps(rep))
    if a.report:
        json.dump(dict(rep, unknown_words=unknown, counts={f'{k[0]}-{k[1]}': u['count'] for k, u in units.items()}),
                  open(a.report, 'w'), indent=1)


if __name__ == '__main__':
    main()
