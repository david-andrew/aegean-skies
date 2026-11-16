#!/usr/bin/env python3
"""The CI side of captures.yml: validate the specs, plan the shards, run one shard's captures.

  python3 tools/ci_capture_job.py plan --specs specs.json --shards 4      # prints GITHUB_OUTPUT lines
  python3 tools/ci_capture_job.py run  --specs specs.json --shard 0 --shards 4 --out captures [--workers 1]
  python3 tools/ci_capture_job.py index --out captures                    # merged summary + manifest

A spec is {"name": str, "env": {...}, "frames": int, "size": "1280x720", "program": "aegean.jo",
"video": {"fps": 30, "dir": "frames", "keep_frames": false}, "timeout": 2400}. Only name is
required. A capture runs the program headless (SLOPPY_SOFTWARE=1, no audio, no display) with
SLOPPY_WINDOW=size, SLOPPY_FRAMES=frames and SLOPPY_SCREENSHOT={out}/<name>.png unless env sets
that itself. In env values {out} is the capture's own output folder (created, as is {out}/frames):
AEGEAN_SEAT_FRAMES={out}/frames makes the game write its frame sequence there. With "video" the
PNGs in {out}/<dir> are encoded to {out}/<name>.mp4 (ffmpeg, H.264, no audio) and, unless
keep_frames, deleted. Everything under {out} that is not a png, mp4, log or json is removed
before upload, and the plan refuses env values that point outside {out}.
"""
import argparse
import concurrent.futures as cf
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
# env values may not name places outside the run: nothing from the agents' scratch or references
BAD_VALUE = re.compile(r"(^|[\s=:,;])(/|~|\.\.)|\.\./|dev/tmp|/refs|refs/|/home/|\\|\$\(|`")
UPLOAD_SUFFIXES = {".png", ".mp4", ".log", ".json"}
# set for every capture, so a spec cannot open a window or play sound
FORCED = {"SLOPPY_SOFTWARE": "1", "SLOPPY_NO_AUDIO": "1"}
DEFAULTS = {"SLOPPY_SOFT_SCALE": "1"}   # the render scale, 0.1..1: 1 is full resolution (the software renderer defaults to 0.5, about 4x less work)


def load_specs(path):
    specs = json.loads(Path(path).read_text())
    if isinstance(specs, dict):
        specs = specs.get("captures", [specs])
    if not isinstance(specs, list) or not specs:
        raise SystemExit("specs: a non-empty JSON list of {name, env, frames, size} is needed")
    names = set()
    for i, s in enumerate(specs):
        if not isinstance(s, dict):
            raise SystemExit("spec %d: not an object" % i)
        n = s.get("name")
        if not isinstance(n, str) or not NAME_RE.match(n):
            raise SystemExit("spec %d: name must match %s, got %r" % (i, NAME_RE.pattern, n))
        if n in names:
            raise SystemExit("spec %d: duplicate name %r" % (i, n))
        names.add(n)
        s["frames"] = int(s.get("frames", 90))
        if not 1 <= s["frames"] <= 20000:
            raise SystemExit("%s: frames must be 1..20000" % n)
        s["size"] = str(s.get("size", "1280x720"))
        m = re.match(r"^(\d{2,4})x(\d{2,4})$", s["size"])
        if not m or int(m[1]) > 3840 or int(m[2]) > 2160:
            raise SystemExit("%s: size must be WxH up to 3840x2160" % n)
        prog = s.setdefault("program", "aegean.jo")
        if not re.match(r"^[A-Za-z0-9_./-]+\.jo$", prog) or ".." in prog or prog.startswith("/"):
            raise SystemExit("%s: program must be a repo .jo path" % n)
        env = s.setdefault("env", {})
        if not isinstance(env, dict):
            raise SystemExit("%s: env must be an object" % n)
        for k, v in env.items():
            if not KEY_RE.match(k):
                raise SystemExit("%s: bad env name %r" % (n, k))
            if k in ("DISPLAY", "WAYLAND_DISPLAY", "PATH", "HOME", "LD_PRELOAD", "LD_LIBRARY_PATH") or k in FORCED:
                raise SystemExit("%s: env %s may not be set" % (n, k))
            env[k] = v = str(v)
            if BAD_VALUE.search(v.replace("{out}", "OUT")):
                raise SystemExit("%s: env %s=%r points outside the capture folder (use {out})" % (n, k, v))
        v = s.get("video")
        if v is not None:
            if not isinstance(v, dict):
                raise SystemExit("%s: video must be an object {fps, dir, keep_frames}" % n)
            v.setdefault("fps", 30)
            v.setdefault("dir", "frames")
            v.setdefault("keep_frames", False)
            if not 1 <= int(v["fps"]) <= 120 or not re.match(r"^[A-Za-z0-9_-]+$", str(v["dir"])):
                raise SystemExit("%s: video needs fps 1..120 and a plain dir name" % n)
        s["timeout"] = int(s.get("timeout", 2400))
    return specs


