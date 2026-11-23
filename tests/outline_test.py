"""The land's outline drawn on the screen: tools/outline_check.jo (a far wooded slope: the
outline is there, is only crowns on a line, and is steady). Needs a real GPU, headless: the
software renderer draws no outline, so CI skips it (tools/ci_test_shard.py GPU_ONLY).
Run serially: python3 tests/outline_test.py. Requires Sloppy.
"""
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    scratch = Path.home() / 'dev/tmp/aegean-skies/outline-test'
    scratch.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, SLOPPY_NO_AUDIO='1', SLOPPY_THREADS='1', SLOPPY_SCREENSHOT=str(scratch / 'last.png'))
    for name in ('DISPLAY', 'WAYLAND_DISPLAY', 'SLOPPY_SOFTWARE', 'AEGEAN_OUTLINE', 'AEGEAN_OUTLINE_OUT'):
        env.pop(name, None)
    done = subprocess.run(['sloppy', '--release', 'tools/outline_check.jo'], cwd=ROOT, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    lines = [line for line in done.stdout.splitlines() if line.startswith('OUTLINE')]
    assert done.returncode == 0 and lines and lines[-1].startswith('OUTLINE PASS'), \
        'the land\'s outline\n' + '\n'.join(lines or done.stdout.splitlines()[-20:])
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
