"""Every full-screen panel opens and closes by each route, one at a time, through tools/panel_probe.jo
(SLOPPY_INPUT: touches, keys and a controller's buttons, at fixed steps):
- the notebook (the Log button and J; its own Close, the Log button again, Escape, a controller's B);
- the chart (Map and M; Map again, Escape, B);
- the pause menu (II, P and Start; II, P, Escape, B), on its Paint page too;
- the bill of fare and the newspaper (Escape, B);
- a conversation (Escape), with the chart and the notebook refused over it and the pause menu
  covering it.
Opening the pause menu, the chart or the notebook closes the other two, and one Escape closes the
top panel only. Run serially: python3 tests/panel_close_test.py.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(work, name, frames, script, **extra):
    env = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")}
    for k in ("AEGEAN_TITLE", "AEGEAN_CAPTURE_PANEL", "AEGEAN_LEISURE", "AEGEAN_TALK", "SLOPPY_TOUCH", "AEGEAN_TOUCH"):
        env.pop(k, None)
    env.update(SLOPPY_NO_AUDIO="1", SLOPPY_THREADS=env.get("SLOPPY_THREADS", "1"), SLOPPY_FRAMES=str(frames),
               SLOPPY_INPUT=script, SLOPPY_SAVE_DIR=str(Path(work) / name), SLOPPY_WINDOW="1280x720",
               SLOPPY_FIXED_STEP="1", AEGEAN_NO_WORLD="1", SLOPPY_SCREENSHOT=str(Path(work) / f"{name}.png"), **extra)
    out = subprocess.run(["sloppy", "--release", "tools/panel_probe.jo"], cwd=ROOT, env=env,
                         capture_output=True, text=True, timeout=1200)
    assert out.returncode == 0, f"{name}: exit {out.returncode}\n{out.stderr[-3000:]}"
    states = [dict(re.findall(r"(\w+)=(\S*)", l)) for l in out.stdout.splitlines() if l.startswith("PROBE ")]
    assert states, f"{name}: no PROBE lines\n{out.stdout[-2000:]}\n{out.stderr[-2000:]}"
    return states


def at(states, frame):
    return next(s for s in states if int(s["f"]) >= frame)


def where(states, label):
    for s in states:
        for b in s["buttons"].split(","):
            if b.startswith(label + "@"):
                return b.split("@")[1]
    raise AssertionError(f"no {label} button")


def tap(frame, xy):
    return f"{frame}:touch1={xy} {frame + 3}:touch1-"


def key(frame, k):
    return f"{frame}:{k}+ {frame + 2}:{k}-"


def pad(frame, b):
    return f"{frame}:pad_{b}+ {frame + 3}:pad_{b}-"


def open_(s):
    return {k: s[k] for k in ("paused", "chart", "notebook", "ui", "leisure")}


def expect(states, frame, **want):
    s = at(states, frame)
    got = open_(s)
    assert all(got[k] == v for k, v in want.items()), f"frame {frame}: {got}, wanted {want}"


def main():
    scratch = Path.home() / "dev/tmp/aegean-skies/panel-close-test"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as work:
        # (the touch buttons' places, and the notebook's Close, as the game draws them)
        probe = run(work, "layout", 60, key(30, "j"), SLOPPY_TOUCH="1")
        ii, mp, log = where(probe, "II"), where(probe, "Map"), where(probe, "Log")
        close = at(probe, 50)["close"]
        # (without the touch pad the notebook sits higher: its Close where the mouse finds it)
        close_mouse = at(run(work, "layout-keys", 60, key(30, "j")), 50)["close"]

        # a touch screen: the buttons along the top and the notebook's own Close
        steps = [tap(40, log), tap(60, close), tap(80, log), tap(100, log), tap(120, log), tap(140, ii),
                 tap(160, ii), tap(180, mp), tap(200, ii), tap(220, mp), tap(240, mp), tap(260, log),
                 tap(280, mp), tap(300, log), tap(320, log)]
        s = run(work, "touch", 340, " ".join(steps), SLOPPY_TOUCH="1")
        expect(s, 50, notebook="true")
        expect(s, 70, notebook="false")                         # its own Close
        expect(s, 90, notebook="true"); expect(s, 110, notebook="false")    # Log again
        expect(s, 130, notebook="true")
        expect(s, 150, paused="true", notebook="false")         # II over the notebook: the pause menu alone
        expect(s, 170, paused="false")
        expect(s, 190, chart="true")
        expect(s, 210, paused="true", chart="false")            # II over the chart
        expect(s, 230, paused="false", chart="true")            # Map over the pause menu
        expect(s, 250, chart="false")                           # Map again
        expect(s, 270, notebook="true")
        expect(s, 290, notebook="false", chart="true")          # Map over the notebook
        expect(s, 310, notebook="true", chart="false")          # Log over the chart
        expect(s, 330, notebook="false")
        print("touch: Log, Close, II and Map open and close their panels, one at a time")

        # the keyboard and mouse: J, M, P and Escape; the notebook's line takes letters; a click on Close
        steps = [key(40, "j"), key(60, "escape"), key(80, "j"), key(100, "m"), key(104, "p"), key(120, "escape"),
                 key(140, "m"), key(160, "escape"), key(180, "p"), key(200, "escape"), key(220, "m"), key(240, "p"),
                 key(260, "escape"), key(280, "p"), key(300, "m"), key(320, "escape"), key(340, "j"),
                 f"350:mouse={close_mouse} 360:mouse_left+ 362:mouse_left-"]
        s = run(work, "keys", 380, " ".join(steps))
        expect(s, 50, notebook="true"); expect(s, 70, notebook="false")
        expect(s, 110, notebook="true", chart="false", paused="false")    # M and P typed into its line
        expect(s, 130, notebook="false")
        expect(s, 150, chart="true"); expect(s, 170, chart="false")
        expect(s, 190, paused="true"); expect(s, 210, paused="false")
        expect(s, 250, paused="true", chart="false")            # P over the chart: the pause menu alone
        expect(s, 270, paused="false", chart="false")           # one Escape: the top one only
        expect(s, 310, paused="false", chart="true")            # M over the pause menu
        expect(s, 330, chart="false", paused="false")
        expect(s, 345, notebook="true"); expect(s, 370, notebook="false")    # the mouse on Close
        print("keyboard and mouse: J, M, P, Escape and a click on Close, one panel at a time")

        # a controller: Start pauses, B closes the top panel
        steps = [pad(40, "start"), pad(60, "b"), key(80, "j"), pad(100, "b"), key(120, "m"), pad(140, "b"),
                 key(160, "m"), pad(180, "start"), pad(200, "b")]
        s = run(work, "pad", 220, " ".join(steps))
        expect(s, 50, paused="true"); expect(s, 70, paused="false")
        expect(s, 90, notebook="true"); expect(s, 110, notebook="false")
        expect(s, 130, chart="true"); expect(s, 150, chart="false")
        expect(s, 190, paused="true", chart="false"); expect(s, 210, paused="false", chart="false")
        print("controller: Start and B, the top panel only")

        # the pause menu on its Paint page closes as the pause menu does
        s = run(work, "paint", 140, " ".join([pad(80, "b"), key(100, "p"), key(120, "p")]), AEGEAN_CAPTURE_PANEL="paint")
        expect(s, 70, paused="true"); expect(s, 90, paused="false")
        expect(s, 110, paused="true"); expect(s, 130, paused="false")
        print("the Paint page: B and P close the pause menu")

        # the bill of fare (Escape) and the newspaper (B): back to the table's card
        s = run(work, "menu", 100, key(60, "escape"), AEGEAN_LEISURE="menu")
        expect(s, 50, ui="leisure", leisure="1"); expect(s, 80, ui="leisure", leisure="0")
        s = run(work, "paper", 100, pad(60, "b"), AEGEAN_LEISURE="paper")
        expect(s, 50, ui="leisure", leisure="9"); expect(s, 80, ui="leisure", leisure="0")
        print("the bill of fare and the newspaper: Escape and B")

        # a conversation: Map and Log refused over it; the pause menu covers it and one Escape
        # closes the pause menu alone; Escape then ends the conversation
        steps = [key(90, "m"), key(100, "j"), key(110, "p"), key(130, "escape"), key(150, "escape")]
        s = run(work, "talk", 170, " ".join(steps), AEGEAN_TALK="1")
        expect(s, 85, ui="talk")
        expect(s, 105, ui="talk", chart="false", notebook="false")
        expect(s, 120, ui="talk", paused="true")
        expect(s, 140, ui="talk", paused="false")
        expect(s, 160, ui="none")
        print("a conversation: Map and Log refused, the pause menu over it, Escape the top one only")


if __name__ == "__main__":
    main()
