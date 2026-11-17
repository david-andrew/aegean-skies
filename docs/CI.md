# Continuous integration

Two workflows run on GitHub Actions (`.github/workflows/`):

| Workflow | Runs on | Does |
| --- | --- | --- |
| `pages.yml` | push to `main`, manual | guard, geography/terrain/sea/flight checks, builds and deploys the web page |
| `tests.yml` | push to any `t3/**` branch, manual | guard, then the whole test suite in 6 parallel jobs; never on `main` |
| `captures.yml` | manual only (`tools/ci_capture.py`) | builds the game once, runs a list of headless screenshot captures in parallel jobs, uploads the PNGs, logs and optional MP4s |

All three pin Sloppy with `SLOPPY_VERSION` at the top of the file: change them together.

## The test workflow

`tests.yml` bakes the land, clouds and registries (`sloppy --release tools/bake.jo`, which writes
everything the game embeds), then each of 6 jobs runs `tools/ci_test_shard.py --shard N --shards 6`:
every `tests/*.jo` file as its own `sloppy test <file>` run (and every `tests/*_test.py`), 4 at a
time, headless (`SLOPPY_SOFTWARE=1 SLOPPY_NO_AUDIO=1 SLOPPY_THREADS=1`, no display). Files are dealt
to shards by measured seconds in `tools/ci_test_weights.json`; after adding or slowing tests,
refresh it from the `weights` artifact of a finished run (a new file counts as the median).
Each job's summary page lists its failing files with the last 80 lines of their output; the
shard-0 summary lists what is not run in CI:

- `tests/river_depth_render_test.py`: needs a real GPU (software rendering has no hidden-bed pixels);
- `tests/title_reel_detail_test.py` and `tests/title_over_play_test.py`: the software-rendered full
  game takes 16 min and over 25 min; run them with the manual dispatch input `slow: true`.
- `tests/playtest_loops_test.py` and `tests/playtest_town_test.py`: the whole game played through
  a pleasure flight and the town's loops by `tools/playtest_probe.jo` (a minute a case here, some
  five in CI, two at a time, with a 45 min item timeout); also with `slow: true`.
  `tests/playtest_situations_test.py` (a wreck towed in by the call for help, the strait and the
  canal escape) needs a real GPU: run it on the desktop (`python3 tests/playtest_situations_test.py`). One case alone:
  `PLAYTEST_NO_DRAW=1 tools/playtest.sh <case> [AEGEAN_...]` (cases and their staging in the test).

A new push to the same branch cancels the run before it.

## The guard

`tools/check_tracked_files.py` fails if a file in the tree, or in any commit that is about to be
public, is under a scratch/reference/voice/recording folder; is an audio or video file (by name or
by its header, so a renamed `.wav` is caught), except the four edited ambience beds named exactly in
`ALLOWED_AUDIO` (each must be Ogg and under its size; `docs/CREDITS.md`); is a soundfont or carries a FluidR3 name; is a binary
over 5 MB that is not a known baked asset (`KNOWN_LARGE` in the script); or (in commit ranges) adds a
line that copies a path from the scratch and reference areas. It is the first step of `tests.yml`
and `pages.yml`, and runs as git hooks:

    sh tools/install_hooks.sh      # once per clone; sets core.hooksPath = tools/githooks for every worktree

`pre-commit` checks the staged files, `pre-push` checks every commit being pushed (a new branch is
checked from where it leaves the remotes). Run it by hand: `python3 tools/check_tracked_files.py`
(tree), `--staged`, `--range origin/main..HEAD`, `--all-history HEAD`. `.gitignore` also ignores
these file types, so `git add` skips them unless forced.

Branches pushed for testing are public (the repository is). If the guard ever finds something
that was already pushed, tell the coordinator: history has to be rewritten, not just the tip.

## Captures on Actions

