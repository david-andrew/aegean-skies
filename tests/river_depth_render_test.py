"""The two-sided native river prepass hides deep bed shading, retaining shallows."""
import os
from pathlib import Path
import subprocess
import tempfile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

def main():
    scratch = Path.home() / 'dev/tmp/aegean-skies/river-depth-test'
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as folder:
        shot = Path(folder) / 'depth.png'
        env = {k: v for k, v in os.environ.items() if k not in ('DISPLAY', 'WAYLAND_DISPLAY')}
        env.update(SLOPPY_NO_AUDIO='1', SLOPPY_THREADS='1', SLOPPY_FRAMES='2',
                   SLOPPY_SCREENSHOT=str(shot), SLOPPY_SAVE_DIR=folder)
        subprocess.run(['sloppy', '--release', 'tools/river_depth_check.jo'], cwd=ROOT, env=env, check=True)
        with Image.open(shot) as image:
            pixels = list(image.convert('RGB').getdata())
        hidden = sum(max(p) < 10 for p in pixels)
        shallow = sum(r > 240 and g < 10 and b < 10 for r, g, b in pixels)
        assert hidden > 5000 and shallow > 5000, (hidden, shallow)
        print(f'Native water prepass: {hidden} hidden-bed pixels; {shallow} visible shallow-bed pixels')

if __name__ == '__main__':
    main()
