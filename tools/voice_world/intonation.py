"""Sentence intonation and the energy envelope, learned from a speaker's aligned takes.

Each syllable (vowel) gets a pitch level (semitones relative to the line's median), a slope
through the vowel (st/s) and an energy level (dB relative to the line, after the vowel's own
intrinsic loudness), each a linear function of the same few features of the syllable:

  - stress: an accented syllable (primary stress in a content word), a secondary stress; which
    accent of the phrase it is (first, nuclear = last), before the first or after the last;
  - place in the phrase: normalised position (declination), the first, last and second-to-last
    syllable; what ends the phrase (full stop, question, exclamation, comma, other break such as
    "..." or a dash, a breath) on the last syllable and on the nuclear accent;
  - resets: a later phrase of a sentence, a later sentence of the line;
  - genre (plain, news, war, race, advert, weather): accent height, declination and the final
    syllable per genre.

The game computes the same features (src/voice_text.jo voice_syllable_features) and renders the
contour by joining the syllable targets; the fitted weights travel in the voice data file
("tune_pitch", "tune_slope", "tune_energy", "tune_intrinsic"). Phrases are split exactly as the
game splits them (voice_tokens, the breath rule), so the features match.
"""
import re
import numpy as np

GENRES = ['', 'news', 'war', 'race', 'advert', 'weather']          # VoiceStyle.genre values; '' is the plain reading
DATA_GENRE = {'neutral': '', 'contrast': '', 'news': 'news', 'ident': 'news', 'war': 'war', 'race': 'race', 'advert': 'advert',
              'weather': 'weather'}
# phrase-ending tones (VoicePhone.tone in the game)
TONES = {'.': 1, '?': 2, '!': 3, ',': 4, ';': 5, ':': 5, '…': 5, '—': 5, '–': 5}
BREATH, FINAL = 6, 1                # a breath break; the end of a text without punctuation reads as a full stop
NF = 43
VOWELS = {'AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY', 'IH', 'IY', 'OW', 'OY', 'UH', 'UW', 'AX', 'IX', 'AXR', 'IYX'}


def game_lists(repo):
    """VOICE_FUNCTION and VOICE_BREATH_BEFORE from the game's source, so both sides use one list."""
    src = open(repo + '/src/voice_text.jo').read()
    get = lambda name: re.findall(r'"([^"]+)"', re.search(name + r' = \[([^\]]*)\]', src).group(1))
    return set(get('VOICE_FUNCTION')), set(get('VOICE_BREATH_BEFORE'))


def words_and_breaks(text, number_words, function, breath_before):
    """The game's token stream reduced to words and break tones: [(word, content, tone_after)],
    tone_after > 0 where a pause follows the word (voice_tokens and voice_phones' breath rule)."""
    toks = []
    for m in re.finditer(r"([A-Za-z][A-Za-z'é]*)|([0-9]+)|([,.;:!?…—–])", text):
        if m.group(1):
            w = m.group(1).lower().replace('é', 'e').strip("'")
            if w:
                toks.append(w)
        elif m.group(2):
            toks += number_words(int(m.group(2)))
        else:
            toks.append(m.group(3))
    out = []
    since = 0
    for t in toks:
        if t in TONES:
            if out and out[-1][2] == 0:
                out[-1][2] = TONES[t]
                since = 0
            continue
        if since >= 7 and t in breath_before and out and out[-1][2] == 0:
            out[-1][2] = BREATH
            since = 0
        out.append([t, t not in function, 0])
        since += 1
    if out and out[-1][2] == 0:
        out[-1][2] = FINAL
    return out


