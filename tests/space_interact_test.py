"""Space interacts with whatever is highlighted on foot and in rooms (tools/panel_probe.jo):
- on foot looking at a townsperson (AEGEAN_LEISURE=foot-person): Space walks the pilot over and
  opens the conversation;
- in a hotel room (AEGEAN_LEISURE=stay-hotel): Tab highlights the bed and Space sends the pilot
  to lie down and sleep; Space wakes him; Left highlights the door and Space leaves the room.
Run serially: python3 tests/space_interact_test.py.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(work, name, frames, script, **extra):
    env = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")}
    for k in ("AEGEAN_TITLE", "AEGEAN_CAPTURE_PANEL", "AEGEAN_LEISURE", "AEGEAN_TALK",
              "SLOPPY_TOUCH", "AEGEAN_TOUCH", "AEGEAN_CAPTURE_MINUTES", "AEGEAN_TALK_FOLLOW",
              "AEGEAN_LOOK_TRACE"):
        env.pop(k, None)
    env.update(
        SLOPPY_NO_AUDIO="1",
        SLOPPY_THREADS=env.get("SLOPPY_THREADS", "1"),
        SLOPPY_FRAMES=str(frames),
        SLOPPY_INPUT=script,
        SLOPPY_SAVE_DIR=str(Path(work) / name),
        SLOPPY_WINDOW="1280x720",
        SLOPPY_FIXED_STEP="1",
        AEGEAN_NO_WORLD="1",
        SLOPPY_SCREENSHOT=str(Path(work) / f"{name}.png"),
    )
    env.update(extra)
    out = subprocess.run(["sloppy", "--release", "tools/panel_probe.jo"], cwd=ROOT, env=env,
                         capture_output=True, text=True, timeout=1200)
    assert out.returncode == 0, f"{name}: exit {out.returncode}\n{out.stderr[-3000:]}"
    lines = out.stdout.splitlines()

    def table(head):
        return {int(d["f"]): d for d in (dict(re.findall(r"(\w+)=(\S*)", l)) for l in lines if l.startswith(head + " "))}
    return table("PROBE"), table("TALK"), out.stderr.splitlines()


def key(frame, k):
    return f"{frame}:{k}+ {frame + 2}:{k}-"


def main():
    scratch = Path.home() / "dev/tmp/aegean-skies/space-interact-test"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as work:
        # ---- on foot: looking at a townsperson, Space walks over and talks
        probe, talk, err = run(
            work, "foot-person", 320, "1:mouse=5x5 " + key(70, "space"),
            AEGEAN_LEISURE="foot-person", AEGEAN_LOOK_TRACE="1", AEGEAN_CAPTURE_MINUTES="40",
        )
        looks = [l for l in err if l.startswith("LOOK ")]
        assert looks and not looks[0].endswith(" -"), f"nothing highlighted on foot: {looks}"
        assert talk, f"Space did not open talk with highlighted person (looks={looks})"
        first = min(talk)
        assert first > 70 and probe[first]["ui"] == "talk", f"unexpected talk open at frame {first}"
        print(f"space on foot: highlighted ({looks[0]}), Space walked over and opened talk at frame {first}")

        # ---- in a room: Tab + Space lies down on the bed; Space wakes; Left + Space leaves by the door
        script = " ".join([
            "1:mouse=5x5",
            key(40, "tab"),      # highlight bed
            key(65, "space"),    # Space -> walk to bed, lie down, sleep
            key(520, "space"),   # Space -> wake
            key(550, "left"),    # highlight door
            key(575, "space"),   # Space -> get up, walk to door, leave
        ])
        probe, _, _ = run(work, "room-bed-door", 1120, script, AEGEAN_LEISURE="stay-hotel")
        assert all(probe[f]["ui"] == "leisure" and probe[f]["leisure"] == "15" for f in range(20, 100)), "not in hotel room"
        left = next((f for f in sorted(probe) if f > 575 and probe[f]["ui"] == "none"), None)
        assert left is not None, f"Space on highlighted door did not leave room (final={probe.get(1110)})"
        print(f"space in room: Tab+Space used bed, Space woke, Left+Space left by the door at frame {left}")
    print("ok")


if __name__ == "__main__":
    main()
