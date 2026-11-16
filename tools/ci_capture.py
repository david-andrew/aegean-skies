#!/usr/bin/env python3
"""Run a batch of headless screenshot captures on GitHub Actions and fetch the results.

  python3 tools/ci_capture.py specs.json [--branch t3/x] [--name label] [--out DIR] [--shards 4]
                              [--workflow-ref main] [--dry-run] [--no-wait | --run-id N]

specs.json is a list of {"name", "env": {...}, "frames", "size"} (see tools/ci_capture_job.py for
every field: program, video, timeout). Push your branch first (git push -u origin t3/<name>, with the
sandbox off): the workflow builds what is on GitHub, not your working tree. The tool dispatches
captures.yml with `gh workflow run`, waits with `gh run watch`, downloads the artifact into
--out (default ~/dev/tmp/aegean-skies/ci-captures/<name>/) and prints every file's path. Exit status
is 1 if any capture failed (their logs are downloaded too). Never pushes, never uploads references:
the specs' env values may not name paths (use {out}), and the workflow only ships PNG, MP4, log and
JSON files written by the captures themselves.
"""
import argparse
import importlib.util
import json
import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKFLOW = "captures.yml"
# the GitHub API allows 5,000 calls an hour for every agent and tool on the account together:
# never poll faster than this (gh run watch defaults to 3 s and used the whole hour up once)
WATCH_SECONDS = 90
BASE_OUT = Path.home() / "dev/tmp/aegean-skies/ci-captures"


