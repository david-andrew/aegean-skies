"""No title layer over play: after each kind of choice on the title (New, a Situation, Continue)
the first seconds of play have no title layer up. The title closed, no choice left waiting, its
dusk gone within a second (the dusk left fully up over a long first frame showed as a dark box
over the game in a browser), no panel. Runs the game headless, a small window, once per choice
(AEGEAN_TITLE_PICK, made as a click would), and reads its TITLE_LAYERS report; the game quits
itself two seconds into play.
"""
import os, re, subprocess, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def layers_after(folder, pick):
    env = {k: v for k, v in os.environ.items() if k not in ('DISPLAY', 'WAYLAND_DISPLAY')}
    # (a small window and no world drawn, AEGEAN_NO_WORLD: the layers are what is read, not the
    # picture, and software rendering takes seconds a frame over the title's first shot;
    # SLOPPY_FRAMES only a bound, the game quitting once its report is done)
    env.update(SLOPPY_NO_AUDIO='1', SLOPPY_THREADS=env.get('SLOPPY_THREADS', '1'), SLOPPY_FRAMES='2400', SLOPPY_FIXED_STEP='1', SLOPPY_WINDOW='320x180', AEGEAN_NO_WORLD='1',
               SLOPPY_SAVE_DIR=folder, AEGEAN_TITLE='1', AEGEAN_TITLE_PICK=pick)
    began = time.time()
    out = subprocess.run(['sloppy', '--release', 'aegean.jo'], cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
    assert 'TITLE leaving after' in out.stdout and 'TITLE play:' in out.stdout, (pick, out.stdout[-3000:] + out.stderr[-2000:])
    rows = [m.groups() for m in re.finditer(r'TITLE_LAYERS play frame (\d+): open (\w+) leaving (\w+) dusk ([\d.]+) panel (\d+)', out.stdout)]
    assert len(rows) >= 12, (pick, out.stdout[-3000:])
    return [(int(f), o == 'true', l == 'true', float(d), int(p)) for f, o, l, d, p in rows], time.time() - began


def main():
    scratch = Path.home() / 'dev/tmp/aegean-skies/title-check'
    scratch.mkdir(parents=True, exist_ok=True)
    # (a fresh save folder: the new game's autosave is what Continue then loads)
    with tempfile.TemporaryDirectory(dir=scratch) as folder:
        for pick in os.environ.get('AEGEAN_HANDOVER_PICKS', 'new strait continue').split():
            rows, took = layers_after(folder, pick)
            for frame, opened, leaving, dusk, panel in rows:
                assert not opened and not leaving and panel == 0, (pick, frame, opened, leaving, panel)
                if frame >= 60:
                    assert dusk == 0.0, (pick, frame, dusk)
            print(f'{pick}: no title layer over play ({len(rows)} reports, the dusk gone by frame 60; {took:.0f} s)')


if __name__ == '__main__':
    main()
