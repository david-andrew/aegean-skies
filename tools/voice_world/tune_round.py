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
        rec_phones = aligner.align(rec, pron.line(line['text']))
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


def corpus_files(subset, aligned, work):
    """Write the analysis/phones/words/speakers files build_units and prosody_fit read."""
    f0, mc, ap, si, ss, pw = [], [], [], [], [], []
    phones, words, speakers = [], [], []
    for k, (line, al, an) in enumerate(subset):
        n = len(an['f0'])
        f0.append(an['f0']); mc.append(an['mcep']); ap.append(an['ap'])
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


def fit_user(subset, work, prior_fit):
    """The user's diphone units and prosody from the subset; thin parts of the prosody fall back
    to the prior. Returns (units, fit, notes)."""
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
    # every phone must be able to start and end a phrase: borrow the nearest pause unit if missing
    phrases = pf.load(phones_json, words_json, npz, speakers)
    fit = dict(prior_fit)
    if phrases:
        d = pf.fit_durations(phrases, pack.PHONES)
        counts = {}
        for p in phones:
            if p['p'] != '[SIL]':
                lab = bu.unit_label(p['p'], p['stress'])
                counts[lab] = counts.get(lab, 0) + 1
        prior_ms = prior_fit['durations']['intercept_ms']
        ok = lambda v: isinstance(v, (int, float)) and np.isfinite(v) and v > 0
        d['intercept_ms'] = {l: v for l, v in d['intercept_ms'].items() if ok(v)}
        shared = [l for l in d['intercept_ms'] if counts.get(l, 0) >= 5 and ok(prior_ms.get(l))]
        ratio = float(np.exp(np.median([np.log(d['intercept_ms'][l] / prior_ms[l]) for l in shared]))) if shared else 1.0
        dur = dict(prior_fit['durations'])
        dur['intercept_ms'] = {l: (d['intercept_ms'][l] if counts.get(l, 0) >= 5 and l in d['intercept_ms'] else round(v * ratio, 1))
                               for l, v in prior_ms.items()}
        own = sum(1 for l in dur['intercept_ms'] if counts.get(l, 0) >= 5)
        notes.append(f'durations: {own} phones from your takes, the rest the prior scaled by {ratio:.2f}')
        if len(phrases) >= 150:
            dur['factors'] = d['factors']; dur['elasticity'] = d['elasticity']; dur['reference_rate'] = d['reference_rate']
            notes.append('duration factors and tempo elasticities from your takes')
        else:
            dur['reference_rate'] = round(prior_fit['durations']['reference_rate'] / ratio, 3)
            notes.append('duration factors and tempo elasticities from the prior (fewer than 150 phrases)')
        fit['durations'] = dur
        data = pf.prepare_f0(phrases)
        allf = np.concatenate([x['s'] for x in data]) if data else np.array([])
        if len(allf) > 200:
            fit['f0_st'] = dict(median=round(float(np.median(allf)), 2), p5=round(float(np.percentile(allf, 5)), 2), p95=round(float(np.percentile(allf, 95)), 2))
            notes.append(f"pitch level from your takes ({100 * 2 ** (fit['f0_st']['median'] / 12):.0f} Hz median)")
        if len(data) >= 60:
            sp = pf.fit_superposition(data)
            # a phrase-position class with no examples keeps the prior's level
            lv = dict(prior_fit['superposition'].get('level_by_index', {}))
            lv.update(sp.get('level_by_index', {}))
            sp['level_by_index'] = lv
            fit['superposition'] = sp
            notes.append('intonation shapes fitted to your takes')
        else:
            sp = dict(prior_fit['superposition'])
            if len(data) >= 5:
                lv = [float(np.median(x['s'])) for x in data]
                sp['level_spread'] = round(float(np.percentile(lv, 75) - np.percentile(lv, 25)), 2)
            fit['superposition'] = sp
            notes.append('intonation shapes from the prior (fewer than 60 phrases)')
        try:
            e = pf.effort(phrases)
            if e['frames'] >= 300:
                fit['effort'] = e
                notes.append('raised-voice spectrum direction from your takes')
        except Exception:
            pass
        fr = pf.fricatives(phrases)
        fit['fricatives'] = {k: v for k, v in prior_fit['fricatives'].items()}
        fit['fricatives'].update({k: v for k, v in fr.items() if v['n'] >= 5})
        pz = pf.pauses(phrases)
        fit['pauses'] = {k: (pz[k] if k in pz and pz[k]['n'] >= 5 else v) for k, v in prior_fit['pauses'].items()}
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
    entries = _evaluate_voice(repo, heldout, takes, data, outdir, root, rel_base, full, asr)
    tmp = done + '.tmp'
    json.dump(dict(key=key, entries=entries), open(tmp, 'w'))
    os.replace(tmp, done)
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
            cache = os.path.join(root, 'tune', 'cache-phone')
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
        lex, _ = pack.lexicon(a.repo)
        listen = held_ids[:a.listen]
        sizes = []
        for fr in fractions:
            n = len(order) if fr >= 1 else min(len(order), max(a.min_lines, int(math.ceil(fr * len(order)))))
            if n not in sizes:
                sizes.append(n)
        full_entries, notes_full = {}, []
        for i, n in enumerate(sizes):
            subset = [(l, aligned[l['id']][0], aligned[l['id']][1]) for l in order[:n]]
            full = n == len(order)
            share = '' if full else f' ({round(100 * n / len(order))}%)'
            prog.set('fit', f'Fitting voices to {n} lines{share}', 38 + 55 * i / len(sizes))
            user, fit, notes = fit_user(subset, os.path.join(root, 'tune', 'work', f'{rnd_id}-{n}'), prior_fit)
            adapted, phones_seen = adapt_units(narr['units'], user, M)
            blended, own = blend_units(adapted, user)
            kinds = [('adapt', adapted, f'starting voice adapted to you ({phones_seen} phones measured)'),
                     ('blend', blended, f'your units where you have them ({own}), adapted elsewhere'),
                     ('units', user, f'your units only ({len(user)})')]
            for j, (kind, units, about) in enumerate(kinds):
                voice = os.path.join(root, 'voices', f'{rnd_id}-{kind}-{n}.z')
                os.makedirs(os.path.dirname(voice), exist_ok=True)
                pack_voice(units, fit, lex, voice, prior_fit)
                prog.set('evaluate', f'Scoring "{kind}" from {n} lines on {len(heldout)} held-out lines', 40 + 55 * (i + (j + 1) / 3) / len(sizes))
                ents = evaluate_voice(a.repo, heldout, takes, voice, os.path.join(base_dir, f'{kind}-n{n}'), root, f'compare/{rnd_id}/{kind}-n{n}', full, asr)
                curve.append(dict(lines=n, kind=kind, label=f'{kind}, {n} lines{share}', about=about, summary=summary(ents),
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
                           aligner='phone' if aligner else 'dtw'))
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
