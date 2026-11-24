"""A conversation with no panel, played in the game itself through tools/panel_probe.jo (SLOPPY_INPUT
at fixed steps; its TALK line: how much of the person's line has arrived, whose bubbles are up, and
where each of the pilot's reply bubbles was drawn):
- the person's line arrives a few characters a frame in their bubble, and nothing can be said back
  until it is whole; then the reply bubbles are there, four and the way out, with arrows for more;
- Space finishes the line at once and does nothing else, and so does a click on their bubble;
- Tab turns to the next set, a number says that set's reply, a click on a bubble says it, a click
  on an arrow turns the sets, a click on Goodbye ends it;
- a controller's d-pad reaches a reply and A says it, a bumper turns the sets, B is goodbye;
- what is said puts the pilot's words over his head, then the person's answer arrives;
- an answer to their question fades away unanswered and the subjects stay;
- goodbye ends the conversation and both bubbles with it.
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
    for k in ("AEGEAN_TITLE", "AEGEAN_CAPTURE_PANEL", "AEGEAN_LEISURE", "AEGEAN_TALK", "SLOPPY_TOUCH", "AEGEAN_TOUCH", "AEGEAN_TALK_FOLLOW"):
        env.pop(k, None)
    env.update(SLOPPY_NO_AUDIO="1", SLOPPY_THREADS=env.get("SLOPPY_THREADS", "1"), SLOPPY_FRAMES=str(frames),
               SLOPPY_INPUT=script, SLOPPY_SAVE_DIR=str(Path(work) / name), SLOPPY_WINDOW="1280x720",
               SLOPPY_FIXED_STEP="1", AEGEAN_NO_WORLD="1",
               # (someone with nowhere to be, forty minutes into the day, who stands for the talk:
               # tests/talk_hold_test.py has the ones who walk on)
               AEGEAN_TALK="idle", AEGEAN_CAPTURE_MINUTES="40",
               SLOPPY_SCREENSHOT=str(Path(work) / f"{name}.png"))
    env.update(extra)
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


def click(frame, box):
    x, y, w, h = box
    return f"{frame}:mouse={int(x + w / 2)}x{int(y + h / 2)} {frame + 1}:mouse_left+ {frame + 3}:mouse_left-"


def shown(t):
    return int(t["chars"]) if t["shown"] == "-1" else int(t["shown"])


def boxes(t):
    return [tuple(float(v) for v in b.split(",")) for b in t["boxes"].split(";") if b]


def bubble(t):
    return tuple(float(v) for v in t["bubble"].split(","))


def own_bubble(t):
    return tuple(float(v) for v in t["own"].split(","))


def rects_overlap(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def menu_bounds(bs):
    x0 = min(r[0] for r in bs)
    y0 = min(r[1] for r in bs)
    x1 = max(r[0] + r[2] for r in bs)
    y1 = max(r[1] + r[3] for r in bs)
    return (x0, y0, x1 - x0, y1 - y0)


def said_by(talk, frame, within=4):
    return next((f for f in range(frame, frame + within + 1) if f in talk and talk[f]["words"] != talk[frame - 1]["words"]), None)


def main():
    scratch = Path.home() / "dev/tmp/aegean-skies/talk-bubbles-test"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as work:
        # ---- left alone: the line arrives, then what he can say is there; an answer unanswered fades
        probe, talk = run(work, "alone", 1150, "1:mouse=5x5")
        first = min(talk)
        chars = int(talk[first]["chars"])
        assert chars >= 30, f"a short greeting to time ({chars} characters): {talk[first]}"
        whole = next(f for f in sorted(talk) if talk[f]["done"] == "true")
        last = 0
        for f in range(first, whole):
            t = talk[f]
            n = shown(t)
            assert 0 <= n - last <= 2, f"frame {f}: {last} -> {n} characters"
            assert t["ready"] == "false" and t["pilot"] == "false" and not boxes(t), f"frame {f}: {t}"
            # (the probe reads a frame before it is drawn: the bubble's first shows in the next)
            assert f < first + 2 or (t["person"] == "true" and t["space"] == "true"), f"frame {f}: {t}"
            last = n
        seconds = (whole - first) / 60.0
        assert chars / 50.0 - 0.1 <= seconds <= chars / 35.0 + 2.5, f"{chars} characters in {seconds:.2f} s"
        assert talk[whole + 1]["ready"] == "true" and talk[whole + 3]["space"] == "false"
        # (what he can say: four of them, two arrows for the rest, and the way out; on the screen,
        # none over another, none over their bubble, each big enough to hit)
        t = talk[whole + 20]
        options = int(t["options"])
        got = boxes(t)
        assert options > 4 and len(got) == 4 + 2 + 1, f"{options} things to say, {len(got)} bubbles: {t['boxes']}"
        theirs = bubble(t)
        for i, (x, y, w, h) in enumerate(got):
            assert x >= 0 and y >= 0 and x + w <= 1280 and y + h <= 720 and w >= 28 and h >= 28, f"bubble {i}: {x},{y},{w},{h}"
            assert not (x < theirs[0] + theirs[2] and theirs[0] < x + w and y < theirs[1] + theirs[3] and theirs[1] < y + h), f"bubble {i} over their line"
            for j, (x2, y2, w2, h2) in enumerate(got[:i]):
                assert not (x < x2 + w2 and x2 < x + w and y < y2 + h2 and y2 < y + h), f"bubbles {i} and {j} overlap"
        # (the menu stays pinned from its first visible frame through fading replies too)
        first_menu = next(f for f in sorted(talk) if boxes(talk[f]))
        pinned = boxes(talk[first_menu])
        for f in range(first_menu, whole + 60 * 11):
            if f in talk and boxes(talk[f]) and int(talk[f]["options"]) == options:
                assert boxes(talk[f]) == pinned, f"frame {f}: menu moved from {pinned} to {boxes(talk[f])}"
        # (their question unanswered: its answers gone some twelve seconds on, the subjects still
        # there, and their line with them; the menu stays pinned at the same top edge)
        late = talk[whole + 60 * 14]
        assert 0 < int(late["options"]) < options, f"the answers stayed: {late['options']} of {options}"
        assert late["person"] == "true" and probe[whole + 60 * 14]["ui"] == "talk"
        assert abs(boxes(late)[0][1] - pinned[0][1]) < 1.0, f"menu top jumped when replies expired: {pinned[0]} -> {boxes(late)[0]}"
        print(f"left alone: {chars} characters in {seconds:.1f} s, then {options} things to say; the answers faded, {late['options']} left")
        at = whole + 30

        # ---- the keys: Space, Tab, a number, Escape
        probe, talk = run(work, "keys", at + 520, " ".join([key(first + 20, "space"), key(at, "tab"), key(at + 20, "n1"), key(at + 500, "escape")]))
        before = talk[first + 19]
        assert before["done"] == "false" and shown(before) < chars
        after = talk[first + 23]
        assert after["done"] == "true" and after["words"] == "" and int(after["chars"]) == chars, after
        assert all(probe[f]["ui"] == "talk" for f in range(first + 18, at)), "Space did more than finish the line"
        assert talk[first + 25]["ready"] == "true"
        # (Tab: the next set; 1 there says the fifth thing, not the first)
        assert talk[at - 1]["set"] == "0" and talk[at + 4]["set"] == "1", talk[at + 4]
        said = said_by(talk, at + 20)
        assert said is not None, "1 said nothing"
        words = talk[said]["words"]
        t = talk[said + 2]
        assert t["pilot"] == "true" and t["person"] == "true" and t["done"] == "false" and shown(t) == 0, t
        assert not boxes(talk[said + 6]), "the replies stayed up while the answer arrived"
        reply = int(t["chars"])
        mid = talk[said + 60]
        assert mid["pilot"] == "true" and mid["person"] == "true" and 0 < shown(mid), mid
        done = next(f for f in sorted(talk) if f > said + 2 and talk[f]["done"] == "true")
        assert (done - said) / 60.0 >= reply / 50.0, f"{reply} characters in {(done - said) / 60.0:.2f} s"
        gone = at + 500 + 4
        assert probe[gone]["ui"] == "none", probe[gone]
        assert not [f for f in talk if f >= gone], "a bubble outlived the conversation"
        print(f"the keys: Space finished the line, Tab turned the set, 1 said \"{words.replace('_', ' ')}\", Escape left")

        # ---- the mouse: their bubble finishes the line; a reply, an arrow and Goodbye are clicked
        got = boxes(talk[at - 2])
        probe, talk = run(work, "mouse", at + 420, " ".join([click(first + 20, bubble(talk[first + 19])), click(at, got[5]), click(at + 30, got[1]), "PLACEHOLDER"]).replace("PLACEHOLDER", ""))
        assert talk[first + 19]["done"] == "false" and talk[first + 25]["done"] == "true", talk[first + 25]
        for f in range(first + 20, at - 1):
            assert probe[f]["ui"] == "talk" and talk[f]["words"] == "" and int(talk[f]["chars"]) == chars, f"frame {f}: the click on their line said something: {talk[f]}"
        assert talk[at + 6]["set"] == "1", f"the arrow turned nothing: {talk[at + 6]}"
        said = said_by(talk, at + 30, 6)
        assert said is not None and talk[said]["words"] != "", "a click on a reply said nothing"
        ready = next(f for f in sorted(talk) if f > said + 10 and talk[f]["ready"] == "true")
        leave = boxes(talk[ready + 15])[-1]
        probe, talk = run(work, "mouse-leave", ready + 60, " ".join([key(first + 20, "space"), click(at, got[5]), click(at + 30, got[1]), click(ready + 20, leave)]))
        assert probe[ready + 16]["ui"] == "talk" and probe[ready + 30]["ui"] == "none", "a click on Goodbye did not end it"
        print("the mouse: their bubble, an arrow, a reply and Goodbye")

        # ---- a controller: the d-pad, A, a bumper, B
        steps = [key(first + 20, "pad_a"), key(at, "pad_down"), key(at + 10, "pad_down"), key(at + 20, "pad_rb"), key(at + 40, "pad_down"), key(at + 50, "pad_a"), key(at + 300, "pad_b")]
        probe, talk = run(work, "pad", at + 320, " ".join(steps))
        assert talk[first + 19]["done"] == "false" and talk[first + 24]["done"] == "true", "A did not finish the line"
        assert all(talk[f]["words"] == "" for f in range(first + 20, at)), "A finishing the line also said something"
        assert talk[at + 4]["reach"] == "0" and talk[at + 14]["reach"] == "1", talk[at + 14]
        assert talk[at + 24]["set"] == "1" and talk[at + 24]["reach"] == "-1", talk[at + 24]
        assert talk[at + 44]["reach"] == "0"
        said = said_by(talk, at + 50, 6)
        assert said is not None and talk[said]["words"] != "", "A said nothing"
        assert probe[at + 296]["ui"] == "talk" and probe[at + 306]["ui"] == "none", "B did not end it"
        print("a controller: the d-pad reached a reply, a bumper turned the set, A said it, B left")

        # ---- moving scene: speaker walking, pilot walking, camera rotating -> menu never moves,
        # and neither the speaker's nor the pilot's speech bubble ever overlaps the open menu
        # (AEGEAN_TALK=1 opens a talk with someone who soon gets a load and walks off; we also walk
        # and rotate the camera with Q and D while the reply fan is open)
        move_script = "1:mouse=5x5 300:q+ 480:q- 360:d+ 450:d-"
        probe, talk = run(work, "moving", 720, move_script, AEGEAN_TALK="1", AEGEAN_TALK_FOLLOW="1", AEGEAN_CAPTURE_MINUTES="0")
        # Check every contiguous open run of the menu (same option count and set): zero drift after first frame.
        open_runs = 0
        run_boxes = None
        run_opts = None
        run_set = None
        run_bubbles = set()
        for f in sorted(talk):
            t = talk[f]
            b = boxes(t)
            if not b:
                if run_boxes is not None:
                    open_runs += 1
                    run_boxes = None
                continue
            opts, cur_set = t["options"], t["set"]
            run_bubbles.add(t["bubble"])
            # (neither speaker's nor pilot's bubble may be covered by the open menu)
            mb = menu_bounds(b)
            if t["person"] == "true":
                th = bubble(t)
                assert not rects_overlap(th, mb), f"moving frame {f}: speaker bubble {th} overlapped menu {mb}"
            if t["pilot"] == "true":
                ow = own_bubble(t)
                assert not rects_overlap(ow, mb), f"moving frame {f}: pilot bubble {ow} overlapped menu {mb}"
            if run_boxes is None or opts != run_opts or cur_set != run_set:
                if run_boxes is not None:
                    # (if options or set changed while still open, top edge must remain pinned)
                    assert abs(b[0][1] - run_boxes[0][1]) < 1.0, f"moving frame {f}: menu top jumped {run_boxes[0]} -> {b[0]}"
                run_boxes = b
                run_opts = opts
                run_set = cur_set
            else:
                assert b == run_boxes, f"moving frame {f}: menu moved after first frame: {run_boxes} -> {b}"
        if run_boxes is not None:
            open_runs += 1
        assert open_runs >= 1, "moving scene never opened a talk menu"
        assert len(run_bubbles) >= 5, f"moving scene speaker bubble did not actually move ({len(run_bubbles)} positions)"
        print(f"moving scene: {open_runs} open menu span(s), speaker bubble moved across {len(run_bubbles)} positions, menu stayed steady and bubbles clear")

        # ---- walk-with-me scene: pilot answers "Lead on." and walks alongside as both bubbles pass
        # behind the pinned menu -> menu stays pinned, neither bubble ever overlaps the menu or each other
        called = next(f for f in sorted(talk) if talk[f]["walking"] == "true")
        ready_walk = next(f for f in sorted(talk) if f > called + 20 and talk[f]["ready"] == "true" and boxes(talk[f]))
        press_at = ready_walk + 30
        probe, talk = run(work, "walk-clear", press_at + 380, "1:mouse=5x5 " + key(press_at, "n1"), AEGEAN_TALK="1", AEGEAN_CAPTURE_MINUTES="0")
        checked_both = 0
        checked_speaker = 0
        run_boxes = None
        run_opts = None
        run_set = None
        for f in sorted(talk):
            t = talk[f]
            b = boxes(t)
            if not b:
                run_boxes = None
                continue
            opts, cur_set = t["options"], t["set"]
            if run_boxes is None or opts != run_opts or cur_set != run_set:
                run_boxes = b; run_opts = opts; run_set = cur_set
            else:
                assert b == run_boxes, f"walk-clear frame {f}: menu moved {run_boxes} -> {b}"
            mb = menu_bounds(b)
            if t["person"] == "true":
                th = bubble(t)
                checked_speaker += 1
                assert not rects_overlap(th, mb), f"walk-clear frame {f}: speaker bubble {th} overlapped menu {mb}"
            if t["pilot"] == "true":
                ow = own_bubble(t)
                assert not rects_overlap(ow, mb), f"walk-clear frame {f}: pilot bubble {ow} overlapped menu {mb}"
                if t["person"] == "true":
                    checked_both += 1
                    assert not rects_overlap(ow, bubble(t)), f"walk-clear frame {f}: pilot bubble {ow} overlapped speaker bubble {bubble(t)}"
        assert checked_speaker >= 100 and checked_both >= 20, f"walk-clear did not cover enough frames (speaker={checked_speaker}, both={checked_both})"
        print(f"walk-clear scene: {checked_speaker} menu frames ({checked_both} with both bubbles) — zero overlap, menu pinned")
    print("ok")


if __name__ == "__main__":
    main()
