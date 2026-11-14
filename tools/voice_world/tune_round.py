"""One tuning round on whatever the user has recorded so far (run by the voice studio's "Tune"
button, or by hand):

  python tune_round.py --root VOICE_USER_DIR --repo REPO --prior-data NARRATOR.z --prior-fit FIT.json
                       [--round rN] [--fractions 0.25,0.5,1] [--listen 2]

1. Pool: every accepted take of a training line; the held-out lines with accepted takes are only
   ever scored, never fitted.
2. Baseline: if no round exists yet, round r0 scores the prior (narrator) voice on the held-out set.
3. Alignment: each new take is aligned to a synthesis of its line (evaluate.py's DTW aligner,
   which carries the synthesis's phone boundaries onto the recording) and analysed WORLD-style.
   Both are cached per take, so a re-tune only aligns what is new.
4. Nested random subsets of the pool (a fixed shuffle, so 25% is inside 50% inside 100%): for each,
   fit diphone units, durations and intonation to the user's takes and pack a voice file. Where
   the subset is still too small for a part of the model, that part falls back to the prior's
   (named in the round's note).
5. Each voice synthesizes the held-out lines and is scored; the full pool's voice provides the
   Compare entries (recording, synthesis, radio), the smaller ones a learning curve and a couple
   of listenable lines.
Progress goes to VOICE_USER_DIR/tune/progress.json. Everything stays in VOICE_USER_DIR; nothing
derived from the recordings enters the repository.
"""
import argparse, json, math, os, random, re, sys, time
import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import world_analysis as wa
import evaluate as ev
import build_units as bu
import pack
import prosody_fit as pf

RAW = {'AX': ('AH', 0), 'IX': ('IH', 0), 'AXR': ('ER', 0), 'IYX': ('IY', 0)}
STAGES = ['baseline', 'align', 'fit', 'evaluate', 'publish']


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

    def finish(self, state, message):
        self.state.update(state=state, step=message, finished=time.strftime('%Y-%m-%dT%H:%M:%S'), percent=100 if state == 'done' else self.state['percent'])
        self.set(self.state['stage'], message, self.state['percent'])


def words_of(text):
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9']*[,.;:!?]?", text)


def align_take(root, repo, line, take, syn_entry, cache):
    """Aligned phones (recording time) and the analysis of the trimmed take, cached."""
    key = f"{line['id']}-{take['n']:02d}"
    jpath = os.path.join(cache, key + '.json')
    npath = os.path.join(cache, key + '.npz')
    if os.path.exists(jpath) and os.path.exists(npath):
        return json.load(open(jpath)), np.load(npath)
    rec = ev.trim(ev.load16(os.path.join(root, take['file'])))
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
        # word index: the synthesis plan marks each word's last phone
        wi = 0
        for p in al['phones']:
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


def fit_voice(subset, aligned_dir, work, repo, prior_fit, out):
    """Units and prosody from the subset; thin parts fall back to the prior. Returns notes."""
    os.makedirs(work, exist_ok=True)
    phones_json, words_json, npz, speakers = corpus_files(subset, aligned_dir, work)
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
        shared = [l for l in d['intercept_ms'] if counts.get(l, 0) >= 5 and l in prior_ms]
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
            fit['superposition'] = pf.fit_superposition(data)
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
    lex, _ = pack.lexicon(repo)
    model = pack.model_numbers(fit, fit['superposition'])
    pack.pack(units, lex, out, model)
    notes.insert(0, f'{len(units)} diphone units from {len(subset)} lines')
    return notes, len(units)


def evaluate_voice(repo, heldout, takes, data, outdir, root, rel_base, full):
    syn = ev.synthesize(repo, heldout, os.path.join(outdir, 'synth'), data=data, radio=full)
    entries = []
    for l in heldout:
        rec = ev.trim(ev.load16(os.path.join(root, takes[l['id']]['file'])))
        dry, radio, ph = syn[l['id']]
        s = ev.trim(ev.load16(dry))
        m, _ = ev.score(rec, s, ph)
        e = dict(line=l['id'], text=l['text'], genre=l['genre'], metrics=m)
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


