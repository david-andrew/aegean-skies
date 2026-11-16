#!/usr/bin/env python3
"""tools/ci_capture_job.py: spec validation and the dealing of captures to shards."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import ci_capture_job as job


def specs(items):
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(items, f)
    f.close()
    return f.name


def refused(items):
    try:
        job.load_specs(specs(items))
    except SystemExit:
        return True
    return False


def main():
    ok = job.load_specs(specs([{"name": "a"}, {"name": "b", "env": {"AEGEAN_CAPTURE": "home", "AEGEAN_X": "{out}/frames"}, "frames": 10, "size": "640x360"}]))
    assert ok[0]["frames"] == 90 and ok[0]["size"] == "1280x720" and ok[0]["program"] == "aegean.jo"
    assert ok[1]["frames"] == 10
    # nothing that points at the agents' scratch, references or the home folder goes in
    for bad in ({"AEGEAN_P": "/var/home/david/dev/tmp/x"}, {"AEGEAN_P": "~/refs"}, {"AEGEAN_P": "../x"}, {"AEGEAN_P": "a=/etc/passwd"},
                {"AEGEAN_P": "dev/tmp/aegean-skies"}, {"DISPLAY": ":0"}, {"SLOPPY_SOFTWARE": "0"}, {"bad name": "1"}):
        assert refused([{"name": "a", "env": bad}]), bad
    assert refused([{"name": "../x"}]) and refused([{"name": "a"}, {"name": "a"}]) and refused([])
    assert refused([{"name": "a", "frames": 0}]) and refused([{"name": "a", "size": "9999x9999"}]) and refused([{"name": "a", "program": "/etc/x.jo"}])
    # a shard deal keeps every capture exactly once and balances by cost
    many = job.load_specs(specs([{"name": "c%d" % i, "frames": 30 + 40 * i} for i in range(10)]))
    shards = job.deal(many, 3)
    assert sorted(s["name"] for sh in shards for s in sh) == sorted(s["name"] for s in many)
    loads = [sum(job.cost(s) for s in sh) for sh in shards]
    assert max(loads) < 1.2 * min(loads), loads
    # the high tier costs more than the low one for the same frames and size
    lo, hi = job.load_specs(specs([{"name": "l", "env": {"AEGEAN_QUALITY": "low"}}, {"name": "h", "env": {"AEGEAN_QUALITY": "high"}}]))
    assert job.cost(hi) > job.cost(lo)
    print("ok")


if __name__ == "__main__":
    main()
