"""The part balance: every part of every piece at a reasonable loudness against the others, the
tune forward and what is behind it heard, without a human listener.

For each piece in the catalogue (tools/music_pack.py PIECES):

1. Parts. The arranged, interpreted notes (music_pack.build) are split into parts: an instrument
   on its staff (music_pack.part_of; a keyboard's or a harp's staves are one part, the percussion
   one). A piece with one pitched part (a piano alone) has nothing to balance.
2. Measure. Each part is rendered alone, whole, by the game's own synthesizer (tools/music_stems.jo
   playing a scratch-packed score, in the piece's hall and at its level), and its loudness taken
   by ITU-R BS.1770: K-weighted, in 400 ms blocks, gated, so only the span where the part plays
   counts.
3. Roles, from the notes, in windows of a few seconds (a part's role changes through a piece):
   the melody (the staff marked as the melody in music_performance.CONFIG wherever it plays
   moving notes; otherwise the part holding the top line with notes that move), a doubling of it (the same
   notes at the unison or the octave), the bass (the lowest line, low), a counter-melody (one
   line, moving by step, in its own rhythm), the harmony (the rest), percussion.
4. Targets, in two steps, one gain per part for the whole piece. Both leave alone what is
   already reasonable and bring what is not just inside: the score's own dynamics stand.
   Everything that plays is heard. In each window every accompanying part is compared with the
   median of the parts accompanying with it, after its role's place (SHAPE_LU: the bass and a
   counter-melody level, the inner harmony a little under them; a part lying in the melody's own
   register, where it masks the tune, a little further under, REGISTER_LU). A part that sits, on
   the median of its windows, more than SHAPE_FLOOR_LU under is raised to that; nothing is
   lowered. A doubling is compared with the part it doubles: more than DOUBLING_FLOOR_LU under
   it, it is raised to that. A part that is the tune in some windows is moved by the share of
   the windows it is not.
   The tune over the rest. The melody's partial loudness (with its doublings) over everything
   pitched behind it: loudness as the ear sums it across critical bands, each counted only above
   what the other masks there (tools/music_balance.py's measure, Moore and Glasberg's form). It is
   the measure the pieces balanced by ear agree on (--calibrate): the Adagietto -2.3 and the
   orchestral Gymnopedie -0.1, where the plain loudness difference puts them 10 LU apart (a
   single line against chords spread over many bands; a bright plucked tune over a dull bass).
   Outside MELODY_PARTIAL, the parts that carry the tune and the parts behind it are moved apart
   or together until it is MELODY_INSIDE within the nearer edge, each part by its share of
   carrying the tune. Two limits: the parts behind the tune, together, are never raised nearer
   than MELODY_FLOOR_LU under the tune's own plain loudness, and a tune under its accompaniment
   is raised by at most MELODY_RAISE_DB (a buried top line is as often not the tune).
   Percussion is measured and left where the score put it.
5. Apply and verify. The gains are made loudness-neutral (the mix's gated loudness is unchanged),
   the balanced piece is rendered whole and trimmed so its BS.1770 loudness equals the unbalanced
   piece's on the catalogue's own meter (tools/music_level.py's: the piece's level in levels.json
   stays valid), and the melody's masked partial
   loudness over the rest (tools/music_balance.py's measure) is reported before and after.

Writes data/music/part-balance.json (read by tools/music_pack.py, which applies the gains as mix
gains at pack time and records them in data/music/performance.json; a piece whose notes have
changed since is reported there as stale) and a report. Pieces balanced by hand
(music_pack.HAND_SET_BALANCE), and the four that already had a balance in performance.json
(music_pack.kept_balance), are measured and reported, never changed.

  python tools/music_part_balance.py [piece ...] [--stems binary] [--jobs 2] [--work dir]
                                     [--report file.md] [--no-verify] [--calibrate]
  then: python tools/music_pack.py
  (the binary: sloppy build tools/music_stems.jo --release -o stems; without it, it is built)
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse, json, math, os, subprocess, sys, tempfile
import numpy as np
from scipy.io import wavfile
from scipy.signal import lfilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parents[1]
RATE = 16000
STEP = 0.05                         # the grid the notes are read on, seconds
WINDOW = 4.0                        # a role is held for about a phrase: seconds
FRESH = 2.0                         # a top note is the tune while it is this new (a held pedal is not)
# The place of each accompanying role, in loudness units: the bass firm, a counter-melody as
# near, the inner harmony a little under the bass.
SHAPE_LU = {'bass': 0.0, 'counter-melody': 0.0, 'harmony': -2.0}
SHAPE_FLOOR_LU = 8.0                # an accompanying part further under the others' median than this is raised to it
DOUBLING_FLOOR_LU = 6.0             # a doubling further under the part it doubles than this is raised to it
# Masking: a part within REGISTER_NEAR semitones of the melody sits this much further under,
# falling to nothing REGISTER_FAR semitones away (a bass two octaves down masks little of the tune).
REGISTER_LU, REGISTER_NEAR, REGISTER_FAR = 1.5, 7.0, 19.0
# The melody's partial loudness over the rest (10 per doubling of loudness). The pieces balanced
# by ear measure -2.2 (the Adagietto) and -0.6 (the orchestral Gymnopedie); the earlier automatic
# balance set +3 (Adelita, Ave Maria, El Choclo, the Magnetic Rag, heard since). A piece inside
# the band is left; one outside is brought MELODY_INSIDE within its nearer edge (from above to
# +3: the melody stays forward; from below to -1.5, between the two set by ear).
MELODY_PARTIAL = (-2.5, 4.0)
MELODY_INSIDE = 1.0
# Whatever the partial loudness says, the parts behind the tune, together, are never raised nearer
# than this under the tune's own plain (K-weighted) loudness: a dull bass carries more energy than
# it sounds, but only so far; the melody stays forward by any measure (and where the pieces the
# partial loudness does settle come out: +2 to +5).
MELODY_FLOOR_LU = 2.0
MELODY_RAISE_DB = 4.0               # a tune under its accompaniment is raised by no more than this
MELODY_LEVERAGE = 0.3               # LU per dB: under this no part carries the tune clearly enough to move it
MAX_GAIN_DB = 20.0                  # the balance never moves a part by more than this
SUSPICIOUS_DB = 8.0                 # and a move past this is flagged
SETTLED_DB = 0.75                   # every part already within this: left as it is
ROLES = ['melody', 'doubling', 'counter-melody', 'harmony', 'bass', 'percussion']
PERCUSSION = (11, 12)
ABSOLUTE_GATE = 10 ** ((-70 + 0.691) / 10)
BAND_EDGES = [20, 100, 200, 300, 400, 510, 630, 770, 920, 1080, 1270, 1480, 1720, 2000, 2320, 2700, 3150, 3700, 4400,
              5300, 6400, 7990]


# ---------------- loudness ----------------

def k_weighting(rate):
    """BS.1770's K-weighting for any sample rate (the standard's two filters, re-derived)."""
    f0, gain, q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
    k = math.tan(math.pi * f0 / rate); vh = 10 ** (gain / 20); vb = vh ** 0.4996667741545416
    a0 = 1 + k / q + k * k
    shelf = ([(vh + vb * k / q + k * k) / a0, 2 * (k * k - vh) / a0, (vh - vb * k / q + k * k) / a0],
             [1.0, 2 * (k * k - 1) / a0, (1 - k / q + k * k) / a0])
    f0, q = 38.13547087602444, 0.5003270373238773
    k = math.tan(math.pi * f0 / rate); a0 = 1 + k / q + k * k
    high = ([1.0, -2.0, 1.0], [1.0, 2 * (k * k - 1) / a0, (1 - k / q + k * k) / a0])
    return shelf, high


def k_weighted(x, rate=RATE):
    shelf, high = k_weighting(rate)
    return lfilter(*high, lfilter(*shelf, x))


def block_powers(y, rate=RATE):
    """Mean square of a K-weighted signal in 400 ms blocks, 100 ms apart."""
    block, hop = int(0.4 * rate), int(0.1 * rate)
    if len(y) < block: y = np.concatenate([y, np.zeros(block - len(y))])
    c = np.concatenate([[0.0], np.cumsum(y * y)])
    starts = np.arange(0, len(y) - block + 1, hop)
    return (c[starts + block] - c[starts]) / block


def gated_lufs(powers):
    """BS.1770 integrated loudness from block powers: the absolute and the relative gate."""
    kept = powers[powers > ABSOLUTE_GATE]
    if len(kept) == 0: return -70.0
    relative = kept.mean() / 10
    kept = powers[(powers > ABSOLUTE_GATE) & (powers > relative)]
    return float(-0.691 + 10 * np.log10(kept.mean() + 1e-30))


def band_powers(y, rate=RATE, n=2048):
    """Per frame, a K-weighted signal's power in each critical band."""
    if len(y) < 2 * n: y = np.concatenate([y, np.zeros(2 * n - len(y))])
    window = np.hanning(n); freqs = np.fft.rfftfreq(n, 1 / rate)
    edges = np.searchsorted(freqs, BAND_EDGES)
    out = np.zeros(((len(y) - n) // (n // 2), len(BAND_EDGES) - 1), np.float32)
    for k in range(len(out)):
        spec = np.abs(np.fft.rfft(y[k * n // 2:k * n // 2 + n] * window)) ** 2
        out[k] = np.add.reduceat(spec, edges[:-1])[:len(BAND_EDGES) - 1]
    return out


# ---------------- the parts and their roles ----------------

def split_parts(notes):
    """{part: its notes}, in score order (the first staff first)."""
    import music_pack as mp
    parts = {}
    for n in sorted(notes, key=lambda n: (n[6], n[3], n[0])): parts.setdefault(mp.part_of(n), []).append(n)
    return parts


def read_roles(parts, length, melody_tracks=()):
    """Each part's role in each window, from the notes: (roles [part][window] as an index into
    ROLES or -1 when it rests, each part's median pitch per window, the windows' lead part or -1).
    `melody_tracks`: the staves marked as carrying the tune (music_performance.CONFIG): they
    lead wherever they play moving notes."""
    names = list(parts); count = len(names)
    steps = int(math.ceil(length / STEP)) + 2
    per = int(round(WINDOW / STEP)); windows = max(1, int(math.ceil((steps - 2) / per)))
    hi = np.full((count, steps), -1, np.int16); lo = np.full((count, steps), 999, np.int16)
    poly = np.zeros((count, steps), np.int16); onset = np.full((count, steps), -10 ** 6, np.int32)
    percussion = np.array([parts[p][0][3] in PERCUSSION for p in names])
    hinted = np.array([parts[p][0][6] in melody_tracks for p in names])
    for k, p in enumerate(names):
        for n in parts[p]:
            a = min(steps - 1, int(n[0] / STEP)); b = min(steps, max(a + 1, int(round((n[0] + n[1]) / STEP))))
            hi[k, a:b] = np.maximum(hi[k, a:b], n[2]); lo[k, a:b] = np.minimum(lo[k, a:b], n[2])
            poly[k, a:b] += 1; onset[k, a] = a
    last = np.maximum.accumulate(onset, axis=1)
    fresh = (np.arange(steps)[None, :] - last) <= FRESH / STEP
    role = np.full((count, windows), -1, np.int8); median = np.zeros((count, windows)); leads = np.full(windows, -1)
    starts = [sorted((n[0], n[2]) for n in parts[p]) for p in names]
    cursor = [0] * count
    for w in range(windows):
        a, b = w * per, min(steps, (w + 1) * per)
        sounding = (poly[:, a:b] > 0)
        active = sounding.mean(axis=1) >= 0.2
        notes_in = []
        for k in range(count):
            i = cursor[k]
            while i < len(starts[k]) and starts[k][i][0] < a * STEP: i += 1
            j = i
            while j < len(starts[k]) and starts[k][j][0] < b * STEP: j += 1
            cursor[k] = i; notes_in.append(starts[k][i:j])
            if active[k] and not percussion[k]: median[k, w] = np.median(hi[k, a:b][sounding[k]])
        for k in range(count):
            if active[k] and percussion[k]: role[k, w] = ROLES.index('percussion')
        pitched = [k for k in range(count) if active[k] and not percussion[k]]
        if not pitched: continue
        # (the top line among the notes that are new: a pedal held over the tune does not hide it)
        moving = np.where(fresh[pitched, a:b], hi[pitched, a:b], -1)
        top = moving.max(axis=0)
        on_top = ((moving == top) & (moving >= 0)).sum(axis=1).astype(float)
        # (a staff marked as the melody leads wherever it plays moving notes: a soloist under the
        # orchestra's top line, a singer's part)
        on_top += np.array([b - a if hinted[k] and len(notes_in[k]) >= 2 else 0 for k in pitched])
        if on_top.max() < 0.15 * (b - a):
            for k in pitched: role[k, w] = ROLES.index('harmony')
            continue
        lead = pitched[int(np.argmax(on_top))]; leads[w] = lead; role[lead, w] = ROLES.index('melody')
        tune = {}
        for t, pitch in notes_in[lead]: tune.setdefault(int(round(t / STEP)), set()).add(pitch % 12)
        def together(k, with_pitch=True, line=tune):
            mine = notes_in[k]
            if not mine: return 0.0
            hit = 0
            for t, pitch in mine:
                s = int(round(t / STEP))
                if any((pitch % 12 in line.get(s + d, ()) if with_pitch else (s + d) in line) for d in (-1, 0, 1)): hit += 1
            return hit / len(mine)
        rest = []
        for k in pitched:
            if k == lead: continue
            if len(notes_in[k]) >= 2 and together(k) >= 0.7: role[k, w] = ROLES.index('doubling')
            else: rest.append(k)
        if rest:
            bottom = lo[pitched, a:b].min(axis=0)
            on_bottom = np.array([((lo[k, a:b] == bottom) & sounding[k]).sum() for k in rest])
            low = rest[int(np.argmax(on_bottom))]
            if on_bottom.max() >= 0.3 * sounding[pitched].any(axis=0).sum() and median[low, w] <= 57 and median[lead, w] - median[low, w] >= 10:
                role[low, w] = ROLES.index('bass')
                line = {}
                for t, pitch in notes_in[low]: line.setdefault(int(round(t / STEP)), set()).add(pitch % 12)
                for k in rest:
                    if k != low and median[k, w] <= 57 and len(notes_in[k]) >= 2 and together(k, True, line) >= 0.7:
                        role[k, w] = ROLES.index('bass')
        for k in rest:
            if role[k, w] >= 0: continue
            mine = notes_in[k]; pitches = [p for _, p in mine]
            moves = np.abs(np.diff(pitches)) if len(pitches) > 1 else np.array([12])
            single = poly[k, a:b][sounding[k]].mean() <= 1.25
            if single and len(mine) >= 4 and len(set(pitches)) >= 3 and (moves <= 2).mean() >= 0.5 and together(k, False) < 0.6:
                role[k, w] = ROLES.index('counter-melody')
            else: role[k, w] = ROLES.index('harmony')
    return role, median, leads


def window_levels(powers, windows):
    """Each part's K-weighted loudness in each window, over the blocks where it sounds (nan: silent)."""
    per = int(round(WINDOW / 0.1))
    out = np.full((len(powers), windows), np.nan)
    for k, p in enumerate(powers):
        for w in range(windows):
            block = p[w * per:(w + 1) * per]
            loud = block[block > ABSOLUTE_GATE]
            if len(block) and len(loud) >= max(1, 0.25 * len(block)): out[k, w] = -0.691 + 10 * math.log10(loud.mean())
    return out


def nearness(separation):
    """1 for a part in the melody's register, 0 for one far from it (semitones apart)."""
    return min(1.0, max(0.0, (REGISTER_FAR - abs(separation)) / (REGISTER_FAR - REGISTER_NEAR)))


def solve_shape(role, median, leads, levels, percussion):
    """The first step: one gain per part (dB) so that everything that plays is heard. Each
    accompanying part against the median of the parts accompanying with it (the other one, of
    two; one dominant voice among many does not bury the rest), each doubling against the part
    it doubles; only a part that is buried is moved, up to the floor."""
    count, windows = role.shape
    off = [[] for _ in range(count)]; under = [[] for _ in range(count)]
    for w, lead in enumerate(leads):
        if lead < 0 or np.isnan(levels[lead, w]): continue
        placed = {}
        for k in range(count):
            if k == lead or role[k, w] < 0 or np.isnan(levels[k, w]) or percussion[k]: continue
            near = nearness(median[lead, w] - median[k, w])
            if ROLES[role[k, w]] == 'doubling': under[k].append(levels[k, w] - levels[lead, w])
            else: placed[k] = levels[k, w] - (SHAPE_LU[ROLES[role[k, w]]] - REGISTER_LU * near)
        for k, v in placed.items():
            others = [u for j, u in placed.items() if j != k]
            if others: off[k].append(v - float(np.median(others)))
    gains = np.zeros(count)
    for k in range(count):
        played = max(1, int((role[k] >= 0).sum()))
        if off[k]: gains[k] += max(0.0, -SHAPE_FLOOR_LU - float(np.median(off[k]))) * len(off[k]) / played
        if under[k]: gains[k] += max(0.0, -DOUBLING_FLOOR_LU - float(np.median(under[k]))) * len(under[k]) / played
    return gains


def melody_over_rest(role, leads, levels, gains, percussion):
    """The melody and its doublings over the sum of the pitched parts behind them, in plain
    K-weighted loudness units, the mean of the windows that have both (None: no such window)."""
    out = []
    tune = (role == ROLES.index('melody')) | (role == ROLES.index('doubling'))
    power = 10 ** ((levels + gains[:, None]) / 10)
    for w, lead in enumerate(leads):
        if lead < 0: continue
        ok = (role[:, w] >= 0) & ~np.isnan(levels[:, w]) & ~percussion
        front = power[ok & tune[:, w], w].sum(); behind = power[ok & ~tune[:, w], w].sum()
        if front > 0 and behind > 0: out.append(10 * math.log10(front / behind))
    return float(np.mean(out)) if out else None


def melody_share(role):
    """For each part, the share of its windows in which it carries the tune."""
    tune = (role == ROLES.index('melody')) | (role == ROLES.index('doubling'))
    return tune.sum(axis=1) / np.maximum(1, (role >= 0).sum(axis=1))


def solve_melody(role, leads, bands, levels, gains, percussion):
    """The second step: the parts that carry the tune moved against those behind it (each by its
    share of carrying it) until the melody's partial loudness over the rest is inside
    MELODY_PARTIAL, the rest never raised past MELODY_FLOOR_LU. Returns the gains and the move
    in dB (0: it was inside, or no part carries the tune clearly enough)."""
    share = np.where(percussion, 0.0, melody_share(role))
    moved = lambda s: gains - s * (1 - share) * ~percussion
    at = lambda s: partial_lu(bands, role, leads, moved(s), percussion)
    now = at(0.0)
    if now is None or MELODY_PARTIAL[0] <= now <= MELODY_PARTIAL[1]: return gains, 0.0
    if (at(1.0) - at(-1.0)) / 2 < MELODY_LEVERAGE: return gains, 0.0
    above = now > MELODY_PARTIAL[1]
    want = MELODY_PARTIAL[1] - MELODY_INSIDE if above else MELODY_PARTIAL[0] + MELODY_INSIDE
    # (a positive move lowers the rest: the melody further over)
    lo, hi = (-2 * MAX_GAIN_DB, 0.0) if above else (0.0, MELODY_RAISE_DB)
    for _ in range(24):
        mid = (lo + hi) / 2
        if at(mid) < want: lo = mid
        else: hi = mid
    move = (lo + hi) / 2
    if above:
        # the plain loudness floor: the parts behind the tune together stay under it
        over = lambda s: melody_over_rest(role, leads, levels, moved(s), percussion)
        if over(0.0) is not None and over(move) < MELODY_FLOOR_LU:
            lo, hi = move, 0.0
            for _ in range(24):
                mid = (lo + hi) / 2
                if over(mid) < MELODY_FLOOR_LU: lo = mid
                else: hi = mid
            move = hi if over(0.0) >= MELODY_FLOOR_LU else 0.0
    return moved(move), move


def neutral(gains, powers, percussion):
    """The pitched parts' gains shifted together so the mix's gated loudness stays where it was
    (the parts' powers add: they are different instruments); the percussion is not moved."""
    n = min(len(p) for p in powers)
    before = gated_lufs(sum(p[:n] for p in powers))
    free = ~np.asarray(percussion)
    lo, hi = -30.0, 30.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if gated_lufs(sum(p[:n] * 10 ** ((g + mid * f) / 10) for p, g, f in zip(powers, gains, free))) < before: lo = mid
        else: hi = mid
    return gains + (lo + hi) / 2 * free


def partial_lu(bands, role, leads, gains=None, percussion=None):
    """The melody's partial loudness over the rest's (masked: tools/music_balance.py), with the
    doublings counted as melody, over the windows that have one; percussion apart."""
    from music_balance import partial_difference
    frames_per = WINDOW * RATE / 1024
    n = min(len(b) for b in bands)
    em = np.zeros((n, bands[0].shape[1])); ea = np.zeros_like(em)
    tune = (ROLES.index('melody'), ROLES.index('doubling'))
    for k in range(len(bands)):
        if percussion is not None and percussion[k]: continue
        scale = 10 ** (gains[k] / 10) if gains is not None else 1.0
        for w, lead in enumerate(leads):
            if lead < 0 or role[k, w] < 0: continue
            a, b = int(w * frames_per), min(n, int((w + 1) * frames_per))
            (em if role[k, w] in tune else ea)[a:b] += bands[k][a:b] * scale
    keep = (em.sum(axis=1) > 0) & (ea.sum(axis=1) > 0)
    if keep.sum() < 8: return None
    return round(float(partial_difference(em[keep], ea[keep])), 2)


# ---------------- rendering ----------------

def render(stems, index, blob, out, seconds):
    """A packed score played by the synthesizer as the piece `index` (its hall, level and shelf):
    the K-weighted samples."""
    packed = Path(str(out) + '.z'); packed.write_bytes(blob)
    env = dict(os.environ, MUSIC_PIECE=str(index), MUSIC_EVENTS=str(packed), MUSIC_SECONDS=f'{seconds:.2f}', MUSIC_OUT=str(out),
               MUSIC_MONO='1', SLOPPY_NO_AUDIO='1', SLOPPY_THREADS='1')
    for k in ('DISPLAY', 'WAYLAND_DISPLAY', 'MUSIC_KEEP', 'MUSIC_GAINS', 'MUSIC_SHELF', 'MUSIC_FROM'): env.pop(k, None)
    subprocess.run([str(stems)], env=env, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    rate, x = wavfile.read(out)
    assert rate == RATE
    packed.unlink(); Path(out).unlink()
    return k_weighted(x.astype(np.float64) / 32768.0)


def render_whole(stems, index, blob, out, seconds):
    """A packed score played whole as the piece `index`: its BS.1770 integrated loudness on the
    catalogue's own meter (tools/music_level.py: the 48 kHz file, the standard's filter), so a
    piece trimmed here sits where levels.json put it."""
    from music_balance import lufs
    packed = Path(str(out) + '.z'); packed.write_bytes(blob)
    env = dict(os.environ, MUSIC_PIECE=str(index), MUSIC_EVENTS=str(packed), MUSIC_SECONDS=f'{seconds:.2f}', MUSIC_OUT=str(out),
               SLOPPY_NO_AUDIO='1', SLOPPY_THREADS='1')
    for k in ('DISPLAY', 'WAYLAND_DISPLAY', 'MUSIC_KEEP', 'MUSIC_GAINS', 'MUSIC_SHELF', 'MUSIC_FROM', 'MUSIC_MONO'): env.pop(k, None)
    subprocess.run([str(stems)], env=env, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    rate, x = wavfile.read(out)
    packed.unlink(); Path(out).unlink()
    return lufs(x[:, 0].astype(np.float64) / 32768.0, rate)


def measure(name, index, stems, work):
    """A piece's parts rendered alone and measured (kept in `work`, keyed by the notes' hash)."""
    import music_pack as mp
    notes, _, sections = mp.build(name)
    key = mp.score_hash(notes)
    cache = work / f'{name}-{key}-{mp.LEVEL.get(name, 1.0)}.npz'       # (the stems are at the piece's level)
    parts = split_parts(notes)
    if cache.exists():
        z = np.load(cache)
        return notes, parts, key, [z[f'p{k}'] for k in range(len(parts))], [z[f'b{k}'] for k in range(len(parts))], float(z['whole'])
    seconds = max(n[0] + n[1] for n in notes) + 2.0
    mix = name in mp.ANNOTATED
    powers, bands = [], []
    for k, p in enumerate(parts):
        y = render(stems, index, mp.pack(parts[p], mix_levels=mix, sections=sections)[0], work / f'{name}.{k}.wav', seconds)
        powers.append(block_powers(y)); bands.append(band_powers(y))
    whole = render_whole(stems, index, mp.pack(notes, mix_levels=mix, sections=sections)[0], work / f'{name}.all.wav', seconds)
    np.savez(cache, whole=whole, **{f'p{k}': v for k, v in enumerate(powers)}, **{f'b{k}': v for k, v in enumerate(bands)})
    return notes, parts, key, powers, bands, whole


def balanced_notes(notes, gains):
    import music_pack as mp
    out = []
    for n in notes:
        k = 10 ** (gains.get(mp.part_of(n), 0.0) / 20)
        m = list(n) if len(n) > 7 else list(n) + [1.0, 1.0]
        m[7] *= k; m[8] *= k; out.append(m)
    return out


def balance(name, index, stems, work, verify=True):
    """One piece's entry for part-balance.json."""
    import music_pack as mp
    from music_performance import CONFIG
    notes, parts, key, powers, bands, whole = measure(name, index, stems, work)
    names = list(parts)
    length = max(n[0] + n[1] for n in notes)
    role, median, leads = read_roles(parts, length, CONFIG.get(name, (0, 0, 0, ()))[3])
    levels = window_levels(powers, role.shape[1])
    lufs = [gated_lufs(p) for p in powers]
    pitched = [k for k in range(len(names)) if parts[names[k]][0][3] not in PERCUSSION]
    hand = mp.HAND_SET_BALANCE.get(name)
    kept = None if hand else mp.kept_balance(name)
    entry = dict(score=key, whole_lufs=[round(whole, 2), round(whole, 2)])
    percussion = np.array([parts[p][0][3] in PERCUSSION for p in names])
    gains = np.zeros(len(names))
    settle = lambda g: neutral(np.clip(neutral(g, powers, percussion), -MAX_GAIN_DB, MAX_GAIN_DB), powers, percussion)
    if len(pitched) < 2:
        entry.update(status='hand-set' if hand else 'one part', reason=hand or 'one part alone: nothing to balance')
    else:
        gains = solve_shape(role, median, leads, levels, percussion)
        gains, move = solve_melody(role, leads, bands, levels, gains, percussion)
        if hand or kept:
            entry.update(status='hand-set' if hand else 'kept', would_be_db={names[k]: round(float(g), 1) for k, g in enumerate(settle(gains))},
                         reason=hand or 'the balance it already had in performance.json (balance_db: ' + ', '.join(f'{mp.NAMES[int(i)]} {g:+.2f}' for i, g in kept.items()) + ' dB), from tools/music_balance.py')
        else:
            gains = settle(gains)
            entry['status'] = 'balanced' if np.abs(gains).max() >= SETTLED_DB else 'in balance'
        if entry['status'] != 'balanced': gains = np.zeros(len(names))
    if entry['status'] == 'balanced' and verify:
        # the balanced piece, whole: trimmed so its loudness is the unbalanced piece's
        seconds = length + 2.0
        heard_path = work / f'{name}-{key}-{mp.LEVEL.get(name, 1.0)}.verified.json'      # (renders already made, by their gains)
        heard = json.loads(heard_path.read_text()) if heard_path.exists() else {}
        for attempt in range(6):
            table = {names[k]: round(float(g), 2) for k, g in enumerate(gains)}
            tag = json.dumps(table, sort_keys=True)
            if tag not in heard:
                blob = mp.pack(balanced_notes(notes, table), mix_levels=True)[0]
                heard[tag] = render_whole(stems, index, blob, work / f'{name}.balanced.wav', seconds)
                heard_path.write_text(json.dumps(heard))
            after = heard[tag]
            if abs(after - whole) <= 0.03: break
            gains = gains - (after - whole) * ~percussion
        entry['whole_lufs'] = [round(whole, 2), round(after, 2)]
    table = {names[k]: round(float(g), 2) for k, g in enumerate(gains)}
    if entry['status'] == 'balanced': entry['gains_db'] = table
    entry['parts'] = {}
    for k, p in enumerate(names):
        played = role[k][role[k] >= 0]
        main = int(np.bincount(played, minlength=len(ROLES)).argmax()) if len(played) else ROLES.index('harmony')
        entry['parts'][p] = dict(role=ROLES[main], share=round(float((played == main).mean()), 2) if len(played) else 0.0,
                                 lufs=[round(lufs[k], 1), round(lufs[k] + table[p], 1)], notes=len(parts[p]),
                                 pitch=int(np.median([n[2] for n in parts[p]])))
    show = lambda v: None if v is None else round(v, 1)
    entry['melody_over_rest_lu'] = [show(melody_over_rest(role, leads, levels, g, percussion)) for g in (np.zeros(len(names)), gains)]
    if len(pitched) >= 2 and entry['melody_over_rest_lu'][0] is not None:
        entry['melody_partial_lu'] = [show(partial_lu(bands, role, leads, None, percussion)), show(partial_lu(bands, role, leads, gains, percussion))]
    flags = [f'{p} moved {g:+.1f} dB' for p, g in table.items() if abs(g) > SUSPICIOUS_DB]
    if flags: entry['suspicious'] = flags
    return entry


def report(result, order):
    lines = ['| Piece | Status | Part | Role (share of its windows) | LUFS before | LUFS after | Gain dB | Melody over the rest, LU | Melody partial loudness over the rest, LU |',
             '|---|---|---|---|---:|---:|---:|---|---|']
    for name in order:
        e = result.get(name)
        if not e: continue
        first = True
        for p, v in e['parts'].items():
            gain = e.get('gains_db', {}).get(p, 0.0)
            would = f" (would be {e['would_be_db'][p]:+.1f})" if 'would_be_db' in e else ''
            over = e['melody_over_rest_lu']; partial = e.get('melody_partial_lu') or [None, None]
            show = lambda pair: '' if pair[0] is None else f'{pair[0]:+.1f} → {pair[1]:+.1f}'
            status = e['status'] + (' **SUSPICIOUS**' if e.get('suspicious') else '')
            lines.append(f"| {name if first else ''} | {status if first else ''} | {p} | {v['role']} ({v['share']:.0%}) | {v['lufs'][0]:.1f} | {v['lufs'][1]:.1f} | {gain:+.1f}{would} | {show(over) if first else ''} | {show(partial) if first else ''} |")
            first = False
    return '\n'.join(lines) + '\n'


def calibrate(result):
    """The pieces balanced by ear: what they measure, and what the balance would have asked."""
    for name, e in result.items():
        if e['status'] in ('hand-set', 'kept') and 'would_be_db' in e:
            print(f"{name}: {e['status']}: melody over the rest {e['melody_over_rest_lu'][0]} LU, partial {(e.get('melody_partial_lu') or [None])[0]}; the balance would move "
                  + ', '.join(f"{p} ({e['parts'][p]['role']}) {g:+.1f}" for p, g in e['would_be_db'].items()))


def main():
    import music_pack as mp
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('pieces', nargs='*')
    p.add_argument('--stems', default='')
    p.add_argument('--jobs', type=int, default=2)
    p.add_argument('--work', default=os.environ.get('MUSIC_SCRATCH', ''))
    p.add_argument('--report', default='')
    p.add_argument('--no-verify', action='store_true')
    p.add_argument('--calibrate', action='store_true')
    p.add_argument('--dry', action='store_true', help='print and report, write nothing to data/')
    a = p.parse_args()
    work = Path(a.work or tempfile.mkdtemp(prefix='part-balance-', dir=os.environ.get('TMPDIR'))); work.mkdir(parents=True, exist_ok=True)
    stems = a.stems
    if not stems:
        stems = work / 'stems'
        env = {k: v for k, v in os.environ.items() if k not in ('DISPLAY', 'WAYLAND_DISPLAY')}
        subprocess.run(['sloppy', 'build', str(ROOT / 'tools/music_stems.jo'), '--release', '-o', str(stems)], check=True, cwd=ROOT, env=env)
    order = [r[0] for r in mp.PIECES]
    chosen = a.pieces or order
    path = ROOT / 'data/music/part-balance.json'
    result = json.loads(path.read_text()) if path.exists() else {}
    def one(name):
        entry = balance(name, order.index(name), stems, work, verify=not a.no_verify)
        gains = entry.get('gains_db') or {}
        print(f"{name:30} {entry['status']:10} " + ' '.join(f"{part}[{v['role'][:4]} {v['lufs'][0]:.1f}{gains.get(part, 0.0):+.1f}]" for part, v in entry['parts'].items())
              + f"  over {entry['melody_over_rest_lu']} partial {entry.get('melody_partial_lu')} whole {entry['whole_lufs']}" + ('  SUSPICIOUS' if entry.get('suspicious') else ''), flush=True)
        return name, entry
    with ThreadPoolExecutor(max(1, a.jobs)) as pool:
        for name, entry in pool.map(one, chosen): result[name] = entry
    result = {name: result[name] for name in order if name in result}
    if a.calibrate: calibrate(result)
    if a.report: Path(a.report).write_text(report(result, chosen))
    if not a.dry: path.write_text(json.dumps(result, indent=1) + '\n')


if __name__ == '__main__':
    main()
