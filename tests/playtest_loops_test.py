"""The game's loops played through by tools/playtest_probe.jo (the whole game, driven through the
functions the player's inputs reach), each case asserting there is a way on at every step: the first
delivery handed over and paid (saved and loaded on the dock), fuel bought and kept, a night in the
hotel's room to morning (and a save in the room loaded back by the desk), a pleasure flight brought
in, a wreck towed home, broke and dry at home with work still to be had, and the strait (won and
lost) and the canal escape handing back to the ordinary game on arrival, which then saves.
Slow (a minute or so a case here, several in CI). This file plays the flying loops and
tests/playtest_town_test.py the town's, both in CI only with slow: true; tests/playtest_situations_test.py
plays a wreck towed in by the call for help, the strait and the canal escape, on a real GPU only
(under CI's software rendering the strait ran some 300 frames in 14 minutes, and the tow over 30). Two cases at a time: python3 tests/playtest_loops_test.py
[town|flying|situations|pickups|all].
"""
import concurrent.futures as cf
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

GROUPS = {
    "town": [
        ("room", 3000, dict(AEGEAN_LEISURE="stay-hotel-window")),
        ("delivery", 8000, dict(AEGEAN_CAPTURE_DELIVERY="2", AEGEAN_DELIVERY_MOORED="1")),
        ("fuel", 3000, {}),
        ("night", 3000, dict(AEGEAN_LEISURE="stay-hotel")),
        ("broke", 3000, {}),
    ],
    "flying": [
        ("ride", 4000, dict(AEGEAN_LEISURE="ride-air", AEGEAN_FLYING="120")),
    ],
    "pickups": [
        ("bail", 8000, dict(AEGEAN_SCENARIO="strait")),
        ("bail-canal", 10000, dict(AEGEAN_SCENARIO="canal", AEGEAN_CAPTURE_CANAL_RUN="1")),
        ("bail-sea", 8000, dict(AEGEAN_FLYING="150 60")),
    ],
    "situations": [
        ("tow", 6000, dict(AEGEAN_FLYING="60")),
        ("strait-home", 9000, dict(AEGEAN_SCENARIO="strait", AEGEAN_CAPTURE_STRAIT_AFTER="arrive", PLAYTEST_COME_IN="3000")),
        ("strait-lose", 28000, dict(AEGEAN_SCENARIO="strait")),
        ("canal", 9000, dict(AEGEAN_SCENARIO="canal", AEGEAN_CAPTURE_CANAL_RUN="1", PLAYTEST_COME_IN="3600")),
    ],
}


def main(group="flying"):
    cases = [c for g in GROUPS.values() for c in g] if group == "all" else GROUPS[group]
    scratch = Path(os.environ.get("PLAYTEST_DIR", str(Path.home() / "dev/tmp/aegean-skies/playtest-test"))) / group
    scratch.mkdir(parents=True, exist_ok=True)
    # (built once: compiling the game again for every case is most of a case's time in CI)
    probe = scratch / "playtest-probe"
    built = subprocess.run(["sloppy", "build", "tools/playtest_probe.jo", "--release", "-o", str(probe)], cwd=ROOT, capture_output=True, text=True)
    assert built.returncode == 0, built.stdout[-3000:] + built.stderr[-3000:]

    def play(item):
        case, frames, extra = item
        env = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY") and not k.startswith("AEGEAN_")}
        env.update(PLAYTEST_DIR=str(scratch), PLAYTEST_BIN=str(probe), PLAYTEST_FRAMES=str(frames), PLAYTEST_NO_DRAW="1", **extra)
        out = subprocess.run(["sh", "tools/playtest.sh", case], cwd=ROOT, env=env, capture_output=True, text=True, timeout=1800)
        return case, out.returncode == 0 and f"PLAYTEST PASS {case}" in out.stdout, out

    failed = []
    with cf.ThreadPoolExecutor(max_workers=2) as pool:
        for case, ok, out in pool.map(play, cases):
            print(("PASS " if ok else "FAIL ") + case, flush=True)
            if not ok:
                failed.append(case)
                print(out.stdout[-3000:], out.stderr[-1000:], flush=True)
    assert not failed, f"dead ends in: {failed}"
    print("all loops played through")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "flying")
