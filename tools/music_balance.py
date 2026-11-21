"""Automatic mix balance for the procedural band and orchestra, without a human listener.

For each piece:

1. The melody: the instrument that most often has the highest sounding note (by time), from the
   packed notes. A piece is balanced when one instrument carries most of the tune and others
   accompany it (a piano alone, or strings playing both, are left as they are).
2. Stems are rendered by the game's own synthesizer (tools/music_stems.jo): the melody alone, the
   accompaniment alone, and each instrument alone.
3. Loudness, perceptually: ITU-R BS.1770 integrated loudness (K-weighted, gated) of each stem, and
   the melody's partial loudness in the mix: excitation per critical band (Bark), with the
   melody's loudness counted only above what the accompaniment already masks in that band
   (Moore and Glasberg's form, N = (Em + Ea)^0.23 - Ea^0.23), and the same for the
   accompaniment under the melody. Their difference, in loudness units (10 per doubling).
4. Gains: the melody is set a few loudness units (`TARGET_LU`) over the accompaniment, the
   correction split between the two so the whole stays as loud.
5. Harshness, per instrument: the presence band's level (2 to 5 kHz) against the body (300 Hz to
   2 kHz), sharpness (Zwicker's weighting of loudness by critical band), and the presence band's
   flux (how spiky it is). Where a part is harsher than its instrument's allowance, a gentle high
   shelf (above 2.2 kHz) is set for it, and the stem is rendered again to confirm.

Writes data/music/balance.json (read by tools/music_pack.py: the gains as mix gains, the shelves
in the synth) and prints the table. Pieces the user has approved as they are (`LOCKED`) are
measured and reported but not changed.

  python tools/music_balance.py            (needs `sloppy` on the PATH; ~1 minute)
"""
from pathlib import Path
import json, math, os, struct, subprocess, sys, tempfile, zlib
import numpy as np
from scipy.io import wavfile
from scipy.signal import lfilter, resample_poly

ROOT = Path(__file__).resolve().parents[1]
RATE = 16000
NAMES = ['strings', 'brass', 'flute', 'oboe', 'clarinet', 'bassoon', 'piano', 'harp', 'bouzouki', 'accordion', 'banjo',
         'timpani', 'drums', 'bass', 'choir', 'trumpet']
TARGET_LU = 3.0                     # the melody over the accompaniment, in partial loudness
TOLERANCE_LU = 1.0                  # already within this: left as it is
SHELF_HZ = 2200.0
# the presence band (2-5 kHz) a part may carry over its body (0.3-2 kHz), dB, before it is "harsh",
# and its sharpness: set from the parts already approved by ear (Clair de lune's piano -8.0 dB,
# the Adagietto's strings -11.2, the trumpet call -6.4, the Gymnopedie's and Ave Maria's violin
# -11.3 and -12.1 at 1.72 and 1.75), with the instruments' natural brightness for the rest
PRESENCE_ALLOWANCE = {0: -10.0, 1: -4.0, 2: -8.0, 3: -7.0, 4: -6.0, 5: -10.0, 6: -7.5, 7: -8.0, 8: -6.0, 9: -7.0,
                      10: -6.0, 13: -20.0, 15: -4.0}
SHARPNESS_ALLOWANCE = 1.85
MAX_GAIN_DB = 4.0                   # the balance never moves a part by more than this
MAX_SHELF_DB = -5.0                 # nor softens its top by more than this
UNCLEAR_DB = 8.0                    # a correction past this means the melody guess is wrong: skipped
# pieces the user has approved as they sound: measured, never changed
LOCKED = {'clair-de-lune': 'approved as it is', 'adagietto': 'approved as it is', 'mahler-opening': 'approved as it is'}
SECONDS = 75.0


def read_packed(name):
    """Events from a packed piece: (start s, duration s, pitch, instrument)."""
    blob = (ROOT / 'data/music' / f'{name}.z').read_bytes()
    raw = blob[4:] if blob.startswith(b'RAW!') else zlib.decompress(blob, -15)
    version = raw[3]
    count = struct.unpack_from('<I', raw, 4)[0]
    stride = 16 if version >= 51 else 14 if version == 50 else 12
    out = []
    for i in range(count):
        at = 16 + i * stride
        start, dur, pitch, ins = struct.unpack_from('<IIBB', raw, at)
        if version == 52: ins &= 15
        out.append((start / RATE, dur / RATE, pitch, ins))
    return out


