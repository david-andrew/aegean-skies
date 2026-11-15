"""Fit the announcer's prosody models to the analysed narrator.

  python prosody_fit.py PHONES.json WORDS.json ANALYSIS.npz SPEAKERS.json OUT.json

1. Durations, Klatt-style but fitted: log duration = phone intercept + stress, function-word,
   word-position, cluster, polysyllable and phrase-final terms + a per-class rate elasticity
   (how much each class shrinks when the narrator speaks faster), by least squares.
2-3. Intonation and microprosody: a least-squares superposition model (see fit_superposition):
   the arc over each phrase, accent shapes aligned to stressed content-word vowels (first,
   downstepped middle, nuclear), and F0 offsets inside voiced obstruents and after obstruents;
   fitted on held-in phrases, scored on held-out ones. (A Fujisaki command model and a hat-accent
   model were tried first and fitted worse on held-out phrases.)
4. Effort: the mel-cepstral change per semitone of F0 in vowel centres (with per-vowel
   intercepts): how the narrator's spectrum brightens as he raises his voice.
5. Norms for fricative durations by position (caps).
Only these aggregate numbers are written.
"""
import json, sys
import numpy as np
from build_units import segment_tracks, VOWELS, unit_label

FUNCTION = set('a an the and or but of to in on at by for from with as is are was were be been being '
               'it its this that these those he she they we you i his her their our your my me him them us '
               'has have had do does did will would shall should can could may might must not no so than '
               'then there here who whom which what when where while if into onto over under up down out '
               'off about all any some such each every both either neither nor yet'.split())
VOICELESS = set('P T K F TH S SH CH HH'.split())
VOICED_OBS = set('B D G V DH Z ZH JH'.split())
FRIC = set('F V TH DH S Z SH ZH HH'.split())


def st(f):
    return 12 * np.log2(np.maximum(f, 1e-9) / 100.0)


def load(phones_json, words_json, npz, speakers):
    phones = json.load(open(phones_json))['phones']
    words = json.load(open(words_json))
    keep = {s['segment'] for s in json.load(open(speakers))['segments'] if s['announcer_candidate']}
    tracks = segment_tracks(npz)
    segs = {}
    for p in phones:
        if p['segment'] in keep and p['segment'] in tracks:
            segs.setdefault(p['segment'], []).append(p)
    out = []
    for si, ps in sorted(segs.items()):
        wl = words[si]['words'] if si < len(words) else []
        # phrases split at pauses >= 0.12 s, with the punctuation that ends them
        cur = []
        index = 0
        seq = ps + [dict(p='[SIL]', start=ps[-1]['end'], end=ps[-1]['end'] + 1, wi=-1)]
        for k, p in enumerate(seq):
            punct_break = False
            if cur and p['p'] == '[SIL]' and 0 <= cur[-1]['wi'] < len(wl):
                punct_break = wl[cur[-1]['wi']]['word'].strip().endswith((',', ';', ':', '.', '!', '?'))
            if p['p'] == '[SIL]' and (p['end'] - p['start'] >= 0.12 or punct_break):
                if cur:
                    last = cur[-1]
                    w = wl[last['wi']]['word'].strip() if 0 <= last['wi'] < len(wl) else ''
                    punct = 'stop' if w.endswith(('.', '!', '?')) else 'comma' if w.endswith((',', ';', ':')) else 'none'
                    out.append(dict(seg=si, phones=cur, punct=punct, pause=p['end'] - p['start'] if p['end'] - p['start'] < 1 else None,
                                    words=wl, track=tracks[si], index=index))
                    index = 0 if punct == 'stop' else index + 1
                cur = []
            elif p['p'] != '[SIL]':
                cur.append(p)
    return out


