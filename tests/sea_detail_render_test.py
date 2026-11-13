"""Headless render guard for the approved three-scale circular sea painter.
Run serially: python3 tests/sea_detail_render_test.py. Requires Pillow and Sloppy.
The baseline was rendered from the 171834b painter in precision_view's reference path.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
from PIL import Image, ImageChops, ImageFilter

ROOT = Path(__file__).resolve().parents[1]

def main():
    baseline = json.loads((ROOT / 'tests/baselines/sea_detail.json').read_text())
    scratch = Path.home() / 'dev/tmp/aegean-skies/sea-detail-test'
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as work:
        shot = Path(work) / 'marks.png'
        env = dict(os.environ, DISPLAY='', WAYLAND_DISPLAY='', SLOPPY_NO_AUDIO='1',
                   SLOPPY_THREADS='1', SLOPPY_FRAMES='2', PRECISION_MARKS='1',
                   SLOPPY_WINDOW='640x360', SLOPPY_SCREENSHOT=str(shot), SLOPPY_SAVE_DIR=work)
        env.pop('DISPLAY', None)
        env.pop('WAYLAND_DISPLAY', None)
        env.pop('PRECISION_BEFORE', None)
        env.pop('PRECISION_AT', None)
        subprocess.run(['sloppy', 'tools/precision_view.jo'], cwd=ROOT, env=env, check=True)
        with Image.open(shot) as image:
            assert image.size == (baseline['width'], baseline['height'])
            pixels = list(image.convert('RGB').getdata())
        signal = sum(max(p)-128 > 32 or 128-min(p) > 32 for p in pixels)
        ratio = signal / baseline['contrast_pixels']
        assert abs(ratio-1) <= baseline['tolerance'], f'Sea detail changed: {signal} pixels, reference ratio {ratio:.3f}'
        print(f'Sea detail: {signal} contrast pixels; reference ratio {ratio:.3f}')
        # Exercise the actual material as well: a wind gate downstream of the
        # painter must not silently erase it. Fair-water baselines are from
        # 171834b; calm retains at least 40% despite losing wave/crest contrast.
        env.pop('PRECISION_MARKS')
        for hour, expected in baseline['material'].items():
            for wind in ['0', '6']:
                env.update(SEA_HOUR=hour, SEA_WIND=wind)
                subprocess.run(['sloppy', 'tools/sea_detail_view.jo'], cwd=ROOT, env=env, check=True)
                with Image.open(shot) as image:
                    crop = image.convert('RGB').crop(tuple(baseline['material_roi']))
                difference = ImageChops.difference(crop, crop.filter(ImageFilter.GaussianBlur(2)))
                count = sum(max(p) > 3 for p in difference.getdata())
                ratio = count / expected
                minimum = 0.4 if wind == '0' else 0.9
                assert minimum <= ratio <= 1.1, f'Sea material hour={hour} wind={wind}: {count}, ratio={ratio:.3f}'
                print(f'Sea material hour={hour} wind={wind}: {count}, reference ratio={ratio:.3f}')


if __name__ == '__main__':
    main()
