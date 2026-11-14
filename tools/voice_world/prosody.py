"""Step 3: announcer prosody statistics from an aligned, analysed narrator.

Durations (per phone, by vowel stress, phrase-final lengthening), pauses by punctuation,
speaking rate, and F0 in semitones re 100 Hz: level, range, per-phrase declination, accent
rise on stressed content-word vowels, unstressed level, sentence-final fall, continuation.
Only these aggregate numbers are kept.
"""
import json, sys
import numpy as np
from build_units import segment_tracks, VOWELS

FUNCTION = set('a an the and or but of to in on at by for from with as is are was were be been being '
               'it its this that these those he she they we you i his her their our your my me him them us '
               'has have had do does did will would shall should can could may might must not no so than '
               'then there here who whom which what when where while if into onto over under up down out '
               'off about after before all any some such each every both either neither nor yet'.split())


def st(f):
    return 12 * np.log2(f / 100.0)


def stats(phones_json, words_json, npz, speakers=None, until=1e9):
    phones = json.load(open(phones_json))['phones']
    words = json.load(open(words_json))
    tracks = segment_tracks(npz)
    keep = set(tracks)
    segs = {}
    for p in phones:
        if p['segment'] in keep and p['end'] <= until:
            segs.setdefault(p['segment'], []).append(p)
    dur = {}
    final_ratio = []
    pauses = {'comma': [], 'stop': [], 'none': []}
    rate_syll = rate_time = 0.0
    slopes, starts, ends, accents, unstressed, finals, cont, levels = [], [], [], [], [], [], [], []
    peak_pos = []
    allf = []
    for si, ps in segs.items():
        start, f0, _, _ = tracks[si]
        wl = words[si]['words'] if si < len(words) else []
        def frames(a, b):
            j0 = int(round((a - start) / 0.005)); j1 = int(round((b - start) / 0.005))
            j0 = max(0, j0); j1 = min(len(f0), max(j0 + 1, j1))
            return np.arange(j0, j1)
        # phrases: split at pauses >= 120 ms
        phrase = []
        phrases = []
        for p in ps:
            if p['p'] == '[SIL]' and p['end'] - p['start'] >= 0.12:
                if phrase:
                    phrases.append((phrase, p))
                phrase = []
            elif p['p'] != '[SIL]':
                phrase.append(p)
        if phrase:
            phrases.append((phrase, None))
        for i, p in enumerate(ps):
            d = p['end'] - p['start']
            if p['p'] == '[SIL]':
                if 0 < i < len(ps) - 1 and ps[i - 1]['wi'] >= 0 and ps[i - 1]['wi'] < len(wl):
                    w = wl[ps[i - 1]['wi']]['word'].strip()
                    kind = 'comma' if w.endswith((',', ';', ':')) else 'stop' if w.endswith(('.', '!', '?')) else 'none'
                    pauses[kind].append(d)
                continue
            if p['confidence'] < 0.2:
                continue
            key = p['p'] + (str(min(p['stress'], 1)) if p['p'] in VOWELS else '')
            dur.setdefault(key, []).append(d)
        for ph, after in phrases:
            t0, t1 = ph[0]['start'], ph[-1]['end']
            rate_time += t1 - t0
            rate_syll += sum(1 for p in ph if p['p'] in VOWELS)
            # phrase-final lengthening: last vowel and following consonants vs median of the phone
            last_v = max([k for k, p in enumerate(ph) if p['p'] in VOWELS], default=-1)
            if last_v >= 0:
                for p in ph[last_v:]:
                    key = p['p'] + (str(min(p['stress'], 1)) if p['p'] in VOWELS else '')
                    final_ratio.append((key, p['end'] - p['start']))
            js = frames(t0, t1)
            v = js[f0[js] > 0]
            if len(v) < 20:
                continue
            tt = v * 0.005 + start - t0
            s = st(f0[v])
            allf.extend(f0[v])
            A = np.vstack([np.ones_like(tt), tt]).T
            # robust line: fit, drop the top 25% residuals (accents), refit
            c = np.linalg.lstsq(A, s, rcond=None)[0]
            r = s - A @ c
            m = r < np.percentile(r, 75)
            c = np.linalg.lstsq(A[m], s[m], rcond=None)[0]
            slopes.append(c[1]); starts.append(c[0]); ends.append(c[0] + c[1] * (t1 - t0))
            levels.append((t1 - t0, c[0]))
            for p in ph:
                if p['p'] not in VOWELS:
                    continue
                jv = frames(p['start'], p['end'])
                jv = jv[f0[jv] > 0]
                if len(jv) < 2:
                    continue
                res = st(f0[jv]) - (c[0] + c[1] * (jv * 0.005 + start - t0))
                wd = wl[p['wi']]['word'].strip(' ,.!?;:').lower() if 0 <= p['wi'] < len(wl) else ''
                if p['stress'] == 1 and wd not in FUNCTION:
                    accents.append(res.max())
                    peak_pos.append(np.argmax(res) / max(1, len(res) - 1))
                elif p['stress'] == 0:
                    unstressed.append(res.mean())
            # final 250 ms against the line
            jf = frames(t1 - 0.25, t1)
            jf = jf[f0[jf] > 0]
            if len(jf) > 5:
                res = st(f0[jf]) - (c[0] + c[1] * (jf * 0.005 + start - t0))
                last_word = wl[ph[-1]['wi']]['word'].strip() if 0 <= ph[-1]['wi'] < len(wl) else ''
                (finals if last_word.endswith(('.', '!', '?')) else cont).append(res[-5:].mean())
    med = {k: float(np.median(v)) for k, v in dur.items() if len(v) >= 3}
    fr = [d / med[k] for k, d in final_ratio if k in med]
    q = lambda v, p: float(np.percentile(v, p)) if len(v) else None
    allf = np.array(allf)
    return dict(
        duration_ms={k: round(v * 1000, 1) for k, v in sorted(med.items())},
        final_lengthening=round(float(np.median(fr)), 3),
        syllables_per_second=round(rate_syll / rate_time, 2),
        pause_ms={k: dict(n=len(v), median=round(1000 * q(v, 50), 0) if v else None,
                          p25=round(1000 * q(v, 25), 0) if v else None, p75=round(1000 * q(v, 75), 0) if v else None)
                  for k, v in pauses.items()},
        f0_hz=dict(median=round(float(np.median(allf)), 1), p5=round(q(allf, 5), 1), p95=round(q(allf, 95), 1)),
        phrase_start_st=dict(median=round(q(starts, 50), 2), p25=round(q(starts, 25), 2), p75=round(q(starts, 75), 2)),
        phrase_end_st=dict(median=round(q(ends, 50), 2)),
        declination_st_per_s=dict(median=round(q(slopes, 50), 2), p25=round(q(slopes, 25), 2), p75=round(q(slopes, 75), 2)),
        accent_rise_st=dict(median=round(q(accents, 50), 2), p25=round(q(accents, 25), 2), p75=round(q(accents, 75), 2), n=len(accents)),
        accent_peak_position=round(q(peak_pos, 50), 2),
        unstressed_st=round(q(unstressed, 50), 2),
        final_fall_st=dict(median=round(q(finals, 50), 2), n=len(finals)),
        continuation_st=dict(median=round(q(cont, 50), 2), n=len(cont)),
        phrases=len(slopes),
    )


if __name__ == '__main__':
    print(json.dumps(stats(*sys.argv[1:4]), indent=1))
