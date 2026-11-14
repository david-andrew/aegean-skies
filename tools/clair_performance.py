"""Clair de lune as a pianist would shape it: writes data/music/clair-de-lune-performance.json.

The Mutopia transcription plays every note at one velocity, in strict time. This plan, bar by bar
(72 bars of 9/8; quarter = 1 s in the MIDI, so a bar is 4.5 s of score time), gives it:

* a phrase-level tempo arch with real rubato: lingering at phrase peaks and cadences, pushing
  through the flowing middle (Un poco mosso, En animant), broadening at the climax, Calmato,
  Tempo I and the long morendo to the end;
* wide dynamics: a pp opening, the swell through the Un poco mosso arpeggios to the ff of En
  animant, a hushed return, fading to nothing;
* the sustain pedal changed with each harmony (each beat in the chordal sections, each bar
  through the arpeggios);
* the melody voiced over the accompaniment, and chords spread a little from the bass up.

Run after any change to the score or the generic reading:
  python tools/clair_performance.py && python tools/music_pack.py
"""
from pathlib import Path
import json, math
from music_pack import ROOT, read_midi, arrange
from music_performance import score_clock, interpret, performance_signature

NAME = 'clair-de-lune'
BAR = 4.5                           # score seconds per bar
BARS = 72

# (bar, tempo factor: performed / score duration) anchors, interpolated between; the MIDI's
# dotted quarter = 40 is a little brisk for the opening and slow for the Un poco mosso.
TEMPO = [(1, 1.10), (8, 1.06), (9, 1.02), (12, 0.96), (14, 1.02), (15, 0.94), (18, 0.90),
         (19, 0.92), (24, 0.88), (25, 1.00), (26, 1.10), (27, 0.84), (30, 0.82), (34, 0.78),
         (36, 0.80), (37, 0.80), (39, 0.86), (41, 0.92), (42, 1.08), (43, 1.14), (44, 1.12),
         (45, 1.00), (48, 0.96), (49, 1.06), (50, 1.20), (51, 1.10), (58, 1.06), (59, 1.04),
         (62, 1.06), (63, 1.12), (65, 1.16), (66, 1.18), (70, 1.30), (72, 1.70)]

# (bar, level in dB) anchors: 0 dB is a full forte.
LEVEL = [(1, -17), (4, -15), (8, -17), (9, -14), (12, -11), (14, -8), (16, -6), (18, -3),
         (20, -4), (24, -2), (25, 0), (26, -6), (27, -16), (30, -13), (33, -9), (36, -5),
         (37, -2), (39, 1), (41, 0), (42, -6), (43, -18), (44, -17), (45, -12), (48, -7),
         (49, -9), (50, -13), (51, -19), (55, -16), (58, -18), (59, -15), (62, -13), (63, -18),
         (66, -20), (70, -24), (72, -30)]

# phrases (first bar, last bar): rubato lingers into each one's end; dynamics swell to its middle
PHRASES = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12), (13, 14), (15, 16), (17, 18),
           (19, 20), (21, 22), (23, 24), (25, 26), (27, 28), (29, 30), (31, 32), (33, 34),
           (35, 36), (37, 38), (39, 40), (41, 42), (43, 44), (45, 46), (47, 48), (49, 50),
           (51, 52), (53, 54), (55, 56), (57, 58), (59, 60), (61, 62), (63, 65), (66, 68), (69, 72)]

# where the pedal is changed each bar (the arpeggios) rather than each beat
BAR_PEDAL = [(27, 36), (43, 50)]


def anchors(points, bar):
    for (a, x), (b, y) in zip(points, points[1:]):
        if a <= bar <= b:
            u = (bar - a) / (b - a)
            u = u * u * (3 - 2 * u)
            return x + (y - x) * u
    return points[-1][1]


def phrase_at(bar):
    for a, b in PHRASES:
        if a <= math.floor(bar) <= b:
            return a, b + 1
    return math.floor(bar), math.floor(bar) + 1


def tempo(bar):
    """Performed seconds per score second at a fractional bar (1.0 = the first downbeat)."""
    base = anchors(TEMPO, bar)
    a, b = phrase_at(bar)
    u = (bar - a) / (b - a)
    # a breath in, a little push through the middle, and a lingering cadence
    arch = 0.05 * (2 * u - 1) ** 2 - 0.02 + 0.30 * math.exp(-((u - 0.97) / 0.07) ** 2)
    # a small lift onto each bar's first beat, as the hand settles
    within = 0.03 * math.exp(-((bar - math.floor(bar)) / 0.06) ** 2)
    return base * (1 + arch + within)


# (heard across a terrace, not a concert hall: the plan's range is kept, three quarters of it)
COMPRESS = 0.78


def level(bar):
    a, b = phrase_at(bar)
    u = (bar - a) / (b - a)
    return COMPRESS * anchors(LEVEL, bar) + 2.0 * math.sin(math.pi * min(1.0, u / 0.85)) - 1.5


def main():
    source = ROOT / 'data/music/source' / f'{NAME}.mid'
    notes, _ = interpret(arrange(NAME, read_midi(source)), NAME, score_clock(source, NAME))
    end = max(n[0] + n[1] for n in notes)
    # the time map: performed time accumulated over eighth notes (a ninth of a bar)
    step = BAR / 9
    times = [0.0]
    performed = [0.0]
    t = 0.0
    while t < end + BAR:
        bar = 1 + (t + step * 0.5) / BAR
        t += step
        times.append(round(t, 6))
        performed.append(round(performed[-1] + step * tempo(bar), 6))
    dynamics = [[round(t, 6), round(level(1 + t / BAR), 3)] for t in times]
    # the pedal: changed (lifted 60 ms) on each beat, or each bar through the arpeggios
    pedal = []
    beat = BAR / 3
    t = 0.0
    while t < end:
        bar = 1 + t / BAR
        span = BAR if any(a <= math.floor(bar) <= b for a, b in BAR_PEDAL) else beat
        pedal.append([round(t, 6), round(min(end, t + span) - 0.06, 6)])
        t += span
    annotation = dict(
        version=1,
        input_clock='deterministic interpreted score, v1 (no generic rubato or dynamics)',
        input_note_count=len(notes),
        input_sha256=performance_signature(notes),
        time_map=[[a, b] for a, b in zip(times, performed)],
        section_tracks={},
        section_levels={},
        dynamics=dynamics,
        effort_share=0.55,
        voicing=dict(melody_tracks=[1], melody_db=3.5, inner_db=-3.0, lower_tracks=[2], lower_db=-2.5),
        pedal=pedal,
        pedal_max_hold=6.0,
        spread_seconds=0.03,
        notes='Phrase-level rubato, dynamics, pedal and voicing for the Mutopia transcription; '
              'see tools/clair_performance.py for the plan, bar by bar.')
    path = ROOT / 'data/music' / f'{NAME}-performance.json'
    path.write_text(json.dumps(annotation, indent=1) + '\n')
    print(f'{path.name}: {len(times)} time points, {performed[-1]:.1f} s performed from {times[-1]:.1f} s; '
          f'{len(pedal)} pedal spans; level {min(v for _, v in dynamics):.1f} to {max(v for _, v in dynamics):.1f} dB')


if __name__ == '__main__':
    main()
