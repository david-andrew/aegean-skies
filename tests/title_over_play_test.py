"""The game's name belongs to the title screen: once play has begun it is never drawn over the
game. Runs the game headless three ways and reads its TITLE_CHECK report (every drawing of the
name is counted by src/title_screen.jo's draw_game_name):
  * a start that skips the title (as tests and captures do): no name drawn, ever;
  * the title screen up: the name is drawn (so the count is real);
  * play begun from the title (Enter starts a new game): no name drawn after that.
And nothing but the title screen spells the name out to draw it.
"""
import os, re, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(folder, frames, check, **extra):
    env = {k: v for k, v in os.environ.items() if k not in ('DISPLAY', 'WAYLAND_DISPLAY')}
    env.update(SLOPPY_NO_AUDIO='1', SLOPPY_THREADS=env.get('SLOPPY_THREADS', '1'), SLOPPY_FRAMES=str(frames), SLOPPY_SCREENSHOT=str(Path(folder) / 'last.png'),
               SLOPPY_SAVE_DIR=folder, AEGEAN_TITLE_CHECK=str(check), **extra)
    out = subprocess.run(['sloppy', '--release', 'aegean.jo'], cwd=ROOT, env=env, capture_output=True, text=True, timeout=1200)
    m = re.search(r'TITLE_CHECK frame (\d+) open (\w+) names (\d+) over_play (\d+)', out.stdout)
    assert m, out.stdout[-2000:] + out.stderr[-2000:]
    return m.group(2) == 'true', int(m.group(3)), int(m.group(4))


def layers_after(folder, pick, frames):
    """Start play from the title by a choice (AEGEAN_TITLE_PICK, made as a click would) and read the
    title's layers reported over the first seconds of play (TITLE_LAYERS lines)."""
    env = {k: v for k, v in os.environ.items() if k not in ('DISPLAY', 'WAYLAND_DISPLAY')}
    # (a small window: the layers are what is read, not the picture, and software rendering is slow)
    env.update(SLOPPY_NO_AUDIO='1', SLOPPY_THREADS=env.get('SLOPPY_THREADS', '1'), SLOPPY_FRAMES=str(frames), SLOPPY_FIXED_STEP='1', SLOPPY_WINDOW='320x180',
               SLOPPY_SCREENSHOT=str(Path(folder) / 'last.png'), SLOPPY_SAVE_DIR=folder, AEGEAN_TITLE='1', AEGEAN_TITLE_PICK=pick)
    out = subprocess.run(['sloppy', '--release', 'aegean.jo'], cwd=ROOT, env=env, capture_output=True, text=True, timeout=1500)
    assert 'TITLE leaving after' in out.stdout and 'TITLE play:' in out.stdout, (pick, out.stdout[-3000:] + out.stderr[-2000:])
    rows = [m.groups() for m in re.finditer(r'TITLE_LAYERS play frame (\d+): open (\w+) leaving (\w+) dusk ([\d.]+) panel (\d+)', out.stdout)]
    assert rows, (pick, out.stdout[-3000:])
    return [(int(f), o == 'true', l == 'true', float(d), int(p)) for f, o, l, d, p in rows]


def no_title_layer_over_play(folder):
    """After each choice on the title (New, a Situation, Continue, a slot) the first seconds of play
    have no title layer up: the title closed, no choice left waiting, its dusk gone within a second
    (the dusk left fully up over a long first frame showed as a dark box over the game), no panel."""
    for pick, frames in [('new', 1200), ('strait', 1000), ('canal', 1000), ('continue', 1000), ('slot1', 1000)]:
        rows = layers_after(folder, pick, frames)
        for frame, opened, leaving, dusk, panel in rows:
            assert not opened and not leaving and panel == 0, (pick, frame, opened, leaving, panel)
            if frame >= 60:
                assert dusk == 0.0, (pick, frame, dusk)
        print(f'{pick}: no title layer over play ({len(rows)} reports, the dusk gone by frame 60)')


def name_drawn_only_by_the_title():
    """Nothing else in the game draws its name (the old opening card drew it over play)."""
    offenders = []
    for path in [ROOT / 'aegean.jo', *sorted((ROOT / 'src').glob('*.jo'))]:
        for n, line in enumerate(path.read_text().splitlines(), 1):
            if re.search(r'"AEGEAN( SKIES)?"|"SKIES"', line) and path.name != 'title_screen.jo':
                offenders.append(f'{path.name}:{n}: {line.strip()}')
    assert not offenders, offenders


def main():
    name_drawn_only_by_the_title()
    scratch = Path.home() / 'dev/tmp/aegean-skies/title-check'
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as folder:
        # (frame 150 is two and a half seconds in: where the old opening card stood over play)
        opened, names, over = run(folder, 160, 150, AEGEAN_TITLE='0')
        assert not opened and names == 0 and over == 0, (opened, names, over)
        print('skipped title: no name over play')
        # (the title shows once the world is prepared, a few seconds of frames in: see
        # docs/game-saves.md, Loading)
        opened, names, over = run(folder, 420, 400, AEGEAN_TITLE='1')
        assert opened and names > 0, (opened, names)
        print(f'title screen: the name drawn ({names} times)')
        opened, names, over = run(folder, 540, 520, AEGEAN_TITLE='1', SLOPPY_INPUT='400:enter+ 402:enter- 430:enter+ 432:enter-')
        assert not opened and names > 0 and over == 0, (opened, names, over)
        print(f'play begun from the title: the name drawn {names} times before, none after')
    # (a fresh save folder: the new game's autosave is what Continue and slot 1 then load)
    with tempfile.TemporaryDirectory(dir=scratch) as folder:
        no_title_layer_over_play(folder)


if __name__ == '__main__':
    main()
