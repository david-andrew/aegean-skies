"""Whoever the pilot talks with stays for the conversation, in the game itself, through
tools/panel_probe.jo (its WHO lines: where the person stands, which way they and the pilot face,
whether the scene holds them, what has called them away):
- forty minutes into the day the nearest person, stopped for a word, stands exactly where they
  were until goodbye, turned to the pilot and he to them, their day's route untouched; let go,
  they walk on along it;
- in the world's first minute the same person is given a load to carry: they say so (a parting
  line in the panel), stand through it, then go, and the panel shuts by itself.
Run serially: python3 tests/talk_hold_test.py. The rules alone: tests/talk_hold_test.jo.
"""
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(work, name, frames, script, **extra):
    env = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")}
    for k in ("AEGEAN_TITLE", "AEGEAN_CAPTURE_PANEL", "AEGEAN_LEISURE", "AEGEAN_TALK", "SLOPPY_TOUCH", "AEGEAN_TOUCH", "AEGEAN_CAPTURE_MINUTES"):
        env.pop(k, None)
    env.update(SLOPPY_NO_AUDIO="1", SLOPPY_THREADS=env.get("SLOPPY_THREADS", "1"), SLOPPY_FRAMES=str(frames),
               SLOPPY_INPUT=script, SLOPPY_SAVE_DIR=str(Path(work) / name), SLOPPY_WINDOW="1280x720",
               SLOPPY_FIXED_STEP="1", AEGEAN_NO_WORLD="1", AEGEAN_TALK="1",
               SLOPPY_SCREENSHOT=str(Path(work) / f"{name}.png"), **extra)
    out = subprocess.run(["sloppy", "--release", "tools/panel_probe.jo"], cwd=ROOT, env=env,
                         capture_output=True, text=True, timeout=1800)
    assert out.returncode == 0, f"{name}: exit {out.returncode}\n{out.stderr[-3000:]}"
    lines = out.stdout.splitlines()

    def table(head):
        return {int(d["f"]): d for d in (dict(re.findall(r"(\w+)=(\S*)", l)) for l in lines if l.startswith(head + " "))}
    probe, who, talk = table("PROBE"), table("WHO"), table("TALK")
    assert probe and who, f"{name}: no conversation\n{out.stdout[-2000:]}\n{out.stderr[-2000:]}"
    return probe, who, talk


def key(frame, k):
    return f"{frame}:{k}+ {frame + 2}:{k}-"


def turn(a, b):
    return abs((float(a) - float(b) + math.pi) % (2 * math.pi) - math.pi)


def moved(a, b):
    return math.hypot(float(a["x"]) - float(b["x"]), float(a["z"]) - float(b["z"]))


def main():
    scratch = Path.home() / "dev/tmp/aegean-skies/talk-hold-test"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as work:
        # ---- stopped for a word, they stay until goodbye and then walk on
        bye = 600
        probe, who, talk = run(work, "stays", bye + 420, key(bye, "escape"), AEGEAN_CAPTURE_MINUTES="40")
        first = min(who)
        start = who[first]
        for f in range(first, bye):
            w = who[f]
            assert probe[f]["ui"] == "talk", f"frame {f}: the conversation ended by itself: {w}"
            assert w["held"] == "true" and w["call"] == "none", f"frame {f}: {w}"
            assert moved(w, start) < 0.01, f"frame {f}: walked {moved(w, start):.2f} m during the talk"
            assert w["day"] == start["day"], f"frame {f}: their day's plan changed under the hold: {w['day']} from {start['day']}"
        # (turned to each other within a second or so, and kept so)
        for f in range(first + 90, bye):
            w = who[f]
            assert turn(w["yaw"], w["bearing"]) < 0.06, f"frame {f}: not facing the pilot: {w}"
            assert turn(w["me_yaw"], w["me_bearing"]) < 0.06, f"frame {f}: the pilot not facing them: {w}"
        # (they came round to it, not at a snap: part of the way after a fifth of a second)
        if turn(start["yaw"], start["bearing"]) > 1.0:
            part = turn(who[first + 12]["yaw"], who[first + 12]["bearing"])
            assert 0.05 < part < turn(start["yaw"], start["bearing"]), f"turned at a snap: {part}"
        # (goodbye: let go, and on with what they were about, where it has them walking)
        after = who[bye + 400]
        assert probe[bye + 6]["ui"] == "none" and who[bye + 6]["held"] == "false"
        going = start["errand"] != "none" or "/afalse/" in start["day"] and start["day"].endswith("/clear")
        if going: assert moved(after, start) > 1.0, f"let go, they stood where they were: {after}"
        print(f"stopped for a word: stood {bye - first} frames, turned to the pilot, {'walked on' if going else 'nowhere to be'} after goodbye")

        # ---- called away: a load to carry in the world's first minute
        probe, who, talk = run(work, "called", 900, "1:mouse=5x5")
        first = min(who)
        start = who[first]
        called = next((f for f in sorted(who) if who[f]["call"] != "none"), None)
        assert called is not None, "nothing called them away in the first minutes"
        reason = who[called]["call"]
        assert reason in ("load", "work", "boat", "meeting", "prayer"), who[called]
        # (their parting line in the panel, arriving as speech does)
        line = int(talk[called + 2]["chars"])
        assert 10 <= line <= 44 and talk[called + 2]["done"] == "false", talk[called + 2]
        whole = next(f for f in sorted(talk) if f > called and talk[f]["done"] == "true")
        # (they stand through it, and a moment after)
        for f in range(first, whole + 30):
            assert who[f]["held"] == "true" and moved(who[f], start) < 0.01, f"frame {f}: gone before the line was said: {who[f]}"
        # (then they go, and the panel shuts by itself a few seconds on)
        shut = next(f for f in sorted(probe) if f > whole and probe[f]["ui"] == "none")
        assert 4.0 <= (shut - whole) / 60.0 <= 6.5, f"the panel shut {(shut - whole) / 60.0:.1f} s after the line"
        assert who[whole + 70]["held"] == "false"
        assert moved(who[shut + 120], start) > 1.0, f"called away by a {reason}, they stood where they were: {who[shut + 120]}"
        assert not [f for f in talk if f > shut + 2], "a bubble outlived the conversation"
        print(f"called away ({reason}): the line said standing, then gone, the panel shut after {(shut - whole) / 60.0:.1f} s")
    print("ok")


if __name__ == "__main__":
    main()
