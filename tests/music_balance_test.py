"""The automatic balance's measures: BS.1770 loudness, masked partial loudness, harshness."""
import sys, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from music_balance import lufs, bands, partial_difference, harshness, melody_of

RATE = 48000
t = np.arange(RATE * 4) / RATE


class BalanceTests(unittest.TestCase):
    def test_a_full_scale_1k_sine_is_minus_three_lufs(self):
        self.assertAlmostEqual(lufs(np.sin(2 * np.pi * 997 * t)), -3.0, delta=0.3)
        self.assertAlmostEqual(lufs(0.1 * np.sin(2 * np.pi * 997 * t)), -23.0, delta=0.3)

    def test_partial_loudness_rises_with_the_melodys_gain_and_is_masked_by_its_band(self):
        melody = 0.2 * np.sin(2 * np.pi * 880 * t)
        near = 0.2 * np.sin(2 * np.pi * 900 * t)
        far = 0.2 * np.sin(2 * np.pi * 110 * t)
        em = bands(melody)
        a = partial_difference(em, bands(near)); b = partial_difference(em, bands(near), 6.0)
        self.assertGreater(b, a + 2.0)
        # an accompaniment in another band masks the melody less
        self.assertGreater(partial_difference(em, bands(far) * 4), partial_difference(em, bands(near) * 4) - 0.01)

    def test_harshness_sees_a_bright_part(self):
        body = sum(np.sin(2 * np.pi * f * t) / k for k, f in enumerate([440, 880, 1320], 1))
        bright = body + 0.8 * np.sin(2 * np.pi * 3500 * t)
        self.assertGreater(harshness(bright)['presence_db'], harshness(body)['presence_db'] + 10)
        self.assertGreater(harshness(bright)['sharpness'], harshness(body)['sharpness'])

    def test_the_melody_is_the_part_on_top(self):
        events = [(k * 0.5, 0.5, 76 + k % 3, 0) for k in range(20)] + [(k * 0.5, 0.5, 52, 7) for k in range(20)]
        melody, share, purity, others = melody_of(events, 20)
        self.assertEqual((melody, others), (0, [7]))
        self.assertGreater(share, 0.9)


if __name__ == '__main__':
    unittest.main()