TIER_COST = {"low": 1.0, "medium": 1.5, "high": 3.0}   # measured: high is mostly per-frame CPU work, not pixels


def cost(s):
    """Rough seconds-ish: frames x quality tier x (a fixed part + a part that scales with the pixels drawn)."""
    w, h = s["size"].split("x")
    scale = float(s["env"].get("SLOPPY_SOFT_SCALE", DEFAULTS["SLOPPY_SOFT_SCALE"]) or 1)
    pixels = scale * scale * int(w) * int(h) / 921600.0
    return s["frames"] * TIER_COST.get(s["env"].get("AEGEAN_QUALITY", "medium"), 1.5) * (0.3 + 0.7 * pixels)


def deal(specs, n):
    """Longest first onto the least loaded shard (see cost)."""
    shards = [[] for _ in range(n)]
    load = [0] * n
    for s in sorted(specs, key=lambda s: (-cost(s), s["name"])):
        k = min(range(n), key=lambda i: (load[i], i))
        shards[k].append(s)
        load[k] += cost(s)
    return shards


def emit(key, value):
    line = "%s=%s" % (key, value)
    print(line)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(line + "\n")


def cmd_plan(a):
    specs = load_specs(a.specs)
    n = max(1, min(int(a.shards), len(specs), 16))
    programs = sorted({s["program"] for s in specs})
    emit("matrix", json.dumps({"shard": list(range(n))}))
    emit("shards", n)
    emit("programs", " ".join(programs))
    emit("count", len(specs))


