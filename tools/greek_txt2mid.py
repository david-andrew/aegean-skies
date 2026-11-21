#!/usr/bin/env python3
"""Convert our plain-text transcriptions (*.txt) into type-1 MIDI files.

Usage: python tools/greek_txt2mid.py data/music/source/greek/<slug>.txt [...] -o <dir>
(the game uses them as data/music/source/greek-<slug>.mid; data/music/SOURCES.md)

Text format (one transcription per file)
----------------------------------------
Header lines "name: value" until the line "melody:".
  title, number, pages, place, key (signature: +n sharps / -n flats),
  time (initial metre, e.g. 2/4), tempo (as printed), bpm (quarter notes per
  minute used for the MIDI tempo), pickup (length of bar 1 in quarters, if it
  is an anacrusis), form (play order as bar ranges, e.g. "1-20, 5-18, 21-30";
  default: every bar once, in order), tempi (tempo changes as bar=bpm, e.g.
  "49=92, 86=38", applied the first time that bar is played).
Then "melody:" and "bass:" sections, one bar per line:
  <bar number>: <tokens>
Tokens
  C4 F#4 Bb3 En5   pitch as it sounds (accidentals from the key signature and
                   earlier in the bar already applied), C4 = middle C
  :4  :8. :16 :2t  duration after the pitch: 1 2 4 8 16 32, dots, t = triplet
  r:4              rest
  ~                suffix: tied to the next note (same pitch)
  ^                suffix: fermata (kept in the text, not stretched in MIDI)
  g<pitch>         grace note (printed small); given a 64th taken from the
                   following note in the MIDI, not counted in the bar length
  [3/4]            metre change from this bar on (first token of the bar)
Every bar is checked: its notes must fill the metre exactly (bar 1 may be a
pickup, and the last bar may be short if it completes the pickup).
"""
import argparse, re, sys
from fractions import Fraction as F
from pathlib import Path

import mido

TPQ = 480
STEP = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
ACC = {'': 0, 'n': 0, '#': 1, '##': 2, 'b': -1, 'bb': -2}
TOK = re.compile(r'^(g)?([A-G])(##|#|bb|b|n)?(-?\d)(?::(\d+)(\.{0,2})(t)?)?([~^]*)$')
REST = re.compile(r'^r:(\d+)(\.{0,2})(t)?(\^?)$')
MAJOR = {-7: 'Cb', -6: 'Gb', -5: 'Db', -4: 'Ab', -3: 'Eb', -2: 'Bb', -1: 'F', 0: 'C',
         1: 'G', 2: 'D', 3: 'A', 4: 'E', 5: 'B', 6: 'F#', 7: 'C#'}


def dur(base, dots, trip):
    d = F(4, int(base))
    add = d
    for _ in dots:
        add /= 2
        d += add
    if trip:
        d = d * F(2, 3)
    return d


def parse(path):
    head, sec, bars = {}, None, {'melody': {}, 'bass': {}}
    for raw in Path(path).read_text().splitlines():
        line = re.sub(r'(^|\s)#(\s.*)?$', '', raw).rstrip()
        if not line.strip():
            continue
        if line.strip() in ('melody:', 'bass:'):
            sec = line.strip()[:-1]
            continue
        if sec is None:
            k, v = line.split(':', 1)
            head[k.strip()] = v.strip()
            continue
        n, rest = line.split(':', 1)
        bars[sec][int(n)] = rest.split()
    return head, bars


def bar_events(tokens, where):
    """Return (metre or None, [(kind, midi, length, tie, grace)])."""
    metre, ev = None, []
    for t in tokens:
        if t.startswith('['):
            metre = t.strip('[]')
            continue
        m = REST.match(t)
        if m:
            ev.append(('r', None, dur(m[1], m[2], m[3]), False, False))
            continue
        m = TOK.match(t)
        if not m:
            raise SystemExit(f'{where}: bad token {t!r}')
        grace, step, acc, octv, base, dots, trip, flags = m.groups()
        midi = 12 * (int(octv) + 1) + STEP[step] + ACC[acc or '']
        if grace:
            ev.append(('g', midi, F(0), False, True))
            continue
        if base is None:
            raise SystemExit(f'{where}: note without duration {t!r}')
        ev.append(('n', midi, dur(base, dots, trip), '~' in flags, False))
    return metre, ev