def syllables(words, phones):
    """Syllables of a take (or a plan) with their features' inputs. words: words_and_breaks();
    phones: [{'p', 'stress', 'wi', 'start', 'end'}] with wi indexing words."""
    sy = []
    for p in phones:
        if p['p'] in VOWELS and 0 <= p.get('wi', -1) < len(words):
            w = words[p['wi']]
            sy.append(dict(p=p['p'], wi=p['wi'], start=p['start'], end=p['end'], content=w[1],
                           stress=p['stress'] if w[1] else 0))
    # phrases: words up to a break
    phrase_of, ph, sent_of, s_i, ph_in_s = [], 0, [], 0, []
    k_in_s = 0
    for i, w in enumerate(words):
        phrase_of.append(ph); sent_of.append(s_i); ph_in_s.append(k_in_s)
        if w[2]:
            ph += 1; k_in_s += 1
            if w[2] in (1, 2, 3):
                s_i += 1; k_in_s = 0
    groups = {}
    for s in sy:
        groups.setdefault(phrase_of[s['wi']], []).append(s)
    for g, ss in groups.items():
        last_word = max(i for i in range(len(words)) if phrase_of[i] == g)
        tone = words[last_word][2] or FINAL
        acc = [k for k, s in enumerate(ss) if s['content'] and s['stress'] == 1]
        n = len(ss)
        for k, s in enumerate(ss):
            s.update(k=k, n=n, tone=tone, phrase_in_sentence=ph_in_s[last_word], sentence=sent_of[last_word],
                     accented=k in acc, first=bool(acc) and k == acc[0], nuclear=bool(acc) and k == acc[-1],
                     before=bool(acc) and k < acc[0], after=bool(acc) and k > acc[-1])
    return sy


def features(s, genre):
    """NF floats for one syllable; the game's voice_syllable_features computes the same."""
    acc = 1.0 if s['accented'] else 0.0
    t = (s['k'] + 0.5) / s['n']
    last = 1.0 if s['k'] == s['n'] - 1 else 0.0
    f = [1.0, acc, 1.0 if s['content'] and s['stress'] == 2 else 0.0, acc * s['first'], acc * s['nuclear'], t,
         1.0 if s['k'] == 0 else 0.0, last, 1.0 if s['k'] == s['n'] - 2 else 0.0]
    f += [last * (s['tone'] == tone) for tone in (1, 2, 3, 4, 5, 6)]
    f += [float(s['nuclear']) * (s['tone'] == tone) for tone in (1, 2, 3, 4, 5, 6)]
    f += [1.0 if s['phrase_in_sentence'] >= 1 else 0.0, 1.0 if s['sentence'] >= 1 else 0.0]
    for g in GENRES:
        on = 1.0 if genre == g else 0.0
        f += [on * acc, on * t, on * last]
    f += [float(s['after']), float(s['before'])]
    assert len(f) == NF
    return f


def ridge(X, y, lam, prior=None):
    """Weights minimising |Xw - y|^2 + lam |w - prior|^2 (the intercept unpenalised)."""
    X = np.asarray(X, float); y = np.asarray(y, float)
    P = lam * np.eye(X.shape[1]); P[0, 0] = 1e-6
    w0 = np.zeros(X.shape[1]) if prior is None else np.asarray(prior, float)
    return np.linalg.solve(X.T @ X + P, X.T @ y + P @ w0)


def render(sy, levels, slopes, times):
    """Contour (st) at the given frame times from syllable targets: within a vowel its level plus
    its slope about the vowel's middle; between vowels a cosine join from one vowel's end value to
    the next one's start value. The game does the same (voice_pitch)."""
    out = np.zeros(len(times))
    if not sy:
        return out
    mids = [(s['start'] + s['end']) / 2 for s in sy]
    half = [max(0.01, (s['end'] - s['start']) / 2) for s in sy]
    at = lambda i, t: levels[i] + slopes[i] * float(np.clip(t - mids[i], -half[i], half[i]))
    j = 0
    for n, t in enumerate(times):
        while j + 1 < len(sy) and t > sy[j]['end']:
            j += 1
        s = sy[j]
        if s['start'] <= t <= s['end'] or (j == 0 and t < s['start']) or (j == len(sy) - 1 and t > s['end']):
            out[n] = at(j, t)
        else:                        # between vowel j-1's end and vowel j's start
            a, b = sy[j - 1]['end'], s['start']
            u = float(np.clip((t - a) / max(1e-3, b - a), 0, 1))
            w = 0.5 - 0.5 * np.cos(np.pi * u)
            out[n] = (1 - w) * at(j - 1, a) + w * at(j, b)
    return out


def st(f):
    return 12 * np.log2(np.maximum(f, 1.0) / 100.0)


