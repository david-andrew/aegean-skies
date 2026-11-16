"""Phone-level forced alignment of a speaker's takes, labelling what was actually said.

An acoustic phone classifier gives log-probabilities of 39 ARPAbet phones and silence every
10 ms (the Charsiu wav2vec2 frame classifier, charsiu/en_w2v2_fc_10ms, run from a local scratch
copy; analysis only, never shipped). Our own Viterbi then walks the line's pronunciation:

  - optional silence between words;
  - each vowel may be realised as a neighbouring vowel or reduced to schwa (an accent or a
    weak form), each consonant as a common substitute (TH as T or F, DH as D, NG as N, a final
    S as Z, ...), at a small penalty per frame, so an accented or changed phone is labelled as
    spoken rather than forced to the dictionary form;
  - some phones may be dropped (final T/D in a cluster, H, post-vocalic R), at a penalty.

Output per take: phones with start/end in seconds of the trimmed take (the same trim the
analysis uses), the dictionary phone, the spoken phone, stress and a confidence.
"""
import json, os, re
import numpy as np

VOWELS = ['AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY', 'IH', 'IY', 'OW', 'OY', 'UH', 'UW']
# Vowels a speaker may produce in place of the dictionary's (neighbours in vowel space, plus
# schwa for reduction).
VOWEL_VARIANTS = {
    'AA': ['AO', 'AH', 'AE'], 'AE': ['EH', 'AA', 'AH'], 'AH': ['AA', 'IH', 'ER', 'UH'], 'AO': ['AA', 'OW', 'AH'],
    'AW': ['AA', 'AO'], 'AY': ['AA', 'AH'], 'EH': ['AE', 'IH', 'EY', 'AH'], 'ER': ['AH', 'EH'], 'EY': ['EH', 'IY'],
    'IH': ['IY', 'EH', 'AH'], 'IY': ['IH', 'EY'], 'OW': ['AO', 'UH', 'AH'], 'OY': ['AO'], 'UH': ['UW', 'AH'], 'UW': ['UH', 'OW']}
CONS_VARIANTS = {'TH': ['T', 'F', 'S'], 'DH': ['D', 'Z', 'V'], 'NG': ['N'], 'Z': ['S'], 'S': ['Z'], 'V': ['F', 'W'], 'W': ['V'],
                 'T': ['D'], 'D': ['T'], 'R': ['ER'], 'ZH': ['SH', 'JH'], 'JH': ['ZH', 'CH'], 'CH': ['SH']}
DROPPABLE = {'HH', 'R', 'T', 'D'}
PENALTY = 0.35          # nats per frame for a non-dictionary realisation
DROP_PENALTY = 4.0      # nats for leaving a phone out
REDUCED = {'AX': ('AH', 0), 'IX': ('IH', 0), 'AXR': ('ER', 0), 'IYX': ('IY', 0)}


