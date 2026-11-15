"""The title reel's low pass must show the sea's speed flecks as flight does.
Run serially: python3 tests/title_reel_detail_test.py. Requires Pillow and Sloppy.

Renders a fixed frame of the reel's low pass (no menu) and a fixed frame of real flight at the
same speed (125 m/s), hour, weather and resolution, and compares the fine detail on the water
(pixels that differ from a 2-pixel blur, as tests/sea_detail_render_test.py counts it) in the band
below the horizon. The reel once drew a parked sea under a moving camera (no streaks, the flecks
at a third of their strength); this keeps it at flight's density.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import warnings
from PIL import Image, ImageChops, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
MINIMUM = 0.7          # (of flight's density; measured 2026-11-14 at 0.79-0.82 with the eye at
                       # 12-15 m; the parked sea it guards against measured 0.20-0.23)


def detail(path):
    with Image.open(path) as image:
        im = image.convert('RGB')
    w, h = im.size
    band = im.crop((0, int(h * 0.58), w, int(h * 0.76)))
    difference = ImageChops.difference(band, band.filter(ImageFilter.GaussianBlur(2)))
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        pixels = list(difference.getdata())
    return sum(max(p) > 3 for p in pixels) / len(pixels)


def render(work, name, frames, extra):
    shot = Path(work) / f'{name}.png'
    env = {k: v for k, v in os.environ.items() if k not in ('DISPLAY', 'WAYLAND_DISPLAY') and not k.startswith('AEGEAN_')}
    env.update(SLOPPY_NO_AUDIO='1', SLOPPY_THREADS='1', SLOPPY_SEED='12345', SLOPPY_WINDOW='1280x720',
               SLOPPY_FRAMES=str(frames), SLOPPY_SCREENSHOT=str(shot), SLOPPY_SAVE_DIR=str(Path(work) / name), **extra)
    subprocess.run(['sloppy', '--release', 'aegean.jo'], cwd=ROOT, env=env, check=True, stdout=subprocess.DEVNULL)
    return detail(shot)


def main():
    scratch = Path.home() / 'dev/tmp/aegean-skies/sea-detail-test'
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as work:
        flight = render(work, 'flight', 125, dict(AEGEAN_TITLE='0', AEGEAN_FLYING='8 125', AEGEAN_HOUR='10.69', AEGEAN_WEATHER='fair'))
        reel = render(work, 'reel', 400, dict(AEGEAN_TITLE='1', AEGEAN_TITLE_BARE='1', AEGEAN_TITLE_SHOT='low-free', AEGEAN_TITLE_SEED='4'))
    ratio = reel / max(flight, 1e-9)
    print(f'Title reel sea detail: reel {reel:.3f}, flight {flight:.3f}, ratio {ratio:.3f}')
    assert ratio >= MINIMUM, f'The reel low pass shows the sea parked: {ratio:.3f} of flight (at least {MINIMUM})'


if __name__ == '__main__':
    main()
