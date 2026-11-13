#!/usr/bin/env python3
"""60 s far-town frame gate. Run on redfox; each case holds bench.lock separately.

Build tools/stutter_trace.jo --release for native and/or --target wasm first.
Example: python3 tools/test_stutter.py --native ./trace --web ./trace.html \
    --chrome /path/to/chromium --out /path/to/new/results
Default: Olythoria, Pheryalara, Kalyrassa, stationary; --mode fly adds movement.
"""
import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import socket
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--native', type=Path)
parser.add_argument('--web', type=Path)
parser.add_argument('--chrome', type=Path)
parser.add_argument('--node', default='node')
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--town', action='append')
parser.add_argument('--mode', choices=['stay', 'fly'], default='stay')
parser.add_argument('--profile', action='store_true', help='CPU attribution; exclude from final gates')
parser.add_argument('--lock', type=Path, default=Path.home() / 'dev/tmp/bench.lock')
args = parser.parse_args()
if not args.native and not args.web:
    parser.error('Supply --native and/or --web')
if args.web and not args.chrome:
    parser.error('--web needs --chrome')
args.out.mkdir(parents=True, exist_ok=True)
results = []
now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
for town in args.town or ['Olythoria', 'Pheryalara', 'Kalyrassa']:
    for backend, artifact in [('native', args.native), ('web', args.web)]:
        if artifact is None:
            continue
        case = args.out / f'{backend}-{town}-{args.mode}'
        case.mkdir()  # Refuse stale saves/results.
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('SLOPPY_', 'AEGEAN_', 'STUTTER_'))
               and k not in ('DISPLAY', 'WAYLAND_DISPLAY')}
        if backend == 'native':
            env.update(SLOPPY_THREADS='1', SLOPPY_NO_AUDIO='1', SLOPPY_SEED='12345',
                       SLOPPY_SAVE_DIR=str(case / 'save'), SLOPPY_SCREENSHOT=str(case / 'end.png'),
                       SLOPPY_FRAMES='100000000', AEGEAN_QUALITY='low', AEGEAN_RUNTIME_TRACE='1',
                       STUTTER_TOWN=town, STUTTER_MODE=args.mode, STUTTER_WARMUP='15', STUTTER_SECONDS='60')
            command = [str(artifact.resolve())]
        else:
            env['STUTTER_PROFILE'] = '1' if args.profile else '0'
            command = [args.node, str(Path(__file__).with_suffix('.mjs')), str(args.chrome.resolve()),
                       str(artifact.resolve()), str(case.resolve()), town, args.mode]
        print('QUEUED', now(), backend, town, flush=True)
        with args.lock.open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            started = now()
            print('START', started, backend, town, flush=True)
            with (case / 'run.log').open('w') as log:
                try:
                    code = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT,
                                          timeout=300, pass_fds=(lock.fileno(),)).returncode
                except subprocess.TimeoutExpired:
                    code = 124
            ended = now()
            print('END', ended, backend, town, code, flush=True)
        log_path = case / ('console.log' if backend == 'web' else 'run.log')
        log = log_path.read_text() if log_path.exists() else ''
        frames = [list(map(float, m)) for m in re.findall(
            r'^STUTTER_FRAME,\d+,([^,\n]+),([^,\n]+),([^,\n]+),([^,\n]+)', log, re.M)]
        intervals = sorted(f[1] for f in frames)
        end = re.search(r'STUTTER_END .*seconds=([\d.]+).*over50=(\d+)', log)
        passed = code == 0 and end is not None and float(end[1]) >= 60 and int(end[2]) == 0 and bool(frames)
        result = dict(host=socket.gethostname(), backend=backend, town=town, mode=args.mode,
                      started=started, ended=ended, exit_code=code, passed=passed, frames=len(frames),
                      max_ms=max(intervals, default=None),
                      p99_ms=intervals[int((len(intervals)-1)*.99)] if intervals else None,
                      over50=sum(t > 50 for t in intervals), profiled=args.profile)
        results.append(result)
        (args.out / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(json.dumps(result), flush=True)
raise SystemExit(0 if all(r['passed'] for r in results) else 1)
