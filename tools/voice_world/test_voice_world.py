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
        self.assertEqual(lts.pronounce('station'), ['S', 'T', 'EY1', 'SH', 'AH0', 'N'])
        self.assertEqual(lts.pronounce('kalyrassa').count('AE1'), 1)
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


if __name__ == '__main__':
    unittest.main()
