"""One tuning round on whatever the user has recorded so far (run by the voice studio's "Tune"
button, or by hand):

  python tune_round.py --root VOICE_USER_DIR --repo REPO --prior-data NARRATOR.z --prior-fit FIT.json
                       [--round rN] [--fractions 0.25,0.5,1] [--listen 2]

1. Pool: every accepted take of a training line; the held-out lines with accepted takes are only
   ever scored, never fitted.
2. Baseline: if no round exists yet, round r0 scores the prior (narrator) voice on the held-out set.
3. Alignment: each new take is labelled phone by phone (phone_align.py; --dtw for the old
   alignment to a synthesis) and analysed WORLD-style. Both are cached per take, so a re-tune only
   aligns what is new.
4. Nested random subsets of the pool (a fixed shuffle, so 25% is inside 50% inside 100%): for each,
   fit diphone units, durations and intonation to the user's takes and pack a voice file. Where
   the subset is still too small for a part of the model, that part falls back to the prior's
   (named in the round's note).
5. Each voice synthesizes the held-out lines and is scored; the full pool's voice provides the
   Compare entries (recording, synthesis, radio), the smaller ones a learning curve and a couple
   of listenable lines.
Progress goes to VOICE_USER_DIR/tune/progress.json; a failure records the stage and the reason.
`--round rN` retries a failed round: every scoring of the same voice file on the same held-out
takes is reused (compare/rN/*/entries.json), so it carries on where it stopped. Everything stays in VOICE_USER_DIR; nothing
derived from the recordings enters the repository.
"""
import argparse, hashlib, json, math, os, random, re, shutil, subprocess, sys, time
import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import world_analysis as wa
import evaluate as ev
import build_units as bu
import pack
import prosody_fit as pf
import voicefile
import intonation

RAW = {'AX': ('AH', 0), 'IX': ('IH', 0), 'AXR': ('ER', 0), 'IYX': ('IY', 0)}
STAGES = ['baseline', 'align', 'fit', 'evaluate', 'publish']
STAGE_NAMES = dict(baseline='scoring the starting voice', align='aligning your takes', fit='fitting the voices',
                   evaluate='scoring the voices', publish='publishing the round')


class Progress:
    def __init__(self, root, rnd):
        self.path = os.path.join(root, 'tune', 'progress.json')
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.state = dict(round=rnd, state='running', started=time.strftime('%Y-%m-%dT%H:%M:%S'), stage='', step='', percent=0, log=[])

    def set(self, stage, step, percent):
        self.state.update(stage=stage, step=step, percent=round(max(0, min(100, percent)), 1))
        self.state['log'] = (self.state['log'] + [f"{time.strftime('%H:%M:%S')} {step}"])[-40:]
        tmp = self.path + '.tmp'
        json.dump(self.state, open(tmp, 'w'), indent=1)
        os.replace(tmp, self.path)
        print(step, flush=True)

    def finish(self, state, message, **extra):
        self.state.update(state=state, step=message, finished=time.strftime('%Y-%m-%dT%H:%M:%S'), percent=100 if state == 'done' else self.state['percent'],
                          **extra)
        self.set(self.state['stage'], message, self.state['percent'])


def file_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()[:16]


def reason_of(e):
    """A one-line reason a person can read (a bare KeyError prints only the key)."""
    if isinstance(e, KeyError):
        return f'a value the model needs was missing ({e.args[0]!r})'
    if isinstance(e, RuntimeError):
        return str(e)
    return f'{type(e).__name__}: {e}'


def words_of(text):
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9']*[,.;:!?]?", text)


def align_take(root, repo, line, take, syn_entry, cache, aligner=None, pron=None):
    """Aligned phones (recording time) and the analysis of the trimmed take, cached. With an
    aligner: phone recognition constrained to the line's pronunciation and its variants
    (phone_align.py), labelling what was said; without: the older DTW to a synthesis."""
    key = f"{line['id']}-{take['n']:02d}"
    jpath = os.path.join(cache, key + '.json')
    npath = os.path.join(cache, key + '.npz')
    if os.path.exists(jpath) and os.path.exists(npath):
        return json.load(open(jpath)), np.load(npath)
    rec = ev.trim(ev.load16(os.path.join(root, take['file'])))
    if aligner is not None:
        rec_phones, _ = aligner.align_choosing(rec, pron.line_alternatives(line['text']))
        metrics = {}
    else:
        dry, _, ph = syn_entry
        syn = ev.trim(ev.load16(dry))
        metrics, rec_phones = ev.score(rec, syn, ph)
        for r, q in zip(rec_phones, ph):
            r['word_end'] = q.get('word_end', False)
    an = wa.analyse(rec)
    json.dump(dict(phones=rec_phones, metrics=metrics), open(jpath, 'w'))
    np.savez_compressed(npath, f0=an['f0'], mcep=an['mcep'], ap=an['ap'])
    return json.load(open(jpath)), np.load(npath)


# ------------------------------------------------------------------ room noise
ROOM = None           # power envelope of the speaker's room tone (set by main), subtracted from every frame


def room_noise(root):
    """Median power envelope of the room-tone take (Mic & room tone tab), or None."""
    try:
        e = json.load(open(os.path.join(root, 'manifest.json')))['setup']['roomtone']
        an = wa.analyse(ev.load16(os.path.join(root, e['file'])))
        return np.median(an['env'], 0)
    except (OSError, KeyError, ValueError):
        return None


def denoise(mcep, room, over=1.5, floor=0.03):
    """Spectral subtraction of the room's noise from each frame's envelope: a stop's closure
    in a home recording is room noise, not silence, and without this it entered the units (and
    the adapted voice's per-phone offsets) about 20 dB too loud, heard as a scratch at stops."""
    if room is None:
        return mcep
    p = np.exp(wa.mcep_to_log_power(mcep))
    return wa.envelope_to_mcep(np.maximum(p - over * room, floor * p))


def corpus_files(subset, aligned, work):
    """Write the analysis/phones/words/speakers files build_units and prosody_fit read."""
    f0, mc, ap, si, ss, pw = [], [], [], [], [], []
    phones, words, speakers = [], [], []
    for k, (line, al, an) in enumerate(subset):
        n = len(an['f0'])
        f0.append(an['f0']); mc.append(denoise(an['mcep'], ROOM)); ap.append(an['ap'])
        si.append(np.full(n, k)); ss.append(np.zeros(n)); pw.append(np.zeros(n))
        toks = words_of(line['text'])
        words.append(dict(text=line['text'], words=[dict(word=' ' + t) for t in toks]))
        speakers.append(dict(segment=k, announcer_candidate=True))
        # word index: from the aligner, or counted from the synthesis plan's word ends
        wi = 0
        has_wi = any('wi' in p for p in al['phones'])
        for p in al['phones']:
            if has_wi and p['p'] != 'pau':
                wi = max(0, p['wi'])
            lab = p['p']
            if lab == 'pau':
                phones.append(dict(p='[SIL]', start=p['start'], end=p['end'], stress=0, wi=-1, word='', confidence=1.0, segment=k))
                continue
            base, stress = RAW.get(lab, (lab, p.get('stress', 0)))
            w = toks[min(wi, len(toks) - 1)].strip(',.;:!?').lower() if toks else ''
            phones.append(dict(p=base, start=p['start'], end=max(p['end'], p['start'] + 0.005), stress=stress, wi=min(wi, max(0, len(toks) - 1)),
                               word=w, confidence=1.0, segment=k, pronunciation_fallback=False))
            if p.get('word_end'):
                wi += 1
    np.savez_compressed(os.path.join(work, 'corpus.npz'), f0=np.concatenate(f0), mcep=np.concatenate(mc), ap=np.concatenate(ap),
                        seg_index=np.concatenate(si), seg_start=np.concatenate(ss), power=np.concatenate(pw))
    json.dump(dict(phones=phones), open(os.path.join(work, 'phones.json'), 'w'))
    json.dump(words, open(os.path.join(work, 'words.json'), 'w'))
    json.dump(dict(segments=speakers), open(os.path.join(work, 'speakers.json'), 'w'))
    return [os.path.join(work, f) for f in ('phones.json', 'words.json', 'corpus.npz', 'speakers.json')]


