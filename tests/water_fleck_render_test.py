"""Exact inland hash-cache GPU check, including cold fill, wrap and teleport."""
import os
from pathlib import Path
import subprocess
import tempfile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    scratch = Path.home() / 'dev/tmp/aegean-skies/water-fleck-test'
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as folder:
        env = {k: v for k, v in os.environ.items() if k not in ('DISPLAY', 'WAYLAND_DISPLAY')}
        env.update(SLOPPY_NO_AUDIO='1', SLOPPY_THREADS='1', SLOPPY_FRAMES='112',
                   SLOPPY_SCREENSHOT=str(Path(folder) / 'final.png'), FLECK_CHECK_FRAMES=folder,
                   SLOPPY_SAVE_DIR=folder)
        subprocess.run(['sloppy', '--release', 'tools/water_fleck_check.jo'], cwd=ROOT, env=env, check=True)
        for frame in (1, 31, 33, 40, 64, 65, 96, 110):
            with Image.open(Path(folder) / f'{frame:03}.png') as image:
                pixels = list(image.convert('RGB').getdata())
            assert all(g > 200 and r < 10 and b < 10 for r, g, b in pixels), f'Hash-cache mismatch or undrawn check at frame {frame}'
        print('Eight GPU checks: exact marks through cold fill, movement, ring wrap and teleport')


if __name__ == '__main__':
    main()