def build(path):
    head, bars = parse(path)
    name = Path(path).stem
    nums = sorted(bars['melody'])
    if sorted(bars['bass']) != nums:
        missing = set(nums) ^ set(bars['bass'])
        raise SystemExit(f'{name}: melody and bass bars differ: {sorted(missing)}')
    if nums != list(range(1, len(nums) + 1)):
        raise SystemExit(f'{name}: bars must be numbered 1..N')
    metre = head['time']
    info = {}  # bar -> (metre, length)
    parsed = {}
    pickup = F(head['pickup']) if 'pickup' in head else None
    for n in nums:
        mm, mel = bar_events(bars['melody'][n], f'{name} melody bar {n}')
        mb, bas = bar_events(bars['bass'][n], f'{name} bass bar {n}')
        if mm != mb:
            raise SystemExit(f'{name} bar {n}: metre change differs between parts')
        if mm:
            metre = mm
        num, den = map(int, metre.split('/'))
        full = F(num * 4, den)
        for part, ev in (('melody', mel), ('bass', bas)):
            got = sum(e[2] for e in ev)
            ok = got == full or (n == 1 and pickup is not None and got == pickup) \
                or (n == nums[-1] and pickup is not None and got == full - pickup)
            if not ok:
                raise SystemExit(f'{name} {part} bar {n}: {got} quarters, metre {metre} needs {full}')
        info[n] = (metre, sum(e[2] for e in mel))
        parsed[n] = (mel, bas)
    order = []
    form = head.get('form')
    if form:
        for part in form.split(','):
            a, _, b = part.strip().partition('-')
            order += list(range(int(a), int(b or a) + 1))
    else:
        order = nums
    return head, info, parsed, order


def write_midi(path, outdir):
    head, info, parsed, order = build(path)
    bpm = float(head['bpm'])
    mid = mido.MidiFile(type=1, ticks_per_beat=TPQ)
    tracks = []
    for prog, ch, label, vel in ((0, 0, 'Melody', 92), (32, 1, 'Bass', 72)):
        tr = mido.MidiTrack()
        mid.tracks.append(tr)
        tr.append(mido.MetaMessage('track_name', name=label, time=0))
        tracks.append((tr, prog, ch, vel))
    t0 = tracks[0][0]
    t0.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm), time=0))
    key = int(head.get('key', '0'))
    t0.append(mido.MetaMessage('key_signature', key=MAJOR[key], time=0))
    # absolute-time event lists
    abs_ev = [[], []]
    meta = []
    now = F(0)
    last_metre = None
    tempi = {}
    for part in filter(None, (x.strip() for x in head.get('tempi', '').split(','))):
        b, v = part.split('=')
        tempi[int(b)] = float(v)
    seen = set()
    for n in order:
        metre, length = info[n]
        if n in tempi and n not in seen:
            meta.append((now, mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(tempi[n]), time=0)))
        seen.add(n)
        if metre != last_metre:
            a, b = map(int, metre.split('/'))
            meta.append((now, mido.MetaMessage('time_signature', numerator=a, denominator=b, time=0)))
            last_metre = metre
        for pi, ev in enumerate(parsed[n]):
            t = now
            steal = F(0)
            for kind, midi, d, tie, grace in ev:
                if kind == 'g':
                    abs_ev[pi].append((t, midi, F(1, 16), False))
                    t += F(1, 16)
                    steal += F(1, 16)
                    continue
                if kind == 'n':
                    abs_ev[pi].append((t, midi, d - steal, tie))
                t += d - steal
                steal = F(0)
        now += length
    for t, m in meta:
        pass
    for pi, (tr, prog, ch, vel) in enumerate(tracks):
        tr.append(mido.Message('program_change', program=prog, channel=ch, time=0))
        # merge ties
        notes = []
        for t, midi, d, tie in abs_ev[pi]:
            if notes and notes[-1][3] and notes[-1][1] == midi and notes[-1][0] + notes[-1][2] == t:
                pt, pm, pd, _ = notes[-1]
                notes[-1] = (pt, pm, pd + d, tie)
            else:
                notes.append((t, midi, d, tie))
        msgs = []
        if pi == 0:
            for t, m in meta:
                msgs.append((t, 0, m))
        for t, midi, d, _ in notes:
            msgs.append((t + d, 1, mido.Message('note_off', note=midi, velocity=0, channel=ch)))
            msgs.append((t, 2, mido.Message('note_on', note=midi, velocity=vel, channel=ch)))
        msgs.sort(key=lambda x: (x[0], x[1]))
        prev = 0
        for t, _, m in msgs:
            tick = round(t * TPQ)
            m.time = tick - prev
            prev = tick
            tr.append(m)
        tr.append(mido.MetaMessage('end_of_track', time=0))
    out = Path(outdir) / (Path(path).stem + '.mid')
    mid.save(out)
    return out, len(info), len(order)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='+')
    ap.add_argument('-o', '--outdir', default='midi')
    a = ap.parse_args()
    Path(a.outdir).mkdir(parents=True, exist_ok=True)
    for f in a.files:
        out, nb, np_ = write_midi(f, a.outdir)
        print(f'{out}: {nb} bars written, {np_} bars played')
