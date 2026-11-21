"""A conversation played in the game itself, through tools/panel_probe.jo (SLOPPY_INPUT at fixed steps):
- the person's line arrives a few characters a frame, and nothing can be answered until it is whole;
- Space finishes it at once and does nothing else, and so does a tap on the panel, without that tap
  also being an answer;
- choosing an answer puts the pilot's words over his head, then the person's answer arrives while
  both bubbles are up;
- left alone, a line takes a speaking pace (35 to 50 characters a second and its pauses);
- Escape (goodbye) ends the conversation and both bubbles with it.
Run serially: python3 tests/talk_bubbles_test.py. The arithmetic alone: tests/talk_bubbles_test.jo.
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
               SLOPPY_FIXED_STEP="1", AEGEAN_NO_WORLD="1",
               # (the mechanic, forty minutes into the day: nothing calls him away from the talk,
               # as a load does the merchant in the world's first minute: tests/talk_hold_test.py)
               AEGEAN_TALK="mechanic", AEGEAN_CAPTURE_MINUTES="40",
               SLOPPY_SCREENSHOT=str(Path(work) / f"{name}.png"), **extra)
    out = subprocess.run(["sloppy", "--release", "tools/panel_probe.jo"], cwd=ROOT, env=env,
                         capture_output=True, text=True, timeout=1200)
    assert out.returncode == 0, f"{name}: exit {out.returncode}\n{out.stderr[-3000:]}"
    lines = out.stdout.splitlines()
    probe = {int(d["f"]): d for d in (dict(re.findall(r"(\w+)=(\S*)", l)) for l in lines if l.startswith("PROBE "))}
    talk = {int(d["f"]): d for d in (dict(re.findall(r"(\w+)=(\S*)", l)) for l in lines if l.startswith("TALK "))}
    assert probe and talk, f"{name}: no conversation\n{out.stdout[-2000:]}\n{out.stderr[-2000:]}"
    return probe, talk


def key(frame, k):
    return f"{frame}:{k}+ {frame + 2}:{k}-"


def tap(frame, xy):
    return f"{frame}:touch1={xy} {frame + 3}:touch1-"


def shown(t):
    return int(t["chars"]) if t["shown"] == "-1" else int(t["shown"])


def main():
    scratch = Path.home() / "dev/tmp/aegean-skies/talk-bubbles-test"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as work:
        # ---- the keys: Space finishes the greeting, 1 answers, the answer arrives, Escape leaves
        probe, talk = run(work, "alone", 420, "1:mouse=5x5")
        first = min(talk)
        chars = int(talk[first]["chars"])
        assert chars >= 30, f"a short greeting to time ({chars} characters): {talk[first]}"
        # (left alone: a little more each frame, never a jump, nothing answerable, Space held)
        whole = next(f for f in sorted(talk) if talk[f]["done"] == "true")
        last = 0
        for f in range(first, whole):
            t = talk[f]
            n = shown(t)
            assert 0 <= n - last <= 2, f"frame {f}: {last} -> {n} characters"
            assert t["ready"] == "false" and t["pilot"] == "false", f"frame {f}: {t}"
            # (the probe reads a frame before it is drawn: the panel's first shows in the next)
            assert f < first + 2 or (t["person"] == "true" and t["space"] == "true"), f"frame {f}: {t}"
            last = n
        seconds = (whole - first) / 60.0
        assert chars / 50.0 - 0.1 <= seconds <= chars / 35.0 + 2.5, f"{chars} characters in {seconds:.2f} s"
        assert talk[whole + 1]["ready"] == "true" and talk[whole + 3]["space"] == "false"
        at = whole + 30

        probe, talk = run(work, "skip", at + 700, " ".join([key(first + 20, "space"), key(at, "n1"), key(at + 600, "escape")]))
        # (Space: whole within a frame or two, the conversation still open, and nothing chosen)
        before = talk[first + 19]
        assert before["done"] == "false" and shown(before) < chars
        after = talk[first + 23]
        assert after["done"] == "true" and after["words"] == "" and int(after["chars"]) == chars, after
        assert all(probe[f]["ui"] == "talk" for f in range(first + 18, at)), "Space did more than finish the line"
        assert talk[first + 25]["ready"] == "true"
        # (the first answer: the pilot's words over his head at once, the reply after a moment,
        # arriving, with both bubbles up)
        said = next(f for f in sorted(talk) if f >= at and talk[f]["words"] != "")
        assert said <= at + 3, f"the pilot said nothing by frame {said}"
        t = talk[said + 2]
        assert t["pilot"] == "true" and t["person"] == "true" and t["done"] == "false" and shown(t) == 0, t
        reply = int(t["chars"])
        mid = talk[said + 60]
        assert mid["pilot"] == "true" and mid["person"] == "true" and 0 < shown(mid), mid
        done = next(f for f in sorted(talk) if f > said + 2 and talk[f]["done"] == "true")
        assert (done - said) / 60.0 >= reply / 50.0, f"{reply} characters in {(done - said) / 60.0:.2f} s"
        # (the bubbles kept above the panel's top edge, which is on the screen)
        assert 0 < float(mid["top"]) < 720
        # (Escape: goodbye; the panel and both bubbles gone, and they stay gone)
        gone = at + 600 + 4
        assert probe[gone]["ui"] == "none", probe[gone]
        assert not [f for f in talk if f >= gone], "a bubble outlived the conversation"
        print("a conversation: the line arrives, Space finishes it, the pilot and the person both speak, goodbye clears them")

        # ---- a tap on the panel finishes the line, and is not an answer
        probe, talk = run(work, "tap", first + 120, tap(first + 20, "640x650"), SLOPPY_TOUCH="1")
        assert talk[first + 19]["done"] == "false"
        assert talk[first + 24]["done"] == "true", talk[first + 24]
        for f in range(first + 20, first + 110):
            assert probe[f]["ui"] == "talk" and talk[f]["words"] == "" and int(talk[f]["chars"]) == chars, f"frame {f}: the tap answered: {talk[f]}"
        print("a tap on the panel finishes the line and chooses nothing")
    print("ok")


if __name__ == "__main__":
    main()
