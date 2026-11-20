"""Each piece's level, so the whole repertoire sits at one loudness.

The first thirteen pieces' levels were set by ear (tools/music_pack.py LEVEL). Every later piece is
rendered whole by the game's own synthesizer (tools/music_stems.jo, its level 1.0), its BS.1770
integrated loudness measured, and its level set so it sits at the median loudness of the
hand-set radio pieces. Writes data/music/levels.json (read by tools/music_pack.py; run that after)
and prints the table. With --check it measures every piece at its current level and fails when a
later piece is more than 1.5 LU from the target.

  python tools/music_level.py [--stems binary] [--jobs 2] [--check]
  (the binary: sloppy build tools/music_stems.jo --release -o stems; without it, sloppy runs it)
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse, json, math, os, subprocess, sys, tempfile
import numpy as np
from scipy.io import wavfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
from music_balance import lufs

ROOT = Path(__file__).resolve().parents[1]
RATE = 16000
HAND_SET = 13                       # the pieces whose level was set by ear
REFERENCE = [0, 2, 3, 4, 5, 6, 12]  # the hand-set radio pieces: their median is the target
TOLERANCE_LU = 1.5


def render(binary, index, seconds, out):
    env = dict(os.environ, MUSIC_PIECE=str(index), MUSIC_KEEP='all', MUSIC_SECONDS=f'{seconds:.2f}', MUSIC_OUT=str(out),
               SLOPPY_NO_AUDIO='1', SLOPPY_THREADS='1')
    env.pop('DISPLAY', None); env.pop('WAYLAND_DISPLAY', None)
    cmd = [binary] if binary else ['sloppy', '--release', str(ROOT / 'tools/music_stems.jo')]
    subprocess.run(cmd, env=env, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    rate, x = wavfile.read(out)
    x = x.astype(np.float64) / (32768.0 if x.dtype.kind == 'i' else 1.0)
    return lufs(x[:, 0] if x.ndim > 1 else x, rate)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stems', default='')
    p.add_argument('--jobs', type=int, default=2)
    p.add_argument('--check', action='store_true')
    a = p.parse_args()
    catalogue = json.loads((ROOT / 'data/music/catalogue.json').read_text())
    from music_pack import LEVEL
    with tempfile.TemporaryDirectory(dir=os.environ.get('MUSIC_SCRATCH')) as tmp:
        def one(i):
            return render(a.stems, i, catalogue[i]['frames'] / RATE, Path(tmp) / f'{i}.wav')
        with ThreadPoolExecutor(max(1, a.jobs)) as pool:
            loud = list(pool.map(one, range(len(catalogue))))
    target = float(np.median([loud[i] for i in REFERENCE]))
    levels, worst = {}, 0.0
    print(f'target {target:.1f} LUFS (the median of the hand-set radio pieces)')
    for i, r in enumerate(catalogue):
        level = LEVEL.get(r['id'], 1.0)
        off = loud[i] - target
        line = f"{i:3d} {r['id']:22s} {loud[i]:6.1f} LUFS  {off:+5.1f} LU  level {level:.3f}"
        if i >= HAND_SET:
            worst = max(worst, abs(off))
            # (the level scales the signal; the synth's gentle saturation makes it nearly linear)
            levels[r['id']] = round(level * 10 ** (-off / 20), 3)
            line += f'  -> {levels[r["id"]]:.3f}'
        print(line)
    if a.check:
        print(f'worst later piece: {worst:.1f} LU from the target')
        sys.exit(0 if worst <= TOLERANCE_LU else 1)
    (ROOT / 'data/music/levels.json').write_text(json.dumps(levels, indent=1) + '\n')


if __name__ == '__main__':
    main()
