"""Every place someone puts a question to the pilot, played in the game itself through
tools/panel_probe.jo (its FAN line: the place's panel number, the speaker's bubble and the pilot's
reply bubbles where they were drawn; SAID: what he answered, over his head; KEEPER: the keeper's
word on an order). For each place: their words come in a bubble, what he can answer comes as
bubbles beside him (on the screen, big enough to hit, none over another or over their words, no
panel), a number answers, the answer is over his head, and the place goes on as it did with its
panel. The places: the hotel's desk and its room asked for at the table, a host's spare room, a
ride asked for and the rider left in the second seat, someone asking to join the table, the waiter's
"Finished with this?", the band (a number asked for, a player missing, the jar), tavli (whom to
play, then for what), the workshop's desk (a word, then the work list), the bath keeper; and the
keeper's word on an order over whoever serves.
Run serially: python3 tests/talk_places_test.py.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CLEAR = ("AEGEAN_TITLE", "AEGEAN_CAPTURE_PANEL", "AEGEAN_LEISURE", "AEGEAN_TALK", "SLOPPY_TOUCH", "AEGEAN_TOUCH",
         "AEGEAN_CAPTURE_MINUTES", "AEGEAN_TALK_FOLLOW", "AEGEAN_CAPTURE_WORKSHOP", "AEGEAN_BATH_ARRIVE", "AEGEAN_FOOT_GO",
         "AEGEAN_BATH_PAY", "AEGEAN_RIDE_AGREE", "AEGEAN_COMPANY")


def run(work, name, frames, script, **extra):
    env = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY") and k not in CLEAR}
    env.update(SLOPPY_NO_AUDIO="1", SLOPPY_THREADS=env.get("SLOPPY_THREADS", "1"), SLOPPY_FRAMES=str(frames),
               SLOPPY_INPUT=script, SLOPPY_SAVE_DIR=str(Path(work) / name), SLOPPY_WINDOW="1280x720",
               SLOPPY_FIXED_STEP="1", AEGEAN_NO_WORLD="1", SLOPPY_SCREENSHOT=str(Path(work) / f"{name}.png"), **extra)
    out = subprocess.run(["sloppy", "--release", "tools/panel_probe.jo"], cwd=ROOT, env=env,
                         capture_output=True, text=True, timeout=1200)
    assert out.returncode == 0, f"{name}: exit {out.returncode}\n{out.stderr[-3000:]}"
    lines = out.stdout.splitlines()

    def table(head):
        return {int(d["f"]): d for d in (dict(re.findall(r"(\w+)=(\S*)", l)) for l in lines if l.startswith(head + " "))}
    return table("PROBE"), table("FAN"), table("SAID"), table("KEEPER")


def key(frame, k):
    return f"{frame}:{k}+ {frame + 2}:{k}-"


def rects(text):
    return [tuple(float(v) for v in b.split(",")) for b in text.split(";") if b]


def cross(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


# (name, frames to run, the place's panel number, how many replies and the way out, the reply to
# give (a number key), what that leaves showing (a predicate on PROBE lines after it), env)
PLACES = [
    ("desk", 300, ("leisure", "2"), 2, "n0", lambda p: p["ui"] == "none", dict(AEGEAN_LEISURE="desk")),
    ("room at the table", 300, ("leisure", "2"), 2, "n0", lambda p: p["ui"] == "leisure" and p["leisure"] == "0", dict(AEGEAN_LEISURE="rest")),
    ("spare room", 300, ("leisure", "4"), 2, "n0", lambda p: p["ui"] == "none", dict(AEGEAN_LEISURE="spare")),
    ("ride asked for", 300, ("leisure", "16"), 2, "n1", lambda p: p["ui"] == "none", dict(AEGEAN_LEISURE="ride-ask")),
    ("rider waiting", 300, ("leisure", "18"), 2, "n1", lambda p: p["ui"] == "none", dict(AEGEAN_LEISURE="ride-wait")),
    ("company at the table", 300, ("leisure", "14"), 2, "n1", lambda p: p["ui"] == "leisure" and p["leisure"] == "0", dict(AEGEAN_LEISURE="company-ask")),
    ("waiter", 1100, ("leisure", "19"), 2, "n1", lambda p: p["ui"] == "leisure" and p["leisure"] == "0", dict(AEGEAN_LEISURE="waiter-ask")),
    ("band", 300, ("leisure", "8"), None, "n0", lambda p: p["ui"] == "leisure" and p["leisure"] == "0", dict(AEGEAN_LEISURE="request")),
    ("player missing", 500, ("leisure", "8"), None, "n0", lambda p: p["ui"] == "leisure" and p["leisure"] == "0", dict(AEGEAN_LEISURE="fetch")),
    ("tip jar", 300, ("leisure", "20"), 3, "n0", lambda p: p["ui"] == "none", dict(AEGEAN_LEISURE="tip-panel")),
    ("tavli", 300, ("leisure", "6"), None, "n1", lambda p: p["ui"] == "leisure" and p["leisure"] == "6", dict(AEGEAN_LEISURE="tavli-choose")),
    ("workshop", 500, ("workshop", "0"), 2, "n1", lambda p: p["ui"] == "workshop", dict(AEGEAN_CAPTURE_WORKSHOP="talk")),
    ("bath keeper", 1600, ("leisure", "21"), 2, "n0", lambda p: p["ui"] == "none", dict(AEGEAN_BATH_ARRIVE="141625", AEGEAN_FOOT_GO="60:The waters")),
]


def main():
    scratch = Path.home() / "dev/tmp/aegean-skies/talk-places-test"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as work:
        for name, frames, where, count, answer, after, extra in PLACES:
            # (a first run finds when the question is asked and its bubbles are up)
            probe, fan, said, _ = run(work, name.replace(" ", "-"), frames, "1:mouse=5x5", **extra)
            assert fan, f"{name}: no reply bubbles in {frames} frames"
            first = min(fan)
            f = fan[first]
            assert (f["ui"], f["leisure"] if where[0] == "leisure" else "0") == where, f"{name}: {f}"
            # (their words first, where they are said: the bubbles wait for them)
            ready = next((g for g in sorted(fan) if g > first + 2 and fan[g]["boxes"] == fan[first]["boxes"]), first + 3)
            t = fan[ready]
            got = rects(t["boxes"])
            if count is not None: assert len(got) == count, f"{name}: {len(got)} bubbles: {t['boxes']}"
            assert len(got) >= 2, f"{name}: {t['boxes']}"
            theirs = rects(t["bubble"])[0] if t["said"] == "true" else None
            for i, b in enumerate(got):
                assert b[0] >= 0 and b[1] >= 0 and b[0] + b[2] <= 1280 and b[1] + b[3] <= 720 and b[2] >= 28 and b[3] >= 28, f"{name}: bubble {i} {b}"
                if theirs: assert not cross(b, theirs), f"{name}: bubble {i} over their words"
                for j, c in enumerate(got[:i]): assert not cross(b, c), f"{name}: bubbles {i} and {j} overlap"
            # (the answer: given at once, the pilot's words over his head, the place gone on)
            at = ready + 20
            probe, fan, said, _ = run(work, name.replace(" ", "-") + "-answered", at + 60, key(at, answer), **extra)
            spoke = [g for g in said if g >= at]
            assert spoke, f"{name}: nothing said over his head after {answer}"
            words = said[min(spoke)]["pilot"].replace("_", " ")
            assert after(probe[at + 20]), f"{name}: after {answer} ('{words}'): {probe[at + 20]}"
            print(f"{name}: {len(got)} bubbles{', their words over them' if theirs else ''}; {answer[1]} said '{words}'")
        # (the keeper's word on an order: over whoever serves, not under the bill of fare)
        probe, fan, said, keeper = run(work, "remark", 200, "1:mouse=5x5", AEGEAN_LEISURE="remark")
        assert keeper, "the keeper's word was not drawn"
        k = keeper[max(keeper)]
        assert k["remark"] != "" and k["leisure"] == "13", k
        b = rects(k["bubble"])[0]
        assert b[2] > 20 and b[3] > 20 and b[0] + b[2] <= 1280 and b[1] + b[3] <= 720, k
        print(f"the keeper's word: '{k['remark'].replace('_', ' ')}' over whoever serves")
    print("ok")


if __name__ == "__main__":
    main()
