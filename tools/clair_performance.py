"""Clair de lune as a pianist would shape it: writes data/music/clair-de-lune-performance.json.

The Mutopia transcription plays every note at one velocity, in strict time. This plan, bar by bar
(72 bars of 9/8; quarter = 1 s in the MIDI, so a bar is 4.5 s of score time), gives it:

* its tempo from the general expressive-timing system (tools/expressive_timing.py): an intensity
  curve measured from the score (density, motion, register, tension, the dynamics below, the
  melody's rise) moves it on where the music flows and builds and broadens it at peaks and
  cadences, within the pace of the score's own tempo markings (Un poco mosso, En animant,
  Calmato, Tempo I, morendo), with a bounded, seeded variation;
* wide dynamics: a pp opening, the swell through the Un poco mosso arpeggios to the ff of En
  animant, a hushed return, fading to nothing;
* the sustain pedal changed with each harmony (each beat in the chordal sections, each bar
  through the arpeggios);
* the melody voiced a little over the accompaniment (the left hand kept up with it), each
  arpeggio shaped as one gesture across both hands, and chords spread a little from the bass up.

Run after any change to the score or the generic reading:
  python tools/clair_performance.py && python tools/music_pack.py
"""
from pathlib import Path
import json, math
from music_pack import ROOT, read_midi, arrange
from music_performance import score_clock, interpret, performance_signature
from expressive_timing import ExpressiveTiming, timing_map

NAME = 'clair-de-lune'
BAR = 4.5                           # score seconds per bar
BARS = 72

# The timing: the score's tempo markings (rate factors: below 1 is faster) and the system's
# few parameters; everything within a section comes from the measured intensity.
TIMING = ExpressiveTiming(
    base=0.98, min_rate=0.64, max_rate=1.5, sensitivity=1.0, flow=0.75, build=0.15, peak=0.1,
    cadence=0.08, final_ritard=0.6, variation=0.03, seed=7, phrase_bars=2,
    # only what the printed score marks; within each section the intensity shapes it
    tempo_marks=[(1, 1.0),       # Andante très expressif
                 (15, 0.94),     # peu à peu cresc. et animé
                 (27, 0.84),     # Un poco mosso
                 (37, 0.86),     # En animant
                 (43, 1.12),     # Calmato
                 (51, 1.0),      # Tempo I
                 (66, 1.1)])     # morendo jusqu'à la fin

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
    # the dynamics, as the score marks them, on eighth notes
    step = BAR / 9
    times = [round(k * step, 6) for k in range(int((end + BAR) / step) + 1)]
    dynamics = [[t, round(level(1 + t / BAR), 3)] for t in times]
    # the tempo, from the intensity those and the notes make
    time_map, curves = timing_map(notes, score_clock(source, NAME), TIMING, markings=dynamics)
    performed = [p[1] for p in time_map]
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
        time_map=time_map,
        section_tracks={},
        section_levels={},
        dynamics=dynamics,
        effort_share=0.55,
        voicing=dict(melody_tracks=[1], melody_db=2.0, inner_db=-1.0, lower_tracks=[2], lower_db=0.5, held_seconds=0.9),
        arpeggios=dict(gap=0.55, long_seconds=0.9, min_notes=5, rise_db=2.5, base_db=0.0),
        pedal=pedal,
        pedal_max_hold=6.0,
        spread_seconds=0.03,
        notes='Phrase-level rubato, dynamics, pedal and voicing for the Mutopia transcription; '
              'see tools/clair_performance.py for the plan, bar by bar.')
    path = ROOT / 'data/music' / f'{NAME}-performance.json'
    path.write_text(json.dumps(annotation, indent=1) + '\n')
    # (CLAIR_CURVES=path: the intensity and tempo curves, for plotting)
    import os
    if os.environ.get('CLAIR_CURVES'): Path(os.environ['CLAIR_CURVES']).write_text(json.dumps(dict(beats=curves['beats'], intensity=[round(v, 4) for v in curves['intensity']], rate=[round(v, 4) for v in curves['rate']], time_map=time_map)) + '\n')
    print(f'{path.name}: {len(time_map)} time points, {performed[-1]:.1f} s performed from {time_map[-1][0]:.1f} s; '
          f'{len(pedal)} pedal spans; level {min(v for _, v in dynamics):.1f} to {max(v for _, v in dynamics):.1f} dB')


if __name__ == '__main__':
    main()
