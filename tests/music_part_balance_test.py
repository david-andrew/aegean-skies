"""The part balance: its loudness measure, the roles it reads from the notes, its two steps, and
the balance recorded for every piece of the catalogue."""
import json, math, struct, sys, unittest, zlib
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import music_part_balance as pb
import music_pack as mp
from music_balance import lufs

STRINGS, CLARINET, HARP, ACCORDION, DRUMS = 0, 4, 7, 9, 12


def tone(hz, level=0.1, seconds=4, rate=pb.RATE):
    return level * np.sin(2 * np.pi * hz * np.arange(int(rate * seconds)) / rate)


def loudness(x): return pb.gated_lufs(pb.block_powers(pb.k_weighted(x)))


def band():
    """A tune (strings, staff 0), an accordion doubling it an octave below, a guitar bass on the
    beats, a clarinet holding chords in the tune's register, and a drum: 32 s."""
    notes = []
    for k in range(64):
        pitch = 72 + [0, 2, 4, 5, 7, 5, 4, 2][k % 8]
        notes.append([k * 0.5, 0.45, pitch, STRINGS, .8, .8, 0])
        notes.append([k * 0.5, 0.45, pitch - 12, ACCORDION, .3, .3, 0])
        if k % 2 == 0: notes.append([k * 0.5, 0.9, 40 + [0, 5, 7, 5][k // 2 % 4], HARP, .7, .7, 1])
        if k % 8 == 0:
            for chord in (64, 67): notes.append([k * 0.5, 3.9, chord, CLARINET, .5, .5, 2])
        notes.append([k * 0.5, 0.1, 38, DRUMS, .4, .4, 9])
    return notes


class Loudness(unittest.TestCase):
    def test_k_weighting_at_the_synths_rate_agrees_with_the_standards_48k_filter(self):
        self.assertAlmostEqual(loudness(tone(997, 1.0)), -3.0, delta=0.3)
        for hz in (110, 440, 997, 2500):
            self.assertAlmostEqual(loudness(tone(hz)), lufs(tone(hz, rate=48000)), delta=0.25, msg=hz)

    def test_the_gate_measures_a_part_only_where_it_plays(self):
        playing = tone(440)
        resting = np.concatenate([playing, np.zeros(len(playing) * 3)])
        self.assertAlmostEqual(loudness(resting), loudness(playing), delta=0.3)


class Roles(unittest.TestCase):
    def setUp(self):
        self.parts = pb.split_parts(band())
        self.names = list(self.parts)
        self.role, self.median, self.leads = pb.read_roles(self.parts, 32.0)

    def test_parts_are_instruments_on_their_staves(self):
        self.assertEqual(self.names, ['strings@0', 'accordion@0', 'harp', 'clarinet@2', 'drums'])

    def test_each_part_gets_its_role(self):
        main = {p: pb.ROLES[int(np.bincount(self.role[k][self.role[k] >= 0]).argmax())] for k, p in enumerate(self.names)}
        self.assertEqual(main, {'strings@0': 'melody', 'accordion@0': 'doubling', 'harp': 'bass', 'clarinet@2': 'harmony',
                                'drums': 'percussion'})
        self.assertTrue((self.leads == 0).all())

    def test_a_held_note_on_top_is_not_the_tune(self):
        notes = [n for n in band() if n[3] != CLARINET] + [[0.0, 31.5, 96, CLARINET, .5, .5, 2]]
        parts = pb.split_parts(notes)
        role, _, leads = pb.read_roles(parts, 32.0)
        self.assertEqual(list(parts)[int(np.bincount(leads[1:]).argmax())], 'strings@0')


    def test_a_staff_marked_as_the_melody_leads_under_the_top_line(self):
        # a singer's line (clarinet, staff 2, moving) under the strings' figures
        notes = [n for n in band() if n[3] not in (CLARINET, ACCORDION)]
        notes += [[k * 1.0, 0.9, 60 + [0, 2, 3, 5][k % 4], CLARINET, .9, .9, 2] for k in range(32)]
        parts = pb.split_parts(notes)
        names = list(parts)
        _, _, plain = pb.read_roles(parts, 32.0)
        _, _, marked = pb.read_roles(parts, 32.0, {2})
        self.assertTrue((plain == names.index('strings@0')).all())
        self.assertTrue((marked == names.index('clarinet@2')).all())


class Steps(unittest.TestCase):
    def setUp(self):
        self.parts = pb.split_parts(band())
        self.role, self.median, self.leads = pb.read_roles(self.parts, 32.0)
        self.percussion = np.array([False, False, False, False, True])
        windows = self.role.shape[1]
        # (the tune at -28, its doubling buried, the bass firm, the chords buried, the drum)
        self.levels = np.array([[-28.0] * windows, [-54.0] * windows, [-33.0] * windows, [-50.0] * windows, [-45.0] * windows])

    def test_buried_parts_are_raised_to_the_floor_and_nothing_is_lowered(self):
        gains = pb.solve_shape(self.role, self.median, self.leads, self.levels, self.percussion)
        self.assertAlmostEqual(gains[1], 54 - 28 - pb.DOUBLING_FLOOR_LU, delta=0.01)
        self.assertGreater(gains[3], 5.0)
        self.assertEqual((gains[0], gains[2], gains[4]), (0.0, 0.0, 0.0))
        level = self.levels[3, 0] + gains[3]
        self.assertGreaterEqual(level, self.levels[2, 0] - pb.SHAPE_FLOOR_LU - 2.0 - pb.REGISTER_LU - 0.01)

    def test_one_dominant_voice_does_not_bury_the_rest(self):
        # three chord parts level with each other and a fourth far over them: nothing is raised
        role = np.array([[0] * 4, [3] * 4, [3] * 4, [3] * 4, [3] * 4], np.int8)
        median = np.array([[84.0] * 4, [60.0] * 4, [62.0] * 4, [64.0] * 4, [55.0] * 4])
        levels = np.array([[-30.0] * 4, [-44.0] * 4, [-45.0] * 4, [-44.5] * 4, [-28.0] * 4])
        gains = pb.solve_shape(role, median, np.zeros(4, int), levels, np.zeros(5, bool))
        self.assertFalse(gains.any())

    def test_parts_within_reason_are_left(self):
        levels = self.levels.copy(); levels[1] = -32.0; levels[3] = -36.0
        self.assertFalse(pb.solve_shape(self.role, self.median, self.leads, levels, self.percussion).any())

    def test_the_melody_over_the_rest_counts_doublings_with_the_tune(self):
        over = pb.melody_over_rest(self.role, self.leads, self.levels, np.zeros(5), self.percussion)
        front = 10 ** -2.8 + 10 ** -5.4; behind = 10 ** -3.3 + 10 ** -5.0
        self.assertAlmostEqual(over, 10 * math.log10(front / behind), delta=0.01)

    def test_the_gains_keep_the_mix_as_loud_and_the_percussion_where_it_was(self):
        rng = np.random.default_rng(1)
        powers = [pb.block_powers(pb.k_weighted(rng.normal(0, a, pb.RATE * 8))) for a in (.1, .01, .05, .02, .03)]
        gains = pb.neutral(np.array([0.0, 12.0, 6.0, 9.0, 0.0]), powers, self.percussion)
        before = pb.gated_lufs(sum(powers)); after = pb.gated_lufs(sum(p * 10 ** (g / 10) for p, g in zip(powers, gains)))
        self.assertAlmostEqual(before, after, delta=0.02)
        self.assertEqual(gains[4], 0.0)
        self.assertAlmostEqual(gains[1] - gains[0], 12.0, delta=1e-6)

    def test_a_tune_far_over_a_dull_bass_is_brought_in_but_never_under_it(self):
        seconds = 32
        tune = pb.k_weighted(sum(tone(523 * h, 0.1 / h, seconds) for h in range(1, 9)))
        bass = pb.k_weighted(sum(tone(98 * h, 0.004 / h, seconds) for h in range(1, 3)))
        role = np.array([[0] * 8, [4] * 8], np.int8); leads = np.zeros(8, int); none = np.array([False, False])
        bands = [pb.band_powers(tune), pb.band_powers(bass)]
        levels = pb.window_levels([pb.block_powers(tune), pb.block_powers(bass)], 8)
        self.assertGreater(pb.partial_lu(bands, role, leads), pb.MELODY_PARTIAL[1] + 5)
        gains, move = pb.solve_melody(role, leads, bands, levels, np.zeros(2), none)
        self.assertGreater(gains[1] - gains[0], 8.0)
        after = pb.melody_over_rest(role, leads, levels, gains, none)
        self.assertGreaterEqual(after, pb.MELODY_FLOOR_LU - 0.05)
        partial = pb.partial_lu(bands, role, leads, gains)
        self.assertTrue(abs(after - pb.MELODY_FLOOR_LU) < 0.1 or abs(partial - (pb.MELODY_PARTIAL[1] - pb.MELODY_INSIDE)) < 0.2)

    def test_a_tune_inside_the_band_is_left(self):
        seconds = 32
        tune = pb.k_weighted(sum(tone(523 * h, 0.05 / h, seconds) for h in range(1, 9)))
        chords = pb.k_weighted(sum(tone(f, 0.02, seconds) for f in (262, 330, 392, 660)))
        role = np.array([[0] * 8, [3] * 8], np.int8); leads = np.zeros(8, int); none = np.array([False, False])
        bands = [pb.band_powers(tune), pb.band_powers(chords)]
        levels = pb.window_levels([pb.block_powers(tune), pb.block_powers(chords)], 8)
        middle = sum(pb.MELODY_PARTIAL) / 2
        trim = min(np.arange(-30, 30, 0.5), key=lambda t: abs(pb.partial_lu(bands, role, leads, np.array([t, 0.0])) - middle))
        start = np.array([trim, 0.0])
        self.assertTrue(pb.MELODY_PARTIAL[0] < pb.partial_lu(bands, role, leads, start) < pb.MELODY_PARTIAL[1])
        gains, move = pb.solve_melody(role, leads, bands, levels, start, none)
        self.assertEqual(move, 0.0)


class Catalogue(unittest.TestCase):
    """What is committed: every piece balanced, by hand or by the tool, on the notes it now has."""
    def setUp(self):
        self.balance = json.loads((ROOT / 'data/music/part-balance.json').read_text())
        self.performance = json.loads((ROOT / 'data/music/performance.json').read_text())
        self.catalogue = json.loads((ROOT / 'data/music/catalogue.json').read_text())

    def test_every_piece_has_a_fresh_balance(self):
        for piece in self.catalogue:
            record = self.performance[piece['id']]['part_balance']
            self.assertIn(record['status'], ('balanced', 'in balance', 'one part', 'hand-set', 'kept'),
                          f"{piece['id']}: run tools/music_part_balance.py {piece['id']}, then tools/music_pack.py")
            self.assertEqual(piece['balance'], record['status'])

    def test_hand_set_pieces_are_respected(self):
        for name in mp.HAND_SET_BALANCE:
            if name not in self.performance: continue      # (a name the piece does not have yet, or no longer)
            self.assertEqual(self.performance[name]['part_balance']['status'], 'hand-set')
            self.assertNotIn('gains_db', self.balance[name])
            self.assertNotIn('parts', self.performance[name]['part_balance'])

    def test_a_balance_a_piece_already_had_is_kept(self):
        for name in ('magnetic', 'el-choclo', 'ave-maria', 'adelita'):
            self.assertEqual(self.performance[name]['part_balance']['status'], 'kept')
            self.assertEqual(self.performance[name]['balance_db'], mp.kept_balance(name))
            self.assertNotIn('gains_db', self.balance[name])

    def test_gains_are_bounded_recorded_and_loudness_neutral(self):
        for name, entry in self.balance.items():
            if name not in self.performance: continue
            gains = entry.get('gains_db', {})
            self.assertEqual(bool(gains), entry['status'] == 'balanced', name)
            for part, gain in gains.items():
                self.assertLessEqual(abs(gain), pb.MAX_GAIN_DB + 3.0, f'{name} {part}')
                self.assertEqual(self.performance[name]['part_balance']['parts'][part]['gain_db'], gain)
                self.assertAlmostEqual(entry['parts'][part]['lufs'][1] - entry['parts'][part]['lufs'][0], gain, delta=0.11)
            self.assertAlmostEqual(entry['whole_lufs'][0], entry['whole_lufs'][1], delta=0.1, msg=name)
            flagged = [p for p, g in gains.items() if abs(g) > pb.SUSPICIOUS_DB]
            self.assertEqual(bool(flagged), 'suspicious' in entry, name)

    def test_the_balance_is_for_the_notes_as_they_are_and_is_in_the_packed_score(self):
        name = 'greek-sta-giannina'
        notes, _, _ = mp.build(name)
        entry = self.balance[name]
        self.assertEqual(entry['score'], mp.score_hash(notes))
        self.assertEqual(sorted(entry['parts']), sorted(set(mp.part_of(n) for n in notes)))
        raw = zlib.decompress((ROOT / 'data/music' / f'{name}.z').read_bytes(), -15)
        self.assertEqual(raw[:4], b'MUS3')
        want = {mp.NAMES.index(p.split('@')[0]): 10 ** (g / 20) for p, g in entry['gains_db'].items()}
        for i in range(struct.unpack_from('<I', raw, 4)[0]):
            ins = raw[16 + i * 16 + 9]; mix = struct.unpack_from('<H', raw, 16 + i * 16 + 12)[0] / 4096
            self.assertAlmostEqual(mix, want[ins], delta=0.001)

    def test_the_songs_the_balance_was_asked_for(self):
        # Sta Giannina and Ena poulaki: the tune no longer far over what is behind it, still in front
        for name in ('greek-sta-giannina', 'greek-ena-poulaki'):
            before, after = self.balance[name]['melody_over_rest_lu']
            self.assertGreater(before, 12.0)
            self.assertTrue(pb.MELODY_FLOOR_LU - 0.3 <= after <= 6.0, f'{name}: {after}')
            self.assertTrue(any(g > 8 for g in self.balance[name]['gains_db'].values()))


if __name__ == '__main__':
    unittest.main()
