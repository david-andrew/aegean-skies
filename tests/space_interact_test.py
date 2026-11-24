"""Space interacts with highlighted world things, mouse clicks do not, and touch taps still do:
- on foot looking at a townsperson (AEGEAN_LEISURE=foot-person):
  - Space walks the pilot over and opens the conversation;
  - left-clicking the highlighted person (unlocked or locked) does not open talk;
  - a touch tap (without SLOPPY_TOUCH=1, proving it is gated on touch input rather than platform)
    walks over and opens the conversation.
- in a hotel room (AEGEAN_LEISURE=stay-hotel):
  - Tab highlights the bed and Space lies down and sleeps; Space wakes him; Left highlights the
    door and Space leaves the room;
  - hovering and left-clicking the highlighted bed or door does nothing;
  - touch-tapping the bed (without SLOPPY_TOUCH=1) lies down and sleeps, and touch-tapping the
    door wakes him and leaves the room.
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
    return table("PROBE"), table("TALK"), table("ROOM"), out.stderr.splitlines()


def key(frame, k):
    return f"{frame}:{k}+ {frame + 2}:{k}-"


def click(frame, xy):
    return f"{frame}:mouse={xy} {frame + 2}:mouse_left+ {frame + 4}:mouse_left-"


def tap(frame, xy):
    return f"{frame}:touch1={xy} {frame + 3}:touch1-"


def main():
    scratch = Path.home() / "dev/tmp/aegean-skies/space-interact-test"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as work:
        # ---- on foot: looking at a townsperson, Space walks over and talks
        probe, talk, _, err = run(
            work, "foot-person-space", 320, "1:mouse=5x5 " + key(70, "space"),
            AEGEAN_LEISURE="foot-person", AEGEAN_LOOK_TRACE="1", AEGEAN_CAPTURE_MINUTES="40",
        )
        looks = [l for l in err if l.startswith("LOOK ")]
        assert looks and not looks[0].endswith(" -"), f"nothing highlighted on foot: {looks}"
        assert talk, f"Space did not open talk with highlighted person (looks={looks})"
        first = min(talk)
        assert first > 70 and probe[first]["ui"] == "talk", f"unexpected talk open at frame {first}"
        print(f"space on foot: highlighted ({looks[0]}), Space walked over and opened talk at frame {first}")

        # ---- on foot: left-clicking the highlighted person does nothing (unlocked or locked)
        probe, talk, _, err = run(
            work, "foot-person-click", 300,
            " ".join([click(70, "640x360"), click(120, "640x360")]),
            AEGEAN_LEISURE="foot-person", AEGEAN_LOOK_TRACE="1", AEGEAN_CAPTURE_MINUTES="40",
        )
        looks = [l for l in err if l.startswith("LOOK ")]
        assert looks and not looks[0].endswith(" -"), f"nothing highlighted on foot for click test: {looks}"
        assert not talk, f"mouse click unexpectedly opened talk on foot (first={min(talk)})"
        assert all(probe[f]["ui"] == "none" for f in range(20, 295)), "mouse click changed ui on foot"
        print("click on foot: highlighted person ignored left clicks (unlocked and locked)")

        # ---- on foot: touch tap (without SLOPPY_TOUCH=1) walks over and talks
        probe, talk, _, err = run(
            work, "foot-person-touch", 320, "1:mouse=5x5 " + tap(70, "640x360"),
            AEGEAN_LEISURE="foot-person", AEGEAN_LOOK_TRACE="1", AEGEAN_CAPTURE_MINUTES="40",
        )
        assert talk, f"touch tap did not open talk with highlighted person"
        first = min(talk)
        assert first > 70 and probe[first]["ui"] == "talk", f"unexpected touch talk open at frame {first}"
        print(f"touch on foot: tap walked over and opened talk at frame {first} (without SLOPPY_TOUCH)")

        # ---- in a room: Tab + Space lies down on the bed; Space wakes; Left + Space leaves by the door
        script = " ".join([
            "1:mouse=5x5",
            key(40, "tab"),      # highlight bed
            key(65, "space"),    # Space -> walk to bed, lie down, sleep
            key(520, "space"),   # Space -> wake
            key(550, "left"),    # highlight door
            key(575, "space"),   # Space -> get up, walk to door, leave
        ])
        probe, _, room, _ = run(work, "room-space", 1120, script, AEGEAN_LEISURE="stay-hotel")
        assert all(probe[f]["ui"] == "leisure" and probe[f]["leisure"] == "15" for f in range(20, 100)), "not in hotel room"
        assert any(room[f]["skip"] == "true" for f in range(100, 520)), "Space on bed did not sleep"
        left = next((f for f in sorted(probe) if f > 575 and probe[f]["ui"] == "none"), None)
        assert left is not None, f"Space on highlighted door did not leave room (final={probe.get(1110)})"
        bed = room[30]["bed"]
        door = room[30]["door"]
        door_asleep = room[515]["door"]
        assert bed != "none" and door != "none" and door_asleep != "none", f"room coords missing: bed={bed} door={door} door_asleep={door_asleep}"
        print(f"space in room: Tab+Space used bed, Space woke, Left+Space left by the door at frame {left}")

        # ---- in a room: hovering and left-clicking the highlighted bed and door does nothing
        script = " ".join([
            f"30:mouse={bed}",
            click(45, bed),
            f"140:mouse={door}",
            click(155, door),
        ])
        probe, _, room, _ = run(work, "room-click", 290, script, AEGEAN_LEISURE="stay-hotel")
        assert room[44]["hover"] == "0", f"bed not hovered before click: {room.get(44)}"
        assert room[154]["hover"] == "3", f"door not hovered before click: {room.get(154)}"
        assert all(room[f]["going"] == "-1" and room[f]["skip"] == "false" for f in range(40, 285)), (
            f"mouse click triggered room movement or sleep: {[room[f] for f in range(40, 285) if room[f]['going'] != '-1' or room[f]['skip'] != 'false'][:3]}"
        )
        assert all(probe[f]["ui"] == "leisure" and probe[f]["leisure"] == "15" for f in range(40, 285)), "mouse click left room"
        print(f"click in room: highlighted bed ({bed}) and door ({door}) ignored left clicks")

        # ---- in a room: touch-tapping the bed sleeps, and touch-tapping the door leaves (without SLOPPY_TOUCH=1)
        script = " ".join([
            "1:mouse=5x5",
            tap(50, bed),
            tap(520, door_asleep),
        ])
        probe, _, room, _ = run(work, "room-touch", 1120, script, AEGEAN_LEISURE="stay-hotel")
        slept = next((f for f in sorted(room) if 60 <= f < 520 and room[f]["skip"] == "true"), None)
        assert slept is not None, "touch tap on bed did not sleep"
        left = next((f for f in sorted(probe) if f > 520 and probe[f]["ui"] == "none"), None)
        assert left is not None, f"touch tap on door did not wake and leave room (final={probe.get(1110)})"
        print(f"touch in room: tap bed slept at frame {slept}, tap door woke and left at frame {left} (without SLOPPY_TOUCH)")
    print("ok")


if __name__ == "__main__":
    main()
