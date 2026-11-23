"""Grace notes: found in a piece's notes and played as acciaccaturas and appoggiaturas."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from music_grace import find_graces, regrace, ACCIACCATURA_S, APPOGGIATURA_MIN, APPOGGIATURA_MAX
from music_performance import BeatMap

STR = 6      # the piano
CLOCK = BeatMap([(0.0, 0.0, 0.5)], 4)      # 120 to the minute: a beat is half a second


def note(start, dur, pitch, track=1, g=0.6):
    return [start, dur, pitch, STR, g, g, track]


class GraceTests(unittest.TestCase):
    def test_a_quick_note_before_a_short_note_is_an_acciaccatura_just_before_the_beat(self):
        # a LilyPond grace: 27 ms, ending where the main note begins, over a held note
        notes = [note(0.0, 1.0, 72), note(1.0 - 0.027, 0.027, 76), note(1.0, 0.25, 74), note(1.25, 0.5, 72)]
        found = find_graces(notes)
        self.assertEqual([(k, g, m) for k, g, m in found], [('acciaccatura', [1], 2)])
        out, counts = regrace(notes, clock=CLOCK)
        self.assertEqual(counts['acciaccatura'], 1)
        grace = next(n for n in out if n[2] == 76)
        main = next(n for n in out if n[2] == 74)
        # a quick note of 40-70 ms that ends at the beat, the main note on the beat as written
        self.assertTrue(ACCIACCATURA_S[0] - 1e-9 <= grace[1] <= ACCIACCATURA_S[1] + 1e-9)
        self.assertAlmostEqual(grace[0] + grace[1], 1.0, places=6)
        self.assertAlmostEqual(main[0], 1.0, places=6)
        # the note before it gave up the time
        before = next(n for n in out if n[2] == 72)
        self.assertLessEqual(before[0] + before[1], grace[0] + 1e-9)
        # heard, not forward
        self.assertLessEqual(grace[4], main[4])
        self.assertGreater(grace[4], 0.8 * main[4])

    def test_a_step_before_a_long_note_is_an_appoggiatura_on_the_beat_taking_its_time_from_the_main_note(self):
        notes = [note(0.0, 1.0, 70), note(1.0 - 0.05, 0.05, 77), note(1.0, 1.6, 75)]
        out, counts = regrace(notes, clock=CLOCK)
        self.assertEqual((counts['appoggiatura'], counts['acciaccatura']), (1, 0))
        grace = next(n for n in out if n[2] == 77)
        main = next(n for n in out if n[2] == 75)
        self.assertAlmostEqual(grace[0], 1.0, places=6)
        self.assertTrue(APPOGGIATURA_MIN <= grace[1] <= APPOGGIATURA_MAX)
        self.assertAlmostEqual(main[0], grace[0] + grace[1], places=6)
        self.assertAlmostEqual(main[0] + main[1], 2.6, places=6)       # the main note ends where it was written to end

    def test_an_appoggiatura_takes_a_quarter_of_the_main_note(self):
        notes = [note(0.0, 1.0, 70), note(1.0 - 0.05, 0.05, 77), note(1.0, 0.8, 75)]
        out, _ = regrace(notes, clock=CLOCK)
        grace = next(n for n in out if n[2] == 77)
        self.assertAlmostEqual(grace[1], 0.2, places=6)

    def test_a_violin_acciaccatura_is_longer_than_a_pianos(self):
        def grace_length(ins):
            notes = [[0.0, 1.0, 72, ins, .6, .6, 1], [1.0 - 0.027, 0.027, 76, ins, .6, .6, 1], [1.0, 0.25, 74, ins, .6, .6, 1], [1.25, 0.5, 72, ins, .6, .6, 1]]
            out, _ = regrace(notes, clock=CLOCK)
            return next(n for n in out if n[2] == 76)[1]
        self.assertLessEqual(grace_length(6), ACCIACCATURA_S[1] + 1e-9)       # the piano
        self.assertGreaterEqual(grace_length(0), 0.1)                         # the violin

    def test_a_run_of_written_notes_is_not_a_grace_note(self):
        # eight sixteenths, then a long note: a run, not a grace note
        notes = [note(i * 0.125, 0.12, 60 + i) for i in range(8)] + [note(1.0, 1.0, 70)]
        self.assertEqual(find_graces(notes, beat_s=lambda t: 0.5), [])
        # a written trill (two notes alternating) before a note is the composer's figure too
        notes = [note(0.0, 0.5, 60)] + [note(0.5 + i * 0.05, 0.05 - 0.004, 73 + 2 * (i % 2)) for i in range(4)] + [note(0.7, 0.4, 71)]
        self.assertEqual(find_graces(notes, beat_s=lambda t: 0.5), [])
        # a dotted figure (a sixteenth after a dotted eighth) is rhythm too
        notes = [note(0.0, 0.375, 60), note(0.375, 0.125, 62), note(0.5, 0.5, 64)]
        self.assertEqual(find_graces(notes, beat_s=lambda t: 0.5), [])

    def test_a_group_of_quick_notes_shares_the_time(self):
        notes = [note(0.0, 0.9, 70), note(0.92, 0.04, 74), note(0.96, 0.04, 72), note(1.0, 0.3, 70)]
        out, counts = regrace(notes, clock=CLOCK)
        self.assertEqual(counts['notes'], 2)
        g = sorted((n for n in out if n[2] in (74, 72)), key=lambda n: n[0])
        self.assertLessEqual(g[-1][0] + g[-1][1], 1.0 + 1e-9)
        self.assertGreater(g[1][0], g[0][0])
        self.assertLessEqual(1.0 - g[0][0], 0.15)

    def test_a_lilypond_two_six_grace_note_that_rings_through_its_main_note_is_cut_short(self):
        notes = [note(1.0 - 0.065, 0.25, 68), note(1.0, 0.25, 69)]     # sounds from 65 ms before the beat, and through it
        self.assertEqual(find_graces(notes), [])                  # generic reading leaves a long overlap alone
        out, counts = regrace(notes, overlapped=True, clock=CLOCK)
        self.assertEqual(counts['acciaccatura'], 1)
        grace = next(n for n in out if n[2] == 68)
        self.assertLessEqual(grace[1], ACCIACCATURA_S[1] + 1e-9)


if __name__ == '__main__':
    unittest.main()
