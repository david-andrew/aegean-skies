"""Cracks in the new world's ground: tools/terrain_crack_check.jo on the four flight paths the
level-of-detail pop check flies (.github/workflows/pages.yml), under software rendering.
Run serially: python3 tests/terrain_crack_test.py. Requires Sloppy.
"""
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
# (the woods glide, a low fast flight over hills, a mountain approach, in to a harbour along the coast)
PATHS = {
    'woods glide': None,
    'hills': '-118000 1250 -128000 0 0 -80 0 -0.1',
    'mountain': '-125000 900 -135000 70 -2 0 -1.5708 -0.12',
    'coast': '-118500 300 -85800 -29.5 -1.5 -34 0.7147 -0.12',
}


def main():
    env = dict(os.environ, SLOPPY_SOFTWARE='1', SLOPPY_NO_AUDIO='1', SLOPPY_THREADS='1')
    for name in ('DISPLAY', 'WAYLAND_DISPLAY', 'AEGEAN_POP_PATH', 'AEGEAN_CRACK_STILLS', 'AEGEAN_CRACK_OUT'):
        env.pop(name, None)
    for name, path in PATHS.items():
        run_env = dict(env)
        if path:
            run_env['AEGEAN_POP_PATH'] = path
        done = subprocess.run(['sloppy', '--release', 'tools/terrain_crack_check.jo'], cwd=ROOT, env=run_env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        lines = [line for line in done.stdout.splitlines() if line.startswith('TERRAIN CRACKS')]
        assert done.returncode == 0 and lines and lines[-1].startswith('TERRAIN CRACKS PASS'), \
            f'{name}: cracks in the ground\n' + '\n'.join(lines or done.stdout.splitlines()[-20:])
        print(f'{name}: {lines[-1]}')


if __name__ == '__main__':
    main()