PLAIN = ('neutral', 'contrast', 'news')     # reads without a performed delivery
SHRINK = dict(duration=8, phrases=30, pauses=10, fricatives=10)


def toward(prior, user, w):
    """prior + w (user - prior), elementwise on numbers and lists."""
    if isinstance(prior, (list, tuple)):
        return [toward(a, b, w) for a, b in zip(prior, user)]
    return round(float(prior + w * (user - prior)), 4)


def fit_user(subset, work, prior_fit, plain_only=True, shrink=True, exclude=()):
    """The user's diphone units and prosody from the subset. Returns (units, fit, notes).

    More data must never make the voice worse, so the prosody:
    - comes from the plain reads only (PLAIN): the game adds each genre's delivery on top, and
      fitting the performed reads (war, race, ident...) would count that delivery twice;
    - moves from the prior toward the user's value gradually, by how much data each number rests
      on (weight n / (n + k), SHRINK), instead of switching over at a threshold.
    Units and the raised-voice spectrum (effort) use every take: they describe the voice itself.
    Lines in `exclude` (the validation lines) never shape the prosody.
    """
    os.makedirs(work, exist_ok=True)
    phones_json, words_json, npz, speakers = corpus_files(subset, None, work)
    notes = []
    # diphone units: the user's voice only (missing diphones borrow halves inside it, at runtime)
    phones = json.load(open(phones_json))['phones']
    tracks = bu.segment_tracks(npz)
    groups = {}
    for a, b, f, m in bu.tokens(phones, tracks, min_conf=0.0):
        groups.setdefault((a, b), []).append((f, m))
    units = {}
    for k, fm in groups.items():
        mean, n = bu.average([f for f, m in fm])
        units[k] = dict(frames=mean, count=n, left=float(np.median([m['left'] for f, m in fm])),
                        right=float(np.median([m['right'] for f, m in fm])))
    every = [p for p in pf.load(phones_json, words_json, npz, speakers) if subset[p['seg']][0]['id'] not in exclude]
    plain = [p for p in every if subset[p['seg']][0]['genre'] in PLAIN] if plain_only else every
    fit = dict(prior_fit)
    wt = (lambda n, k: n / (n + k)) if shrink else (lambda n, k: 1.0)
    if plain_only:
        notes.append(f'prosody from your {len({p["seg"] for p in plain})} plain reads (the game adds each genre\'s delivery itself)')
    if plain:
        d = pf.fit_durations(plain, pack.PHONES)
        counts = {}
        for phr in plain:
            for p in phr['phones']:
                if p['p'] != '[SIL]':
                    lab = bu.unit_label(p['p'], p['stress'])
                    counts[lab] = counts.get(lab, 0) + 1
        prior_ms = prior_fit['durations']['intercept_ms']
        ok = lambda v: isinstance(v, (int, float)) and np.isfinite(v) and v > 0
        d['intercept_ms'] = {l: v for l, v in d['intercept_ms'].items() if ok(v)}
        shared = [l for l in d['intercept_ms'] if counts.get(l, 0) >= 5 and ok(prior_ms.get(l))]
        ratio = float(np.exp(np.median([np.log(d['intercept_ms'][l] / prior_ms[l]) for l in shared]))) if shared else 1.0
        dur = dict(prior_fit['durations'])
        ims = {}
        for l, v in prior_ms.items():
            c = counts.get(l, 0)
            if l in d['intercept_ms'] and c >= 2 and (shrink or c >= 5):
                w = wt(c, SHRINK['duration'])
                ims[l] = round(float(np.exp(np.log(v * ratio) + w * (np.log(d['intercept_ms'][l]) - np.log(v * ratio)))), 1)
            else:
                ims[l] = round(v * ratio, 1)
        dur['intercept_ms'] = ims
        own = sum(1 for l in ims if counts.get(l, 0) >= 2)
        notes.append(f'durations: {own} phones from your takes' + (' (weighted by count)' if shrink else '') + f', the rest the prior scaled by {ratio:.2f}')
        if len(plain) >= 150:
            dur['factors'] = d['factors']; dur['elasticity'] = d['elasticity']; dur['reference_rate'] = d['reference_rate']
            notes.append('duration factors and tempo elasticities from your takes')
        else:
            dur['reference_rate'] = round(prior_fit['durations']['reference_rate'] / ratio, 3)
            notes.append('duration factors and tempo elasticities from the prior (fewer than 150 phrases)')
        fit['durations'] = dur
        data = pf.prepare_f0(plain)
        allf = np.concatenate([x['s'] for x in data]) if data else np.array([])
        if len(allf) > 200:
            fit['f0_st'] = dict(median=round(float(np.median(allf)), 2), p5=round(float(np.percentile(allf, 5)), 2), p95=round(float(np.percentile(allf, 95)), 2))
            notes.append(f"pitch level from your takes ({100 * 2 ** (fit['f0_st']['median'] / 12):.0f} Hz median)")
        psp = prior_fit['superposition']
        if len(data) >= (20 if shrink else 60):
            sp = pf.fit_superposition(data)
            w = wt(len(data), SHRINK['phrases'])
            sp['weights'] = {k: toward(psp['weights'][k], v, w) if k in psp['weights'] else v for k, v in sp['weights'].items()}
            lv = dict(psp.get('level_by_index', {}))      # a position class with no examples keeps the prior's level
            lv.update({k: toward(lv[k], v, w) if k in lv else v for k, v in sp.get('level_by_index', {}).items()})
            sp['level_by_index'] = lv
            sp['level_spread'] = toward(psp['level_spread'], sp['level_spread'], w)
            fit['superposition'] = sp
            notes.append(f'intonation shapes {round(100 * w)}% yours ({len(data)} phrases)')
        else:
            sp = dict(psp)
            if len(data) >= 5:
                lv = [float(np.median(x['s'])) for x in data]
                sp['level_spread'] = toward(psp['level_spread'], float(np.percentile(lv, 75) - np.percentile(lv, 25)), wt(len(data), SHRINK['phrases']))
            fit['superposition'] = sp
            notes.append(f'intonation shapes from the prior (fewer than {20 if shrink else 60} phrases)')
        fr = pf.fricatives(plain)
        fit['fricatives'] = {k: dict(v) for k, v in prior_fit['fricatives'].items()}
        for k, v in fr.items():
            if k in fit['fricatives'] and shrink:
                fit['fricatives'][k]['p90_ms'] = toward(fit['fricatives'][k]['p90_ms'], v['p90_ms'], wt(v['n'], SHRINK['fricatives']))
            elif v['n'] >= 5:
                fit['fricatives'][k] = v
        pz = pf.pauses(plain)
        fit['pauses'] = {}
        for k, v in prior_fit['pauses'].items():
            if k in pz and shrink and pz[k]['n'] >= 1:
                fit['pauses'][k] = dict(v, median_ms=toward(v['median_ms'], pz[k]['median_ms'], wt(pz[k]['n'], SHRINK['pauses'])))
            else:
                fit['pauses'][k] = pz[k] if k in pz and pz[k]['n'] >= 5 else v
    if every:
        try:
            e = pf.effort(every)
            if e['frames'] >= 300:
                fit['effort'] = e
                notes.append('raised-voice spectrum direction from your takes')
        except Exception:
            pass
    return units, fit, notes


