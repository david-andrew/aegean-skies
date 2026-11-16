"""The game's loops played through by tools/playtest_probe.jo (the whole game, driven through the
functions the player's inputs reach), each case asserting there is a way on at every step: the first
delivery handed over and paid (saved and loaded on the dock), fuel bought and kept, a night in the
hotel's room to morning (and a save in the room loaded back by the desk), a pleasure flight brought
in, a wreck towed home, broke and dry at home with work still to be had, and the strait (won and
lost) and the canal escape handing back to the ordinary game on arrival, which then saves.
Slow (a minute or so a case): in CI only with slow: true. Run serially: python3 tests/playtest_loops_test.py.
"""
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

CASES = [
    ("room", 3000, dict(AEGEAN_LEISURE="stay-hotel-window")),
    ("delivery", 8000, dict(AEGEAN_CAPTURE_DELIVERY="2", AEGEAN_DELIVERY_MOORED="1")),
    ("fuel", 3000, {}),
    ("night", 3000, dict(AEGEAN_LEISURE="stay-hotel")),
    ("ride", 4000, dict(AEGEAN_LEISURE="ride-air", AEGEAN_FLYING="120")),
    ("tow", 2000, dict(AEGEAN_FLYING="60")),
    ("broke", 3000, {}),
    ("strait-home", 9000, dict(AEGEAN_SCENARIO="strait", AEGEAN_CAPTURE_STRAIT_AFTER="arrive", PLAYTEST_COME_IN="3000")),
    ("strait-lose", 4000, dict(AEGEAN_SCENARIO="strait")),
    ("canal", 9000, dict(AEGEAN_SCENARIO="canal", AEGEAN_CAPTURE_CANAL_RUN="1", PLAYTEST_COME_IN="3600")),
]


def main():
    scratch = Path(os.environ.get("PLAYTEST_DIR", str(Path.home() / "dev/tmp/aegean-skies/playtest-test")))
    scratch.mkdir(parents=True, exist_ok=True)
    # (built once: compiling the game again for every case is most of a case's time in CI)
    probe = scratch / "playtest-probe"
    built = subprocess.run(["sloppy", "build", "tools/playtest_probe.jo", "--release", "-o", str(probe)], cwd=ROOT, capture_output=True, text=True)
    assert built.returncode == 0, built.stdout[-3000:] + built.stderr[-3000:]
    failed = []
    for case, frames, extra in CASES:
        env = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY") and not k.startswith("AEGEAN_")}
        env.update(PLAYTEST_DIR=str(scratch), PLAYTEST_BIN=str(probe), PLAYTEST_FRAMES=str(frames), PLAYTEST_NO_DRAW="1", **extra)
        out = subprocess.run(["sh", "tools/playtest.sh", case], cwd=ROOT, env=env, capture_output=True, text=True, timeout=1800)
        ok = out.returncode == 0 and f"PLAYTEST PASS {case}" in out.stdout
        print(("PASS " if ok else "FAIL ") + case, flush=True)
        if not ok:
            failed.append(case)
            print(out.stdout[-3000:], out.stderr[-1000:], flush=True)
    assert not failed, f"dead ends in: {failed}"
    print("all loops played through")


if __name__ == "__main__":
    main()
