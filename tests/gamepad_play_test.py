"""The game played with a scripted controller (SLOPPY_INPUT's pad items), through tools/gamepad_probe.jo:
the title's list and its Situations page by d-pad, A and B; the pause menu by Start, the bumpers to
the Controls page, the d-pad and A ticking Invert Y, B carrying on; and a flight stick (a named,
non-standard device's own axes: its lever full forward, the stick back) flying a take-off.
Run serially: python3 tests/gamepad_play_test.py. Needs Sloppy 0.37.0 or later.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def press(frame, button, hold=3):
    return f"{frame}:pad_{button}+ {frame + hold}:pad_{button}-"


def run(work, name, frames, script, draw=True, **extra):
    env = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")}
    env.update(SLOPPY_NO_AUDIO="1", SLOPPY_THREADS=env.get("SLOPPY_THREADS", "1"), SLOPPY_FRAMES=str(frames),
               SLOPPY_INPUT=script, SLOPPY_SAVE_DIR=str(Path(work) / name), SLOPPY_WINDOW="1280x720", **extra)
    for k in ("AEGEAN_TITLE", "AEGEAN_CAPTURE_TAKEOFF", "AEGEAN_FLYING", "AEGEAN_CAPTURE_PANEL"):
        if k not in extra:
            env.pop(k, None)
    # (fixed steps: the same frames on any machine, and no real controller read; the menus drawn
    # over a blank sky, AEGEAN_NO_WORLD, so software rendering keeps up)
    env["SLOPPY_FIXED_STEP"] = "1"
    if draw:
        env.update(SLOPPY_SCREENSHOT=str(Path(work) / f"{name}.png"), AEGEAN_NO_WORLD="1")
    else:
        env["SLOPPY_NO_DRAW"] = "1"
    out = subprocess.run(["sloppy", "--release", "tools/gamepad_probe.jo"], cwd=ROOT, env=env,
                         capture_output=True, text=True, timeout=1200)
    assert out.returncode == 0, f"{name}: exit {out.returncode}\n{out.stderr[-3000:]}"
    states = []
    for line in out.stdout.splitlines():
        if line.startswith("PROBE "):
            states.append(dict(re.findall(r"(\w+)=(\S*)", line)))
    assert states, f"{name}: no PROBE lines\n{out.stdout[-2000:]}\n{out.stderr[-2000:]}"
    return states


def at(states, frame):
    return next(s for s in states if int(s["f"]) >= frame)


def main():
    scratch = Path.home() / "dev/tmp/aegean-skies/gamepad-play-test"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as work:
        # the title: down to Situations, A opens it, the d-pad moves on it, B comes back
        script = " ".join([press(200, "down"), press(230, "a"), press(280, "down"), press(320, "b")])
        s = run(work, "title", 360, script, AEGEAN_TITLE="1")
        assert at(s, 220)["title"] == "true" and at(s, 220)["tfocus"] == "1", at(s, 220)
        assert at(s, 260)["tpage"] == "2", at(s, 260)
        assert at(s, 350)["tpage"] == "0", at(s, 350)
        print("title: d-pad to Situations, A opened it, B came back")

        # the pause menu: Start; RB two pages along to Gamepad (Game, Settings, Gamepad: its focus
        # on the page, the Gamepad tab); the d-pad down past "Left stick steers the aim" to Invert Y;
        # A ticks it; B carries on
        parts = [press(70, "start")] + [press(90 + 8 * k, "rb") for k in range(2)]
        parts += [press(180, "down"), press(195, "down"), press(225, "a"), press(245, "b")]
        s = run(work, "pause", 270, " ".join(parts))
        assert at(s, 80)["paused"] == "true", at(s, 80)
        assert at(s, 160)["page"] == "11", at(s, 160)
        assert at(s, 220)["invert"] == "false" and at(s, 240)["invert"] == "true", (at(s, 220), at(s, 240))
        assert at(s, 260)["paused"] == "false", at(s, 260)
        print("pause: Start, RB to Gamepad, d-pad and A ticked Invert Y, B carried on")

        # a flight stick in the menus (its hat given to hud_nav: raw axes 4 and 5; its trigger,
        # raw button 0, chooses; raw button 2 goes back; raw button 7 pauses)
        name = "1:pad_name=T.16000M 1:pad_axis4=0 1:pad_axis5=0"
        hat = lambda f, axis, v: f"{f}:pad_axis{axis}={v} {f + 3}:pad_axis{axis}=0"
        btn = lambda f, i: f"{f}:pad_button{i}+ {f + 3}:pad_button{i}-"
        script = " ".join([name, hat(200, 5, 1), btn(230, 0), hat(280, 5, 1), btn(320, 2)])
        s = run(work, "title-stick", 360, script, AEGEAN_TITLE="1")
        assert at(s, 220)["tfocus"] == "1" and at(s, 260)["tpage"] == "2" and at(s, 350)["tpage"] == "0", (at(s, 220), at(s, 260), at(s, 350))
        print("title by stick: hat to Situations, trigger opened it, back came back")
        # (the pause menu: right twice from the Game tab is Gamepad; down three to Invert Y, the
        # trigger ticks it, back carries on)
        parts = [name, btn(70, 7), hat(90, 4, 1), hat(100, 4, 1), btn(135, 0)]
        parts += [hat(160, 5, 1), hat(170, 5, 1), hat(180, 5, 1), btn(200, 0), btn(230, 2)]
        s = run(work, "pause-stick", 260, " ".join(parts))
        assert at(s, 80)["paused"] == "true" and at(s, 150)["page"] == "11", (at(s, 80), at(s, 150))
        assert at(s, 190)["sinvert"] == "false" and at(s, 220)["sinvert"] == "true", (at(s, 190), at(s, 220))
        assert at(s, 250)["paused"] == "false", at(s, 250)
        print("pause by stick: its pause button, the hat to Gamepad and Invert Y, the trigger ticked it, back carried on")

        # a flight stick: named, its own axes (the lever 3, full forward; the stick's pitch 1, back)
        script = "1:pad_name=T.16000M 1:pad_axis3=1 40:pad_axis3=-1 930:pad_axis1=0.8 1010:pad_axis1=0.35 1090:pad_axis1=0.12"
        s = run(work, "stick", 1400, script, draw=False, AEGEAN_CAPTURE_TAKEOFF="pad")
        last = s[-1]
        assert last["stick"] == "true" and last["dev"] == "T.16000M", last
        assert at(s, 100)["throttle"] == "1.00" and at(s, 100)["water"] == "true", at(s, 100)
        assert last["water"] == "false" and float(last["y"]) > 100.0, last
        print(f"flight stick: lever open, off the water and up to {float(last['y']):.0f} m")


if __name__ == "__main__":
    main()