KEYS = ['mcd_db', 'f0_rmse_st', 'f0_rmse_st_shape', 'f0_corr', 'energy_corr', 'dur_err', 'voicing_err', 'rate_rec', 'rate_syn']


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
    a = ap.parse_args()
    root = a.root
    os.makedirs(os.path.join(root, 'compare'), exist_ok=True)
    idx_path = os.path.join(root, 'compare', 'index.json')
    idx = json.load(open(idx_path)) if os.path.exists(idx_path) else dict(rounds=[])
    nums = [int(r['id'][1:]) for r in idx['rounds'] if re.match(r'^r\d+$', r['id'])]
    rnd_id = a.round or f'r{max([0] + nums) + 1}'
    prog = Progress(root, rnd_id)
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
        # 1. baseline
        if not any(r['id'] == 'r0' for r in idx['rounds']):
            prog.set('baseline', f'Scoring the starting voice on {len(heldout)} held-out lines', 2)
            out = os.path.join(root, 'compare', 'r0')
            ents = evaluate_voice(a.repo, heldout, takes, a.prior_data, out, root, 'compare/r0', True)
            publish(root, dict(id='r0', label='Round 0: the starting (narrator) voice', note='Before any fitting to your voice.',
                               lines=0, summary=summary(ents), entries=ents, curve=[dict(lines=0, label='starting voice', summary=summary(ents))]))
        # 2. align new takes
        cache = os.path.join(root, 'tune', 'cache')
        os.makedirs(cache, exist_ok=True)
        todo = [l for l in pool if not os.path.exists(os.path.join(cache, f"{l['id']}-{takes[l['id']]['n']:02d}.json"))]
        if todo:
            prog.set('align', f'Synthesizing {len(todo)} new lines to align against', 8)
            syn = ev.synthesize(a.repo, todo, os.path.join(root, 'tune', 'align-synth'), data=a.prior_data, radio=False)
        aligned = {}
        for k, l in enumerate(pool):
            if l in todo:
                prog.set('align', f"Aligning take {k + 1} of {len(pool)} ({l['id']})", 10 + 30 * k / len(pool))
                align_take(root, a.repo, l, takes[l['id']], syn[l['id']], cache)
            key = f"{l['id']}-{takes[l['id']]['n']:02d}"
            aligned[l['id']] = (json.load(open(os.path.join(cache, key + '.json'))), dict(np.load(os.path.join(cache, key + '.npz'))))
        # 3-4. nested subsets
        order = list(pool)
        random.Random(20261114).shuffle(order)
        fractions = sorted(set(float(x) for x in a.fractions.split(',')))
        prior_fit = json.load(open(a.prior_fit))
        listen = heldout[:a.listen]
        curve, notes_full, entries_full = [], [], []
        base_dir = os.path.join(root, 'compare', rnd_id)
        for i, fr in enumerate(fractions):
            n = max(a.min_lines, int(math.ceil(fr * len(order)))) if fr < 1 else len(order)
            n = min(n, len(order))
            if any(c['lines'] == n for c in curve):
                continue
            subset = [(l, aligned[l['id']][0], aligned[l['id']][1]) for l in order[:n]]
            full = n == len(order)
            label = f'{n} lines' + (' (all)' if full else f' ({round(100 * n / len(order))}%)')
            prog.set('fit', f'Fitting a voice to {label}', 40 + 50 * i / len(fractions))
            voice = os.path.join(root, 'voices', f'{rnd_id}-{n}.z')
            os.makedirs(os.path.dirname(voice), exist_ok=True)
            notes, nunits = fit_voice(subset, None, os.path.join(root, 'tune', 'work', f'{rnd_id}-{n}'), a.repo, prior_fit, voice)
            prog.set('evaluate', f'Scoring the {label} voice on {len(heldout)} held-out lines', 45 + 50 * i / len(fractions))
            sub = 'full' if full else f'n{n}'
            ents = evaluate_voice(a.repo, heldout if full else heldout, takes, voice, os.path.join(base_dir, sub), root,
                                  f'compare/{rnd_id}/{sub}', full)
            curve.append(dict(lines=n, label=label, units=nunits, summary=summary(ents), voice=os.path.relpath(voice, root),
                              listen={e['line']: e['synth'] for e in ents if e['line'] in [x['id'] for x in listen]}))
            if full:
                notes_full, entries_full = notes, ents
        prog.set('publish', 'Publishing the round', 97)
        for e in entries_full:
            e['subsets'] = [dict(label=c['label'], synth=c['listen'][e['line']]) for c in curve if e['line'] in c['listen'] and c['lines'] != len(order)]
        r0 = next((r for r in json.load(open(idx_path))['rounds'] if r['id'] == 'r0'), None)
        publish(root, dict(id=rnd_id, label=f'Round {rnd_id[1:]}: fitted to {len(order)} of your lines',
                           note='; '.join(notes_full), lines=len(order), summary=summary(entries_full), entries=entries_full,
                           curve=([dict(lines=0, label='starting voice', summary=r0['summary'])] if r0 else []) + curve,
                           voice=curve[-1]['voice'] if curve else ''))
        prog.finish('done', f'Round {rnd_id[1:]} is ready on the Compare tab')
    except Exception as e:
        import traceback
        traceback.print_exc()
        prog.finish('failed', f'Tuning stopped: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
