"""Step 1: analyse a phone-aligned reference recording into cached WORLD-style tracks.

  python analyse_corpus.py RECORDING.wav PHONES.json OUT.npz [--speakers S.json] [--until SEC]

RECORDING is a separated mono voice track; PHONES the aligner's JSON (phones with start, end,
word, stress, confidence, segment). Only segments the speaker filter accepts (if given) and that
end before --until are analysed. The output stays in scratch: it is derived from the reference
and is never committed; only the aggregate tables built from it are.
"""
import argparse, json, sys
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from fractions import Fraction
import world_analysis as wa


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('wav'); ap.add_argument('phones'); ap.add_argument('out')
    ap.add_argument('--speakers'); ap.add_argument('--until', type=float, default=1e9)
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    x, sr = sf.read(a.wav, dtype='float64')
    if x.ndim > 1:
        x = x.mean(1)
    fr = Fraction(wa.RATE, sr).limit_denominator(1000)
    x = resample_poly(x, fr.numerator, fr.denominator)
    phones = json.load(open(a.phones))['phones']
    keep = None
    if a.speakers:
        keep = {s['segment'] for s in json.load(open(a.speakers))['segments'] if s['announcer_candidate']}
    segs = {}
    for p in phones:
        segs.setdefault(p['segment'], []).append(p)
    out = dict(f0=[], mcep=[], ap=[], seg_index=[], seg_start=[], power=[])
    done = 0
    for si in sorted(segs):
        ps = segs[si]
        if keep is not None and si not in keep:
            continue
        t0 = ps[0]['start']; t1 = ps[-1]['end']
        if t1 > a.until:
            continue
        lo = max(0, int((t0 - 0.05) * wa.RATE)); hi = min(len(x), int((t1 + 0.05) * wa.RATE))
        an = wa.analyse(x[lo:hi])
        n = len(an['times'])
        out['f0'].append(an['f0']); out['mcep'].append(an['mcep']); out['ap'].append(an['ap'])
        out['seg_index'].append(np.full(n, si)); out['seg_start'].append(np.full(n, lo / wa.RATE))
        hop = int(wa.FRAME * wa.RATE)
        seg = x[lo:hi]
        out['power'].append(np.array([np.mean(seg[max(0, j * hop - hop):j * hop + hop] ** 2) if j * hop < len(seg) else 0 for j in range(n)]))
        done += 1
        print('segment', si, f'{t0:.1f}-{t1:.1f}s frames', n, flush=True)
        if a.limit and done >= a.limit:
            break
    np.savez_compressed(a.out, **{k: np.concatenate(v) for k, v in out.items()})
    print('saved', a.out, sum(len(v) for v in out['f0']), 'frames')


if __name__ == '__main__':
    sys.exit(main())