def take_rows(line, phones, f0, c0, words):
    """Per-syllable targets of one take: pitch level (st re the take's median), slope (st/s) and
    energy (log power re the take's median vowel)."""
    sy = syllables(words, phones)
    v = f0 > 0
    if v.sum() < 20 or len(sy) < 2:
        return []
    ref = float(np.median(st(f0[v])))
    rows = []
    for s in sy:
        fr = np.arange(int(s['start'] / 0.005), max(int(s['start'] / 0.005) + 1, int(s['end'] / 0.005)))
        fr = fr[fr < len(f0)]
        vv = fr[f0[fr] > 0]
        lvl = float(np.median(st(f0[vv])) - ref) if len(vv) >= 2 else np.nan
        if np.isfinite(lvl) and abs(lvl) >= 9:
            lvl = np.nan                                   # creak or an octave slip
        slope = float(np.clip(np.polyfit(vv * 0.005, st(f0[vv]), 1)[0], -60, 60)) if len(vv) >= 5 else np.nan
        rows.append(dict(s, lvl=lvl, slope=slope, e=float(np.mean(c0[fr])) if len(fr) else np.nan))
    es = [r['e'] for r in rows if np.isfinite(r['e'])]
    m = float(np.median(es)) if es else 0.0
    for r in rows:
        r['e'] -= m
    return rows


def fit(items, repo, number_words, phones_order, lam=10.0):
    """items: [(line, aligned phones, analysis {'f0', 'mcep'})]. Returns the weights the voice file
    carries: tune_pitch, tune_slope, tune_energy (NF each) and tune_intrinsic (per phone)."""
    function, breath = game_lists(repo)
    data = []
    for line, phones, an in items:
        words = words_and_breaks(line['text'], number_words, function, breath)
        for r in take_rows(line, phones, an['f0'], an['mcep'][:, 0], words):
            data.append((r, DATA_GENRE.get(line['genre'], '')))
    if len(data) < 40:
        return None
    intr = {}
    for r, g in data:
        if np.isfinite(r['e']):
            intr.setdefault(r['p'], []).append(r['e'])
    intr = {p: float(np.mean(v)) for p, v in intr.items() if len(v) >= 3}
    X = np.array([features(r, g) for r, g in data])
    out = {}
    for key, y in (('pitch', [r['lvl'] for r, _ in data]), ('slope', [r['slope'] for r, _ in data]),
                   ('energy', [r['e'] - intr.get(r['p'], 0.0) for r, _ in data])):
        y = np.array(y, float)
        ok = np.isfinite(y)
        out[key] = [round(float(v), 4) for v in ridge(X[ok], y[ok], lam)]
    out['intrinsic'] = [round(intr.get(p, 0.0), 4) for p in phones_order]
    out['syllables'] = len(data)
    return out


def genre_tilts(items, order=25, shrink=2.0):
    """Each genre's vocal effort as the speaker's own spectral change: per vowel phone, the mean
    mel-cepstrum (c1 up) of the genre's takes less that of the plain reads, averaged over phones
    by how often both have them; shrunk toward none by the number of takes (n / (n + shrink))."""
    acc = {}
    takes = {}
    for line, phones, an in items:
        g = DATA_GENRE.get(line['genre'], '')
        takes[g] = takes.get(g, 0) + 1
        for p in phones:
            if p['p'] not in VOWELS:
                continue
            fr = np.arange(int(p['start'] / 0.005), int(p['end'] / 0.005))
            fr = fr[(fr < len(an['f0']))]
            fr = fr[an['f0'][fr] > 0]
            if len(fr):
                a = acc.setdefault(g, {}).setdefault(p['p'], [np.zeros(order), 0])
                a[0] += an['mcep'][fr, :order].sum(0); a[1] += len(fr)
    plain = acc.get('', {})
    out = {}
    for g, ph in acc.items():
        if g == '':
            continue
        diff, wsum = np.zeros(order), 0.0
        for p, (s, n) in ph.items():
            if p in plain and n >= 10 and plain[p][1] >= 10:
                w = min(n, plain[p][1])
                diff += w * (s / n - plain[p][0] / plain[p][1]); wsum += w
        if wsum > 0:
            v = diff / wsum * takes[g] / (takes[g] + shrink)
            v[0] = 0.0                                     # loudness is the energy model's
            out[g] = [round(float(x), 4) for x in v]
    return out