def annotate(phr):
    """Per phone: label, word text, position flags, syllable counts."""
    ps = phr['phones']
    wl = phr['words']
    byword = {}
    for k, p in enumerate(ps):
        byword.setdefault(p['wi'], []).append(k)
    last_v = max([k for k, p in enumerate(ps) if p['p'] in VOWELS], default=-1)
    rows = []
    for k, p in enumerate(ps):
        w = byword[p['wi']]
        word = wl[p['wi']]['word'].strip(' ,.;:!?').lower() if 0 <= p['wi'] < len(wl) else ''
        nsyl = sum(1 for j in w if ps[j]['p'] in VOWELS)
        prev = ps[k - 1]['p'] if k > 0 else 'pau'
        nxt = ps[k + 1]['p'] if k + 1 < len(ps) else 'pau'
        rows.append(dict(
            p=p['p'], label=unit_label(p['p'], p.get('stress', 0)), dur=p['end'] - p['start'], start=p['start'], end=p['end'],
            vowel=p['p'] in VOWELS, stressed=p.get('stress', 0) >= 1, function=word in FUNCTION,
            word_final=k == w[-1], word_initial=k == w[0], nsyl=nsyl,
            cluster=(p['p'] not in VOWELS) and ((prev not in VOWELS and prev != 'pau' and k > w[0]) or (nxt not in VOWELS and nxt != 'pau' and k < w[-1])),
            phrase_final=k >= last_v >= 0, prev=prev, conf=p['confidence'], fallback=p.get('pronunciation_fallback', False)))
    return rows


# ------------------------------------------------------------------ durations
DCLASS = ['stressed_vowel', 'unstressed_vowel', 'onset', 'coda']


def dclass(r):
    if r['vowel']:
        return 0 if r['stressed'] and not r['function'] else 1
    return 3 if r['word_final'] or (not r['word_initial'] and not r['cluster']) else 2


def fit_durations(phrases, labels):
    X, y, rates, test = [], [], [], []
    feats = ['function', 'word_final', 'word_initial', 'cluster', 'syl2', 'syl3', 'final_vowel', 'final_cons', 'stressed_full']
    for i, phr in enumerate(phrases):
        rows = annotate(phr)
        nv = sum(1 for r in rows if r['vowel'])
        span = rows[-1]['end'] - rows[0]['start']
        if nv < 3 or span <= 0:
            continue
        rate = nv / span
        for r in rows:
            if r['conf'] < 0.3 or r['fallback'] or r['dur'] < 0.015:
                continue
            f = [1.0 if r['function'] else 0.0, 1.0 if r['word_final'] else 0.0, 1.0 if r['word_initial'] else 0.0,
                 1.0 if r['cluster'] else 0.0, 1.0 if r['nsyl'] == 2 else 0.0, 1.0 if r['nsyl'] >= 3 else 0.0,
                 1.0 if r['phrase_final'] and r['vowel'] else 0.0, 1.0 if r['phrase_final'] and not r['vowel'] else 0.0,
                 1.0 if r['vowel'] and r['stressed'] and r['label'] == r['p'] else 0.0]
            X.append((labels.index(r['label']), f, dclass(r)))
            y.append(np.log(r['dur']))
            rates.append(np.log(rate))
            test.append(i % 5 == 4)
    rates = np.array(rates)
    ref = float(np.median(rates))
    n = len(y)
    L = len(labels)
    F = len(feats)
    A = np.zeros((n, L + F + len(DCLASS)))
    for j, (li, f, c) in enumerate(X):
        A[j, li] = 1
        A[j, L:L + F] = f
        A[j, L + F + c] = rates[j] - ref
    y = np.array(y)
    test = np.array(test)
    coef, *_ = np.linalg.lstsq(A[~test], y[~test], rcond=None)
    pred = A @ coef
    rmse = lambda m: float(np.sqrt(np.mean((pred[m] - y[m]) ** 2)))
    base = np.array([np.median(y[~test][A[~test, li] > 0]) if np.any(A[~test, li] > 0) else 0 for li in range(L)])
    pb = A[:, :L] @ base
    return dict(
        labels=labels, intercept_ms={labels[i]: round(float(np.exp(coef[i]) * 1000), 1) for i in range(L) if np.any(A[:, i] > 0)},
        factors={feats[k]: round(float(np.exp(coef[L + k])), 3) for k in range(F)},
        elasticity={DCLASS[k]: round(float(coef[L + F + k]), 3) for k in range(len(DCLASS))},
        reference_rate=round(float(np.exp(ref)), 3),
        heldout_rmse_log=round(rmse(test), 3), heldout_rmse_log_phone_median_only=round(float(np.sqrt(np.mean((pb[test] - y[test]) ** 2))), 3),
        tokens=n)


