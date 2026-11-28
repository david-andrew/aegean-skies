# Temporal stability and flicker gate

`tests/temporal_stability_test.py` (harness: `tools/temporal_stability_check.jo`, baseline: `tests/baselines/temporal_stability.json`) is the automated headless gate for temporal shimmer, terrain/canopy morphing, skyline outline flicker and foreground aircraft ghosting.

It runs in CI (`.github/workflows/tests.yml` via `tools/ci_test_shard.py`, under `SLOPPY_SOFTWARE=1 SLOPPY_SOFT_SCALE=1` on GPU-less runners) and locally in about 90 seconds.

## Camera scripts

All seven scripts render fixed-step camera sequences at `384x216` through the game's real terrain, canopy, crown, aircraft and screen-space outline shaders:

| Clip | Frames | What it tests |
| --- | ---: | --- |
| `still` | 6 | Frozen camera and clock over wooded hills; any pixel change (`still_max_diff > 0`) is flicker |
| `pan_150` | 24 | Slow 360° pan at 150 m AGL (6 compass sectors × 4 steps of 1.2°) over wooded hills |
| `pan_800` | 24 | Slow 360° pan at 800 m AGL (6 compass sectors × 4 steps of 1.2°) over wooded hills |
| `flight_300` | 16 | Level flight at 300 m AGL with live tile streaming (`world_generate_tiles = 1`) and 3D depth dumps |
| `approach_woods` | 16 | Straight-in wooded-hill approach across 4 handover bands (2600 m, 950 m, 540 m, 175 m) with live tile streaming and 3D depth dumps |
| `chase_dusk` | 8 | Chase camera with the Supermarine S.6B against a wooded ridge at dusk (19:00), outline on vs off + plane mask |
| `horizon_woods` | 16 | Slow pan along a wooded land/sky skyline, outline on vs off |

## Metrics

- **`flicker_mean` / `flicker_pct`**: for every consecutive triplet `(t-1, t, t+1)`, frames `t-1` and `t+1` are warped into frame `t`'s camera (pure projective rotation for pans/horizon; 3D depth reprojection for `flight_300` and `approach_woods`). Per-pixel temporal sign-change oscillation `min(|d1|, |d2|)` when `(I_t - I_{t-1}) * (I_{t+1} - I_t) < 0` isolates high-frequency shimmer from smooth motion. `flicker_pct` is the share of valid pixels oscillating by `> 6` RGB levels.
- **`reproj_mae` / `reproj_pct`**: mean absolute error and `% > 12` RGB levels between the warped previous frame and the current frame (catches LOD pops, tile snaps and ground morphing).
- **`still_max_diff`** (`still`): maximum RGB difference between any two consecutive frames with camera and time frozen (must be `0`).
- **`horizon_jitter_px` / `horizon_step_px`** (`horizon_woods`): column-by-column skyline profile tracked across reprojected frames; `horizon_jitter_px` measures sign-flipping vertical jitter in pixels and `horizon_step_px` measures mean per-step skyline shift.
- **`horizon_flicker` / `outline_flicker_added` / `outline_pixels_mean`** (`horizon_woods`): flicker energy in the ±10 px band around the skyline, the excess flicker added by `src/silhouette.jo` (outline ON minus outline OFF), and a floor check (`min_outline_pixels`) guaranteeing the outline pass actually drew.
- **`plane_ghost_px` / `plane_ghost_max`** (`chase_dusk`): pixels on the aircraft mask or in the 8 px upward halo above its top edges (excluding true background ridge steps) that differ by `> 6` RGB levels between outline ON and outline OFF.

## Running locally

```sh
# Default headless software run (bit-for-bit identical to CI)
python3 tests/temporal_stability_test.py

# Save all frames, worst-pair strips and results.json to a directory
python3 tests/temporal_stability_test.py --out ~/dev/tmp/aegean-skies/stability-out

# Run on the desktop Vulkan GPU instead of software rendering
python3 tests/temporal_stability_test.py --gpu --no-fail

# Run a subset of clips while iterating
python3 tests/temporal_stability_test.py --clips still,chase_dusk,horizon_woods --no-fail

# Refresh tests/baselines/temporal_stability.json after an intentional improvement
python3 tests/temporal_stability_test.py --write-baseline
```

Each run writes a 3-panel `worst-<clip>.png` strip (`prev_warped | cur | 6x diff`, or `outline_off | outline_on | 6x diff` for `chase_dusk`) and `results.json`. When a default run fails locally, the worst-frame strips are preserved under `~/dev/tmp/aegean-skies/temporal-stability-fail/`.

## Why `SLOPPY_SOFT_SCALE=1`

Sloppy's software renderer defaults to half resolution (`SLOPPY_SOFT_SCALE=0.5`), which shrinks the scene target relative to the full-viewport passes used by `src/silhouette.jo`. Setting `SLOPPY_SOFT_SCALE=1` runs the full terrain, canopy, crown, aircraft and screen-space outline pipeline identically on GPU-less CI runners and locally.
