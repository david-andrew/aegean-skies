"""End-to-end verification of no-warp lodgings, showing/pointing the way, and "Where is...?":
1. Sofia on the dock (AEGEAN_TALK=sofia-dock): agreeing to a hotel room books and pays with zero
   teleportation (no 1-frame position jump), Sofia walks/points the pilot to Hotel Ancora, and
   entering the room happens only when the pilot reaches the hotel door and uses it himself.
2. Family spare room (AEGEAN_TALK=spare-guide): agreeing to a resident's spare room never warps
   the pilot; the resident leads the pilot along the street to their door, stops with an arrival
   line and highlights the door, and the pilot enters the family stay at the door.
3. Pointing out a landmark (AEGEAN_TALK=cafe-point): asking "Where is...?" -> "Where is the cafe?"
   triggers WayMode.point, turns the speaker with a pointing arm gesture, and lights the cafe with
   a brief diegetic soft highlight.
4. Out-of-sight / far landmark (AEGEAN_TALK=far-place): asking "Where is...?" for a far/occluded
   place gives verbal directions only (WayMode.words, no arm point, no highlight).
Run serially: python3 tests/show_the_way_test.py.
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
        AEGEAN_CAPTURE_MINUTES="40",
        SLOPPY_SCREENSHOT=str(Path(work) / f"{name}.png"),
    )
    env.update(extra)
    out = subprocess.run(["sloppy", "--release", "tools/panel_probe.jo"], cwd=ROOT, env=env,
                         capture_output=True, text=True, timeout=1200)
    assert out.returncode == 0, f"{name}: exit {out.returncode}\n{out.stderr[-3000:]}"
    lines = out.stdout.splitlines()

    def table(head):
        return {int(d["f"]): d for d in (dict(re.findall(r"(\w+)=(\S*)", l)) for l in lines if l.startswith(head + " "))}
    return table("PROBE"), table("TALK"), table("WHO"), table("WAY")


def key(frame, k):
    return f"{frame}:{k}+ {frame + 2}:{k}-"


def pick_option(start_frame, idx):
    """Turn reply sets with Tab, then press 1..4 to choose option `idx`."""
    parts = []
    f = start_frame
    for _ in range(idx // 4):
        parts.append(key(f, "tab"))
        f += 8
    parts.append(key(f, f"n{(idx % 4) + 1}"))
    return " ".join(parts), f + 4


def find_opt(talk_row, needle):
    opts = [o for o in talk_row.get("opts", "").split("|") if o]
    low = needle.lower()
    for i, o in enumerate(opts):
        if low in o.lower():
            return i, opts
    raise AssertionError(f"option {needle!r} not found in {opts}")


def max_frame_jump(who, f_start, f_end):
    """Maximum single-frame horizontal displacement of the pilot in [f_start, f_end]."""
    fs = sorted(f for f in who if f_start <= f <= f_end)
    worst = 0.0
    worst_f = -1
    for a, b in zip(fs, fs[1:]):
        if b != a + 1:
            continue
        dx = float(who[b]["me_x"]) - float(who[a]["me_x"])
        dz = float(who[b]["me_z"]) - float(who[a]["me_z"])
        d = math.hypot(dx, dz)
        if d > worst:
            worst = d
            worst_f = b
    return worst, worst_f


def ready_frame(talk, after):
    f = next((k for k in sorted(talk) if k >= after and talk[k].get("ready") == "true" and talk[k].get("opts")), None)
    assert f is not None, f"talk never became ready after frame {after}"
    return f


def main():
    scratch = Path.home() / "dev/tmp/aegean-skies/show-the-way-test"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as work:
        # ---- 1. Sofia on the dock: book hotel room -> NO warp, walk to hotel door, enter room
        _, talk0, _, _ = run(work, "sofia-peek", 140, "1:mouse=5x5 " + key(75, "space"), AEGEAN_TALK="sofia-dock")
        assert talk0, "sofia-dock did not open talk"
        rf0 = ready_frame(talk0, 78)
        stay_idx, _ = find_opt(talk0[rf0 + 2], "Where_can_I_stay")
        ask_seq, after_ask = pick_option(rf0 + 4, stay_idx)
        ask_script = " ".join(["1:mouse=5x5", key(75, "space"), ask_seq, key(after_ask + 45, "space")])
        _, talk1, _, _ = run(work, "sofia-peek2", after_ask + 110, ask_script, AEGEAN_TALK="sofia-dock")
        rf1 = ready_frame(talk1, after_ask + 48)
        take_idx, _ = find_opt(talk1[rf1 + 2], "take_a_room")
        take_seq, accept_f = pick_option(rf1 + 4, take_idx)
        # Close talk after Sofia confirms and points out Hotel Ancora, then walk forward along the
        # waterfront to the hotel door and press Space/F to enter the room.
        walk_start = accept_f + 45
        script = " ".join([
            ask_script,
            take_seq,
            key(accept_f + 35, "escape"),
            f"{walk_start}:w+ {walk_start + 500}:w-",
            f"{walk_start}:shift+ {walk_start + 300}:shift-",
        ])
        probe, talk, who, way = run(work, "sofia-dock", walk_start + 520, script, AEGEAN_TALK="sofia-dock")
        assert any(way[f]["hotel_paid"] == "true" for f in way if f >= accept_f + 5), (
            f"Sofia did not book hotel room (line={talk.get(accept_f + 20, {}).get('line')})"
        )
        # No warp on accepting the room!
        jump, jf = max_frame_jump(who, accept_f, accept_f + 60)
        assert jump < 0.6, f"pilot warped on Sofia hotel room reply: {jump:.2f}m at frame {jf}"
        assert all(probe[f]["ui"] != "leisure" for f in range(accept_f, accept_f + 45)), (
            "accepting Sofia's hotel offer immediately warped into leisure room"
        )
        modes = [way[f]["mode"] for f in sorted(way) if accept_f + 5 <= f <= accept_f + 35]
        assert any(m in ("guide", "point") for m in modes), f"expected Sofia to guide or point to hotel: {set(modes)}"
        # Wait until pilot looks at "Your room" while walking toward Hotel Ancora, then press Space!
        hover_f = next((f for f in sorted(way) if f >= walk_start and way[f]["hover"] == "Your_room"), None)
        assert hover_f is not None, f"pilot walking from dock never saw Your_room door (last hover={way.get(max(way))})"
        enter_script = " ".join([
            ask_script,
            take_seq,
            key(accept_f + 35, "escape"),
            f"{walk_start}:w+ {hover_f - 2}:w-",
            f"{walk_start}:shift+ {hover_f - 2}:shift-",
            key(hover_f + 2, "space"),
        ])
        probe2, _, who2, _ = run(work, "sofia-enter", hover_f + 360, enter_script, AEGEAN_TALK="sofia-dock")
        jump2, jf2 = max_frame_jump(who2, accept_f, max(who2))
        assert jump2 < 0.6, f"pilot warped while walking to hotel: {jump2:.2f}m at frame {jf2}"
        entered_f = next((f for f in sorted(probe2) if f > hover_f and probe2[f]["ui"] == "leisure" and probe2[f]["leisure"] == "15"), None)
        assert entered_f is not None, f"pressing Space on Your_room door at frame {hover_f + 2} did not enter room (final={probe2.get(max(probe2))})"
        walked = math.hypot(
            float(who2[entered_f - 1]["me_x"]) - float(who2[accept_f]["me_x"]),
            float(who2[entered_f - 1]["me_z"]) - float(who2[accept_f]["me_z"]),
        )
        assert walked > 10.0, f"pilot did not walk from dock to hotel door (moved {walked:.2f}m)"
        print(f"sofia on dock: booked without warp (max jump {jump2:.3f}m), walked {walked:.1f}m to hotel door, Space entered room at frame {entered_f}")

        # ---- 2. Family spare room: accept -> NO warp, host guides pilot to their door, enter at door
        _, talk0, _, _ = run(work, "spare-peek", 140, "1:mouse=5x5 " + key(75, "space"), AEGEAN_TALK="spare-guide")
        assert talk0, "spare-guide did not open talk"
        rf0 = ready_frame(talk0, 78)
        stay_idx, _ = find_opt(talk0[rf0 + 2], "Where_can_I_stay")
        ask_seq, after_ask = pick_option(rf0 + 4, stay_idx)
        ask_script = " ".join(["1:mouse=5x5", key(75, "space"), ask_seq, key(after_ask + 45, "space")])
        _, talk1, _, _ = run(work, "spare-peek2", after_ask + 110, ask_script, AEGEAN_TALK="spare-guide")
        rf1 = ready_frame(talk1, after_ask + 48)
        acc_idx, _ = find_opt(talk1[rf1 + 2], "glad")
        acc_seq, accept_f = pick_option(rf1 + 4, acc_idx)
        script = " ".join([ask_script, acc_seq])
        probe, talk, who, way = run(work, "spare-guide", 2600, script, AEGEAN_TALK="spare-guide")
        assert any(way[f]["fam_host"] != "-1" for f in way if f >= accept_f + 5), (
            f"spare room invitation was not recorded (line={talk.get(accept_f + 20, {}).get('line')})"
        )
        jump, jf = max_frame_jump(who, accept_f, max(who))
        assert jump < 0.6, f"pilot warped on spare room reply: {jump:.2f}m at frame {jf}"
        assert all(probe[f]["ui"] != "leisure" for f in range(accept_f, min(accept_f + 60, max(probe)))), (
            "accepting spare room immediately warped into family stay"
        )
        assert any(way[f]["guiding"] == "true" and way[f]["walk_along"] == "true" for f in way if f >= accept_f + 5), (
            "host did not start walking pilot to spare room"
        )
        arrived_f = next((f for f in sorted(way) if f > accept_f + 40 and way[f]["guiding"] == "false" and way[f]["mark"].startswith("home:")), None)
        assert arrived_f is not None, f"host never arrived at their door (final={way.get(max(way))})"
        walked = math.hypot(
            float(who[arrived_f]["me_x"]) - float(who[accept_f]["me_x"]),
            float(who[arrived_f]["me_z"]) - float(who[accept_f]["me_z"]),
        )
        assert walked > 5.0, f"pilot did not walk with host to spare room (moved {walked:.2f}m)"
        enter_script = " ".join([
            script,
            key(arrived_f + 20, "escape"),
            key(arrived_f + 40, "f"),
        ])
        probe2, _, _, _ = run(work, "spare-enter", arrived_f + 90, enter_script, AEGEAN_TALK="spare-guide")
        entered_f = next((f for f in sorted(probe2) if f > arrived_f + 35 and probe2[f]["ui"] == "leisure" and probe2[f]["leisure"] == "15"), None)
        assert entered_f is not None, f"using family door did not enter spare room (final={probe2.get(max(probe2))})"
        print(f"spare room guide: no warp (max jump {jump:.3f}m), host walked pilot {walked:.1f}m to door, entered stay at frame {entered_f}")

        # ---- 3. Pointing out the cafe with arm gesture + diegetic soft highlight
        _, talk0, _, _ = run(work, "cafe-peek", 140, "1:mouse=5x5 " + key(75, "space"), AEGEAN_TALK="cafe-point")
        assert talk0, "cafe-point did not open talk"
        rf0 = ready_frame(talk0, 78)
        way_idx, _ = find_opt(talk0[rf0 + 2], "Where_is...")
        open_way, after_open = pick_option(rf0 + 4, way_idx)
        _, talk1, _, _ = run(work, "cafe-peek2", after_open + 40, "1:mouse=5x5 " + key(75, "space") + " " + open_way, AEGEAN_TALK="cafe-point")
        rf1 = ready_frame(talk1, after_open + 4)
        cafe_idx, _ = find_opt(talk1[rf1 + 2], "Where_is_the_cafe")
        pick_cafe, after_cafe = pick_option(rf1 + 4, cafe_idx)
        script = " ".join(["1:mouse=5x5", key(75, "space"), open_way, pick_cafe])
        _, talk, _, way = run(work, "cafe-point", after_cafe + 120, script, AEGEAN_TALK="cafe-point")
        assert any(way[f]["mode"] == "point" for f in way if f >= after_cafe + 5), f"expected point mode for cafe: {way.get(after_cafe + 30)}"
        peak_pt = max(float(way[f]["pointing"]) for f in way if f >= after_cafe + 5)
        assert peak_pt > 0.7, f"speaker did not raise pointing arm (peak={peak_pt})"
        assert any(way[f]["mark"] == "cafe" for f in way if f >= after_cafe + 5), "cafe diegetic highlight not active"
        line = talk[after_cafe + 30]["line"].replace("_", " ")
        assert "quay" not in line.lower() and line != "", f"bad cafe directions: {line}"
        print(f"cafe point: mode=point, peak pointing={peak_pt:.2f}, mark=cafe, line={line!r}")

        # ---- 4. Far / out-of-sight landmark: verbal directions only (no arm point, no highlight)
        _, talk0, _, _ = run(work, "far-peek", 140, "1:mouse=5x5 " + key(75, "space"), AEGEAN_TALK="far-place")
        assert talk0, "far-place did not open talk"
        rf0 = ready_frame(talk0, 78)
        way_idx, _ = find_opt(talk0[rf0 + 2], "Where_is...")
        open_way, after_open = pick_option(rf0 + 4, way_idx)
        _, talk1, _, _ = run(work, "far-peek2", after_open + 40, "1:mouse=5x5 " + key(75, "space") + " " + open_way, AEGEAN_TALK="far-place")
        rf1 = ready_frame(talk1, after_open + 4)
        far_candidates = ["Where_is_the_fuel", "Where_is_the_Hotel", "Where_is_the_church", "Where_is_the_market"]
        got_words = False
        for cand in far_candidates:
            try:
                f_idx, _ = find_opt(talk1[rf1 + 2], cand)
            except AssertionError:
                continue
            pick_far, after_far = pick_option(rf1 + 4, f_idx)
            script = " ".join(["1:mouse=5x5", key(75, "space"), open_way, pick_far])
            _, talk, _, way = run(work, f"far-{cand}", after_far + 90, script, AEGEAN_TALK="far-place")
            if way[after_far + 20]["mode"] == "words":
                peak_pt = max(float(way[f]["pointing"]) for f in way if f >= after_far + 5)
                assert peak_pt < 0.05, f"speaker pointed at out-of-sight landmark ({cand}): peak={peak_pt}"
                assert all(way[f]["mark"] == "none" for f in way if f >= after_far + 5), f"diegetic mark shown for out-of-sight landmark ({cand})"
                line = talk[after_far + 20]["line"].replace("_", " ")
                assert line != "" and "quay" not in line.lower(), f"bad far directions: {line}"
                print(f"far place ({cand}): mode=words, no point/mark, line={line!r}")
                got_words = True
                break
        assert got_words, "none of the far landmark candidates were out of sight from far-place"
    print("ok")


if __name__ == "__main__":
    main()
