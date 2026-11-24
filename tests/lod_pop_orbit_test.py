"""Level-of-detail pop and far-land stability check under camera rotation:
runs tools/lod_pop_check.jo along the close canopy orbit and a 360-degree pan so
far-land vanishing, height popping, or coarse-ancestor collapse under rotation
fails CI immediately.
"""
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ORBITS = {
    'canopy orbit 28m': ('-128440 154 -130050 28 24', '960', '1680'),
    'pan 800m': ('-126000 800 -128000 0 20 -0.10', '720', '1320'),
}


def main():
    env = dict(os.environ, SLOPPY_SOFTWARE='1', SLOPPY_NO_AUDIO='1', SLOPPY_THREADS='1')
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'AEGEAN_POP_PATH', 'AEGEAN_POP_ORBIT',
                'AEGEAN_POP_FIRST', 'AEGEAN_POP_FRAMES', 'AEGEAN_POP_SLICE', 'AEGEAN_POP_DEBUG'):
        env.pop(key, None)
    for name, (orbit, first, frames) in ORBITS.items():
        run_env = dict(env, AEGEAN_POP_ORBIT=orbit, AEGEAN_POP_FIRST=first, AEGEAN_POP_FRAMES=frames)
        done = subprocess.run(['sloppy', '--release', 'tools/lod_pop_check.jo'], cwd=ROOT, env=run_env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        lines = [line for line in done.stdout.splitlines() if line.startswith('LOD POP')]
        assert done.returncode == 0 and lines and lines[-1].startswith('LOD POP PASS'), \
            f'{name}: LOD pop or far-land instability\n' + '\n'.join(lines or done.stdout.splitlines()[-20:])
        print(f'{name}: {lines[-1]}')


if __name__ == '__main__':
    main()
