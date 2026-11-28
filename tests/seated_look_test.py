"""Seated at the Hotel Ancora, there is no panel: what the view looks at is lit and used with Space
(or tapped), as on foot, and only a few things have a button beside them (each dish and glass, the
menu card, the pilot's own: wait, get up). Played in the game itself (AEGEAN_SEAT_TRACE: the
SEATTHINGS line lists what can be looked at and the buttons; AEGEAN_SEAT_USE=<frame>:<what> uses
a thing as Space on it would). The things: the dishes, the menu card, whoever serves, the people
about, the band's stand (asked from the seat: the pilot stays sat); never the tip jar.
Run serially: python3 tests/seated_look_test.py.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(work, name, frames, **extra):
    env = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY") and not k.startswith("AEGEAN_")}
    env.update(SLOPPY_NO_AUDIO="1", SLOPPY_THREADS=env.get("SLOPPY_THREADS", "1"), SLOPPY_FRAMES=str(frames),
               SLOPPY_SAVE_DIR=str(Path(work) / name), SLOPPY_WINDOW="1280x720", SLOPPY_FIXED_STEP="1",
               AEGEAN_NO_WORLD="1", AEGEAN_SEAT_TRACE="1", AEGEAN_CAPTURE_MINUTES="600",
               SLOPPY_SCREENSHOT=str(Path(work) / f"{name}.png"), **extra)
    out = subprocess.run(["sloppy", "--release", "aegean.jo"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=1500)
    assert out.returncode == 0, f"{name}: exit {out.returncode}\n{out.stderr[-3000:]}"
    lines = out.stdout.splitlines()

    def table(head):
        return [dict(re.findall(r"(\w+)=(\S*)", l)) for l in lines if l.startswith(head + " ")]
    return table("SEATTHINGS"), table("SEATUI")


def main():
    with tempfile.TemporaryDirectory(dir=os.environ.get("AEGEAN_TEST_TMP")) as work:
        # (at the bar: three things on the counter, one in hand; the card; the barkeep; the stand)
        things, ui = run(work, "bar", 90, AEGEAN_LEISURE="seat-bar")
        assert things, "no SEATTHINGS lines"
        last = things[-1]
        seen = last["things"].split("|")
        assert sum(1 for s in seen if s.startswith("dish:")) == 2, seen      # (the third is in hand)
        for want in ("menu", "server", "song"):
            assert want in seen, (want, seen)
        assert "tip" not in seen, seen
        pills = last["pills"].split("|")
        assert pills.count("Drink") + pills.count("Eat") == 3, pills
        assert "Read" in pills and "Wait_an_hour" in pills and ("Put_it_down" in pills or "Get_up" in pills), pills
        # (the buttons never overlap one another)
        rs = [tuple(float(v) for v in r.split(",")) for r in last["rects"].split(";") if r]
        shown = [r for r in rs if r[2] > 0]
        assert len(shown) == len(pills), (shown, pills)
        for i in range(len(shown)):
            for j in range(i + 1, len(shown)):
                a, b = shown[i], shown[j]
                assert not (a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]), (a, b)
        assert last["looked"] != "-", last
        assert not any(u["ui"] == "leisure" and u["leisure"] not in ("0",) for u in ui), "a panel opened by itself"
        # (the band asked from the stool: he calls across, their answer comes, he stays sat)
        _, ui = run(work, "song", 120, AEGEAN_LEISURE="seat-bar", AEGEAN_SEAT_USE="60:song")
        after = [u for u in ui if int(u["f"]) > 62]
        assert after and all(u["sitting"] == "bar" for u in after), after
        assert any(u["leisure"] == "8" for u in after), after
        assert any("play" in u["pilot_word"] for u in after), after
        # (whoever serves, called over: their question, with the menu, a room)
        _, ui = run(work, "server", 100, AEGEAN_LEISURE="seat-bar", AEGEAN_SEAT_USE="60:server")
        assert any(u["leisure"] == "23" and u["sitting"] == "bar" for u in ui if int(u["f"]) > 62), ui
        # (the card read: the bill of fare, still sat)
        _, ui = run(work, "menu", 100, AEGEAN_LEISURE="seat", AEGEAN_SEAT_USE="60:menu")
        assert any(u["leisure"] == "13" and u["sitting"] == "hotel" for u in ui if int(u["f"]) > 62), ui
    print("seated look: ok")


if __name__ == "__main__":
    main()