# ------------------------------------------------------------------ intonation
def prepare_f0(phrases):
    """Voiced F0 (st) of each phrase with its accent spans and phone rows; every fifth held out."""
    data = []
    for i, phr in enumerate(phrases):
        start, f0, _, _ = phr['track']
        rows = annotate(phr)
        t0, t1 = rows[0]['start'], rows[-1]['end']
        j0 = max(0, int(round((t0 - start) / 0.005))); j1 = min(len(f0), int(round((t1 - start) / 0.005)))
        if j1 - j0 < 30:
            continue
        tt = np.arange(j0, j1) * 0.005 + start - t0
        f = f0[j0:j1]
        v = f > 0
        if v.sum() < 20:
            continue
        acc = [(r['start'] - t0, r['end'] - t0) for r in rows if r['vowel'] and r['stressed'] and not r['function']]
        cons = [(r['start'] - t0, r['end'] - t0, r['p'], r['prev']) for r in rows]
        data.append(dict(t=tt[v], s=st(f[v]), acc=acc, dur=t1 - t0, punct=phr['punct'], test=i % 5 == 4, rows=cons,
                         index=phr.get('index', 0)))
    return data


# ------------------------------------------------------------------ effort
def effort(phrases):
    from world_analysis import ORDER
    X, Y, lab = [], [], []
    for phr in phrases:
        start, f0, mcep, _ = phr['track']
        for p in phr['phones']:
            if p['p'] not in VOWELS or p['confidence'] < 0.5 or p['end'] - p['start'] < 0.05:
                continue
            j = int(round(((p['start'] + p['end']) / 2 - start) / 0.005))
            if 0 <= j < len(f0) and f0[j] > 0:
                X.append(st(f0[j])); Y.append(mcep[j]); lab.append(unit_label(p['p'], p['stress']))
    X = np.array(X); Y = np.array(Y)
    med = float(np.median(X))
    labs = sorted(set(lab))
    A = np.zeros((len(X), len(labs) + 1))
    for i, l in enumerate(lab):
        A[i, labs.index(l)] = 1
    A[:, -1] = X - med
    coef, *_ = np.linalg.lstsq(A, Y, rcond=None)
    v = coef[-1]
    # what +3 st does to the spectrum, in dB at a few frequencies
    from world_analysis import warp
    om = np.array([250, 500, 1000, 2000, 3000, 5000]) / 8000 * np.pi
    basis = np.cos(np.outer(warp(om), np.arange(ORDER + 1)))
    db = 10 / np.log(10) * (basis @ (3 * v))
    return dict(vector=[round(float(c), 5) for c in v], median_st=round(med, 2), frames=len(X),
                plus3st_db={f'{hz}': round(float(x), 2) for hz, x in zip([250, 500, 1000, 2000, 3000, 5000], db)})


def fricatives(phrases):
    out = {}
    for phr in phrases:
        for r in annotate(phr):
            if r['p'] in FRIC and r['conf'] >= 0.3:
                key = r['p'] + ('_final' if r['phrase_final'] else '_wordend' if r['word_final'] else '')
                out.setdefault(key, []).append(r['dur'])
    return {k: dict(median_ms=round(1000 * float(np.median(v)), 1), p90_ms=round(1000 * float(np.percentile(v, 90)), 1), n=len(v))
            for k, v in sorted(out.items()) if len(v) >= 5}