The desktop's four test slots are shared by every agent, and a capture batch waited about 30
minutes for a slot on 2026-11-16 (the captures themselves took 17 s each on the GPU). `captures.yml`
runs the same headless captures on GitHub's runners instead, with no slot and as many parallel jobs
as you ask for. It only runs by dispatch, never on a push.

    # 1. a spec file: a JSON list, one object per capture (all fields but name are optional)
    [{"name": "harbour-low",  "env": {"AEGEAN_CAPTURE": "home", "AEGEAN_QUALITY": "low"},  "frames": 300, "size": "1280x720"},
     {"name": "crossing-high","env": {"AEGEAN_FLYING": "8 57.6", "AEGEAN_QUALITY": "high"}, "frames": 600, "size": "1280x720"}]
    # 2. push your branch (sandbox off), then
    python3 tools/ci_capture.py specs.json [--name label] [--shards N] [--out DIR] [--dry-run] [--no-wait]

It dispatches the workflow, waits (`gh run watch`), downloads the artifact to
`~/dev/tmp/aegean-skies/ci-captures/<name>/` and prints every PNG/MP4 path, with
`<capture>/<capture>.png` and `<capture>.log` (the game's stdout) per capture and a `manifest.json` of
exit codes and seconds. Exit status 1 if a capture failed. It builds the commit on GitHub (the tool
warns when your local HEAD is not what is pushed, or the tree is dirty), never pushes, and
`workflow_dispatch` needs `captures.yml` on `main` (the tool says so if it is not). It polls GitHub
every 90 s (the API allows 5,000 calls an hour for the whole account, shared by every agent: never
use `gh run watch` at its 3 s default). `--no-wait` prints the run id and `--run-id N` waits for and
downloads an existing run later.

**Spec fields.** `name` (letters, digits, `._-`), `env` (any `AEGEAN_*`, `COMBAT_*`, `LIFE_*`, `SLOPPY_*`
variables the program reads), `frames` (default 90: the run saves frame N and exits), `size`
(`SLOPPY_WINDOW`, default 1280x720), `program` (default `aegean.jo`; `tools/combatlab.jo` etc. are
built too), `timeout` (seconds, default 2400), `video`. The job sets `SLOPPY_SOFTWARE=1`,
`SLOPPY_NO_AUDIO=1`, no display, `SLOPPY_SOFT_SCALE=1` (full resolution) and a private
`SLOPPY_SAVE_DIR`, and sets `SLOPPY_SCREENSHOT={out}/<name>.png` unless `env` says otherwise. In env
values `{out}` is the capture's folder: `{"AEGEAN_SEAT_FRAMES": "{out}/frames"}` collects a frame
sequence. Pin `AEGEAN_QUALITY` (the `auto` tier depends on frame time, which is not the desktop's).

**Clips.** `"video": {"fps": 30, "dir": "frames", "keep_frames": false}` encodes the PNGs in
`{out}/frames` into `<name>.mp4` (ffmpeg, H.264, no audio; under a second for 120 frames) and, unless
`keep_frames`, drops them. Use `SLOPPY_FIXED_STEP=1` with the game's frame-sequence options
(title clips need it: without it slow frames stretch the shot clock). Example, proven in CI:
`{"name":"clip","env":{"AEGEAN_CAPTURE":"home","AEGEAN_QUALITY":"low","SLOPPY_FIXED_STEP":"1","AEGEAN_CLOUD_FRAMES":"{out}/frames"},"frames":300,"size":"640x360","video":{"fps":30}}`.

**What goes up.** Only PNG, MP4, log and JSON files that the captures wrote under their own folder;
the plan job refuses env values that name paths outside it (absolute, `~`, `..`, scratch or
reference folders), and runs the guard on the branch first. Branches and artifacts of this public
repo are public: spec files and anything else you commit are visible, so keep references,
recordings and scratch out. Artifacts expire after 7 days.

**How it runs.** `plan` (validates the specs, runs the guard) -> `build` (bakes, then `sloppy build
--release` of every program the specs name, once) -> `capture` x N shards (the specs dealt by
estimated cost; one capture at a time on all 4 cores: two at once on two cores each was no faster
overall) -> `collect` (merges the shards into `captures-<name>-<run id>`). Setup is about 30 s. The
tools come from the ref the workflow was dispatched on, the game from the pushed branch.

### Measured (2026-11-16, ubuntu-latest, 4 vCPU; the same 8 captures, 1280x720)

Batch: low/medium/high x home harbour (300 frames), low-altitude flight (600 frames), old quarter
(300), and a 1200-frame crossing, one capture per runner (8 shards).

| render scale | wall, whole batch | slowest capture | fastest | seconds per frame, low / medium / high |
| --- | ---: | --- | --- | --- |
| 1.0 (default, full resolution) | 22.6 min | crossing, 1200 frames: 21 min | home-low: 4.7 min | 0.94 / 1.1-1.4 / 0.9-1.2 |
| 0.5 (`"SLOPPY_SOFT_SCALE": "0.5"`) | 11.0 min | flight-high, 600 frames: 9.5 min | home-low: 1.4 min | 0.28 / 0.37 / 0.8-0.95 |

Run times vary by 20-30% between runs on shared runners. The tiers differ: pixel work dominates the
low tier (scale 0.5 is 3x faster), the high tier is mostly per-frame CPU work (scale barely helps).
Fewer shards than captures cost time linearly (4 shards: 29 min at scale 1.0). The desktop GPU runs
each of these in 17-20 s of one core, so the desktop is far quicker when a slot is free: use Actions
when the queue is long (today 29 minutes) or when a batch has more than about 6 captures.
Frames that are not needed are the best saving: a capture runs from the start, so use the fewest
frames that reach the state you want.

### Differences from the desktop GPU

Compared on the same binary, same env, 1280x720 (desktop: Vulkan, 4 samples per pixel):

| capture | mean abs difference (0-255) at scale 1 | at scale 0.5 | share of pixels off by > 16 |
| --- | ---: | ---: | ---: |
| home-low / medium / high | 1.7 / 1.9 / 2.0 | 3.7 / 4.0 / 4.1 | 2.4 / 3.2 / 3.4 % (scale 1) |
| flight low / high | 4.1 / 5.3 | 5.5 / 6.6 | 8 / 11 % |
| old quarter, high | 26.6 | 29.0 | 36 % |

- **Inland water shows through the land** in software (old quarter: the ground is covered by the
  river/lake bed pattern). The depth prepass that hides it does not work in the software renderer
  (the same reason `river_depth_render_test.py` is not run in CI). Do not judge terrain near rivers,
  lakes or the interior from CI captures; the sea and coast views are fine.
- **Clouds differ** (other placement and size in the flight captures). It is the software
  renderer, not the machine and not the GPU compute path: the desktop run with `SLOPPY_SOFTWARE=1`
  matches the CI image exactly (mean difference 0.00, fly-low at scale 0.5), and `SLOPPY_NO_GPU=1`
  on the GPU renderer changes nothing. Do not judge clouds or sky from CI captures.
- **CI is the software renderer, bit for bit**: the same capture with `SLOPPY_SOFTWARE=1` on the
  desktop gives the same pixels, so a CI result can be reproduced locally without a GPU.
- **Edges and fine marks**: software draws one sample per pixel, so edges are harder; sea glints and
  tree detail differ at the pixel level. Layout, colour and composition of the harbour views match
  (the difference image is edges and glints only). Scale 0.5 is visibly blocky: use it to check
  framing and gross problems, not detail.
- **Limits are not tested**: the software renderer runs the shader functions on the CPU as f32 with
  no uniform, varying or texture-unit limits, so a WebGL2 minimum-limit breach or a precision problem
  of a mobile GPU never shows. Use `tools/check_web_shaders.cjs` and the Chromium proxy for those.
- **Timing is meaningless.** Frame times, `FRAME_STATS` and anything wall-clock stay on `redfox`;
  desktop instruction counts for A/B work.
- Runs of one build are close to repeatable (identical or about 0.005 mean difference on most
  captures), but streaming-dependent scenes can differ by a few levels between runs.

### When to use the desktop

GPU-exact colour or edge work, anything near rivers or lakes, sky and cloud looks, 1-2 quick
captures with a free slot, phone checks (`phone_run`, the test phone), and all timing and
benchmarks (always `redfox`).
