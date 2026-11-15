# Continuous integration

Two workflows run on GitHub Actions (`.github/workflows/`):

| Workflow | Runs on | Does |
| --- | --- | --- |
| `pages.yml` | push to `main`, manual | guard, geography/terrain/sea/flight checks, builds and deploys the web page |
| `tests.yml` | push to any `t3/**` branch, manual | guard, then the whole test suite in 6 parallel jobs; never on `main` |

Both pin Sloppy with `SLOPPY_VERSION` at the top of the file: change the two together.

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

A new push to the same branch cancels the run before it.

## The guard

`tools/check_tracked_files.py` fails if a file in the tree, or in any commit that is about to be
public, is under a scratch/reference/voice/recording folder; is an audio or video file (by name or
by its header, so a renamed `.wav` is caught); is a soundfont or carries a FluidR3 name; is a binary
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
