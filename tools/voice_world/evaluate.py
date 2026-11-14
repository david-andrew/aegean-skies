"""Score the announcer against held-out recordings of a real speaker, and publish a Compare round.

  python evaluate.py --root VOICE_USER_DIR --round ID --repo REPO [--label TEXT] [--note TEXT]
                     [--lines held01,held02,...] [--export-alignment OUT.json]

VOICE_USER_DIR holds script.json, manifest.json (chosen takes) and takes/ (the studio's layout).
The announcer data comes from AEGEAN_VOICE_DATA as for the game. For every held-out line with a
chosen take the game's own code synthesizes the line (dry, and through the radio at strong
signal) in the line's genre delivery. The recording is aligned to the synthesis by dynamic time
warping on mean-normalised mel-cepstra (our own aligner: the synthesis knows its phone
boundaries, the warping path carries them onto the recording), and scored:

  mcd_db           mel-cepstral distortion on aligned speech frames (standard dB scaling)
  f0_rmse_st       F0 RMSE in semitones where both are voiced; f0_rmse_st_shape after removing
                   the mean offset (register difference); f0_corr Pearson correlation
  energy_corr      correlation of the log-energy contours
  dur_err          mean |log ratio| of phone durations (synthesis vs the aligned recording)
  rate_rec, rate_syn   syllables per second of speech; voicing_err  share of frames whose
                   voicing disagrees

Results go to VOICE_USER_DIR/compare/<round>/ (loudness-matched WAVs, metrics.json) and
compare/index.json, which the studio's Compare tab reads. Nothing here enters the repository.
"""
import argparse, json, os, re, subprocess, sys
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import world_analysis as wa

VOWELS = {'AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY', 'IH', 'IY', 'OW', 'OY', 'UH', 'UW', 'AX', 'IX', 'AXR', 'IYX'}
# genre -> (station, programme) for the game's delivery; neutral reads use the narrator's pace
GENRE_STYLE = {'war': ('1', 'news'), 'news': ('0', 'other'), 'weather': ('4', 'other'), 'race': ('3', 'news'),
               'advert': ('3', 'other'), 'ident': ('0', 'other')}


def load16(path):
    x, sr = sf.read(path, dtype='float64')
    if x.ndim > 1:
        x = x.mean(1)
    if sr != wa.RATE:
        from fractions import Fraction
        f = Fraction(wa.RATE, sr).limit_denominator(1000)
        x = resample_poly(x, f.numerator, f.denominator)
    return x


def trim(x, floor_db=None, pad=0.08):
    """Cut leading/trailing silence: 10 ms frames more than 15 dB above the quietest 10%."""
    hop = int(0.01 * wa.RATE)
    e = np.array([np.mean(x[i:i + hop] ** 2) + 1e-12 for i in range(0, max(1, len(x) - hop), hop)])
    db = 10 * np.log10(e)
    floor = floor_db if floor_db is not None else np.percentile(db, 10)
    on = np.nonzero(db > floor + 15)[0]
    if len(on) == 0:
        return x
    a = max(0, on[0] * hop - int(pad * wa.RATE))
    b = min(len(x), (on[-1] + 1) * hop + int(pad * wa.RATE))
    return x[a:b]


def dtw(A, B):
    """Path between frame sequences: Euclidean local cost, symmetric steps (a diagonal step
    counts the local cost twice, a horizontal or vertical one once), so tempo differences warp
    freely without favouring either sequence."""
    n, m = len(A), len(B)
    C = np.sqrt(((A[:, None, :] - B[None, :, :]) ** 2).sum(2))
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0
    for i in range(1, n + 1):
        Ci = C[i - 1]
        Dp = D[i - 1]
        row = D[i]
        for j in range(1, m + 1):
            c = Ci[j - 1]
            row[j] = min(Dp[j - 1] + 2 * c, Dp[j] + c, row[j - 1] + c)
    i, j = n, m
    path = []
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        c = C[i - 1, j - 1]
        k = np.argmin([D[i - 1, j - 1] + 2 * c, D[i - 1, j] + c, D[i, j - 1] + c])
        if k == 0:
            i, j = i - 1, j - 1
        elif k == 1:
            i -= 1
        else:
            j -= 1
    return path[::-1]


def features(x):
    an = wa.analyse(x)
    mc = an['mcep']
    hop = int(wa.FRAME * wa.RATE)
    energy = np.array([10 * np.log10(np.mean(x[max(0, k * hop - hop):k * hop + hop] ** 2) + 1e-10) for k in range(len(an['f0']))])
    return an['f0'], mc, energy