def sh(*cmd, check=True, cwd=HERE):
    r = subprocess.run(list(map(str, cmd)), cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        if "rate limit" in r.stderr.lower():
            sys.exit("GitHub API rate limit hit (5,000 calls an hour shared by every agent): wait for the reset, do not retry in a loop.\n" + r.stderr)
        sys.exit("%s failed (%d):\n%s%s" % (" ".join(map(str, cmd[:4])), r.returncode, r.stdout, r.stderr))
    return r.stdout.strip()


def validated_specs(path):
    spec = importlib.util.spec_from_file_location("ci_capture_job", HERE / "ci_capture_job.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.load_specs(path)


def parse_time(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def dispatch(a, specs, name, repo, default_branch, branch):
    shards = a.shards or min(len(specs), 8)
    # the branch must be on GitHub, at what is committed here
    remote = sh("git", "ls-remote", "origin", "refs/heads/" + branch)
    if not remote:
        sys.exit("branch %s is not on GitHub: git push -u origin %s (sandbox off), then run again" % (branch, branch))
    remote_sha = remote.split()[0]
    if not a.branch or a.branch == sh("git", "branch", "--show-current"):
        local_sha = sh("git", "rev-parse", "HEAD")
        if local_sha != remote_sha:
            print("WARNING: local HEAD %s is not what GitHub has (%s): push first if you want your latest commits." % (local_sha[:9], remote_sha[:9]))
        if sh("git", "status", "--porcelain", "--untracked-files=no"):
            print("WARNING: uncommitted changes are not in the build; only commit %s is." % remote_sha[:9])
    workflow_ref = a.workflow_ref or default_branch
    if sh("gh", "api", "repos/%s/contents/.github/workflows/%s?ref=%s" % (repo, WORKFLOW, workflow_ref), "-q", ".name", check=False) != WORKFLOW:
        sys.exit("%s is not on %s yet: workflow_dispatch needs it on the default branch. Ask the coordinator to merge the workflow file first." % (WORKFLOW, workflow_ref))

    token = secrets.token_hex(3)
    label = "%s-%s" % (name, token)
    dispatch = ["gh", "workflow", "run", WORKFLOW, "--ref", workflow_ref, "-f", "specs=" + json.dumps(specs, separators=(",", ":")),
                "-f", "name=" + label, "-f", "ref=" + remote_sha, "-f", "shards=%d" % shards]
    print("%d captures from %s (%s), %d shards, label %s" % (len(specs), branch, remote_sha[:9], shards, label))
    if a.dry_run:
        print(" ".join(map(shlex.quote, dispatch)))
        return
    t_dispatch = time.time()
    sh(*dispatch)

    run_id = None
    for _ in range(12):
        time.sleep(15)
        runs = json.loads(sh("gh", "run", "list", "--workflow", WORKFLOW, "--event", "workflow_dispatch", "--limit", "30",
                             "--json", "databaseId,displayTitle,createdAt"))
        for r in runs:
            if token in r["displayTitle"]:
                run_id = r["databaseId"]
        if run_id:
            break
    if not run_id:
        sys.exit("dispatched, but the run did not show up: gh run list --workflow %s (label %s)" % (WORKFLOW, label))
    return run_id


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("specs", help="JSON file: a list of capture specs")
    ap.add_argument("--branch", help="branch to build (default: the current branch; must be pushed)")
    ap.add_argument("--name", help="label for the run and the output folder (default: the spec file's name)")
    ap.add_argument("--out", help="output folder (default ~/dev/tmp/aegean-skies/ci-captures/<name>/)")
    ap.add_argument("--shards", type=int, help="parallel jobs (default: one per capture, at most 8)")
    ap.add_argument("--workflow-ref", help="ref holding captures.yml to dispatch (default: the default branch)")
    ap.add_argument("--overwrite", action="store_true", help="replace an earlier download in --out")
    ap.add_argument("--dry-run", action="store_true", help="validate and print the dispatch, do nothing")
    ap.add_argument("--run-id", type=int, help="do not dispatch: wait for and download this existing run (e.g. one you started with --no-wait)")
    ap.add_argument("--no-wait", action="store_true", help="dispatch and print the run id only")
    a = ap.parse_args()

    specs_path = Path(a.specs).resolve()
    specs = validated_specs(specs_path)
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", a.name or specs_path.stem).strip("-")[:32] or "batch"
    repo = sh("gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner")
    default_branch = sh("gh", "repo", "view", "--json", "defaultBranchRef", "-q", ".defaultBranchRef.name")
    branch = a.branch or sh("git", "branch", "--show-current")
    if not branch:
        sys.exit("detached HEAD: pass --branch")

    run_id = a.run_id
    t_dispatch = time.time()
    if run_id is None:
        run_id = dispatch(a, specs, name, repo, default_branch, branch)
        if run_id is None:   # --dry-run
            return
    print("run %s: https://github.com/%s/actions/runs/%s" % (run_id, repo, run_id), flush=True)
    if a.no_wait:
        return

    subprocess.run(["gh", "run", "watch", str(run_id), "-i", str(WATCH_SECONDS), "--compact"], cwd=HERE)   # exit status read below
    info = json.loads(sh("gh", "run", "view", str(run_id), "--json", "conclusion,status,createdAt,updatedAt,jobs"))
    wall = time.time() - t_dispatch
    print("run %s: %s, %.0f s since dispatch" % (run_id, info.get("conclusion") or info["status"], wall))
    stage = {}
    for j in info["jobs"]:
        if j.get("startedAt") and j.get("completedAt") and not j["completedAt"].startswith("0001"):
            kind = j["name"].split(" ")[0].split("(")[0].strip()
            d = (parse_time(j["completedAt"]) - parse_time(j["startedAt"])).total_seconds()
            stage.setdefault(kind, []).append(d)
    print("job seconds: " + ", ".join("%s %s" % (k, "/".join("%.0f" % d for d in v)) for k, v in stage.items()))

    out = Path(a.out).expanduser() if a.out else BASE_OUT / name
    if out.exists() and any(out.iterdir()):
        if a.overwrite or (out / "manifest.json").exists():
            shutil.rmtree(out)
        else:
            out = Path(str(out) + "-" + str(run_id))
    out.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["gh", "run", "download", str(run_id), "--pattern", "captures-*", "-D", str(out)], cwd=HERE)
    if r.returncode != 0:
        sys.exit("no artifact to download: see https://github.com/%s/actions/runs/%s (a failed plan or build job)" % (repo, run_id))
    # one matched artifact lands in out/<artifact name>/ when several match, else in out directly
    inner = [d for d in out.iterdir() if d.is_dir() and d.name.startswith("captures-")]
    if len(inner) == 1 and not (out / "manifest.json").exists():
        for item in inner[0].iterdir():
            shutil.move(str(item), str(out / item.name))
        inner[0].rmdir()
    manifest = out / "manifest.json"
    failed = 0
    if manifest.exists():
        for c in json.loads(manifest.read_text())["captures"]:
            failed += 1 if c["code"] else 0
            print("%s %-36s %6.0f s  exit %d" % ("ok  " if c["code"] == 0 else "FAIL", c["name"], c["wall"], c["code"]))
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.suffix in (".png", ".mp4") and p.parent.name != "frames":
            print(p)
    frames = [d for d in sorted(out.rglob("frames")) if d.is_dir()]
    for d in frames:
        print("%s/  (%d frames)" % (d, sum(1 for _ in d.glob("*.png"))))
    print("logs: " + str(out) + "/<capture>/<capture>.log")
    sys.exit(1 if failed or not manifest.exists() else 0)


if __name__ == "__main__":
    main()
