"""Tests for the announcer analysis tools on procedural signals (no recordings needed).

    python -m unittest tools/voice_world/test_voice_world.py      (numpy, scipy)
"""
import os, sys, unittest, zlib, struct
import numpy as np
from scipy.signal import lfilter, freqz
sys.path.insert(0, os.path.dirname(__file__))
import world_analysis as wa
import vocoder as vc
import lts

FS = wa.RATE


def vowel(f0=130.0, seconds=1.0, formants=((700, 80), (1200, 90), (2600, 120), (3500, 200)), seed=1):
    n = int(FS * seconds)
    f = f0 * (1 + 0.03 * np.sin(2 * np.pi * 3 * np.arange(n) / FS))
    ph = np.cumsum(f / FS)
    p = np.zeros(n)
    p[np.nonzero(np.diff(np.floor(ph)))[0]] = 1
    A = np.array([1.0])
    for F, B in formants:
        r = np.exp(-np.pi * B / FS)
        A = np.convolve(A, [1, -2 * r * np.cos(2 * np.pi * F / FS), r * r])
    x = lfilter([1], A, p) + 0.002 * np.random.default_rng(seed).standard_normal(n)
    return x, f, A


class Analysis(unittest.TestCase):
    def test_f0_envelope_and_aperiodicity_of_a_synthetic_vowel(self):
        x, f, A = vowel()
        an = wa.analyse(x)
        t = an['times']
        true = np.interp(t, np.arange(len(x)) / FS, f)
        m = (an['f0'] > 0) & (t > 0.05) & (t < 0.95)
        self.assertGreater(m.mean(), 0.8)
        self.assertLess(np.median(np.abs(an['f0'][m] / true[m] - 1)), 0.01)
        self.assertTrue(np.all(np.median(an['ap'][m], 0) < 0.1))
        # envelope follows |H|^2 up to the pulse train's constant level (F0/fs)
        _, h = freqz([1], A, worN=wa.FFT // 2 + 1, fs=FS)
        env = an['env'][len(t) // 2]
        d = 10 * np.log10(env) - 10 * np.log10(np.abs(h) ** 2)
        at = [d[int(fr / FS * wa.FFT)] for fr in (500, 700, 1200, 2600, 3500)]
        self.assertLess(np.ptp(at), 6.0)

    def test_noise_is_unvoiced_and_mcep_round_trips(self):
        nz = np.random.default_rng(2).standard_normal(FS) * 0.1
        an = wa.analyse(nz)
        self.assertLess((an['f0'] > 0).mean(), 0.15)
        env = an['env'][40]
        back = wa.mcep_to_log_power(wa.envelope_to_mcep(env))
        err = 10 / np.log(10) * (back - np.log(env))
        self.assertLess(np.sqrt(np.mean(err ** 2)), 3.0)


class Vocoder(unittest.TestCase):
    def test_lattice_matches_direct_form(self):
        r = np.array([1.0, 0.8, 0.5, 0.2, 0.05, 0.0])
        k, e, a = vc.levinson(r, 4)
        x = np.random.default_rng(0).standard_normal(300)
        ref = lfilter([1], a, x)
        b = np.zeros(5)
        y = np.zeros(300)
        for s in range(300):
            f = x[s]
            for i in range(4, 0, -1):
                f = f - k[i - 1] * b[i - 1]
                b[i] = b[i - 1] + k[i - 1] * f
            b[0] = f
            y[s] = f
        self.assertLess(np.abs(y - ref).max(), 1e-9)

    def test_copy_synthesis_keeps_level_and_envelope(self):
        x, f, A = vowel()
        an = wa.analyse(x)
        y = vc.synthesize(an['f0'], an['mcep'], an['ap'])
        seg = slice(4000, 12000)
        ratio = np.sqrt(np.mean(y[seg] ** 2) / np.mean(x[seg] ** 2))
        self.assertGreater(ratio, 0.8)
        self.assertLess(ratio, 1.25)


class LetterToSound(unittest.TestCase):
    def test_rules_and_stress(self):
        # names read Greek-style: a = ah, e = eh, i/y = ee, o = oh, ou = oo; penultimate stress; no reduction
        self.assertEqual(lts.pronounce('kalyrassa'), ['K', 'AA0', 'L', 'IY0', 'R', 'AA1', 'S', 'AA0'])
        self.assertEqual(lts.pronounce('souvlaki'), ['S', 'UW0', 'V', 'L', 'AA1', 'K', 'IY0'])
        self.assertEqual(lts.pronounce('melav'), ['M', 'EH1', 'L', 'AA0', 'V'])
        import pack
        self.assertEqual(pack.MANUAL['kalamos'].split()[1], 'AA1')                 # Kálamos: the name's own stress
        for w in ['thalvery', 'melav', 'orenthessa', 'kryfo', 'nerav']:
            p = lts.pronounce(w)
            self.assertEqual(sum(1 for x in p if x.endswith('1')), 1, (w, p))
            self.assertTrue(all(x.rstrip('012') in __import__('pack').PHONES for x in p))


class Pack(unittest.TestCase):
    def test_tables_round_trip(self):
        import pack
        H = 6
        W = wa.ORDER + 1 + len(wa.BANDS) + 1
        rng = np.random.default_rng(3)
        units = {('pau', 'AA'): dict(frames=rng.standard_normal((2 * H, W)) * 0.3, count=3, left=0.04, right=0.06),
                 ('AA', 'pau'): dict(frames=rng.standard_normal((2 * H, W)) * 0.3, count=1, left=0.05, right=0.04)}
        for u in units.values():
            u['frames'][:, wa.ORDER + 1:] = np.clip(np.abs(u['frames'][:, wa.ORDER + 1:]), 0, 1)
        path = os.path.join(os.environ.get('TMPDIR', '.'), 'announcer-test.z')
        pack.pack(units, {'ah': ['AA1']}, path)
        raw = zlib.decompress(open(path, 'rb').read(), -15)
        os.remove(path)
        self.assertEqual(raw[:4], b'AVX1')
        self.assertEqual(struct.unpack_from('<H', raw, 4)[0], len(pack.PHONES))



class ModelGaps(unittest.TestCase):
    """A small pool can leave a model class without examples; packing must still work."""

    def fit(self):
        import pack
        sp = dict(weights={k: [0.1] * n for k, n in [('arc_stop', 10), ('arc_other', 10), ('accent_first', 13), ('accent_middle', 13),
                                                     ('accent_nuclear', 13), ('micro', 3)]},
                  lags=[round(-0.2 + 0.05 * i, 2) for i in range(13)], level_by_index={'0': -0.5, '1': 0.7}, level_spread=float('nan'))
        fit = dict(durations=dict(intercept_ms={p: 70.0 for p in pack.PHONES if p != 'pau'},
                                  factors={k: 1.0 for k in pack.DURATION_FACTORS}, elasticity={'stressed_vowel': -0.6, 'unstressed_vowel': -0.8},
                                  reference_rate=5.0),
                   fricatives={'S': dict(p90_ms=90.0, n=10)}, f0_st=dict(median=9.0), effort=dict(vector=[0.0] * 25),
                   pauses={'comma': dict(median_ms=120.0, n=8)}, superposition=sp)
        return fit, sp

    def test_missing_level_class_uses_prior_then_mean(self):
        import pack
        fit, sp = self.fit()
        prior = dict(superposition=dict(level_by_index={'0': 0.0, '1': 0.5, '2': 1.25}, level_spread=2.0),
                     pauses={'stop': dict(median_ms=400.0), 'none': dict(median_ms=160.0)}, durations=dict(elasticity={'onset': -0.4, 'coda': -0.3}))
        m = pack.model_numbers(fit, sp, prior)
        self.assertEqual(m['level'][2:], [-0.5, 0.7, 1.25])          # class 2 from the prior
        self.assertEqual(m['level'][1], 2.0)                         # NaN spread replaced by the prior's
        self.assertEqual(m['elasticity'], [-0.6, -0.8, -0.4, -0.3])
        self.assertAlmostEqual(m['pauses'][1], 0.4)
        m2 = pack.model_numbers(fit, sp)                             # no prior: mean of the present classes
        self.assertAlmostEqual(m2['level'][4], 0.1)
        for k, v in m2.items():
            self.assertTrue(all(np.isfinite(x) for x in v), k)

    def test_pack_round_trip_with_missing_class(self):
        import pack, voicefile
        fit, sp = self.fit()
        H = 6
        W = wa.ORDER + 1 + len(wa.BANDS) + 1
        f = np.zeros((2 * H, W)); f[:, wa.ORDER + 1:] = 0.5
        units = {('pau', 'AA'): dict(frames=f, count=2, left=0.04, right=0.06), ('AA', 'pau'): dict(frames=f, count=2, left=0.05, right=0.04)}
        path = os.path.join(os.environ.get('TMPDIR', '.'), 'gaps-test.z')
        pack.pack(units, {'ah': ['AA1']}, path, pack.model_numbers(fit, sp))
        v = voicefile.read(path)
        os.remove(path)
        self.assertEqual(len(v['model']['level']), 5)
        self.assertTrue(all(np.isfinite(x) for x in v['model']['level']))

    def test_breath_band_is_packed_only_when_fitted(self):
        import pack
        fit, sp = self.fit()
        self.assertNotIn('breath_band', pack.model_numbers(fit, sp))
        fit['breath_band'] = [0.3, 0.4, 0.7, 0.6, 1.0]
        self.assertEqual(pack.model_numbers(fit, sp)['breath_band'], [0.3, 0.4, 0.7, 0.6, 1.0])
        fit['breath_band'] = [0.3, float('nan'), 0.7, 0.6, 1.0]
        self.assertNotIn('breath_band', pack.model_numbers(fit, sp))

    def test_band_aperiodicity_of_voiced_frames(self):
        import tune_round as tr
        f0 = np.r_[np.zeros(100), np.full(300, 120.0)]
        ap = np.c_[np.full(400, 0.9), np.r_[np.full(100, 0.9), np.full(300, 0.2)]]
        self.assertEqual(tr.band_ap([dict(f0=f0, ap=ap)]), [0.9, 0.2])
        self.assertIsNone(tr.band_ap([dict(f0=f0[:150], ap=ap[:150])]))     # too few voiced frames


class Intonation(unittest.TestCase):
    def test_fitted_shapes_add_no_level(self):
        """Contours that rise well above the phrase level at every accent: the fitted shapes must
        not carry that rise into the level (the synthesizer adds them uncentred)."""
        import prosody_fit as pf
        rng = np.random.default_rng(4)
        data = []
        for i in range(60):
            dur = rng.uniform(0.7, 1.1)
            t = np.arange(0, dur, 0.005)
            acc = [(a, a + 0.12) for a in np.sort(rng.uniform(0.05, dur - 0.3, rng.integers(1, 3)))]
            s = 12.0 + 0.01 * rng.standard_normal(len(t))
            for a, b in acc:
                s += 5.0 / (1 + np.exp(-(t - a - 0.05) / 0.03))             # a rise held after the accent
            data.append(dict(t=t, s=s, acc=acc, dur=dur, punct='stop' if i % 2 else 'comma', test=i % 5 == 4, rows=[], index=i % 3))
        sp = pf.fit_superposition(data)
        w = np.concatenate([sp['weights'][k] for k in ['arc_stop', 'arc_other', 'accent_first', 'accent_middle', 'accent_nuclear', 'micro']])
        added = [float(np.median(pf.design(d) @ w)) for d in data]
        self.assertLess(abs(np.median(added)), 0.3)
        self.assertGreater(max(sp['level_offset_removed_st'].values()), 0.5)    # there was a level to remove


class ProsodyGuard(unittest.TestCase):
    def test_more_data_wins_only_within_the_tolerance(self):
        import tune_round as tr
        acc = {'new': 0.80, 'mix': 0.85, 'before': 0.86}
        pick = lambda: tr.guard_prosody([(k, k) for k in ['new', 'mix', 'before']], lambda label, fit: acc[label])[0]
        self.assertEqual(pick(), 'mix')                 # 1 point below the best: more data wins
        acc['mix'] = 0.80
        self.assertEqual(pick(), 'before')              # 6 points below: keep what was there
        acc['new'] = 0.86
        self.assertEqual(pick(), 'new')


class SpeakerLexicon(unittest.TestCase):
    def test_most_frequent_realisation_and_systematic_substitutions(self):
        import tune_round as tr
        def take(words):
            ph = []
            for wi, (w, prons) in enumerate(words):
                for p in prons.split():
                    base, st = (p[:-1], int(p[-1])) if p[-1].isdigit() else (p, 0)
                    ph.append(dict(p=base, stress=st, wi=wi, word=w, confidence=0.9))
            return (dict(id='x'), dict(phones=ph), None)
        sub = [take([('chalk', 'CH AO1 K'), ('on', 'AO1 N')]), take([('chalk', 'CH AO1 K')]), take([('chalk', 'CH AA1 K')])]
        sub += [take([('on', 'AO1 N')]) for _ in range(14)]
        own, seen = tr.speaker_lexicon(sub)
        self.assertEqual(own['chalk'], ['CH', 'AO1', 'K'])
        base = {'chalk': ['CH', 'AA1', 'K'], 'on': ['AA1', 'N'], 'father': ['F', 'AA1', 'DH', 'ER0']}
        lex, n, rules = tr.speaker_lex(base, sub)
        self.assertEqual(rules, {'AA1': 'AO1'})                  # 15 of 18 AA1 tokens said as AO1
        self.assertEqual(lex['father'], ['F', 'AO1', 'DH', 'ER0'])  # applied to a word not said


class Intonation2(unittest.TestCase):
    def test_breaks_tones_and_features_match_the_game(self):
        import intonation as it, phone_align as pa
        repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        fn, br = it.game_lists(repo)
        w = it.words_and_breaks("The crew? Off… safe. And the harbor and the boats and the men and the guns", pa.number_words, fn, br)
        self.assertEqual([x[2] for x in w[:4]], [0, 2, 5, 1])
        self.assertIn(it.BREATH, [x[2] for x in w])                 # a long run breathes before "and"
        self.assertEqual(w[-1][2], it.FINAL)
        ph = [dict(p=p, stress=1 if p == 'UW' else 0, wi=i, start=0.1 * k, end=0.1 * k + 0.08)
              for k, (i, p) in enumerate([(0, 'AH'), (1, 'UW'), (2, 'AO'), (3, 'EY')])]
        sy = it.syllables(w, ph)
        self.assertEqual([s['tone'] for s in sy], [2, 2, 5, 1])
        self.assertEqual([s['sentence'] for s in sy], [0, 0, 1, 1])
        self.assertTrue(sy[1]['nuclear'] and sy[1]['first'])
        self.assertEqual(len(it.features(sy[0], 'war')), it.NF)


if __name__ == '__main__':
    unittest.main()
