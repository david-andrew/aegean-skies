#!/usr/bin/env python3
"""Run one shard of the game's tests (the CI matrix job; also usable locally).

  python3 tools/ci_test_shard.py --shard 0 --shards 6 [--workers 4] [--list]

Every tests/*.jo file is one `sloppy test <file>` run, every tests/*_test.py one python run.
The items are dealt to the shards longest first by the seconds in tools/ci_test_weights.json
(items without a weight count as the median), so the shards come out near equal. Each shard
runs its items `--workers` at a time with SLOPPY_THREADS=1, headless, no audio. Writes
ci-results/shard-<n>.json (seconds per item: refresh the weights from these) and, with
GITHUB_STEP_SUMMARY set, a markdown summary with every failing item's output.
Exit status: 1 if any item failed.
"""
import argparse
import concurrent.futures as cf
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEIGHTS = ROOT / "tools" / "ci_test_weights.json"
# files run with --release (their loops are too slow in a debug build; the same ones pages.yml
# runs with --release)
RELEASE = {"tests/sky_test.jo", "tests/nature_test.jo"}
TIMEOUT = int(os.environ.get("CI_TEST_TIMEOUT", "1500"))


def items():
    found = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "tests").glob("*.jo"))
    found += sorted(str(p.relative_to(ROOT)) for p in (ROOT / "tests").glob("*_test.py"))
    return found


def deal(all_items, n):
    weights = json.loads(WEIGHTS.read_text()) if WEIGHTS.exists() else {}
    known = [weights[i] for i in all_items if i in weights]
    default = statistics.median(known) if known else 10.0
    order = sorted(all_items, key=lambda i: (-weights.get(i, default), i))
    shards = [[] for _ in range(n)]
    load = [0.0] * n
    for item in order:
        k = min(range(n), key=lambda s: (load[s], s))
        shards[k].append(item)
        load[k] += weights.get(item, default)
    return shards, load


def run_item(item, env, savedir):
    if item.endswith(".py"):
        cmd = [sys.executable, item]
    else:
        cmd = ["sloppy", "test", item] + (["--release"] if item in RELEASE else [])
    e = dict(env, SLOPPY_SAVE_DIR=str(savedir / Path(item).stem))
    os.makedirs(e["SLOPPY_SAVE_DIR"], exist_ok=True)
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=ROOT, env=e, capture_output=True, text=True, timeout=TIMEOUT)
        out, code = r.stdout + r.stderr, r.returncode
    except subprocess.TimeoutExpired as ex:
        out = (ex.stdout or b"").decode(errors="replace") if isinstance(ex.stdout, bytes) else (ex.stdout or "")
        out += "\nTIMEOUT after %d s" % TIMEOUT
        code = 124
    dt = time.time() - t0
    print("%s %-45s %6.1f s" % ("ok  " if code == 0 else "FAIL", item, dt), flush=True)
    return {"item": item, "code": code, "seconds": round(dt, 1), "output": out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--workers", type=int, default=int(os.environ.get("CI_TEST_WORKERS", "4")))
    ap.add_argument("--list", action="store_true", help="print the shard's items and the expected seconds")
    a = ap.parse_args()
    all_items = items()
    shards, load = deal(all_items, a.shards)
    mine = shards[a.shard]
    if a.list:
        print("\n".join(mine))
        print("# %d items, about %.0f s of work, %d workers" % (len(mine), load[a.shard], a.workers))
        return
    env = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")}
    env.update(SLOPPY_NO_AUDIO="1", SLOPPY_SOFTWARE="1", SLOPPY_THREADS="1", PYTHONDONTWRITEBYTECODE="1")
    savedir = Path(tempfile.mkdtemp(prefix="aegean-saves-"))
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        results = list(ex.map(lambda i: run_item(i, env, savedir), mine))
    wall = time.time() - t0
    failed = [r for r in results if r["code"] != 0]
    out = ROOT / "ci-results"
    out.mkdir(exist_ok=True)
    (out / ("shard-%d.json" % a.shard)).write_text(json.dumps(
        {"shard": a.shard, "wall": round(wall, 1), "items": {r["item"]: r["seconds"] for r in results}}, indent=1))
    lines = ["### Shard %d of %d: %d files, %d failed, %.0f s" % (a.shard + 1, a.shards, len(results), len(failed), wall), ""]
    slow = sorted(results, key=lambda r: -r["seconds"])[:5]
    lines.append("Slowest: " + ", ".join("%s %.0f s" % (Path(r["item"]).name, r["seconds"]) for r in slow))
    lines.append("")
    for r in failed:
        tail = "\n".join(r["output"].strip().splitlines()[-80:])
        lines += ["<details open><summary><b>%s</b> (exit %d)</summary>" % (r["item"], r["code"]), "", "```", tail, "```", "</details>", ""]
    summary = "\n".join(lines)
    print(summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(summary + "\n")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