# ------------------------------------------------------------------ three ways to make a voice
def centre_means(units, M):
    """Mean mel-cepstrum near each phone's centre (the unit points next to it), and the count."""
    acc, cnt = {}, {}
    for (a, b), u in units.items():
        f = u['frames']
        for ph, row in ((a, f[0, :M]), (b, f[-1, :M])):
            if ph == 'pau':
                continue
            acc[ph] = acc.get(ph, 0) + row * u['count']
            cnt[ph] = cnt.get(ph, 0) + u['count']
    return {p: acc[p] / cnt[p] for p in acc}, cnt


CONS_LEVEL_SLACK = 0.35     # log amplitude, about 3 dB


def adapt_units(narr, user, M, shrink=5.0):
    """The narrator's units moved toward the user's voice: per phone, the difference between the
    user's and the narrator's mean spectral envelope near the phone's centre (shrunk toward zero
    when the user has few tokens of it; a phone the user has not said takes its class's mean
    offset at half weight) is added along each unit, crossfading from the first phone's offset
    to the second's."""
    nm, _ = centre_means(narr, M)
    um, uc = centre_means(user, M)
    off = {}
    for p in nm:
        if p in um:
            w = uc[p] / (uc[p] + shrink)
            off[p] = w * (um[p] - nm[p])
    vowels = [p for p in off if p in ev.VOWELS]
    cons = [p for p in off if p not in ev.VOWELS]
    vmean = np.mean([off[p] for p in vowels], 0) if vowels else np.zeros(M)
    # a consonant's level offset stays near the vowels' (the voice's overall level difference):
    # its own centre is mostly closure or frication, whose level says little about the voice
    for p in cons:
        off[p] = off[p].copy()
        off[p][0] = float(np.clip(off[p][0], vmean[0] - CONS_LEVEL_SLACK, vmean[0] + CONS_LEVEL_SLACK))
    cmean = np.mean([off[p] for p in cons], 0) if cons else np.zeros(M)
    for p in nm:
        if p not in off:
            off[p] = 0.5 * (vmean if p in ev.VOWELS else cmean)
    off['pau'] = np.zeros(M)
    out = {}
    for (a, b), u in narr.items():
        f = u['frames'].copy()
        n = len(f)
        for k in range(n):
            lam = k / (n - 1)
            f[k, :M] += (1 - lam) * off.get(a, 0) + lam * off.get(b, 0)
        out[(a, b)] = dict(u, frames=f)
    return out, len([p for p in uc if p != 'pau'])


def blend_units(adapted, user, min_count=2):
    """The user's own unit where it has at least min_count tokens, the adapted narrator's elsewhere."""
    out = dict(adapted)
    own = 0
    for k, u in user.items():
        if u['count'] >= min_count or k not in adapted:
            out[k] = u
            own += 1
    return out, own


VOWEL_LABELS = {'AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY', 'IH', 'IY', 'OW', 'OY', 'UH', 'UW'}


def speaker_lexicon(subset, min_conf=0.35):
    """How the speaker says each word: the most frequent realisation in their aligned takes
    (phone by phone as the aligner labelled it, reductions and dropped phones included). Words
    the aligner was unsure of keep the dictionary's."""
    seen = {}
    for line, al, an in subset:
        cur = {}
        for p in al['phones']:
            if p['p'] != 'pau' and p.get('wi', -1) >= 0:
                cur.setdefault((p['wi'], p['word']), []).append(p)
        for (wi, w), ps in cur.items():
            if not w or np.mean([p['confidence'] for p in ps]) < min_conf:
                continue
            seen.setdefault(w, []).append(tuple(p['p'] + (str(p['stress']) if p['p'] in VOWEL_LABELS else '') for p in ps))
    out = {}
    for w, reals in seen.items():
        counts = {}
        for r in reals:
            counts[r] = counts.get(r, 0) + 1
        out[w] = list(max(counts, key=lambda r: (counts[r], -reals.index(r))))
    return out, seen


def substitutions(seen, lex, min_n=15, share=0.5):
    """The speaker's systematic substitutions: a dictionary phone (with its stress) they say as
    another phone in at least `share` of `min_n` or more tokens. Reductions of unstressed AH, IH,
    ER and IY are left out: the game makes those itself."""
    tally = {}
    for w, reals in seen.items():
        d = lex.get(w)
        if not d:
            continue
        for r in reals:
            if len(r) != len(d):
                continue
            for a, b in zip(d, r):
                tally.setdefault(a, {}).setdefault(b, 0)
                tally[a][b] += 1
    rules = {}
    for a, c in tally.items():
        n = sum(c.values())
        b, k = max(c.items(), key=lambda x: x[1])
        if n >= min_n and b != a and k / n >= share and not (a[:-1] in ('AH', 'IH', 'ER', 'IY') and a.endswith('0')):
            rules[a] = b
    return rules


def speaker_lex(base, subset):
    """The dictionary with the speaker's own pronunciations first and their substitutions applied
    to words they have not said. Returns (lexicon, words from the takes, rules)."""
    own, seen = speaker_lexicon(subset)
    rules = substitutions(seen, base)
    lex = {w: [rules.get(p, p) for p in pr] for w, pr in base.items()}
    lex.update(own)
    return lex, len(own), rules


# ------------------------------------------------------------------ calibration by synthesis
# The learned energy envelope made the synthesis's syllable energies less like the speaker's
# (round 5: 0.69 against 0.72 without it, on the held-out lines), so voices do not carry it.
ENERGY_ENVELOPE = False
# High energy is parked (round 8): the per-energy steps are neither fitted nor calibrated, and the
# game reads every station at the speaker's plain delivery (VOICE_ENERGY_PARKED). Set True to resume.
ENERGY_LEVELS = False
OUTPUT_PEAK_DB = -5.0           # the dry voice's peaks (99.9th percentile, dBFS) the studio stage was voiced for
GAME_GENRE = {'war': 'war', 'news': 'news', 'ident': 'news', 'race': 'race', 'advert': 'advert', 'weather': 'weather'}
NEUTRAL_STYLE = [1.0, 0.0, 1.0, 1.0]          # speed, pitch (st), range, pause scale: the plain reading


def delivery(phones, f0, start_of=lambda p: p['start'], dur_of=lambda p: p['end'] - p['start']):
    """Articulation rate (syllables per second of speech), internal pause time, pitch median and
    within-line spread (st), voiced fraction of the speech span, from phones and a 5 ms F0 track."""
    sp = [p for p in phones if p['p'] != 'pau']
    if len(sp) < 3:
        return None
    t0, t1 = start_of(sp[0]), start_of(sp[-1]) + dur_of(sp[-1])
    talk = sum(dur_of(p) for p in sp)
    syl = sum(1 for p in sp if re.sub(r'\d', '', p['p']) in ev.VOWELS)
    pause = sum(dur_of(p) for p in phones if p['p'] == 'pau' and start_of(p) > t0 and start_of(p) < t1)
    j0, j1 = int(t0 / 0.005), min(len(f0), int(t1 / 0.005) + 1)
    seg = np.asarray(f0[j0:j1])
    v = seg[seg > 0]
    if len(v) < 20:
        return None
    s = 12 * np.log2(v / 100.0)
    med = float(np.median(s))
    # spread: twice the median absolute deviation (robust to creak and octave slips in a track);
    # tail: how far the low end falls below the median (the depth of the falls)
    return dict(rate=syl / max(talk, 1e-3), pause=pause, med=med, spread=2.0 * float(np.median(np.abs(s - med))), voiced=len(v) / max(1, len(seg)),
                tail=max(0.3, med - float(np.percentile(s, 10))))