def map_time(path, t_syn, n_syn):
    """Recording time (s) of a synthesis time, through the warping path (median of matches)."""
    j = min(n_syn - 1, max(0, int(round(t_syn / wa.FRAME))))
    rec = [i for i, jj in path if jj == j]
    return (np.median(rec) if rec else 0) * wa.FRAME


def score(rec, syn, phones):
    f0r, mcr, er = features(rec)
    f0s, mcs, es = features(syn)
    A = mcr[:, 1:] - mcr[:, 1:].mean(0)
    B = mcs[:, 1:] - mcs[:, 1:].mean(0)
    path = dtw(A, B)
    ri = np.array([p[0] for p in path]); si = np.array([p[1] for p in path])
    speech = (er[ri] > np.percentile(er, 30)) & (es[si] > np.percentile(es, 30))
    # our coefficients describe log power = c0 + sum a_m cos(m w~); a_m / 4 is the usual
    # log-amplitude cepstrum, so MCD = 10/ln10 * sqrt(2 * sum (a_m/4 - b_m/4)^2)
    d = (mcr[ri, 1:] - mcs[si, 1:]) / 4
    mcd = float(np.mean(10 / np.log(10) * np.sqrt(2 * np.sum(d[speech] ** 2, 1)))) if speech.any() else float('nan')
    both = (f0r[ri] > 0) & (f0s[si] > 0)
    out = dict(mcd_db=round(mcd, 2))
    if both.sum() > 10:
        a = 12 * np.log2(f0r[ri][both] / 100); b = 12 * np.log2(f0s[si][both] / 100)
        out['f0_rmse_st'] = round(float(np.sqrt(np.mean((a - b) ** 2))), 2)
        out['f0_rmse_st_shape'] = round(float(np.sqrt(np.mean(((a - a.mean()) - (b - b.mean())) ** 2))), 2)
        out['f0_corr'] = round(float(np.corrcoef(a, b)[0, 1]), 3)
        out['f0_median_rec_hz'] = round(float(np.median(f0r[ri][both])), 1)
        out['f0_median_syn_hz'] = round(float(np.median(f0s[si][both])), 1)
    out['energy_corr'] = round(float(np.corrcoef(er[ri][speech], es[si][speech])[0, 1]), 3) if speech.sum() > 10 else float('nan')
    vr = f0r[ri] > 0; vs = f0s[si] > 0
    out['voicing_err'] = round(float(np.mean(vr[speech] != vs[speech])), 3) if speech.any() else float('nan')
    # phone boundaries carried onto the recording
    n_syn = len(f0s)
    bounds = [map_time(path, p['start'], n_syn) for p in phones] + [map_time(path, phones[-1]['start'] + phones[-1]['dur'], n_syn)]
    errs = []
    rec_phones = []
    for k, p in enumerate(phones):
        drec = bounds[k + 1] - bounds[k]
        rec_phones.append(dict(p=p['p'], start=bounds[k], end=bounds[k + 1], stress=p['stress']))
        if p['p'] != 'pau' and p['dur'] > 0.015 and drec > 0.005:
            errs.append(abs(np.log(p['dur'] / drec)))
    out['dur_err'] = round(float(np.mean(errs)), 3) if errs else float('nan')
    sp = [p for p in phones if p['p'] != 'pau']
    nv = sum(1 for p in sp if p['p'] in VOWELS)
    t_syn = sum(p['dur'] for p in sp)
    t_rec = sum(r['end'] - r['start'] for r in rec_phones if r['p'] != 'pau')
    out['rate_syn'] = round(nv / max(t_syn, 1e-3), 2)
    out['rate_rec'] = round(nv / max(t_rec, 1e-3), 2)
    return out, rec_phones


def level(x, target_db=-20.0):
    rms = np.sqrt(np.mean(x ** 2)) + 1e-9
    y = x * 10 ** ((target_db - 20 * np.log10(rms)) / 20)
    peak = np.max(np.abs(y))
    return y / peak * 0.95 if peak > 0.95 else y