def melody_of(events, limit):
    """The instrument with the top line most of the time, its share, and how much of its own time
    it spends on top (a part that also accompanies is no melody to balance)."""
    events = [e for e in events if e[0] < limit and e[3] not in (11, 12)]
    times = sorted(set(round(e[0], 3) for e in events))
    top_time = {}; own = {}; on_top = {}
    for e in events: own[e[3]] = own.get(e[3], 0.0) + e[1]
    for a, b in zip(times, times[1:] + [times[-1] + 0.5]):
        sounding = [e for e in events if e[0] <= a + 1e-4 < e[0] + e[1]]
        if not sounding: continue
        top = max(sounding, key=lambda e: e[2])
        top_time[top[3]] = top_time.get(top[3], 0.0) + (b - a)
    total = sum(top_time.values()) or 1.0
    melody = max(top_time, key=top_time.get)
    share = top_time[melody] / total
    purity = top_time[melody] / max(own.get(melody, 1e-9), 1e-9)
    return melody, share, min(1.0, purity), sorted(i for i in own if i != melody and own[i] > 0.05 * total)


def doubling(events, melody, others, limit):
    """How much of the accompaniment only doubles the tune (same moment, same note or octaves)."""
    tune = {}
    for e in events:
        if e[3] == melody and e[0] < limit: tune.setdefault(round(e[0], 2), set()).add(e[2] % 12)
    acc = [e for e in events if e[3] in others and e[0] < limit]
    if not acc: return 0.0
    same = sum(1 for e in acc if e[2] % 12 in tune.get(round(e[0], 2), set()))
    return same / len(acc)


def render(index, keep, out, gains=None, shelf=None, seconds=SECONDS):
    env = dict(os.environ, MUSIC_PIECE=str(index), MUSIC_KEEP=keep, MUSIC_SECONDS=str(seconds), MUSIC_OUT=str(out),
               SLOPPY_NO_AUDIO='1', SLOPPY_THREADS='1')
    env.pop('DISPLAY', None); env.pop('WAYLAND_DISPLAY', None)
    if gains: env['MUSIC_GAINS'] = ','.join(f'{k}:{v:.3f}' for k, v in gains.items())
    if '--measure' not in sys.argv:
        env['MUSIC_SHELF'] = 'none' if not shelf else f"{shelf['hz']}|" + ','.join(f'{k}:{v:.2f}' for k, v in shelf['db'].items())
    subprocess.run(['sloppy', '--release', str(ROOT / 'tools/music_stems.jo')], env=env, check=True, capture_output=True, cwd=ROOT)
    rate, x = wavfile.read(out)
    return rate, x[:, 0].astype(np.float64) / 32768.0


# ---------------- loudness ----------------

def k_weighted(x):
    """ITU-R BS.1770's K-weighting at 48 kHz (its published coefficients)."""
    y = lfilter([1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585], x)
    return lfilter([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621], y)


def lufs(x, rate=48000):
    """BS.1770 integrated loudness: 400 ms blocks overlapping by 75%, absolute and relative gates."""
    y = k_weighted(x)
    block, hop = int(0.4 * rate), int(0.1 * rate)
    powers = np.array([np.mean(y[i:i + block] ** 2) for i in range(0, max(1, len(y) - block), hop)])
    loud = -0.691 + 10 * np.log10(powers + 1e-12)
    gated = powers[loud > -70]
    if len(gated) == 0: return -70.0
    relative = -0.691 + 10 * np.log10(gated.mean()) - 10
    gated = powers[(loud > -70) & (loud > relative)]
    return float(-0.691 + 10 * np.log10(gated.mean() + 1e-12))


BARK_EDGES = [20, 100, 200, 300, 400, 510, 630, 770, 920, 1080, 1270, 1480, 1720, 2000, 2320, 2700, 3150, 3700, 4400,
              5300, 6400, 7700, 9500, 12000]