class Aligner:
    def __init__(self, model_dir, vocab_path):
        import torch
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Config
        torch.set_num_threads(1)
        self.torch = torch
        self.vocab = json.load(open(vocab_path))
        cfg = json.load(open(os.path.join(model_dir, 'config.json')))
        cfg.pop('gradient_checkpointing', None)
        self.model = Wav2Vec2ForCTC(Wav2Vec2Config(**cfg)).eval()
        ck = torch.load(os.path.join(model_dir, 'pytorch_model.bin'), map_location='cpu', weights_only=True)
        # the checkpoint predates weight-norm parametrizations: map the two legacy keys, load strictly
        st = {k.replace('.conv.weight_g', '.conv.parametrizations.weight.original0').replace('.conv.weight_v', '.conv.parametrizations.weight.original1'): v
              for k, v in ck.items()}
        res = self.model.load_state_dict(st, strict=True)
        assert not res.missing_keys and not res.unexpected_keys

    def logp(self, x16):
        x = (x16 - x16.mean()) / (x16.std() + 1e-7)
        with self.torch.inference_mode():
            out = self.model(self.torch.from_numpy(x.astype(np.float32))[None]).logits.log_softmax(-1)[0].numpy()
        return out

    def _word_states(self, wi, w, pron):
        out = []
        for k, ph in enumerate(pron):
            base, stress = REDUCED.get(ph, (re.sub(r'\d', '', ph), int(ph[-1]) if ph[-1].isdigit() else 0))
            if base not in self.vocab:
                continue
            alts = (VOWEL_VARIANTS.get(base, []) if base in VOWELS else CONS_VARIANTS.get(base, []))
            final = k == len(pron) - 1
            skip = base in DROPPABLE and (base != 'T' and base != 'D' or (final and k > 0 and re.sub(r'\d', '', pron[k - 1]) not in VOWELS))
            out.append(dict(p=base, dict_p=base, choices=[base] + [a for a in alts if a in self.vocab], stress=stress, wi=wi, word=w,
                            skip=skip, reduced=ph in REDUCED or (base in VOWELS and stress == 0)))
        return out

    def _emissions(self, lp, states):
        E = np.empty((len(lp), len(states)))
        for j, s in enumerate(states):
            ids = [self.vocab[c] for c in s['choices']]
            e = lp[:, ids[0]]
            if len(ids) > 1:
                e = np.maximum(e, lp[:, ids[1:]].max(1) - PENALTY)
            E[:, j] = e
        return E

    def align_choosing(self, x16, words):
        """words: [(word, [pronunciation, alternative, ...])]. Each word's alternatives (the
        dictionary's other pronunciations, e.g. "gentlemen" with and without its T) are scored on
        the frames the first pass gave that word; the best one is aligned in a second pass.
        Returns (phones, the pronunciation chosen for each word)."""
        lp = self.logp(x16)
        first = self.align(x16, [(w, alts[0]) for w, alts in words], lp=lp)
        chosen = []
        for wi, (w, alts) in enumerate(words):
            ps = [p for p in first if p['wi'] == wi]
            if len(alts) < 2 or not ps:
                chosen.append(alts[0]); continue
            a = int(round((ps[0]['start'] - 0.0075) / 0.01)); b = int(round((ps[-1]['end'] - 0.0075) / 0.01))
            seg = lp[max(0, a):min(len(lp), b)]
            best, best_score = alts[0], -np.inf
            for pron in alts:
                st = self._word_states(wi, w, pron)
                if not st or len(st) > len(seg):
                    continue
                E = self._emissions(seg, st)
                cost = np.array([DROP_PENALTY if s['skip'] else np.inf for s in st])
                path = viterbi(E, cost)
                score = float(E[np.arange(len(seg)), path].sum()) - sum(DROP_PENALTY for j, s in enumerate(st) if j not in set(path.tolist()))
                if score > best_score + 1e-6:
                    best, best_score = pron, score
            chosen.append(best)
        return self.align(x16, list(zip([w for w, _ in words], chosen)), lp=lp), chosen

    def align(self, x16, words, lp=None):
        """words: [(word, [ARPAbet with stress digits or reduced labels])]. Returns phone dicts."""
        lp = self.logp(x16) if lp is None else lp
        T = len(lp)
        sil = self.vocab['[SIL]']
        states = [dict(p='pau', dict_p='pau', choices=['[SIL]'], stress=0, wi=-1, skip=False)]
        for wi, (w, pron) in enumerate(words):
            states += self._word_states(wi, w, pron)
            states.append(dict(p='pau', dict_p='pau', choices=['[SIL]'], stress=0, wi=-1, skip=True))
        states[-1]['skip'] = False
        n = len(states)
        if n > T:
            raise ValueError('take shorter than its phone sequence')
        # emission per state: dictionary phone, or the best variant minus a penalty
        E = self._emissions(lp, states)
        cost = np.array([(0.0 if s['p'] == 'pau' else DROP_PENALTY) if s['skip'] else np.inf for s in states])
        path = viterbi(E, cost)
        out = []
        for j in np.unique(path):
            ix = np.nonzero(path == j)[0]
            s = states[j]
            ids = [self.vocab[c] for c in s['choices']]
            scores = [lp[ix, i].mean() - (0 if k == 0 else PENALTY) for k, i in enumerate(ids)]
            spoken = s['choices'][int(np.argmax(scores))]
            spoken = 'pau' if spoken == '[SIL]' else spoken
            label = spoken
            if spoken in ('AH', 'IH', 'ER', 'IY') and s.get('reduced') and s['stress'] == 0:
                label = {'AH': 'AX', 'IH': 'IX', 'ER': 'AXR', 'IY': 'IYX'}[spoken]
            out.append(dict(p=label, spoken=spoken, dictionary=s['dict_p'], stress=s['stress'], wi=s['wi'], word=s.get('word', ''),
                            start=0.0075 + ix[0] * 0.01, end=0.0075 + (ix[-1] + 1) * 0.01,
                            confidence=float(np.exp(lp[ix, self.vocab.get(spoken if spoken != 'pau' else '[SIL]', sil)]).mean())))
        out[0]['start'] = 0.0
        out[-1]['end'] = len(x16) / 16000
        # merge consecutive pauses (an optional silence state next to the edge ones)
        merged = []
        for p in out:
            if merged and p['p'] == 'pau' and merged[-1]['p'] == 'pau':
                merged[-1]['end'] = p['end']
            else:
                merged.append(p)
        return merged


