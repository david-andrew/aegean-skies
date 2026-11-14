"""Step 2: diphone spectral trajectories from the analysed narrator.

A diphone runs from the centre of phone A to the centre of phone B, so it holds the whole
A->B transition (formant movement, closure, burst, frication onset). Each half is resampled to
HALF points; tokens of a type are averaged around their medoid (outliers - misaligned or noisy
tokens - fall outside the nearest group and are dropped).

Gain: c0 is made relative to the segment's median vowel level, so a /k/ closure stays as much
quieter than its vowel as the speaker made it (no per-unit normalisation).
"""
import json
import numpy as np
import world_analysis as wa

HALF = 6
SIL = 'pau'
SIL_SPAN = 0.045          # seconds of a pause used next to the boundary
VOWELS = {'AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY', 'IH', 'IY', 'OW', 'OY', 'UH', 'UW'}
# Unstressed vowels the narrator says differently enough to need their own units: schwa (AX) is
# not the vowel of "strut" (AH), and so on. Other vowels are rarely unstressed and share units.
REDUCED = {'AH': 'AX', 'IH': 'IX', 'ER': 'AXR', 'IY': 'IYX'}


def unit_label(p, stress=0):
    return REDUCED[p] if p in REDUCED and stress == 0 else p


def label(p):
    return SIL if p['p'] == '[SIL]' else unit_label(p['p'], p.get('stress', 0))


def segment_tracks(npz):
    """Per segment: (start time of frame 0, f0, mcep, ap)."""
    d = np.load(npz)
    out = {}
    for si in np.unique(d['seg_index']):
        m = d['seg_index'] == si
        out[int(si)] = (float(d['seg_start'][m][0]), d['f0'][m], d['mcep'][m], d['ap'][m])
    return out


def sample(track, t0, times):
    """Interpolated frame features at absolute times: [mcep..., ap..., voiced]."""
    start, f0, mcep, ap = track
    u = (np.asarray(times) - start) / wa.FRAME
    idx = np.arange(len(f0))
    feats = np.concatenate([mcep, ap, (f0 > 0)[:, None].astype(float)], 1)
    return np.array([np.interp(u, idx, feats[:, c]) for c in range(feats.shape[1])]).T


def tokens(phones, tracks, min_conf=0.2, min_dur=0.019):
    """Yield (A, B, features[2*HALF, F], meta) for each usable adjacent pair."""
    segs = {}
    for p in phones:
        if p['segment'] in tracks:
            segs.setdefault(p['segment'], []).append(p)
    for si, ps in segs.items():
        tr = tracks[si]
        # relative gain reference: median c0 at vowel centres
        vc = [sample(tr, 0, [(p['start'] + p['end']) / 2])[0, 0] for p in ps if p['p'] in VOWELS and p.get('stress', 0) >= 1]
        if len(vc) < 3:
            continue
        ref = float(np.median(vc))
        seq = list(ps)
        if label(seq[0]) != SIL:
            seq.insert(0, dict(p='[SIL]', start=seq[0]['start'] - 0.1, end=seq[0]['start'], confidence=1, stress=0, word=''))
        if label(seq[-1]) != SIL:
            seq.append(dict(p='[SIL]', start=seq[-1]['end'], end=seq[-1]['end'] + 0.1, confidence=1, stress=0, word=''))
        for a, b in zip(seq, seq[1:]):
            la, lb = label(a), label(b)
            if la == SIL and lb == SIL:
                continue
            bad = False
            for p, l in ((a, la), (b, lb)):
                if l != SIL and (p['confidence'] < min_conf or p['end'] - p['start'] < min_dur or p.get('pronunciation_fallback')):
                    bad = True
            if bad:
                continue
            bound = a['end']
            ca = max((a['start'] + a['end']) / 2, bound - SIL_SPAN) if la == SIL else (a['start'] + a['end']) / 2
            cb = min((b['start'] + b['end']) / 2, bound + SIL_SPAN) if lb == SIL else (b['start'] + b['end']) / 2
            k = (np.arange(HALF) + 0.5) / HALF
            times = np.concatenate([ca + (bound - ca) * k, bound + (cb - bound) * k])
            f = sample(tr, 0, times)
            f[:, 0] -= ref
            yield la, lb, f, dict(segment=si, left=bound - ca, right=cb - bound,
                                  stress_a=a.get('stress', 0), stress_b=b.get('stress', 0))


def average(feats, keep=0.6, cap=12):
    """Mean of the tokens nearest the medoid (in mel-cepstral distance, c0 half weight)."""
    X = np.array(feats)
    if len(X) == 1:
        return X[0], 1
    w = np.ones(X.shape[2]); w[0] = 0.5; w[wa.ORDER + 1:] = 0
    D = np.sqrt((((X[:, None] - X[None]) * w) ** 2).sum((2, 3)))
    med = np.argmin(D.sum(1))
    k = max(1, min(cap, int(round(len(X) * keep))))
    near = np.argsort(D[med])[:k]
    return X[near].mean(0), len(X)


def build(phones_json, npz, out_json=None):
    phones = json.load(open(phones_json))['phones']
    tracks = segment_tracks(npz)
    groups = {}
    meta = {}
    for a, b, f, m in tokens(phones, tracks):
        groups.setdefault((a, b), []).append(f)
        meta.setdefault((a, b), []).append(m)
    units = {}
    for key, fs in groups.items():
        mean, n = average(fs)
        units[key] = dict(frames=mean, count=n,
                          left=float(np.median([m['left'] for m in meta[key]])),
                          right=float(np.median([m['right'] for m in meta[key]])))
    return units
