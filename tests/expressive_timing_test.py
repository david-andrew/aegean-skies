"""Expressive timing from the score: flowing, building music moves on, sparse music and phrase
ends breathe, the variation is bounded and seeded, and arpeggios are one gesture across hands."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from music_performance import BeatMap, arpeggio_gestures
from expressive_timing import ExpressiveTiming, timing_map, warp


def score():
    # 3/4 at one beat a second: 8 bars of slow chords, 8 bars of running eighths, 8 of chords
    notes = []
    for bar in range(24):
        t0 = bar * 3.0
        if 8 <= bar < 16:
            for k in range(6):
                notes.append([t0 + k * 0.5, 0.45, 60 + (k * 4) % 19, 6, 0.6, 0.6, 2])
            notes.append([t0, 2.9, 79, 6, 0.6, 0.6, 1])
        else:
            for p in (48, 55, 64):
                notes.append([t0, 2.9, p, 6, 0.6, 0.6, 2])
            notes.append([t0, 2.9, 72, 6, 0.6, 0.6, 1])
    return notes


CLOCK = BeatMap([(0.0, 0.0, 1.0)], 3)


class ExpressiveTimingTests(unittest.TestCase):
    def test_flowing_music_moves_on_and_rates_stay_bounded(self):
        params = ExpressiveTiming(min_rate=0.7, max_rate=1.3, final_ritard=0.0, variation=0.0)
        points, curves = timing_map(score(), CLOCK, params)
        rates, beats = curves['rate'], curves['beats']
        middle = [r for b, r in zip(beats, rates) if 30 <= b < 42]
        outer = [r for b, r in zip(beats, rates) if b < 18]
        self.assertLess(sum(middle) / len(middle), sum(outer) / len(outer) * 0.95)
        self.assertTrue(all(0.7 <= r <= 1.3 + 1e-9 for r in rates))
        self.assertTrue(all(b[0] > a[0] and b[1] > a[1] for a, b in zip(points, points[1:])))

    def test_the_variation_is_seeded_and_bounded(self):
        a = timing_map(score(), CLOCK, ExpressiveTiming(seed=1, variation=0.03))[0]
        b = timing_map(score(), CLOCK, ExpressiveTiming(seed=1, variation=0.03))[0]
        c = timing_map(score(), CLOCK, ExpressiveTiming(seed=2, variation=0.03))[0]
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertLess(abs(a[-1][1] - c[-1][1]) / a[-1][1], 0.06)

    def test_the_markings_set_each_sections_pace(self):
        plain = timing_map(score(), CLOCK, ExpressiveTiming(variation=0.0))[1]
        marked = timing_map(score(), CLOCK, ExpressiveTiming(variation=0.0, tempo_marks=[(1, 1.0), (17, 1.2)]))[1]
        late = [m / p for b, m, p in zip(plain['beats'], marked['rate'], plain['rate']) if 52 <= b < 66]
        # (the soft limit eases a large factor a little)
        self.assertGreater(min(late), 1.08)

    def test_warp_keeps_order_and_ends(self):
        points = timing_map(score(), CLOCK, ExpressiveTiming())[0]
        out = warp(score(), points)
        self.assertEqual(len(out), len(score()))
        self.assertTrue(all(n[1] > 0 for n in out))

    def test_an_arpeggio_across_both_hands_is_one_gesture(self):
        # up through the left hand into the right, and down again; the right hand also holds a
        # melody in thirds (a chord in its hand: not part of the arpeggio)
        pitches = [40, 44, 47, 52, 56, 59, 64, 68, 71, 68, 64, 59]
        notes = [[k * 0.25, 0.2, p, 6, 0.5 if p < 60 else 0.9, 0.5 if p < 60 else 0.9, 2 if p < 60 else 1] for k, p in enumerate(pitches)]
        notes += [[0.0, 2.0, 76, 6, 0.9, 0.9, 1], [0.0, 2.0, 79, 6, 0.9, 0.9, 1]]
        g = arpeggio_gestures(notes, dict(gap=0.4, long_seconds=1.0, min_notes=5, rise_db=2.0))
        self.assertEqual(sorted(g), list(range(len(pitches))))
        touches = {round(g[i][1], 6) for i in g}
        self.assertEqual(len(touches), 1)
        steps = [abs(g[i + 1][0] - g[i][0]) for i in range(len(pitches) - 1)]
        self.assertLessEqual(max(steps), 1.0 + 1e-9)
        self.assertEqual(max(range(len(pitches)), key=lambda i: g[i][0]), 8)


if __name__ == '__main__':
    unittest.main()