def viterbi(E, cost):
    """Monotonic left-to-right path over states; state j may be passed over at cost[j] (inf: never;
    an optional pause between words: free)."""
    T, n = E.shape
    NEG = -1e18
    dp = np.full((T, n), NEG)
    back = np.zeros((T, n), np.int8)
    dp[0, 0] = E[0, 0]
    skip_cost = np.where(np.isfinite(cost), cost, -NEG)
    for t in range(1, T):
        prev = dp[t - 1]
        stay = prev
        move = np.full(n, NEG); move[1:] = prev[:-1]
        jump = np.full(n, NEG); jump[2:] = prev[:-2] - skip_cost[1:-1]
        # free skip of an inter-word pause
        best = np.maximum(np.maximum(stay, move), jump)
        b = np.where(best == stay, 0, np.where(best == move, 1, 2)).astype(np.int8)
        dp[t] = best + E[t]
        back[t] = b
    j = n - 1
    path = np.zeros(T, np.int64)
    for t in range(T - 1, -1, -1):
        path[t] = j
        j -= back[t, j]
    return path


# ------------------------------------------------------------------ pronouncing a script line
WEAK = {"a": "AX", "an": "AX N", "the": "DH AX", "and": "AX N D", "of": "AX V", "to": "T AX", "for": "F AXR", "from": "F R AX M",
        "at": "AX T", "as": "AX Z", "was": "W AX Z", "were": "W AXR", "are": "AXR", "can": "K AX N", "has": "HH AX Z",
        "have": "HH AX V", "had": "HH AX D", "them": "DH AX M", "than": "DH AX N", "but": "B AX T", "or": "AXR", "your": "Y AXR",
        "her": "HH AXR", "his": "HH IX Z", "is": "IX Z", "it": "IX T", "in": "IX N", "with": "W IX DH", "will": "W IX L",
        "be": "B IYX", "he": "HH IYX", "she": "SH IYX", "we": "W IYX", "me": "M IYX", "been": "B IX N", "into": "IX N T AX"}
ONES = 'zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split()
TENS = ' ten twenty thirty forty fifty sixty seventy eighty ninety'.split(' ')


def number_words(n):
    if n < 20:
        return [ONES[n]]
    if n < 100:
        return [TENS[n // 10]] + ([ONES[n % 10]] if n % 10 else [])
    if n < 1000:
        return [ONES[n // 100], 'hundred'] + (['and'] + number_words(n % 100) if n % 100 else [])
    return number_words(n // 1000) + ['thousand'] + (number_words(n % 1000) if n % 1000 else [])


def add_s(stem):
    """The -s ending: a vowel and Z after a sibilant, S after a voiceless stop or fricative, else Z."""
    last = re.sub(r'\d', '', stem[-1])
    if last in ('S', 'Z', 'SH', 'ZH', 'CH', 'JH'):
        return stem + ['IH0', 'Z']
    return stem + (['S'] if last in ('P', 'T', 'K', 'F', 'TH') else ['Z'])


class Pronouncer:
    def __init__(self, extra=None):
        import cmudict
        import lts
        from pack import MANUAL
        self.d = cmudict.dict()
        self.manual = {k: v.split() for k, v in MANUAL.items()}
        self.manual.update({k: v.split() for k, v in (extra or {}).items()})
        self.lts = lts

    def word(self, w):
        if w in WEAK:
            return WEAK[w].split()
        if w in self.manual:
            return self.manual[w]
        if w in self.d:
            return self.d[w][0]
        # plural and possessive endings on a known stem, as the game does (voice_text.jo voice_pronounce)
        for suf, longer in (("'s", 2), ('s', 3), ('es', 4)):
            stem = w[:-len(suf)]
            if w.endswith(suf) and len(w) > longer and (stem in self.manual or stem in self.d):
                return add_s(self.manual[stem] if stem in self.manual else self.d[stem][0])
        # another form of a dictionary word (a British spelling, un-/re-, a compound...), as the
        # voice's lexicon has it; the rules read only names (Greek-style)
        from pack import derive
        d = derive(w, self.d)
        if d:
            return d
        return self.lts.pronounce(w)

    def alternatives(self, w):
        """The word's pronunciation first, then the dictionary's other ones."""
        out = [self.word(w)]
        if w not in WEAK and w not in self.manual and w in self.d:
            for p in self.d[w][1:]:
                if p not in out:
                    out.append(p)
        return out

    def line_alternatives(self, text):
        return [(w, self.alternatives(w)) for w, _ in self.line(text)]

    def line(self, text):
        out = []
        for tok in re.findall(r"[A-Za-z][A-Za-z'é]*|[0-9]+", text):
            if tok[0].isdigit():
                for w in number_words(int(tok)):
                    out.append((w, self.word(w)))
            else:
                w = tok.lower().replace('é', 'e').strip("'")
                out.append((w, self.word(w)))
        return out