def encode(s, out, log):
    v = s["video"]
    frames = out / v["dir"]
    pngs = sorted(frames.glob("*.png"))
    if not pngs:
        log.write("\nVIDEO: no PNG frames in %s, nothing to encode\n" % frames)
        return False
    mp4 = out / (s["name"] + ".mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(int(v["fps"])), "-pattern_type", "glob",
           "-i", str(frames / "*.png"), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-an", str(mp4)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    log.write("\nVIDEO: %d frames at %d fps -> %s (ffmpeg exit %d)\n%s\n" % (len(pngs), int(v["fps"]), mp4.name, r.returncode, r.stderr[-2000:]))
    if r.returncode == 0 and not v["keep_frames"]:
        shutil.rmtree(frames, ignore_errors=True)
    return r.returncode == 0


def run_capture(s, root, outdir, scratch, threads):
    name = s["name"]
    out = outdir / name
    out.mkdir(parents=True, exist_ok=True)
    (out / "frames").mkdir(exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")}
    env.update(DEFAULTS)
    if threads:
        env["SLOPPY_THREADS"] = str(threads)
    env.update(SLOPPY_WINDOW=s["size"], SLOPPY_FRAMES=str(s["frames"]),
               SLOPPY_SCREENSHOT=str(out / (name + ".png")), SLOPPY_SAVE_DIR=str(scratch / name))
    for k, v in s["env"].items():
        v = v.replace("{out}", str(out))
        env[k] = v
        if "{out}" in s["env"][k] and not Path(v).suffix:
            Path(v).mkdir(parents=True, exist_ok=True)
    env.update(FORCED)
    (scratch / name).mkdir(parents=True, exist_ok=True)
    binary = root / "build" / Path(s["program"]).stem
    t0 = time.time()
    code = 0
    with open(out / (name + ".log"), "w") as log:
        log.write("CAPTURE %s program=%s frames=%d size=%s\nENV %s\n\n" % (
            name, s["program"], s["frames"], s["size"], json.dumps({k: v for k, v in s["env"].items()}, sort_keys=True)))
        log.flush()
        try:
            r = subprocess.run([str(binary)], cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=s["timeout"])
            code = r.returncode
        except subprocess.TimeoutExpired:
            code = 124
            log.write("\nTIMEOUT after %d s\n" % s["timeout"])
        game = time.time() - t0
        shot = out / (name + ".png")
        if code == 0 and not shot.exists():
            # the run ended without the screenshot (a spec that sets its own SLOPPY_SCREENSHOT path is fine)
            if not any(out.rglob("*.png")):
                code = 3
                log.write("\nNo PNG was written\n")
        video = None
        if s.get("video") and code == 0:
            t1 = time.time()
            video = encode(s, out, log)
            log.write("encode seconds %.1f\n" % (time.time() - t1))
    wall = time.time() - t0
    shutil.rmtree(scratch / name, ignore_errors=True)
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.suffix not in UPLOAD_SUFFIXES:
            p.unlink()
    for d in sorted((p for p in out.rglob("*") if p.is_dir()), reverse=True):
        try:
            d.rmdir()
        except OSError:
            pass
    pngs = sum(1 for _ in out.rglob("*.png"))
    print("%s %-40s %7.1f s (game %.1f s) %d png" % ("ok  " if code == 0 else "FAIL", name, wall, game, pngs), flush=True)
    return {"name": name, "code": code, "wall": round(wall, 1), "game": round(game, 1), "frames": s["frames"],
            "size": s["size"], "pngs": pngs, "mp4": video, "env": s["env"]}


def cmd_run(a):
    specs = load_specs(a.specs)
    n = max(1, min(int(a.shards), len(specs), 16))
    mine = deal(specs, n)[a.shard] if a.shard < n else []
    root = Path.cwd()
    outdir = Path(a.out).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="aegean-capture-saves-"))
    t0 = time.time()
    # One capture at a time on all the cores: two at once on two cores each measured no faster in
    # total (more shards are the way to run more at once)
    workers = max(1, min(a.workers, len(mine)))
    threads = max(1, (os.cpu_count() or 4) // workers) if workers > 1 else 0
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(lambda s: run_capture(s, root, outdir, scratch, threads), mine))
    wall = time.time() - t0
    (outdir / ("shard-%d.json" % a.shard)).write_text(json.dumps({"shard": a.shard, "wall": round(wall, 1), "captures": results}, indent=1))
    failed = [r for r in results if r["code"] != 0]
    lines = ["### Shard %d of %d: %d captures, %d failed, %.0f s" % (a.shard + 1, n, len(results), len(failed), wall), "",
             "| capture | frames | size | seconds | pngs | exit |", "| --- | ---: | --- | ---: | ---: | ---: |"]
    for r in results:
        lines.append("| %s | %d | %s | %.0f | %d | %d |" % (r["name"], r["frames"], r["size"], r["wall"], r["pngs"], r["code"]))
    for r in failed:
        log = (outdir / r["name"] / (r["name"] + ".log"))
        tail = "\n".join(log.read_text(errors="replace").strip().splitlines()[-60:]) if log.exists() else ""
        lines += ["", "<details open><summary><b>%s</b> (exit %d)</summary>" % (r["name"], r["code"]), "", "```", tail, "```", "</details>"]
    print("\n".join(lines))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write("\n".join(lines) + "\n")
    sys.exit(1 if failed else 0)


def cmd_index(a):
    outdir = Path(a.out)
    shards = [json.loads(p.read_text()) for p in sorted(outdir.glob("shard-*.json"))]
    caps = sorted((c for s in shards for c in s["captures"]), key=lambda c: c["name"])
    manifest = {"captures": caps, "shard_walls": {str(s["shard"]): s["wall"] for s in shards}}
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=1))
    for p in outdir.glob("shard-*.json"):
        p.unlink()
    lines = ["## Captures: %d, %d failed, slowest shard %.0f s" % (
        len(caps), sum(1 for c in caps if c["code"]), max([s["wall"] for s in shards] or [0])), ""]
    lines.append("| capture | frames | size | seconds | exit |")
    lines.append("| --- | ---: | --- | ---: | ---: |")
    for c in caps:
        lines.append("| %s | %d | %s | %.0f | %d |" % (c["name"], c["frames"], c["size"], c["wall"], c["code"]))
    print("\n".join(lines))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--specs", required=True)
    p.add_argument("--shards", default="4")
    p = sub.add_parser("run")
    p.add_argument("--specs", required=True)
    p.add_argument("--shard", type=int, default=0)
    p.add_argument("--shards", default="4")
    p.add_argument("--out", default="captures")
    p.add_argument("--workers", type=int, default=int(os.environ.get("CI_CAPTURE_WORKERS", "1")))
    p = sub.add_parser("index")
    p.add_argument("--out", default="captures")
    a = ap.parse_args()
    {"plan": cmd_plan, "run": cmd_run, "index": cmd_index}[a.cmd](a)


if __name__ == "__main__":
    main()
