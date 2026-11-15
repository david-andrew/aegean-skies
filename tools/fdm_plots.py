"""Plot tools/fdm_compare.jo traces: the liked model against flight model v2, per manoeuvre.
python3 tools/fdm_plots.py out.txt outdir   (matplotlib, no display)
Each figure: the side view (ground distance against height), true airspeed against time, and the
nose's pitch (solid) against the flight path's angle (dashed): where they part, the aircraft is
pointing one way and going another.
"""
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLORS = {"0": "#eb6834", "1": "#2a78d6", "2": "#1baf7a", "3": "#6250d6"}   # liked, v2, Sky Barons, v2 SB-like
NAMES = {"0": "liked model", "1": "flight model v2", "2": "Sky Barons", "3": "v2 Sky Barons-like"}
CRAFTS = "Gull Heron Corsair Falco Tern Petrel Osprey Swift Pelican Kite Ibis Kestrel Minnow Albatross Cormorant Kingfisher".split()
INK = "#3a3a38"
MUTED = "#8a8980"
CASES = {
    "stall_idle": "Zoom to 50° at idle until it breaks, then hands off and power on",
    "stall_zoom": "Zoom to 50° at 70% power until it breaks, then hands off and full power",
    "loop": "A loop from cruise: full throttle, full stick",
    "dive_zoom": "45° dive for 150 m, then up to 80° until the apex",
    "stall_level": "Level at idle, holding height; stick fully back once slow",
    "stall_rudder": "Stick back and full rudder at idle for 6 s, then recover",
    "takeoff": "From rest on calm water: full throttle, a gentle climb once off",
    "landing": "An approach at 1.3 × stall on 3.5°, flared from 5 m",
    "sustained": "Level turns (all banks swept)",
}


def load(path):
    traces = defaultdict(lambda: defaultdict(list))
    for line in open(path):
        if not line.startswith("T,") or line.startswith("T,case"):
            continue
        f = line.strip().split(",")
        case, model, kind = f[1], f[2], CRAFTS[int(f[3])]
        t, dist, alt, speed, pitch, bank, path = (float(x) for x in f[4:11])
        rows = traces[(case, kind)][model]
        # (a manoeuvre run several times, as the sustained sweep, restarts its clock: keep the last)
        if rows and t < rows[-1][0]:
            rows.clear()
        rows.append((t, dist, alt, speed, pitch * 57.2958, path * 57.2958))
    return traces


def style(ax, xlabel, ylabel):
    ax.set_xlabel(xlabel, color=MUTED)
    ax.set_ylabel(ylabel, color=MUTED)
    ax.tick_params(colors=MUTED)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#d6d5ce")
    ax.grid(color="#ecebe5", linewidth=0.8)


def plot(case, kind, models, out):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))
    fig.suptitle(f"{kind}: {CASES.get(case, case)}", color=INK, x=0.01, ha="left", fontsize=13)
    for model in ("0", "1", "2", "3"):
        rows = models.get(model)
        if not rows:
            continue
        c = COLORS[model]
        t = [r[0] for r in rows]
        axes[0].plot([r[1] for r in rows], [r[2] for r in rows], color=c, lw=2, label=NAMES[model])
        axes[1].plot(t, [r[3] for r in rows], color=c, lw=2, label=NAMES[model])
        axes[2].plot(t, [r[4] for r in rows], color=c, lw=2, label=f"{NAMES[model]}: nose")
        axes[2].plot(t, [r[5] for r in rows], color=c, lw=1.6, ls="--", label=f"{NAMES[model]}: path")
    style(axes[0], "ground distance (m, true)", "height (m, true)")
    style(axes[1], "time (s)", "true airspeed (m/s)")
    style(axes[2], "time (s)", "angle above the horizon (°)")
    axes[0].set_aspect("equal", adjustable="datalim")
    axes[0].legend(frameon=False, labelcolor=INK)
    axes[2].legend(frameon=False, labelcolor=INK, fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)


def main():
    source, outdir = Path(sys.argv[1]), Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    for (case, kind), models in load(source).items():
        if case.startswith("pull_") or case.startswith("roll_") or case in ("top", "climb", "skim", "trip"):
            continue
        plot(case, kind, models, outdir / f"{case}_{kind}.png")


if __name__ == "__main__":
    main()