def spectral(x, f0):
    """Brightness (dB of 1-4 kHz over 80 Hz-1 kHz, median over voiced frames) and level
    movement (st. dev. of voiced frames' energy, dB) of a stretch of speech."""
    from scipy.signal import stft
    f, t, Z = stft(x, wa.RATE, nperseg=512, noverlap=432)
    P = np.abs(Z) ** 2
    v = np.asarray(f0)[np.clip((t / 0.005).astype(int), 0, len(f0) - 1)] > 0
    if v.sum() < 10:
        return None
    lo = P[(f > 80) & (f < 1000)][:, v].sum(0); hi = P[(f >= 1000) & (f < 4000)][:, v].sum(0)
    e = 10 * np.log10(P[:, v].sum(0) + 1e-12)
    return dict(bright=float(10 * np.log10(np.median(hi / np.maximum(lo, 1e-12)))), dyn=float(np.std(e)))


def brightness_per_c1():
    """How much one unit of c1 changes the brightness measure (dB), from the warped-cosine basis."""
    B = wa._mcep_basis(wa.FFT // 2 + 1)
    f = np.linspace(0, wa.RATE / 2, wa.FFT // 2 + 1)
    return float(10 / np.log(10) * (B[(f >= 1000) & (f < 4000), 1].mean() - B[(f > 80) & (f < 1000), 1].mean()))


def calibrate(repo, lines, takes, aligned, units, fit, lex, prior_fit, work, passes=4, per_genre_plain=12, root=None):
    """Fit the delivery by synthesis: render sample training lines, compare each genre with the
    speaker's takes, and set that genre's speed, pitch, range and pauses (and, from the plain
    reads, the register, shape gain, pitch limit, voicing threshold and reference rate) so the
    synthesis matches. Each genre's numbers are shrunk toward the plain reading by how many of its
    lines there are. Returns (fit, report)."""
    fit = dict(fit)
    fit['shape'] = [1.0 if fit.get('tune') else 1.6, 7.0, 0.5]      # a learned contour starts at its own size
    # only genres with takes get a fitted delivery; the rest keep the station's hand-set style
    fit['styles'] = {g: list(NEUTRAL_STYLE) for g in sorted({GAME_GENRE[l['genre']] for l in lines if l['genre'] in GAME_GENRE})}
    plain = [l for l in lines if l['genre'] not in GAME_GENRE][:per_genre_plain]
    sample = plain + [l for l in lines if l['genre'] in GAME_GENRE]
    rec = {}
    for l in sample:
        al, an = aligned[l['id']]
        d = delivery(al['phones'], an['f0'])
        if d:
            rec[l['id']] = d
    sample = [l for l in sample if l['id'] in rec]
    # brightness and level movement of the takes (vocal effort, sustain)
    for l in sample:
        if root:
            sp = spectral(ev.trim(ev.load16(os.path.join(root, takes[l['id']]['file']))), aligned[l['id']][1]['f0'])
            if sp:
                rec[l['id']].update(sp)
    sens = brightness_per_c1()
    fit['tilts'] = {g: list(v) for g, v in (fit.get('tilts') or {}).items()}
    fit['sustain'] = 9.0
    report = []
    for it in range(passes):
        v = os.path.join(work, f'calibrate-{it}.z')
        pack_voice(units, fit, lex, v, prior_fit)
        out = os.path.join(work, f'calibrate-{it}')
        syn = ev.synthesize(repo, sample, out, data=v, radio=False)
        got, vfrac, peaks = {}, {}, []
        for l in sample:
            dry, _, ph = syn[l['id']]
            x = ev.load16(dry)
            if l['genre'] not in GAME_GENRE:
                v = np.abs(x[np.abs(x) > 1e-3])
                if len(v):
                    peaks.append(float(np.percentile(v, 99.9)))
            an = wa.analyse(x)
            d = delivery(ph, an['f0'], dur_of=lambda p: p['dur'])
            if d:
                sp = spectral(x, an['f0'])
                if sp:
                    d.update(sp)
                got[l['id']] = d
            vp = os.path.join(out, f"{l['id']}-voicing.txt")
            if os.path.exists(vp):
                vfrac[l['id']] = np.loadtxt(vp, ndmin=1)
        groups = {}
        for l in sample:
            if l['id'] in got:
                groups.setdefault(GAME_GENRE.get(l['genre'], 'plain'), []).append(l['id'])
        step = {}
        for g, ids in groups.items():
            r = {k: float(np.median([rec[i][k] for i in ids])) for k in ('rate', 'med', 'spread', 'voiced')}
            y = {k: float(np.median([got[i][k] for i in ids])) for k in ('rate', 'med', 'spread', 'voiced')}
            r['pause'] = float(np.mean([rec[i]['pause'] for i in ids])); y['pause'] = float(np.mean([got[i]['pause'] for i in ids]))
            both = [i for i in ids if 'bright' in rec[i] and 'bright' in got[i]]
            if both:
                for k in ('bright', 'dyn'):
                    r[k] = float(np.median([rec[i][k] for i in both])); y[k] = float(np.median([got[i][k] for i in both]))
            step[g] = dict(n=len(ids), rec=r, syn=y)
            # brightness: the speaker's vocal effort, through c1 (plain reading under 'plain')
            if 'bright' in r and abs(sens) > 1e-6:
                key = 'plain' if g == 'plain' else g
                v = fit['tilts'].setdefault(key, [0.0] * 25)
                w = 1.0 if g == 'plain' else len(ids) / (len(ids) + 1.0)
                v[1] = round(float(np.clip(v[1] + w * (r['bright'] - y['bright']) / sens, -1.5, 1.5)), 4)
            if g == 'plain' and peaks:
                # output level: the plain reads' peaks (99.9th percentile) at OUTPUT_PEAK_DB, where the
                # studio's carbon microphone was voiced; a hotter voice overdrives it into hiss and distortion
                fit['output_gain'] = round(float(np.clip(fit.get('output_gain', 1.0) * 10 ** ((OUTPUT_PEAK_DB - 20 * np.log10(np.median(peaks))) / 20), 0.2, 3.0)), 4)
            if g == 'plain' and 'dyn' in r:
                # sustain: a voiced frame no further below the vowels than the speaker's level movement allows
                fit['sustain'] = round(float(np.clip(fit['sustain'] - (y['dyn'] - r['dyn']) / 4.343 * 1.5, 1.5, 9.0)), 3)
            if g == 'plain':
                fit['durations'] = dict(fit['durations'], reference_rate=round(fit['durations']['reference_rate'] * float(np.clip(r['rate'] / y['rate'], 0.7, 1.4)), 3))
                fit['f0_st'] = dict(fit.get('f0_st', {}), median=round(fit.get('f0_st', {}).get('median', 7.0) + float(np.clip(r['med'] - y['med'], -4, 4)), 2))
                gain, lim, thr = fit['shape']
                gain = float(np.clip(gain * np.clip(r['spread'] / max(0.5, y['spread']), 0.6, 1.8), 0.6, 4.0))
                lim = float(np.clip(max(lim, 0.6 * r['spread'] + 2.0), 5.0, 14.0))
                vals = np.concatenate([vfrac[i] for i in ids if i in vfrac]) if any(i in vfrac for i in ids) else np.array([])
                vals = vals[vals > 0.02]
                if len(vals) > 100:
                    now = float(np.mean(vals > thr))
                    target = float(np.clip(now + (r['voiced'] - y['voiced']), 0.3, 0.97))
                    thr = float(np.clip(np.quantile(vals, 1 - target), 0.2, 0.6))
                fit['shape'] = [round(gain, 3), round(lim, 2), round(thr, 3)]
                # pauses inside a line (comma, breath and between sentences) scale to the speaker's
                pz = float(np.clip((r['pause'] + 0.05) / (y['pause'] + 0.05), 0.3, 2.0))
                fit['pauses'] = {k: dict(v, median_ms=round(v['median_ms'] * pz, 1)) for k, v in fit['pauses'].items()}
            else:
                # the style that would match this pass (the current one times the ratios), then
                # pulled toward the plain reading by how few lines the genre has; stable across passes
                speed, pitch, rng, pz = fit['styles'][g]
                full = [speed * r['rate'] / y['rate'], pitch + (r['med'] - y['med']),
                        rng * r['spread'] / max(0.5, y['spread']), pz * (r['pause'] + 0.05) / (y['pause'] + 0.05)]
                w = len(ids) / (len(ids) + 0.5)
                speed, pitch, rng, pz = full[0] ** w, w * full[1], full[2] ** w, full[3] ** w
                fit['styles'][g] = [round(float(np.clip(speed, 0.6, 1.8)), 3), round(float(np.clip(pitch, -6, 14)), 2),
                                    round(float(np.clip(rng, 0.5, 2.5)), 3), round(float(np.clip(pz, 0.3, 2.5)), 3)]
        # each line's own energy, by synthesis: the slope of what is left (after each genre's median)
        # against the line's distance from its genre's usual energy corrects the per-step pitch,
        # range, tempo and fall depth, so the output lands on the takes at every energy
        en = fit.get('energy')
        if en and len(en.get('effect') or []) == 5:
            rows = []
            for l in sample:
                g = GAME_GENRE.get(l['genre']); e = l.get('energy') or 0
                if not g or e <= 0 or l['id'] not in got or g not in en['refs']:
                    continue
                r, y = rec[l['id']], got[l['id']]
                rows.append((g, e - en['refs'][g], r['med'] - y['med'], np.log(r['spread'] / max(0.3, y['spread'])),
                             np.log(r['rate'] / y['rate']), np.log(r['tail'] / max(0.3, y['tail']))))
            if len(rows) >= 6 and len({round(x[1]) for x in rows}) >= 2:
                adj = []
                for k in (2, 3, 4, 5):
                    med_g = {g: float(np.median([x[k] for x in rows if x[0] == g])) for g in {x[0] for x in rows}}
                    d = np.array([x[1] for x in rows]); res = np.array([x[k] - med_g[x[0]] for x in rows])
                    adj.append(float(np.sum(d * res) / (np.sum(d * d) + 2.0)))
                ef = en['effect']
                en['effect'] = [round(float(np.clip(ef[0] + adj[0], -3, 5)), 3), round(float(np.clip(ef[1] + adj[1], -0.5, 0.4)), 4),
                                round(float(np.clip(ef[2] + adj[2], -0.3, 0.3)), 4), ef[3], round(float(np.clip(ef[4] + adj[3], -0.8, 0.3)), 4)]
                step['energy'] = dict(n=len(rows), adjust=[round(a, 3) for a in adj], effect=en['effect'])
        report.append(step)
    return fit, report


def energy_effect(lines, takes, aligned, root, lam=4.0):
    """How the speaker's delivery moves with a line's intended energy (script 'energy', 1..5), from
    their takes of the genres that vary in it: per energy step, pitch (st), log pitch spread, log
    articulation rate and brightness, each a least-squares slope shared by the genres (each genre
    its own intercept), shrunk toward none (ridge lam). Returns {'effect': [pitch, log range, log
    speed, tilt dB/octave], 'refs': {genre: mean energy}, 'n': takes} or None when the energies
    do not vary enough."""
    rows = []
    for l in lines:
        g = GAME_GENRE.get(l['genre'])
        e = l.get('energy') or 0
        if not g or e <= 0:
            continue
        al, an = aligned[l['id']]
        d = delivery(al['phones'], an['f0'])
        sp = spectral(ev.trim(ev.load16(os.path.join(root, takes[l['id']]['file']))), an['f0'])
        if d and sp and d['spread'] > 0.3:
            rows.append((g, e, d['med'], np.log(d['spread']), np.log(d['rate']), sp['bright']))
    levels = {}
    for g, e, *_ in rows:
        levels[e] = levels.get(e, 0) + 1
    if len([k for k, n in levels.items() if n >= 3]) < 2:
        return None
    genres = sorted({r[0] for r in rows})
    X = np.array([[1.0 if r[0] == g else 0.0 for g in genres] + [r[1]] for r in rows])
    P = np.zeros((X.shape[1], X.shape[1])); P[-1, -1] = lam
    slope = lambda col: float(np.linalg.solve(X.T @ X + P, X.T @ np.array([r[col] for r in rows]))[-1])
    pitch, spread, rate, bright = slope(2), slope(3), slope(4), slope(5)
    refs = {g: round(float(np.mean([r[1] for r in rows if r[0] == g])), 3) for g in genres}
    return dict(effect=[round(float(np.clip(pitch, -3, 4)), 3), round(float(np.clip(spread, -0.4, 0.4)), 4),
                        round(float(np.clip(rate, -0.3, 0.3)), 4), round(float(np.clip(bright / 2, -1.5, 1.5)), 3), 0.0],
                refs=refs, n=len(rows), levels=levels)


GUARD_FLOOR = 0.05     # word accuracy a choice with more of the speaker's data may give up; within it the user's ear decides     # word accuracy a choice with more of the speaker's data may give up


def validation_lines(pool, k_min=6, k_max=10, share=0.12):
    """A fixed draw of training lines that never shape the prosody: the prosody guard scores
    candidate prosodies on them."""
    ids = sorted(l['id'] for l in pool)
    k = min(k_max, max(k_min, round(share * len(ids))))
    pick = set(random.Random(20261115).sample(ids, min(k, len(ids))))
    return [l for l in pool if l['id'] in pick]


def guard_prosody(candidates, score, floor=GUARD_FLOOR):
    """candidates: [(label, fit)] with the most of the speaker's data first. Each is scored
    (word accuracy on the validation lines); the first within `floor` of the best wins. The
    speaker's own prosody is kept unless it costs intelligibility beyond the floor: how close it
    sounds to them is theirs to judge, and the round's note reports what it cost."""
    scored = [(label, fit, score(label, fit)) for label, fit in candidates]
    best = max(a for _, _, a in scored)
    for label, fit, acc in scored:
        if acc >= best - floor:
            return label, fit, {l: round(a, 3) for l, _, a in scored}


def pack_voice(units, fit, lex, out, prior=None):
    pack.pack(units, lex, out, pack.model_numbers(fit, fit['superposition'], prior))


def evaluate_voice(repo, heldout, takes, data, outdir, root, rel_base, full, asr=None):
    """Scores a voice on the held-out lines; a finished scoring of the same voice file on the same
    held-out takes is reused, so a retried round only scores what it had not finished."""
    key = dict(voice=file_hash(data), lines=[f"{l['id']}-{takes[l['id']]['n']}" for l in heldout], full=bool(full), asr=asr is not None)
    done = os.path.join(outdir, 'entries.json')
    if os.path.exists(done):
        try:
            d = json.load(open(done))
            if d.get('key') == key:
                evaluate_voice.reused += 1
                return d['entries']
        except (OSError, ValueError):
            pass
    # the same voice on the same takes, scored by an earlier round (its files stay where they are)
    shared = os.path.join(root, 'tune', 'scores', hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:20] + '.json')
    if not full and os.path.exists(shared):
        try:
            entries = json.load(open(shared))['entries']
            if all(os.path.exists(os.path.join(root, e['synth'])) for e in entries):
                evaluate_voice.reused += 1
                return entries
        except (OSError, ValueError, KeyError):
            pass
    entries = _evaluate_voice(repo, heldout, takes, data, outdir, root, rel_base, full, asr)
    tmp = done + '.tmp'
    json.dump(dict(key=key, entries=entries), open(tmp, 'w'))
    os.replace(tmp, done)
    if rel_base:
        os.makedirs(os.path.dirname(shared), exist_ok=True)
        json.dump(dict(key=key, entries=entries), open(shared + '.tmp', 'w'))
        os.replace(shared + '.tmp', shared)
    return entries


evaluate_voice.reused = 0


def _evaluate_voice(repo, heldout, takes, data, outdir, root, rel_base, full, asr=None):
    syn = ev.synthesize(repo, heldout, os.path.join(outdir, 'synth'), data=data, radio=full)
    entries = []
    for l in heldout:
        rec = ev.trim(ev.load16(os.path.join(root, takes[l['id']]['file'])))
        dry, radio, ph = syn[l['id']]
        s = ev.trim(ev.load16(dry))
        m, _ = ev.score(rec, s, ph)
        if asr is not None:
            m['word_acc'], hyp = asr.accuracy(s, l['text'])
            m['word_acc'] = round(m['word_acc'], 3)
        e = dict(line=l['id'], text=l['text'], genre=l['genre'], metrics=m)
        if asr is not None:
            e['heard'] = hyp
        d = os.path.join(outdir, l['id'])
        os.makedirs(d, exist_ok=True)
        sf.write(os.path.join(d, 'synth.wav'), ev.level(s).astype(np.float32), wa.RATE, subtype='PCM_16')
        e['synth'] = f"{rel_base}/{l['id']}/synth.wav"
        if full:
            sf.write(os.path.join(d, 'rec.wav'), ev.level(rec).astype(np.float32), wa.RATE, subtype='PCM_16')
            sf.write(os.path.join(d, 'radio.wav'), ev.level(ev.trim(ev.load16(radio))).astype(np.float32), wa.RATE, subtype='PCM_16')
            e['rec'] = f"{rel_base}/{l['id']}/rec.wav"; e['radio'] = f"{rel_base}/{l['id']}/radio.wav"
        entries.append(e)
    return entries


KEYS = ['word_acc', 'mcd_db', 'f0_rmse_st', 'f0_rmse_st_shape', 'f0_corr', 'energy_corr', 'dur_err', 'voicing_err', 'rate_rec', 'rate_syn']


def summary(entries):
    return {k: round(float(np.nanmean([e['metrics'].get(k, np.nan) for e in entries])), 3) for k in KEYS}


def publish(root, rnd):
    idx_path = os.path.join(root, 'compare', 'index.json')
    idx = json.load(open(idx_path)) if os.path.exists(idx_path) else dict(rounds=[])
    idx['rounds'] = [r for r in idx['rounds'] if r['id'] != rnd['id']] + [rnd]
    tmp = idx_path + '.tmp'
    json.dump(idx, open(tmp, 'w'), indent=1)
    os.replace(tmp, idx_path)


def main():
    global ROOM
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--repo', required=True)
    ap.add_argument('--prior-data', required=True)
    ap.add_argument('--prior-fit', required=True)
    ap.add_argument('--round', default='')
    ap.add_argument('--fractions', default='0.25,0.5,1')
    ap.add_argument('--listen', type=int, default=2)
    ap.add_argument('--min-lines', type=int, default=10)
    ap.add_argument('--aligner', default='', help='phone classifier model directory (scratch); without it, the old DTW')
    ap.add_argument('--aligner-vocab', default='')
    ap.add_argument('--asr', default='', help='speech recognizer model directory (scratch), for word accuracy')
    ap.add_argument('--dtw', action='store_true', help='use the old DTW alignment (not recommended)')
    a = ap.parse_args()
    # the phone aligner and the recognizer are the defaults wherever their scratch copies exist
    models = os.environ.get('VOICE_ANALYSIS_MODELS', os.path.expanduser('~/dev/tmp/aegean-skies/radio/voice4/models'))
    if not a.aligner and not a.dtw and os.path.isdir(os.path.join(models, 'aligner')):
        a.aligner, a.aligner_vocab = os.path.join(models, 'aligner'), os.path.join(models, 'phones', 'vocab.json')
    if not a.asr and os.path.isdir(os.path.join(models, 'whisper')):
        a.asr = os.path.join(models, 'whisper')
    root = a.root
    os.makedirs(os.path.join(root, 'compare'), exist_ok=True)
    idx_path = os.path.join(root, 'compare', 'index.json')
    idx = json.load(open(idx_path)) if os.path.exists(idx_path) else dict(rounds=[])
    nums = [int(r['id'][1:]) for r in idx['rounds'] if re.match(r'^r\d+$', r['id'])]
    rnd_id = a.round or f'r{max([0] + nums) + 1}'
    prog = Progress(root, rnd_id)
    if a.round and os.path.isdir(os.path.join(root, 'compare', rnd_id)):
        prog.set('baseline', f'Resuming round {rnd_id[1:]}: finished alignments and scorings are reused', 0)
    try:
        script = json.load(open(os.path.join(root, 'script.json')))
        manifest = json.load(open(os.path.join(root, 'manifest.json')))
        takes = {}
        for l in script['lines']:
            e = manifest['lines'].get(l['id']) or {}
            if e.get('chosen') is not None:
                t = next((t for t in e['takes'] if t['n'] == e['chosen']), None)
                if t and os.path.exists(os.path.join(root, t['file'])):
                    takes[l['id']] = t
        pool = [l for l in script['lines'] if not l['heldout'] and l['id'] in takes]
        heldout = [l for l in script['lines'] if l['heldout'] and l['id'] in takes]
        if not heldout:
            raise RuntimeError('no held-out line is recorded yet: keep recording, held-out lines come up every so often')
        if len(pool) < a.min_lines:
            raise RuntimeError(f'only {len(pool)} training lines recorded; tune needs at least {a.min_lines}')
        # the synthesizer, built once for the whole run
        prog.set('baseline', 'Building the synthesizer', 1)
        os.makedirs(os.path.join(root, 'tune'), exist_ok=True)
        binp = os.path.join(root, 'tune', 'voicelab')
        r = subprocess.run(['sloppy', 'build', '--release', 'tools/voicelab.jo', '-o', binp], cwd=a.repo, capture_output=True, text=True)
        if r.returncode == 0:
            os.environ['VOICELAB_BIN'] = binp
        asr = ev.Recognizer(a.asr) if a.asr else None
        date = time.strftime('%Y-%m-%dT%H:%M:%S')
        base_dir = os.path.join(root, 'compare', rnd_id)
        held_ids = [l['id'] for l in heldout]
        curve = []
        # the speaker's own held-out recordings: the ceiling for word accuracy
        rec_acc = None
        if asr is not None:
            prog.set('baseline', f'Checking your {len(heldout)} held-out recordings with the recognizer', 2)
            ra_path = os.path.join(root, 'tune', 'recordings-word-acc.json')
            ra = {}
            try:
                ra = json.load(open(ra_path))
            except (OSError, ValueError):
                pass
            for l in heldout:
                k = f"{l['id']}-{takes[l['id']]['n']}"
                if k not in ra:
                    ra[k] = asr.accuracy(ev.trim(ev.load16(os.path.join(root, takes[l['id']]['file']))), l['text'])[0]
            json.dump(ra, open(ra_path + '.tmp', 'w')); os.replace(ra_path + '.tmp', ra_path)
            rec_acc = round(float(np.mean([ra[f"{l['id']}-{takes[l['id']]['n']}"] for l in heldout])), 3)
        # 1. the starting voice, scored on today's held-out set
        prog.set('baseline', f'Scoring the starting voice on {len(heldout)} held-out lines', 4)
        start = evaluate_voice(a.repo, heldout, takes, a.prior_data, os.path.join(base_dir, 'start'), root, f'compare/{rnd_id}/start', False, asr)
        curve.append(dict(lines=0, kind='start', label='starting voice', summary=summary(start)))
        # earlier rounds' voices, scored again on the same held-out lines
        for r0 in [r for r in idx['rounds'] if r.get('voice') and os.path.exists(os.path.join(root, r['voice']))][-3:]:
            prog.set('baseline', f"Scoring {r0['id']}'s voice on today's held-out lines", 6)
            ents = evaluate_voice(a.repo, heldout, takes, os.path.join(root, r0['voice']), os.path.join(base_dir, 'earlier-' + r0['id']), root,
                                  f"compare/{rnd_id}/earlier-{r0['id']}", False, asr)
            curve.append(dict(lines=r0.get('lines', 0), kind='earlier', label=f"{r0['id']} voice", summary=summary(ents)))
        # 2. alignment
        aligner = pron = None
        cache = os.path.join(root, 'tune', 'cache')
        if a.aligner:
            import phone_align as pa
            aligner = pa.Aligner(a.aligner, a.aligner_vocab)
            pron = pa.Pronouncer()
            cache = os.path.join(root, 'tune', 'cache-phone3')     # 3: Greek-style names, derived English words
        os.makedirs(cache, exist_ok=True)
        key = lambda l: f"{l['id']}-{takes[l['id']]['n']:02d}"
        todo = [l for l in pool if not os.path.exists(os.path.join(cache, key(l) + '.json'))]
        syn = {}
        if todo and aligner is None:
            prog.set('align', f'Synthesizing {len(todo)} new lines to align against', 8)
            syn = ev.synthesize(a.repo, todo, os.path.join(root, 'tune', 'align-synth'), data=a.prior_data, radio=False)
        aligned = {}
        for k, l in enumerate(pool):
            if l in todo:
                prog.set('align', f"Aligning take {k + 1} of {len(pool)} ({l['id']})", 10 + 25 * k / len(pool))
                align_take(root, a.repo, l, takes[l['id']], syn.get(l['id']), cache, aligner, pron)
            aligned[l['id']] = (json.load(open(os.path.join(cache, key(l) + '.json'))), dict(np.load(os.path.join(cache, key(l) + '.npz'))))
        # 3. voices on nested random subsets, three ways each
        order = list(pool)
        random.Random(20261114).shuffle(order)
        fractions = sorted(set(float(x) for x in a.fractions.split(',')))
        prior_fit = json.load(open(a.prior_fit))
        narr = voicefile.read(a.prior_data)
        M = narr['M']
        # the dictionary for every word of the script (the game's own text has its own), then the
        # speaker's pronunciations per subset; the room's noise comes off every analysed frame
        lex, _ = pack.lexicon(a.repo, extra_text=' '.join(l['text'] for l in script['lines']))
        ROOM = room_noise(root)
        listen = held_ids[:a.listen]
        sizes = []
        for fr in fractions:
            n = len(order) if fr >= 1 else min(len(order), max(a.min_lines, int(math.ceil(fr * len(order)))))
            if n not in sizes:
                sizes.append(n)
        full_entries, notes_full = {}, []
        # the prosody guard: candidate prosodies scored on validation lines from the pool
        val = validation_lines(pool) if asr is not None else []
        val_ids = {l['id'] for l in val}
        chosen = None                     # the prosody chosen at the previous size
        guard_log, calibration_log = [], []
        for i, n in enumerate(sizes):
            subset = [(l, aligned[l['id']][0], aligned[l['id']][1]) for l in order[:n]]
            full = n == len(order)
            share = '' if full else f' ({round(100 * n / len(order))}%)'
            prog.set('fit', f'Fitting voices to {n} lines{share}', 38 + 55 * i / len(sizes))
            work = os.path.join(root, 'tune', 'work', f'{rnd_id}-{n}')
            user, fit, notes = fit_user(subset, work, prior_fit, exclude=val_ids)
            adapted, phones_seen = adapt_units(narr['units'], user, M)
            lex_n, own_words, rules = speaker_lex(lex, subset)
            # sentence intonation, the energy envelope and each genre's vocal effort, learned from the takes
            items = [(l, al['phones'], an) for l, al, an in subset if l['id'] not in val_ids]
            import phone_align as pa_
            fit['tune'] = intonation.fit(items, a.repo, pa_.number_words, pack.PHONES)
            if fit['tune'] and not ENERGY_ENVELOPE:
                fit['tune'] = dict(fit['tune'], energy=None, intrinsic=None)
            fit['tilts'] = intonation.genre_tilts(items)
            if fit['tune']:
                notes = notes + [f"intonation learned from {fit['tune']['syllables']} syllables of your takes"
                                 + (f"; vocal effort of {', '.join(sorted(fit['tilts']))} from your takes of them" if fit['tilts'] else '')]
            notes = notes + [f'pronunciations: {own_words} words as you say them' + (', and for other words ' + ', '.join(f'{k} as {v}' for k, v in rules.items()) if rules else '')
                             + (', room noise taken off your takes' if ROOM is not None else '')]
            likeness = {}
            if val:
                if chosen is None:        # before any of the speaker's prosody: the prior's, at the speaker's pitch
                    chosen = ('starting prosody at your pitch', dict(prior_fit, f0_st=fit.get('f0_st', prior_fit['f0_st'])))
                cands = [(f'yours from {n} lines', fit),
                         (f'yours from {n} lines, intonation as before', dict(fit, superposition=chosen[1]['superposition'], tune=chosen[1].get('tune'))),
                         (f'as before ({chosen[0]})', chosen[1])]

                def vscore(label, f, n=n, adapted=adapted):
                    slug = re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-')[:60]
                    v = os.path.join(work, f'guard-{slug}.z')
                    pack_voice(adapted, f, lex_n, v, prior_fit)
                    prog.set('fit', f'Checking prosody "{label}" on {len(val)} validation lines', 38 + 55 * i / len(sizes))
                    ents = evaluate_voice(a.repo, val, takes, v, os.path.join(work, 'guard-' + slug), root, '', False, asr)
                    likeness[label] = round(float(np.nanmean([e['metrics'].get('f0_corr', np.nan) for e in ents])), 3)
                    return float(np.mean([e['metrics']['word_acc'] for e in ents]))
                label, fit, accs = guard_prosody(cands, vscore)
                if label.startswith('as before'):
                    label = chosen[0]
                chosen = (label, fit)
                guard_log.append(dict(lines=n, chosen=label, validation_word_acc=accs, validation_pitch_corr=likeness))
                notes = notes + [f'prosody kept: {label} (on {len(val)} validation lines, word accuracy / pitch match with your takes: '
                                 + ', '.join(f'{k} {v:.0%} / {likeness.get(k, float("nan")):.2f}' for k, v in accs.items()) + ')']
            # the delivery, fitted by synthesis against the speaker's takes of each genre
            prog.set('fit', f'Calibrating the delivery of the {n}-line voice against your takes', 38 + 55 * (i + 0.2) / len(sizes))
            # a line's own energy within its genre: measured from the takes, then corrected by synthesis
            fit['energy'] = energy_effect([l for l, _, _ in subset if l['id'] not in val_ids], takes, aligned, root) if ENERGY_LEVELS else None
            fit, cal = calibrate(a.repo, [l for l, _, _ in subset if l['id'] not in val_ids], takes, aligned, adapted, fit, lex_n, prior_fit, work, root=root)
            if fit.get('energy'):
                ee = fit['energy']['effect']
                notes = notes + [f"per energy step (from {fit['energy']['n']} takes): pitch {ee[0]:+.1f} st, range x{np.exp(ee[1]):.2f}, "
                                 f"tempo x{np.exp(ee[2]):.2f}, tilt {ee[3]:+.2f} dB/octave" + (f", falls x{np.exp(ee[4]):.2f}" if len(ee) > 4 else '') + ", calibrated by synthesis, about each genre's usual energy "
                                 + ', '.join(f'{g} {r:.1f}' for g, r in fit['energy']['refs'].items())]
            last = cal[-1]
            notes = notes + ['delivery fitted to your takes: ' + '; '.join(
                f"{g} {v[0]:.2f}x tempo, {v[1]:+.1f} st, range {v[2]:.2f}, pauses {v[3]:.2f}" for g, v in sorted(fit['styles'].items()) if g in last)
                + f"; register {100 * 2 ** (fit['f0_st']['median'] / 12):.0f} Hz, shape gain {fit['shape'][0]:.2f}, pitch limit {fit['shape'][1]:.1f} st, voicing above {fit['shape'][2]:.2f}"
                + f", sustain {fit['sustain']:.1f}, brightness " + ', '.join(f"{g or 'plain'} {v[1]:+.2f}" for g, v in sorted(fit['tilts'].items()))]
            calibration_log.append(dict(lines=n, styles=fit['styles'], shape=fit['shape'], passes=cal))
            blended, own = blend_units(adapted, user)
            kinds = [('adapt', adapted, f'starting voice adapted to you ({phones_seen} phones measured)'),
                     ('blend', blended, f'your units where you have them ({own}), adapted elsewhere'),
                     ('units', user, f'your units only ({len(user)})')]
            for j, (kind, units, about) in enumerate(kinds):
                voice = os.path.join(root, 'voices', f'{rnd_id}-{kind}-{n}.z')
                os.makedirs(os.path.dirname(voice), exist_ok=True)
                pack_voice(units, fit, lex_n, voice, prior_fit)
                prog.set('evaluate', f'Scoring "{kind}" from {n} lines on {len(heldout)} held-out lines', 40 + 55 * (i + (j + 1) / 3) / len(sizes))
                ents = evaluate_voice(a.repo, heldout, takes, voice, os.path.join(base_dir, f'{kind}-n{n}'), root, f'compare/{rnd_id}/{kind}-n{n}', full, asr)
                curve.append(dict(lines=n, kind=kind, label=f'{kind}, {n} lines{share}', about=about, summary=summary(ents),
                                  prosody=chosen[0] if val else 'yours',
                                  voice=os.path.relpath(voice, root), listen={e['line']: e['synth'] for e in ents if e['line'] in listen}))
                if full:
                    full_entries[kind] = ents
            if full:
                notes_full = notes
        # 4. publish: the best full-pool voice by word accuracy (then spectral distance) leads
        best = max(full_entries, key=lambda k: (np.nanmean([e['metrics'].get('word_acc', 0) for e in full_entries[k]]),
                                                -np.nanmean([e['metrics']['mcd_db'] for e in full_entries[k]])))
        entries = full_entries[best]
        start_by = {e['line']: e for e in start}
        for e in entries:
            e['variants'] = [dict(label='starting voice', synth=start_by[e['line']]['synth'])]
            e['variants'] += [dict(label=c['label'], synth=c['listen'][e['line']]) for c in curve
                              if c.get('listen') and e['line'] in c['listen'] and not (c['kind'] == best and c['lines'] == len(order))]
        acc = {c['label']: c['summary'].get('word_acc') for c in curve}
        main_voice = next(c['voice'] for c in curve if c['kind'] == best and c['lines'] == len(order))
        note = (f"Leading voice: {best} ({next(c['about'] for c in curve if c['kind'] == best and c['lines'] == len(order))}). "
                + (f"Word accuracy (a recognizer's, on {len(heldout)} held-out lines): your recordings {rec_acc:.0%}; "
                   + '; '.join(f'{k} {v:.0%}' for k, v in acc.items() if v is not None) + '. ' if asr else '')
                + 'Prosody: ' + '; '.join(notes_full) + '.')
        prog.set('publish', 'Publishing the round', 98)
        # leftovers of an earlier failed attempt at this round (other pool sizes) go
        keep_dirs = {'start'} | {f"earlier-{c['label'].split()[0]}" for c in curve if c['kind'] == 'earlier'} \
            | {f"{c['kind']}-n{c['lines']}" for c in curve if c['kind'] not in ('start', 'earlier')}
        for d in os.listdir(base_dir):
            if d not in keep_dirs and os.path.isdir(os.path.join(base_dir, d)):
                shutil.rmtree(os.path.join(base_dir, d), ignore_errors=True)
        keep_voices = {os.path.basename(c['voice']) for c in curve if c.get('voice')}
        for f in os.listdir(os.path.join(root, 'voices')):
            if f.startswith(rnd_id + '-') and f not in keep_voices:
                os.remove(os.path.join(root, 'voices', f))
        publish(root, dict(id=rnd_id, label=f'Round {rnd_id[1:]}: {len(order)} of your lines, best: {best}', note=note, date=date,
                           heldout=len(heldout), heldout_lines=held_ids, recordings_word_acc=rec_acc, lines=len(order),
                           kind=best, summary=summary(entries), entries=entries, curve=curve, voice=main_voice,
                           aligner='phone' if aligner else 'dtw', guard=guard_log, calibration=calibration_log, validation_lines=sorted(val_ids)))
        prog.finish('done', f'Round {rnd_id[1:]} is ready on the Compare tab'
                    + (f' ({evaluate_voice.reused} scorings reused from the earlier attempt)' if evaluate_voice.reused else ''))
    except Exception as e:
        import traceback
        traceback.print_exc()
        stage = prog.state.get('stage') or 'baseline'
        where = STAGE_NAMES.get(stage, stage)
        m = re.match(r'(Fitting voices to|Scoring "\w+" from) (\d+) lines', prog.state.get('step', ''))
        if m:
            where += f' ({m.group(2)} lines)'
        reason = reason_of(e)
        prog.finish('failed', f'Tuning failed at {where}: {reason}', failed_stage=where, reason=reason, resumable=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