def pauses(phrases):
    out = {'comma': [], 'stop': [], 'none': []}
    # A sentence-final pause usually falls between transcript segments: measure the gap to the
    # next segment (the aligner's own silences inside a segment are mostly short catches).
    for phr, nxt in zip(phrases, phrases[1:]):
        if nxt['seg'] != phr['seg'] and phr['punct'] == 'stop':
            gap = nxt['phones'][0]['start'] - phr['phones'][-1]['end']
            if 0.05 <= gap <= 1.5:
                out['stop'].append(gap)
    for phr in phrases:
        if phr['punct'] == 'stop':
            continue
        # aligner silences under 50 ms inside running speech are not pauses
        if phr['pause'] is not None and phr['pause'] >= 0.05:
            out[phr['punct']].append(phr['pause'])
    return {k: dict(median_ms=round(1000 * float(np.median(v)), 0), p25_ms=round(1000 * float(np.percentile(v, 25)), 0),
                    p75_ms=round(1000 * float(np.percentile(v, 75)), 0), n=len(v)) for k, v in out.items() if v}


def main():
    phones_json, words_json, npz, speakers, out = sys.argv[1:6]
    from pack import PHONES
    phrases = load(phones_json, words_json, npz, speakers)
    res = dict(phrases=len(phrases))
    res['durations'] = fit_durations(phrases, PHONES)
    data = prepare_f0(phrases)
    res['superposition'] = fit_superposition(data)
    res['effort'] = effort(phrases)
    res['fricatives'] = fricatives(phrases)
    res['pauses'] = pauses(phrases)
    allf = np.concatenate([d['s'] for d in data])
    res['f0_st'] = dict(median=round(float(np.median(allf)), 2), p5=round(float(np.percentile(allf, 5)), 2), p95=round(float(np.percentile(allf, 95)), 2))
    json.dump(res, open(out, 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k not in ('fricatives',)}, indent=1)[:6000])



# ------------------------------------------------------------------ superposition (least squares)
# F0 (st) of a phrase = its own level + an arc over the phrase's normalised time (10 points,
# separate for phrases ending in a full stop and the rest) + an accent shape aligned to the onset
# of each stressed content-word vowel (first / middle / nuclear accent of the phrase, lag points
# every 50 ms from -200 to +400 ms) + microprosody (inside voiced obstruents; first 40 ms of a
# vowel after a voiceless or voiced obstruent). Hat-function bases, so the runtime contour is
# piecewise linear in the fitted weights. Fitted by least squares on held-in phrases.
ARC_POINTS = 10
LAGS = np.arange(-0.2, 0.4001, 0.05)
ACC_TYPES = ['first', 'middle', 'nuclear']
MICRO = ['inside_voiced_obstruent', 'after_voiceless', 'after_voiced_obstruent']


def hat(x, n):
    """Weights of x in [0, n-1] on n hat functions."""
    x = np.clip(x, 0, n - 1)
    i = np.minimum(np.floor(x).astype(int), n - 2)
    f = x - i
    W = np.zeros((len(x), n))
    W[np.arange(len(x)), i] = 1 - f
    W[np.arange(len(x)), i + 1] = f
    return W


def clean(s):
    from scipy.signal import medfilt
    m = medfilt(s, 7)
    keep = np.abs(s - m) < 3.0
    return keep