def bands(x, rate=48000, n=4096):
    """Per frame, the K-weighted power in each critical band."""
    y = k_weighted(x)
    window = np.hanning(n)
    frames = [np.abs(np.fft.rfft(y[i:i + n] * window)) ** 2 for i in range(0, len(y) - n, n // 2)]
    spec = np.array(frames)
    freqs = np.fft.rfftfreq(n, 1 / rate)
    out = np.zeros((len(frames), len(BARK_EDGES) - 1))
    for b in range(len(BARK_EDGES) - 1):
        m = (freqs >= BARK_EDGES[b]) & (freqs < BARK_EDGES[b + 1])
        out[:, b] = spec[:, m].sum(axis=1)
    return out


def partial_difference(em, ea, melody_db=0.0):
    """The melody's partial loudness over the accompaniment's, in loudness units (10 per
    doubling), with the melody scaled by melody_db; frames where the music sounds."""
    em = em * 10 ** (melody_db / 10)
    total = em + ea
    nm = (total ** 0.23 - ea ** 0.23).sum(axis=1)
    na = (total ** 0.23 - em ** 0.23).sum(axis=1)
    active = total.sum(axis=1) > np.percentile(total.sum(axis=1), 30)
    # (only where the melody is actually playing)
    active &= em.sum(axis=1) > 1e-3 * np.median(em.sum(axis=1)[active] + 1e-30)
    return float(10 * np.log2(nm[active].mean() / na[active].mean()))


# ---------------- harshness ----------------

def harshness(x, rate=48000, n=4096):
    window = np.hanning(n)
    spec = np.array([np.abs(np.fft.rfft(x[i:i + n] * window)) ** 2 for i in range(0, len(x) - n, n // 2)])
    freqs = np.fft.rfftfreq(n, 1 / rate)
    body = spec[:, (freqs >= 300) & (freqs < 2000)].sum(axis=1)
    presence = spec[:, (freqs >= 2000) & (freqs < 5000)].sum(axis=1)
    sounding = body + presence > np.percentile(body + presence, 40)
    presence_db = float(10 * np.log10(presence[sounding].sum() / (body[sounding].sum() + 1e-30) + 1e-30))
    # sharpness: Zwicker's weighting of specific loudness by critical band (acum-like)
    b = bands(x, rate, n)[sounding] ** 0.23
    z = np.arange(len(BARK_EDGES) - 1) + 0.5
    g = np.where(z <= 15.8, 1.0, 0.066 * np.exp(0.171 * z))
    sharp = float(0.11 * ((b * g * z).sum(axis=1) / (b.sum(axis=1) + 1e-12)).mean())
    p = presence[sounding]
    flux = float(np.mean(np.maximum(0, np.diff(p))) / (p.mean() + 1e-30)) if len(p) > 2 else 0.0
    return dict(presence_db=round(presence_db, 2), sharpness=round(sharp, 3), flux=round(flux, 3))


# ---------------- the balance ----------------

def main():
    catalogue = json.loads((ROOT / 'data/music/catalogue.json').read_text())
    work = Path(os.environ.get('BALANCE_WORK', tempfile.mkdtemp(prefix='balance-', dir=os.environ.get('TMPDIR'))))
    work.mkdir(parents=True, exist_ok=True)
    result = {}; rows = []
    for index, piece in enumerate(catalogue):
        name = piece['id']
        events = read_packed(name)
        length = min(SECONDS, piece['frames'] / RATE - 2)
        melody, share, purity, others = melody_of(events, length)
        instruments = sorted(set(e[3] for e in events if e[0] < length))
        entry = dict(melody=NAMES[melody], melody_instrument=melody, share=round(share, 2), purity=round(purity, 2),
                     accompaniment=[NAMES[i] for i in others])
        # harshness of each part, alone
        harsh = {}
        for ins in instruments:
            if ins in (11, 12): continue
            rate, x = render(index, str(ins), work / f'{name}-{ins}.wav', seconds=length)
            harsh[ins] = harshness(x, rate)
        entry['harshness'] = {NAMES[i]: h for i, h in harsh.items()}
        doubled = doubling(events, melody, others, length) if others else 0.0
        entry['doubling'] = round(doubled, 2)
        balanced = share >= 0.6 and purity >= 0.55 and others and doubled < 0.6
        shelf = {}
        for ins, h in harsh.items():
            allowance = PRESENCE_ALLOWANCE.get(ins)
            cut = 0.0
            if allowance is not None and h['presence_db'] > allowance + 0.5: cut = allowance - h['presence_db'] - 1.0
            if h['sharpness'] > SHARPNESS_ALLOWANCE: cut -= 1.5
            if cut < -0.3: shelf[ins] = round(max(MAX_SHELF_DB, min(0.0, cut)), 2)
        gains = {}
        if balanced:
            _, xm = render(index, str(melody), work / f'{name}-melody.wav', seconds=length,
                           shelf=dict(hz=SHELF_HZ, db=shelf) if shelf else None)
            _, xa = render(index, ','.join(map(str, others)), work / f'{name}-accompaniment.wav', seconds=length,
                           shelf=dict(hz=SHELF_HZ, db=shelf) if shelf else None)
            em, ea = bands(xm), bands(xa)
            k = min(len(em), len(ea)); em, ea = em[:k], ea[:k]
            before = partial_difference(em, ea)
            entry.update(lufs_melody=round(lufs(xm), 1), lufs_accompaniment=round(lufs(xa), 1), partial_lu_before=round(before, 1))
            correction = 0.0
            if abs(before - TARGET_LU) > TOLERANCE_LU:
                lo, hi = -15.0, 10.0
                for _ in range(40):
                    mid = (lo + hi) / 2
                    if partial_difference(em, ea, mid) > TARGET_LU: hi = mid
                    else: lo = mid
                correction = (lo + hi) / 2
            if abs(correction) > UNCLEAR_DB:
                entry['unclear'] = f'a {correction:+.1f} dB correction: the top line is not the tune'
                correction = 0.0; balanced = False
            correction = max(-2 * MAX_GAIN_DB, min(2 * MAX_GAIN_DB, correction))
            entry['partial_lu_after'] = round(partial_difference(em, ea, correction), 1)
            if correction:
                gains[melody] = round(correction / 2, 2)
                for i in others: gains[i] = round(-correction / 2, 2)
        locked = name in LOCKED
        if locked:
            entry['locked'] = LOCKED[name]
        elif gains or shelf:
            entry['gains_db'] = {str(k): v for k, v in gains.items()}
            if shelf:
                entry['shelf'] = dict(hz=SHELF_HZ, db={str(k): v for k, v in shelf.items()})
                # confirm: each shelved part rendered again
                entry['harshness_after'] = {}
                for ins in shelf:
                    rate, x = render(index, str(ins), work / f'{name}-{ins}-shelved.wav', seconds=length,
                                     shelf=dict(hz=SHELF_HZ, db=shelf))
                    entry['harshness_after'][NAMES[ins]] = harshness(x, rate)
        entry['summary'] = dict(melody=NAMES[melody] if balanced else None,
                                partial_lu=[entry.get('partial_lu_before'), entry.get('partial_lu_after')] if balanced else None,
                                gains_db={NAMES[k]: v for k, v in gains.items()} if gains and not locked else None,
                                shelf_db={NAMES[k]: v for k, v in shelf.items()} if shelf and not locked else None,
                                locked=locked or None)
        result[name] = entry
        rows.append(entry | dict(name=name))
        print(f"{name:16} melody {NAMES[melody]:9} share {share:.2f} purity {purity:.2f}"
              + (f"  partial {entry['partial_lu_before']:+.1f} -> {entry['partial_lu_after']:+.1f} LU" if balanced else f"  (not balanced: {entry.get('unclear') or ('the accompaniment doubles the tune' if entry['doubling'] >= 0.6 else 'no melody over an accompaniment')})")
              + (f"  gains {entry.get('gains_db')}" if entry.get('gains_db') else '')
              + (f"  shelf {entry['shelf']['db']}" if entry.get('shelf') else '')
              + ('  LOCKED' if locked else ''), flush=True)
    # (--measure: the packed pieces as they now are, written to a scratch file, the balance untouched)
    if '--measure' in sys.argv:
        Path(os.environ.get('BALANCE_REPORT', work / 'measured.json')).write_text(json.dumps(result, indent=1, sort_keys=True) + '\n')
    else:
        (ROOT / 'data/music/balance.json').write_text(json.dumps(result, indent=1, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
