"""Standing and walking talks, in the game itself, through tools/panel_probe.jo (its WHO line: where
the person and the pilot stand, which way they face, whether the scene holds or paces the person;
its TALK line: how far apart they are and how clearly the person's words carry):
- someone with nowhere to be, stopped for a word, stands exactly where they were, turned to the
  pilot and he to them, their day's route untouched, and are let go at goodbye;
- the pilot walking off: past fifteen metres their words come less clearly, past twenty-five the
  talk is over and a word is called after him;
- come along: in the world's first minute the person he is talking with is given a load; they say
  so and set off at a talking pace, the talk still open;
- walking along: the pilot beside them (AEGEAN_TALK_FOLLOW walks him), the talk goes on as far as
  they go.
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
    for k in ("AEGEAN_TITLE", "AEGEAN_CAPTURE_PANEL", "AEGEAN_LEISURE", "AEGEAN_TALK", "SLOPPY_TOUCH", "AEGEAN_TOUCH", "AEGEAN_CAPTURE_MINUTES", "AEGEAN_TALK_FOLLOW"):
        env.pop(k, None)
    env.update(SLOPPY_NO_AUDIO="1", SLOPPY_THREADS=env.get("SLOPPY_THREADS", "1"), SLOPPY_FRAMES=str(frames),
               SLOPPY_INPUT=script, SLOPPY_SAVE_DIR=str(Path(work) / name), SLOPPY_WINDOW="1280x720",
               SLOPPY_FIXED_STEP="1", AEGEAN_NO_WORLD="1",
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


def moved(a, b, of=""):
    return math.hypot(float(a[of + "x"]) - float(b[of + "x"]), float(a[of + "z"]) - float(b[of + "z"]))


WALK_WORDS = ("Walk_with_me", "Come_along", "Walk_up_with_me", "See_me_to_my_door", "Walk_me_home")


def main():
    scratch = Path.home() / "dev/tmp/aegean-skies/talk-hold-test"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as work:
        # ---- stopped for a word, they stand until goodbye and then walk on
        bye = 480
        probe, who, talk = run(work, "stands", bye + 30, key(bye, "escape"), AEGEAN_TALK="idle", AEGEAN_CAPTURE_MINUTES="40")
        first = min(who)
        start = who[first]
        for f in range(first, bye):
            w = who[f]
            assert probe[f]["ui"] == "talk", f"frame {f}: the conversation ended by itself: {w}"
            assert w["held"] == "true" and w["paced"] == "false" and w["call"] == "none", f"frame {f}: {w}"
            assert moved(w, start) < 0.01, f"frame {f}: walked {moved(w, start):.2f} m during the talk"
            assert w["day"] == start["day"], f"frame {f}: their day's plan changed under the hold: {w['day']} from {start['day']}"
            assert moved(w, start, "me_") < 0.01, f"frame {f}: the pilot moved by himself"
        for f in range(first + 90, bye):
            w = who[f]
            assert turn(w["yaw"], w["bearing"]) < 0.06, f"frame {f}: not facing the pilot: {w}"
            assert turn(w["me_yaw"], w["me_bearing"]) < 0.06, f"frame {f}: the pilot not facing them: {w}"
        # (goodbye: let go. That a walker let go walks on along the same route is
        # tests/talk_hold_test.jo's; this staged quay gives this one no way through)
        assert probe[bye + 6]["ui"] == "none" and who[bye + 6]["held"] == "false" and who[bye + 6]["paced"] == "false"
        print(f"stopped for a word: stood {bye - first} frames, turned to the pilot, let go at goodbye")

        # ---- the pilot walks off: fainter past fifteen metres, over past twenty-five
        off = 200
        probe, who, talk = run(work, "walks-off", off + 900, f"{off}:shift+ {off}:s+", AEGEAN_TALK="idle", AEGEAN_CAPTURE_MINUTES="40")
        first = min(who)
        start = who[first]
        assert float(talk[off - 2]["gap"]) < 3.5 and talk[off - 2]["clarity"] == "1.00"
        ended = next((f for f in sorted(probe) if f > off and probe[f]["ui"] == "none"), None)
        assert ended is not None, f"walked {moved(who[max(who)], start, 'me_'):.1f} m and still talking"
        gaps = [float(talk[f]["gap"]) for f in range(off, ended - 1) if f in talk]
        assert all(b >= a - 0.05 for a, b in zip(gaps, gaps[1:])), "the gap did not grow as he walked off"
        assert 24.0 < gaps[-1] < 27.0, f"the talk ended at {gaps[-1]:.1f} m"
        # (the person stood through it; their words clear to fifteen metres and less so after)
        for f in range(off, ended - 1):
            t = talk[f]
            assert who[f]["held"] == "true" and moved(who[f], start) < 0.01, f"frame {f}: {who[f]}"
            gap = float(t["gap"])
            if gap < 14.5: assert t["clarity"] == "1.00", t
            if gap > 16.0: assert float(t["clarity"]) < 1.0, t
            if gap > 23.0: assert float(t["clarity"]) < 0.3, t
        called = who[ended + 3]["toast"]
        assert called.endswith("!") and ":" in called, f"nothing called after him: {called!r}"
        assert not [f for f in talk if f > ended + 2], "a bubble outlived the conversation"
        assert who[ended + 30]["held"] == "false"
        print(f"walked off: clear to 15 m, the talk over at {gaps[-1]:.1f} m, called after: {called.replace('_', ' ')}")

        # ---- come along: given a load a minute in, they say so and set off, the talk still open
        probe, who, talk = run(work, "come-along", 900, "1:mouse=5x5", AEGEAN_TALK="1")
        first = min(who)
        start = who[first]
        assert talk[first + 30]["walking"] == "false" and who[first + 30]["held"] == "true"
        called = next((f for f in sorted(talk) if talk[f]["walking"] == "true"), None)
        assert called is not None, "nothing gave them somewhere to be in the first minutes"
        line = talk[called + 1]["line"]
        assert any(w in line for w in WALK_WORDS), f"set off without asking him along: {line}"
        for f in range(first, called): assert moved(who[f], start) < 0.01, f"frame {f}: gone before saying so"
        assert who[called + 2]["paced"] == "true" and who[called + 2]["held"] == "false"
        # (ten seconds on: well on their way at a talking pace, under a walk's 1.25 m/s; the pilot
        # left standing, the talk still open and what he can say still there)
        end = called + 600
        gone = moved(who[end], start)
        assert gone > 4.0, f"they went {gone:.1f} m in ten seconds"
        steady = moved(who[end], who[end - 180]) / 3.0
        assert 0.4 < steady < 1.1, f"walking at {steady:.2f} m/s"
        assert moved(who[end], start, "me_") < 0.01
        for f in range(called + 2, end):
            assert probe[f]["ui"] == "talk" and talk[f]["walking"] == "true" and who[f]["paced"] == "true", f"frame {f}: {talk[f]}"
        assert int(talk[end]["options"]) > 0 and talk[end]["boxes"] != ""
        print(f"come along: '{line.replace('_', ' ')}', {gone:.1f} m on in ten seconds at {steady:.2f} m/s, still talking")

        # ---- walking along: the pilot beside them, the talk goes on as far as they go
        probe, who, talk = run(work, "along", called + 900, "1:mouse=5x5", AEGEAN_TALK="1", AEGEAN_TALK_FOLLOW="1")
        end = called + 840
        far = moved(who[end], start)
        went = moved(who[end], start, "me_")
        assert far > 4.0 and went > far - 6.0, f"they went {far:.1f} m and the pilot {went:.1f} m"
        for f in range(called + 240, end):
            assert probe[f]["ui"] == "talk" and float(talk[f]["gap"]) < 5.0 and talk[f]["clarity"] == "1.00", f"frame {f}: {talk.get(f)}"
        print(f"walking along: {far:.0f} m together, {float(talk[end]['gap']):.1f} m apart, still talking")
    print("ok")


if __name__ == "__main__":
    main()