def synthesize(repo, lines, outdir):
    """Render each line with the game's code in its genre's delivery; returns {id: (dry, radio, phones)}."""
    os.makedirs(outdir, exist_ok=True)
    groups = {}
    for l in lines:
        groups.setdefault(l['genre'] if l['genre'] in GENRE_STYLE else 'neutral', []).append(l)
    res = {}
    for g, ls in groups.items():
        txt = os.path.join(outdir, f'lines-{g}.txt')
        with open(txt, 'w') as f:
            for l in ls:
                f.write(f"{l['id']}|{l['text']}\n")
        env = dict(os.environ, VOICE_TEXTS=txt, VOICE_DIR=outdir, VOICE_DUMP='1', SLOPPY_NO_AUDIO='1', SLOPPY_THREADS='1')
        env.pop('DISPLAY', None); env.pop('WAYLAND_DISPLAY', None)
        if g in GENRE_STYLE:
            env['VOICE_STATION'], env['VOICE_PROGRAMME'] = GENRE_STYLE[g]
        else:
            env['VOICE_SPEED'] = '1.0'
        r = subprocess.run(['sloppy', '--release', 'tools/voicelab.jo'], cwd=repo, env=env, capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit('voicelab failed: ' + r.stderr[-2000:])
        for l in ls:
            ph = []
            for row in open(os.path.join(outdir, f"{l['id']}-phones.txt")):
                c = row.split()
                ph.append(dict(p=c[0], stress=int(c[1]), start=float(c[2]), dur=float(c[3]), content=c[4] == 'true'))
            res[l['id']] = (os.path.join(outdir, f"{l['id']}-dry.wav"), os.path.join(outdir, f"{l['id']}-strong.wav"), ph)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--round', required=True)
    ap.add_argument('--repo', required=True)
    ap.add_argument('--label', default='')
    ap.add_argument('--note', default='')
    ap.add_argument('--lines', default='')
    ap.add_argument('--export-alignment', default='', help='align every chosen non-held-out take and write phones JSON for fitting')
    a = ap.parse_args()
    if not re.match(r'^[a-z0-9_-]{1,40}$', a.round):
        raise SystemExit('round id: lower-case letters, digits, - and _')
    script = json.load(open(os.path.join(a.root, 'script.json')))
    manifest = json.load(open(os.path.join(a.root, 'manifest.json')))
    want = set(a.lines.split(',')) if a.lines else None
    chosen = lambda l: (manifest['lines'].get(l['id']) or {}).get('chosen')
    if a.export_alignment:
        lines = [l for l in script['lines'] if not l['heldout'] and chosen(l)]
    else:
        lines = [l for l in script['lines'] if l['heldout'] and chosen(l) and (want is None or l['id'] in want)]
    if not lines:
        raise SystemExit('no recorded lines to work on')
    work = os.path.join(a.root, 'compare', a.round)
    syn = synthesize(a.repo, lines, os.path.join(work, 'synth'))
    entries, export = [], []
    for l in lines:
        take = next(t for t in manifest['lines'][l['id']]['takes'] if t['n'] == chosen(l))
        rec = trim(load16(os.path.join(a.root, take['file'])))
        dry, radio, ph = syn[l['id']]
        s = trim(load16(dry))
        m, rec_phones = score(rec, s, ph)
        if a.export_alignment:
            export.append(dict(id=l['id'], text=l['text'], genre=l['genre'], take=take['file'], phones=rec_phones))
            print(l['id'], json.dumps(m), flush=True)
            continue
        d = os.path.join(work, l['id'])
        os.makedirs(d, exist_ok=True)
        sf.write(os.path.join(d, 'rec.wav'), level(rec).astype(np.float32), wa.RATE, subtype='PCM_16')
        sf.write(os.path.join(d, 'synth.wav'), level(s).astype(np.float32), wa.RATE, subtype='PCM_16')
        sf.write(os.path.join(d, 'radio.wav'), level(trim(load16(radio))).astype(np.float32), wa.RATE, subtype='PCM_16')
        rel = f'compare/{a.round}/{l["id"]}'
        entries.append(dict(line=l['id'], text=l['text'], genre=l['genre'], rec=rel + '/rec.wav', synth=rel + '/synth.wav',
                            radio=rel + '/radio.wav', metrics=m))
        print(l['id'], json.dumps(m), flush=True)
    if a.export_alignment:
        json.dump(dict(round=a.round, lines=export), open(a.export_alignment, 'w'), indent=1)
        return
    keys = ['mcd_db', 'f0_rmse_st', 'f0_rmse_st_shape', 'f0_corr', 'energy_corr', 'dur_err', 'voicing_err', 'rate_rec', 'rate_syn']
    summary = {k: round(float(np.nanmean([e['metrics'].get(k, np.nan) for e in entries])), 3) for k in keys}
    json.dump(dict(round=a.round, summary=summary, entries=entries), open(os.path.join(work, 'metrics.json'), 'w'), indent=1)
    idx_path = os.path.join(a.root, 'compare', 'index.json')
    idx = json.load(open(idx_path)) if os.path.exists(idx_path) else dict(rounds=[])
    idx['rounds'] = [r for r in idx['rounds'] if r['id'] != a.round]
    idx['rounds'].append(dict(id=a.round, label=a.label or a.round, note=a.note, summary=summary, entries=entries))
    tmp = idx_path + '.tmp'
    json.dump(idx, open(tmp, 'w'), indent=1)
    os.replace(tmp, idx_path)
    print('SUMMARY', json.dumps(summary))


if __name__ == '__main__':
    main()
