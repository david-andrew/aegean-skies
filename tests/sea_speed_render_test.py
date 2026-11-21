"""The drawn sea's waves move no faster than real ones of their length (docs/glossary: sea state).

Run serially: python3 tests/sea_speed_render_test.py. Requires numpy, Pillow and Sloppy.

tools/sea_speed_view.jo draws the sea alone, straight down, a frame every tenth of a second, over
the open sea, the strait, and the quay at Velyavasia (where on 2026-11-21 a full open sea ran through
the harbour like a river in flood), low for the short waves and high for the long. Each run's frames
are taken apart into plane waves (a 2D Fourier transform); how far each one's phase turns from frame
to frame is how fast that part of the picture travels. For every band of wavelengths that carries
real moving contrast, the contrast-weighted speed may not pass 1.3 times the speed of a real wave of
that length in that depth of water, c = sqrt(g L / 2 pi * tanh(2 pi d / L)). And the harbour is
calmer than the open sea: next to none of the long swell's moving contrast, and a slower picture.
The sea the floats ride has the same check without a picture: tests/sea_speed_test.jo.
"""
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
FRAMES = 24
TOLERANCE = 1.3
VELYAVASIA = '25012'
OUT_OF_HARBOUR = '9 -0.21 0.98'     # the report's wind: 9 m/s blowing out of Velyavasia's harbour
PLACES = {'open sea': {'SEA_PLACE': '60000 -90000'}, 'the strait': {'SEA_PLACE': '138000 -73000'},
          "Velyavasia's quay": {'SEA_HARBOUR': VELYAVASIA}}


def wave_speed(length, depth):
    return math.sqrt(9.8 * length / math.tau * math.tanh(math.tau * max(depth, 0.01) / length))


def view(work, env, place, height, wind):
    frames = Path(work) / 'frames'
    for old in frames.glob('*.png'):
        old.unlink()
    frames.mkdir(exist_ok=True)
    run = dict(env, SEA_FRAMES=str(frames), SEA_HEIGHT=str(height), SEA_WIND=wind,
               SLOPPY_FRAMES=str(FRAMES), **PLACES[place])
    out = subprocess.run(['sloppy', 'tools/sea_speed_view.jo'], cwd=ROOT, env=run, check=True,
                         capture_output=True, text=True).stdout
    said = re.search(r'SEAVIEW depth ([\d.]+) metres_per_pixel ([\d.]+) step ([\d.]+)', out)
    assert said, out[-2000:]
    stack = []
    for k in range(2, FRAMES + 1):
        with Image.open(frames / f'f{k:03}.png') as image:
            grey = np.asarray(image.convert('L'), dtype=np.float64)
        side = min(grey.shape)
        x0 = (grey.shape[1] - side) // 2
        stack.append(grey[:side, x0:x0 + side])
    return np.array(stack), float(said[1]), float(said[2]), float(said[3])


def measure(stack, depth, metres, step):
    """Wavelength bands of the moving picture: (low, high, share of the moving contrast, its
    speed, a real wave's speed there), and the whole picture's moving contrast and speed."""
    n = stack.shape[1]
    moving = stack - stack.mean(axis=0)
    hann = np.hanning(n)
    spectra = np.fft.fft2(moving * np.outer(hann, hann))
    cross = (spectra[1:] * np.conj(spectra[:-1])).sum(axis=0)
    weight = np.abs(cross)
    f = np.fft.fftfreq(n, d=metres)
    wavenumber = math.tau * np.hypot(*np.meshgrid(f, f))
    with np.errstate(divide='ignore', invalid='ignore'):
        length = math.tau / wavenumber
        speed = np.abs(np.angle(cross)) / step / wavenumber
    # (from four pixels a wave to two and a half waves across the picture)
    seen = (wavenumber > 0) & (length >= 4 * metres) & (length <= n * metres / 2.5)
    total = weight[seen].sum()
    bands = []
    low = 4 * metres
    while low < n * metres / 2.5:
        high = low * 2
        band = seen & (length >= low) & (length < high)
        if band.any() and weight[band].sum() > 0:
            share = weight[band].sum() / total
            mean = (speed[band] * weight[band]).sum() / weight[band].sum()
            real = wave_speed(math.sqrt(low * min(high, n * metres / 2.5)), depth)
            bands.append((low, high, share, mean, real))
        low = high
    return bands, total / (n * n) ** 2 / (stack.shape[0] - 1), (speed[seen] * weight[seen]).sum() / total, \
        weight[seen & (length >= 20)].sum() / (n * n) ** 2 / (stack.shape[0] - 1)


def main():
    scratch = Path.home() / 'dev/tmp/aegean-skies/sea-speed-test'
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as work:
        env = dict(os.environ, SLOPPY_NO_AUDIO='1', SLOPPY_THREADS='1', SLOPPY_WINDOW='480x270',
                   SLOPPY_SCREENSHOT=str(Path(work) / 'last.png'), SLOPPY_SAVE_DIR=work)
        env.pop('DISPLAY', None)
        env.pop('WAYLAND_DISPLAY', None)
        failures = []
        results = {}
        for place in PLACES:
            for height in (30, 250):
                stack, depth, metres, step = view(work, env, place, height, OUT_OF_HARBOUR)
                bands, contrast, speed, long_contrast = measure(stack, depth, metres, step)
                results[place, height] = (contrast, speed, long_contrast)
                print(f'{place}, from {height} m ({depth:.0f} m of water): moving contrast {contrast:.4f}, its speed {speed:.2f} m/s')
                for low, high, share, mean, real in bands:
                    carried = share >= 0.05
                    print(f'    {low:6.1f}-{high:6.1f} m: {share*100:5.1f}% of the moving contrast at {mean:5.2f} m/s; a real wave {real:5.2f} m/s (x{mean/real:.2f})' + ('' if carried else '  (too little to judge)'))
                    if carried and mean > TOLERANCE * real:
                        failures.append(f'{place}, {low:.1f}-{high:.1f} m waves drawn at {mean:.2f} m/s; a real one runs at {real:.2f} m/s')
        assert not failures, '; '.join(failures)
        # Harbour water is calmer than the open sea: of the long swell (20 m and more) next to
        # none of the open sea's moving contrast, and the picture by the quay travels slower.
        quay_long, open_long = results["Velyavasia's quay", 250][2], results['open sea', 250][2]
        assert quay_long <= 0.2 * open_long, f"the long swell's moving contrast at the quay {quay_long:.5f} against the open sea's {open_long:.5f}"
        quay, open_sea = results["Velyavasia's quay", 30], results['open sea', 30]
        assert quay[1] <= open_sea[1], f'the quay\'s picture travels at {quay[1]:.2f} m/s, the open sea\'s at {open_sea[1]:.2f} m/s'
        assert quay[0] <= open_sea[0], f'the quay\'s moving contrast {quay[0]:.4f} against the open sea\'s {open_sea[0]:.4f}'
        print(f"Harbour: long swell contrast {quay_long:.5f} against the open sea's {open_long:.5f}; picture speed {quay[1]:.2f} against {open_sea[1]:.2f} m/s")


if __name__ == '__main__':
    main()
