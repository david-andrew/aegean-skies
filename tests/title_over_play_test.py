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
        opened, names, over = run(folder, 120, 100, AEGEAN_TITLE='1')
        assert opened and names > 0, (opened, names)
        print(f'title screen: the name drawn ({names} times)')
        opened, names, over = run(folder, 300, 290, AEGEAN_TITLE='1', SLOPPY_INPUT='60:enter+ 62:enter- 90:enter+ 92:enter-')
        assert not opened and names > 0 and over == 0, (opened, names, over)
        print(f'play begun from the title: the name drawn {names} times before, none after')


if __name__ == '__main__':
    main()
