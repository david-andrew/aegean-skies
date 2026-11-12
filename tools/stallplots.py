"""Plot stalllab CSV with matplotlib (no display): python3 tools/stallplots.py traces.csv outdir."""
import csv
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

NAMES = "Gull Heron Corsair Falco Tern Petrel Osprey Swift Pelican Kite Ibis Kestrel Minnow Albatross Cormorant Kingfisher".split()
CASES = ["Power-off break", "Sideslip + held rudder", "Power + rudder + aileron", "Hammerhead", "Tail slide", "Damaged left wing + rudder"]


def main():
    source, output = Path(sys.argv[1]), Path(sys.argv[2])
    output.mkdir(parents=True, exist_ok=True)
    rows = {}
    with source.open() as stream:
        for raw in csv.DictReader(stream):
            row = {key: float(value) for key, value in raw.items()}
            rows.setdefault((int(row["kind"]), int(row["scenario"])), []).append(row)
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    metrics = []
    for kind, name in enumerate(NAMES):
        for group in range(2):
            fig, axes = plt.subplots(4, 3, figsize=(14, 10), sharex="col", layout="constrained")
            for col in range(3):
                case = group * 3 + col
                data = rows[kind, case]
                time = np.array([r["t"] for r in data])
                for line, (key, label) in enumerate((("pitch", "Pitch (degrees)"), ("roll", "Roll (degrees, unwrapped)"), ("yaw", "Heading (degrees, unwrapped)"), ("alt", "Altitude (world metres)"))):
                    values = np.array([r[key] for r in data])
                    if key != "alt":
                        if key != "pitch":
                            values = np.unwrap(values)
                        values = np.rad2deg(values)
                    axis = axes[line, col]
                    axis.plot(time, values, color="#176782", lw=1.5)
                    axis.axvline(3 if case in (3, 4) else 8, color="#bc5933", ls="--", lw=1, label="Recovery begins")
                    axis.grid(alpha=0.2)
                    if col == 0:
                        axis.set_ylabel(label)
                    if line == 0:
                        axis.set_title(CASES[case])
                    if line == 3:
                        axis.set_xlabel("Simulation time (s)")
                axes[0, col].legend(loc="best", fontsize=8)
                before = [r for r in data if r["t"] < 8]
                metrics.append({"aircraft": name, "case": CASES[case],
                                "max_wing_split_before_8s": max(abs(r["left"] - r["right"]) for r in before),
                                "min_altitude": min(r["alt"] for r in data),
                                "final_separation": (data[-1]["left"] + data[-1]["right"]) / 2,
                                "final_bank_deg": math.degrees(data[-1]["roll"]),
                                "final_speed_true": data[-1]["speed"]})
            fig.suptitle(f"{name} — chaotic stalls trial, 3.3× drawn speed / true-speed aerodynamics\n"
                         "Euler angles become ambiguous at vertical pitch; raw quaternion and body rates are in traces.csv", fontsize=13)
            fig.savefig(output / f"traces-{name.lower()}{'-reversals' if group else ''}.png", dpi=140)
            plt.close(fig)
    with (output / "trace-metrics.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(metrics[0]))
        writer.writeheader()
        writer.writerows(metrics)


if __name__ == "__main__":
    main()
