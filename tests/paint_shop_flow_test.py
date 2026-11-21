"""A visit to the paint shop from end to end, by real input, through tools/paint_shop_probe.jo
(SLOPPY_INPUT: mouse clicks and a key at fixed steps):
- a click on the workshop walks the pilot round its open end to the apron, and the painter is
  spoken to;
- the painter's answer brings the aircraft round to the berth (a few minutes pass) and opens the
  shop's panel;
- a livery is chosen and priced, and "Have her painted" pays the painter and starts the work;
- the painter is spoken to again and the wait is watched: she goes masked, into primer, into her
  top coat, and is dry in the new paint.
Each step's place on the screen is read from the run before it (the same run, a little longer each
time). Run serially: python3 tests/paint_shop_flow_test.py.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
# on the waterfront behind the town's paint shop, looking at it
START = "398.24 -6295.91 2.73"


def run(work, name, frames, script, **extra):
    env = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")}
    for k in ("AEGEAN_TITLE", "AEGEAN_CAPTURE_PANEL", "AEGEAN_LEISURE", "AEGEAN_TALK", "SLOPPY_TOUCH", "AEGEAN_TOUCH"):
        env.pop(k, None)
    env.update(SLOPPY_NO_AUDIO="1", SLOPPY_THREADS=env.get("SLOPPY_THREADS", "1"), SLOPPY_FRAMES=str(frames),
               SLOPPY_INPUT=script, SLOPPY_SAVE_DIR=str(Path(work) / name), SLOPPY_WINDOW="1280x720",
               SLOPPY_FIXED_STEP="1", AEGEAN_NO_WORLD="1", AEGEAN_AT=START,
               SLOPPY_SCREENSHOT=str(Path(work) / f"{name}.png"), **extra)
    out = subprocess.run(["sloppy", "--release", "tools/paint_shop_probe.jo"], cwd=ROOT, env=env,
                         capture_output=True, text=True, timeout=1500)
    assert out.returncode == 0, f"{name}: exit {out.returncode}\n{out.stderr[-3000:]}"
    frames_seen = {}
    for line in out.stdout.splitlines():
        if line.startswith("PAINT "):
            d = dict(m.groups() for m in re.finditer(r"(\w+)=(\S+)", line))
            frames_seen[int(d["f"])] = d
    assert frames_seen, f"{name}: no PAINT lines\n{out.stdout[-2000:]}"
    return frames_seen


def click(f, at):
    x, y = at
    return f"{f - 4}:mouse={x:.0f}x{y:.0f} {f}:mouse_left+ {f + 3}:mouse_left-"


def point(s):
    x, y = s.split("x")
    return float(x), float(y)


def first(s, test, after=0):
    for f in sorted(s):
        if f >= after and test(s[f]):
            return f
    return -1


def main():
    with tempfile.TemporaryDirectory() as work:
        # the workshop on the screen, seen from the waterfront
        s = run(work, "look", 105, "")
        assert s[100]["ui"] == "none" and s[100]["mode"] == "walking" and "shed_px" in s[100], s[100]
        shed = point(s[100]["shed_px"])
        far = float(s[100]["stand_d"])
        assert far > 8.0, s[100]
        script = click(100, shed)

        # a click on it: the walk round the open end to the apron, and the painter spoken to
        s = run(work, "walk", 1100, script)
        talk = first(s, lambda d: d["ui"] == "talk")
        assert talk > 200, f"no talk after the walk: {s[max(s)]}"
        assert s[talk].get("talk") == "mechanic" and float(s[talk]["stand_d"]) < 1.0, s[talk]
        # (he walked there: nearer every second, never through the wall to a stop)
        walked = [float(s[f]["stand_d"]) for f in range(120, talk, 60)]
        assert all(b < a for a, b in zip(walked, walked[1:])), walked
        assert s[talk]["purse"] == s[100]["purse"] and s[talk]["berth"] == "false"
        last = s[max(s)]
        assert last["ui"] == "talk" and last["live"] == "true" and "ask" in last, last
        ask = point(last["ask"])
        asked = first(s, lambda d: d.get("live") == "true" and d.get("ask") == last["ask"], talk) + 30
        script += " " + click(asked, ask)
        print(f"walk: clicked the workshop at frame 100 from {far:.0f} m, there and talking to the painter at frame {talk}")

        # the painter's answer: she is brought round to the berth, and the shop's panel opens
        s = run(work, "ask", asked + 500, script)
        skipped = first(s, lambda d: d["skip"] == "true", asked)
        panel = first(s, lambda d: d["ui"] == "paint", asked)
        assert skipped > 0 and panel > skipped, (skipped, panel, s[max(s)])
        assert s[panel]["berth"] == "true" and int(s[panel]["minute"]) >= int(s[asked]["minute"]) + 6, s[panel]
        opened = s[panel + 20]
        assert opened["ui"] == "paint" and opened["quote"] == "0/0/0" and opened["job"] == "false", opened
        tabs = [float(v) for v in opened["tabs"].split(",")]
        livery = (tabs[0] + tabs[2] * 0.75, tabs[1] + 77.0)     # (the second livery of the first row)
        order = point(opened["order"])
        choose = panel + 40
        script += " " + click(choose, livery) + " " + click(choose + 40, order) + f" {choose + 110}:t+ {choose + 114}:t-"
        print(f"ask: the painter brought her round to the berth, the panel open at frame {panel}")

        # a livery chosen and priced; ordered: the painter paid, the work begun; the painter spoken to
        s = run(work, "order", choose + 110 + 500, script)
        priced = s[choose + 30]
        assert priced["quote"] == "1200/120/1", priced
        begun = s[choose + 60]
        assert begun["job"] == "true" and begun["ui"] == "none" and begun["stage"] == "masked", begun
        assert int(begun["purse"]) == int(priced["purse"]) - 1200, (priced, begun)
        again = first(s, lambda d: d["ui"] == "talk", choose + 100)
        assert again > 0, s[max(s)]
        last = s[max(s)]
        assert last["ui"] == "talk" and last["live"] == "true" and "next" in last, last
        wait = point(last["next"])
        waiting = first(s, lambda d: d.get("live") == "true" and d.get("next") == last["next"], again) + 30
        script += " " + click(waiting, wait)
        print(f"order: a new livery for 12 phoenixes, ordered at frame {choose + 40}; the painter paid, she is masked")

        # the wait, watched: masked, primer, top coat, dry in the new paint
        s = run(work, "wait", waiting + 700, script)
        watched = first(s, lambda d: d["wait_view"] == "true", waiting)
        assert watched > 0, s[max(s)]
        stages = []
        for f in sorted(s):
            if f >= watched and (not stages or stages[-1] != s[f]["stage"]):
                stages.append(s[f]["stage"])
        assert stages == ["masked", "primer", "top", "dry"], stages
        dry = first(s, lambda d: d["stage"] == "dry", watched)
        # (the whole wait in sight: a few seconds, not a dark card; and she stays at the berth)
        assert 120 < dry - watched < 700, (watched, dry)
        done = s[max(s)]
        assert done["job"] == "false" and done["wait_view"] == "false" and done["skip"] == "false" and done["berth"] == "true", done
        assert int(done["minute"]) >= int(begun["minute"]) + 120 and done["purse"] == begun["purse"], (begun, done)
        print(f"wait: watched from frame {watched}: {', '.join(stages)}; dry at frame {dry}")
        print("paint shop flow: the workshop tapped, the walk, the talk, the berth, the order, the wait, the new paint")
        # (PAINT_FLOW_SCRIPT=file: the whole visit's input kept, for a clip of it with the world drawn)
        if os.environ.get("PAINT_FLOW_SCRIPT"):
            Path(os.environ["PAINT_FLOW_SCRIPT"]).write_text(f"{script}\n{dry + 120}\n")


if __name__ == "__main__":
    main()