def design(d):
    t = d['t']
    cols = []
    arc = hat(t / max(d['dur'], 1e-3) * (ARC_POINTS - 1), ARC_POINTS)
    stop = 1.0 if d['punct'] == 'stop' else 0.0
    cols.append(arc * stop)
    cols.append(arc * (1 - stop))
    K = len(d['acc'])
    for typ in ACC_TYPES:
        A = np.zeros((len(t), len(LAGS)))
        for k, (a, b) in enumerate(d['acc']):
            kind = 'nuclear' if k == K - 1 else 'first' if k == 0 else 'middle'
            if kind != typ:
                continue
            lag = t - a
            inside = (lag >= LAGS[0]) & (lag <= LAGS[-1])
            if np.any(inside):
                W = hat((lag[inside] - LAGS[0]) / 0.05, len(LAGS))
                A[inside] += W
        cols.append(A)
    M = np.zeros((len(t), len(MICRO)))
    for a, b, ph, prev in d['rows']:
        if ph in VOICED_OBS:
            M[(t >= a) & (t < b), 0] = 1
        elif ph in VOWELS:
            m = (t >= a) & (t < a + 0.04)
            if prev in VOICELESS:
                M[m, 1] = 1
            elif prev in VOICED_OBS:
                M[m, 2] = 1
    cols.append(M)
    return np.hstack(cols)


def fit_superposition(data):
    Xs, ys, test = [], [], []
    for d in data:
        keep = clean(d['s'])
        X = design(d)[keep]
        y = d['s'][keep]
        if len(y) < 10:
            continue
        Xs.append(X - X.mean(0)); ys.append(y - y.mean()); test.append(d['test'])
    tr = [i for i, t in enumerate(test) if not t]
    te = [i for i, t in enumerate(test) if t]
    X = np.vstack([Xs[i] for i in tr]); y = np.concatenate([ys[i] for i in tr])
    lam = 1.0
    w = np.linalg.solve(X.T @ X + lam * np.eye(X.shape[1]), X.T @ y)
    err = np.concatenate([ys[i] - Xs[i] @ w for i in te])
    flat = np.concatenate([ys[i] for i in te])
    cs = [np.corrcoef(Xs[i] @ w, ys[i])[0, 1] for i in te if np.std(Xs[i] @ w) > 1e-6]
    # The fit is on mean-removed contours, so the shapes carry an arbitrary constant; the
    # synthesizer adds them, uncentred, to the phrase level. Take out the median level the shapes
    # add to a phrase (stop and other phrases apart; the arc's hats sum to one, so a constant on
    # the arc shifts the whole phrase), so a phrase's median pitch is the fitted level, as the
    # level model assumes. Without this a speaker's fit came out 3 st high.
    offset = {}
    for stop in (True, False):
        o = [float(np.median(design(d)[clean(d['s'])] @ w)) for d in data if (d['punct'] == 'stop') == stop and clean(d['s']).sum() >= 10]
        offset['stop' if stop else 'other'] = float(np.median(o)) if o else 0.0
    w = w.copy()
    w[:ARC_POINTS] -= offset['stop']
    w[ARC_POINTS:2 * ARC_POINTS] -= offset['other']
    k = 0
    out = {}
    for name, n in [('arc_stop', ARC_POINTS), ('arc_other', ARC_POINTS)] + [(f'accent_{t}', len(LAGS)) for t in ACC_TYPES] + [('micro', len(MICRO))]:
        out[name] = [round(float(v), 3) for v in w[k:k + n]]
        k += n
    # level of each phrase relative to the speaker median, by position in its sentence
    levels = {}
    for d in data:
        levels.setdefault(min(d.get('index', 0), 2), []).append(float(np.median(d['s'])))
    med = float(np.median(np.concatenate([d['s'] for d in data])))
    return dict(weights=out, lags=[round(float(l), 2) for l in LAGS], micro_names=MICRO,
                level_offset_removed_st={k: round(v, 2) for k, v in offset.items()},
                level_by_index={str(k): round(float(np.median(v)) - med, 2) for k, v in sorted(levels.items())},
                level_spread=round(float(np.percentile([np.median(d['s']) for d in data], 75) - np.percentile([np.median(d['s']) for d in data], 25)), 2),
                heldout_rmse_st=round(float(np.sqrt(np.mean(err ** 2))), 3),
                heldout_rmse_st_flat=round(float(np.sqrt(np.mean(flat ** 2))), 3),
                heldout_median_corr=round(float(np.median(cs)), 3))


if __name__ == '__main__':
    main()
