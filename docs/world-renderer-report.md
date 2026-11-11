# Aegean world renderer — implementation report

Implementation branch: `t3/world-renderer`, based on `97eda0d`. Implementation checkpoint: `6874ff0`; a final reporting commit follows it. Nothing has been pushed or merged, and the main checkout has not been modified. The canceled island-scaling branch remains separate.

## What is built

- A 500 × 400 km, Aegean-inspired world around the original ten islands. The original coordinates, distances, erosion, harbors, towns, 8 m source and 14 m canonical triangles are preserved.
- Eight authored mainland/large-island regions, mountain chains, and 347 seeded small islands. The western/eastern mainlands cover roughly 29,520/25,124 km² in a 2 km sampling survey; the western peninsula adds about 8,976 km². Sampled mainland peaks reach 2,912.5/2,832.1 m; the southern island reaches 2,333.2 m. Seventy-two smaller islands have peak envelopes at or below 35 m. These are approximate authored geography, not a GIS reconstruction.
- A deterministic, versioned macro field and local detail. New terrain queries use a quantized 8 m source and the same 14 m triangulation as near rendering. New regions expose names, outlines, bounds, ridge chains, seeded island IDs and `land_region_at`; original island/harbor records remain unchanged.
- A separate bounded quadtree renderer for new land. It reuses existing stitched grid meshes, keeps coarse ancestors available, balances adjacent levels 2:1, prioritizes nearby tiles, and uses a 512-slot LRU cache. All new land can be approached and queried for aircraft/boat/walking contact; it is not a backdrop.
- Normal streaming creates at most four new tiles / 9,248 height/material upload bytes per update. A cold contact view may use a capped eight-tile / 18,496-byte burst until the camera’s 56 m contact footprint has canonical coverage. Two 544 × 272 RGBA8 atlases total 1,183,744 bytes. No fine terrain bake over the whole country and no streaming service.
- The existing sea material with new depth inputs: fixed coarse world depth plus a double-buffered 256², 6 km near window at the original 23.4375 m sample spacing. Eight rows per update; publish only complete windows. The original 24 km depth map remains authoritative around the old islands.
- A whole-world chart and the preserved readable local chart: M opens, Tab switches, including in the paused teleport picker. No towns or harbors have been placed on the new land.
- Camera-relative terrain and existing spherical curvature, with the far plane extended to include high summits near the mutual horizon.
- A lighter web payload: separate hashed wasm, packed source residency, and one-island-at-a-time derivation of the old render data from the unchanged source. The duplicate 4.1 MB render asset is no longer embedded. The derived bytes match the original asset exactly.

The sourced survey and architectural reasoning are in `design.md`, mirrored in the repository as `docs/world-renderer-design.md`. The survey covers all systems requested in the brief and distinguishes published internals from unknown proprietary details.

## Measurements

All wall-clock/GPU benchmarks are on the quiet Intel i5-8350U/UHD 620 laptop at `dsamson@192.168.1.79`, under `flock ~/dev/tmp/bench.lock`, one job at a time. Desktop results are instruction counts, capabilities, memory and functional checks. All runs are headless and silent.

### Assets, startup and memory

| Item | Baseline | Expanded world |
|---|---:|---:|
| Game payload, zlib6 transfer estimate | 7,204,341 B | 3,704,071 B (48.6% smaller) |
| Wasm module | 10,984,246 B | 8,249,813 B |
| HTML | 14,723,862 B, includes base64 module | 78,770 B loader |
| Wasm linear memory | 68,485,120 B / 65.31 MiB | 52,297,728 B / 49.875 MiB (23.6% lower) |
| Chromium process-tree PSS, laptop Intel hardware | 564,973 KiB | 479,215 KiB (15.2% lower; final spot check) |
| Chromium process-tree PSS, desktop NVIDIA hardware | 900,577 KiB | 683,339 KiB (24.1% lower) |
| Chromium process-tree PSS, desktop SwiftShader | 945,790 KiB | 890,660 KiB compact checkpoint (5.8% lower) |
| Legacy source sample residency | 8,975,872 B expanded floats | 3,365,952 B packed samples |
| Additional macro asset | — | 1,259,469 B raw; 436,554 B zlib6 |
| Additional terrain sample atlases | — | 1,183,744 B, fixed |
| New macro bake, laptop | — | 0.3083 s including validation; peak RSS 5,848 KiB |

Transfer figures sum the loader and module, using the same zlib6 estimator; actual HTTP encoding can differ. The optional CI preview PNG is not requested by the game loader. Browser PSS includes the process tree, does not double-count shared pages like summed RSS, and excludes GPU VRAM. It is a snapshot, not a peak guarantee; the preceding compact NVIDIA run was 666,307 KiB. Software GPU/JIT overhead changes the proportional savings considerably.

The paired checkpoint (`140e392`) native runs initialize the world in 5.37–5.46 s versus baseline 2.39–2.42 s. Native peak RSS is 98,692–100,472 KiB across the six paired-checkpoint views, versus 108,132–109,232 KiB across the paired baseline views (about 8–9% lower at matched cameras). Deriving the old render data trades roughly two seconds of laptop work for about 3 MB less compressed download and lower memory; it is not an erosion bake. The standalone derivation pilot matched all 4,114,200 render bytes in 1.959 s. Initialization figures exclude the first frame's shader compilation. On the laptop's hardware-backed Chromium, logged world initialization is 6.761 s in the final spot check (6.702 s in the paired checkpoint) versus 3.280 s baseline. This also excludes page/module download, compilation and first-frame shader warmup. The full expanded world loads on the 7 GB laptop without an external terrain service.

### Frame and instruction cost

Paired runs at checkpoint `140e392` alternate baseline/expanded-world order, twice per original camera, 360 frames per run at 1280 × 720. The first compilation/warmup stats window is excluded. These medians are highly repeatable across the two orders:

| View | Baseline frame ms, runs 1 / 2 | Final frame ms, runs 1 / 2 | Mean change | Final new-terrain CPU / GPU ms |
|---|---:|---:|---:|---:|
| Porto harbor | 109.4 / 109.4 | 110.7 / 110.8 | +1.23% | 0.26 / 0.07 |
| Crossing | 96.8 / 96.7 | 97.4 / 97.4 | +0.67% | 0.30 / 0.09 |
| Original high view | 96.3 / 96.3 | 97.4 / 97.4 | +1.14% | 0.32 / 0.47 |

| New view | Total frame ms | CPU / GPU frame ms | New-terrain CPU / GPU ms | Peak RSS KiB |
|---|---:|---:|---:|---:|
| Mainland, 4,000 m | 52.00 | 1.8 / 49.6 | 0.70 / 4.40 | 99,800 |
| Mainland coast, 80 m | 55.60 | 3.0 / 52.1 | 1.86 / 4.40 | 98,692 |
| Mainland ground | 50.95 | 3.0 / 47.5 | 1.81 / 3.74 | 98,828 |

After the cold-contact burst change (`6874ff0`), a final locked 360-frame spot check measured harbor **110.7 ms**, crossing **97.45 ms**, original high **97.4 ms**, and mainland ground **50.8 ms**, consistent with the paired results. Native initialization was 5.399–5.502 s. Peak RSS was 102,268–103,696 KiB, about 5% below baseline at matched original views; use this final range rather than assuming the earlier 8–9% reduction persists. Final Intel browser PSS was **479,215 KiB**, wasm memory remained **52,297,728 bytes**, and the deterministic fingerprint matched. Logs and summary are in `laptop-burst-final/` and `laptop-browser/burst-final.log`.

**The strict “no worse frame time” target is missed by 0.65–1.35 ms at the old cameras.** This is an approximately 0.7–1.2% regression, including the corrected conservative legacy LOD bounds. New-world GPU work there is only 0.07–0.47 ms; removing it entirely cannot produce a large whole-game gain. No desktop wall-clock/GPU timing claim is made; desktop instruction counts and successful native/WebGL rendering cover that target as allowed by the machine rules.

Desktop Callgrind, new-world CPU preparation and edge ownership only, after identical warmup:

| Path | Instructions/frame | Streaming over 360 measured frames |
|---|---:|---|
| Crossing near original islands | 625,060 | No generated tiles; cache 84 |
| Mainland movement | 6,016,079 | 64 generated tiles; max 190 selected, cache 341 |

These exclude GPU/driver submission and the old renderer's selection. The baseline old-renderer-only workload was 1,118,153 instructions/frame; adding unlike workloads is not a measured whole-game speed ratio. The counters precede the final small publication-state check.

A straight 500 km crossing at 165–200 m/s takes 50.51–41.67 minutes. This is distance/speed arithmetic, not a measured autopilot trip; flight physics and the 3.3 baseline were not changed.

## Validation

- **94 tests pass; two known pre-existing failures remain**, both in `tests/living_scene_flight.jo`: saved aggregate damage equality at line 127 and engine-health expectation at line 141. Flight 16/16, damage 11/11, geography 5/5, living save 4/4 and all other living tests pass. An isolated save directory is required. `tests-final.json` and `.log` contain per-file results.
- Every one of 511,914 old canonical vertices matches; 424 patch error bounds and 96 stitch families pass. Grounded-surface difference is zero. The original render asset remains byte-identical.
- Five old-terrain camera checks: actual projected error below 0.125 px; shared-edge residual below 0.00049 m. Motion test: actual projected morph below 0.059 px/frame, conservative motion bound below 0.20 px/frame.
- New world: height/peak bounds, corrupt/truncated macro rejection, sampling-order independence, packed source round trip, and preservation of old heights pass.
- New streaming path: high view, ground, 200 m/s movement and far teleport; maximum cache 496/512, selected tiles 191, triangles 98,736; no overlapping domains, 2:1 neighbors, upload cap observed, near-contact agreement, shared-edge residual 0.00015626 m. Arrival morphs start at publication; near-contact tiles use the canonical surface immediately when available.
- A 110° FOV stress test across eight ground teleports reaches 14 m contact terrain in 30–44 updates with the final capped burst (previously 60–88). Cache stays at 512 slots, selected tiles peak at 250. The locked laptop CPU-only preparation probe improves contact-footprint readiness from 81 to 41 updates; peak preparation rises from 6.87 to 12.27 ms. This includes software atlas updates, not GPU draw submission. A 16-tile candidate reached 21 updates but peaked at 23.14 ms and was rejected.
- Depth: three atomic window publications, 768 checked samples; maximum depth difference 0.110175 m, below the 60/255 m quantization step.
- Native and wasm agree on fingerprint **17775399900910795030** for 1,000 canonical-height/region samples. Software, NVIDIA and Intel UHD 620 WebGL2 backends load successfully. The Intel probe also reproduces the same fingerprint.
- Native software-renderer CI smoke passes. One concurrent native/browser GPU check exhausted Vulkan allocation; the serial rerun passed. GPU probes are run serially.

Screenshots and logs live beside this report: `laptop-baseline/`, `laptop-world-compact/`, `laptop-paired-final/`, `laptop-browser/`, `chart-final.png`, browser captures, `world-burst-check.log`, `world-depth.log`, `legacy-error.log`, and `legacy-motion.log`.

## Limits and follow-up choices

1. The strict zero-frame-regression target is missed by about 0.7–1.2% at matched original cameras. The new renderer is bounded and cheap there, but this is a tradeoff, not an exact performance win. Much of the original frame is clouds/other drawing; further terrain-only optimization has a small whole-frame ceiling.
2. The new tree uses conservative visibility bounds and distance-based refinement, not a proven global 1.5 px screen-error bound. The old renderer retains its measured bounds. New seams and near contacts are checked; a complete screen-error hierarchy for procedural terrain remains a separate improvement.
3. A cold teleport shows coarse coverage while the bounded cache fills; the final stress test takes 30–44 updates to publish 14 m contact terrain. The eight-tile contact burst deliberately trades some short-lived CPU cost for faster readiness. A near depth window takes 32 updates; very rapid movement/teleports can temporarily use coarse coastal depth outside the published window. Physics queries remain authoritative throughout. The cheapest next refinement is velocity lookahead or a toroidal near-depth window, not a larger world bake.
4. New land has terrain only: no new settlements, forests, roads, country simulation or harbor placement. Region records and height/coast queries are available for that later work. Geography is deliberately approximate and should receive the user's geographic/art review.
5. Browser memory gains depend on backend: total PSS falls 15.2% on the final laptop Intel GPU run (14.1% in the preceding checkpoint), 24.1% on desktop NVIDIA, and 5.8% under SwiftShader. Wasm residency falls 23.6%. The design’s aspirational 20% total-PSS reduction is not universal; no stronger device-independent claim is justified.
6. Measurements compare the branch base `97eda0d`, not the later main. Main was `c8aa477` when checked, with unrelated boats, cloth, audio and input changes. Recheck the integrated game after merging.

## Merge and reproduce

Keep this branch; do **not** merge `t3/world-scale-implementation`. The implementation commits after `97eda0d` are `5ecb453`, `28688f0`, `b523ef9`, `470812f`, `bb0e619`, `140e392`, and `6874ff0`, plus the final reporting commit. There are no attribution lines and no pushes.

Merge the branch into the current integration branch, preserving main's later work. The shared file is `aegean.jo`: keep main's dock ownership, mouse-capture, boat/cloth and `pc_at` changes; add this branch's imports, packed/source-derived terrain initialization, new-world initialization, draw call, and chart toggle. No flight, objects, cloud or sound implementation files were changed by this branch.

After integration:

1. Run `sloppy --release tools/bake.jo`. This rebuilds the unchanged legacy source/reference LOD and the ignored `assets/world.bin`. For geography-only edits, `tools/bake_world.jo` is enough; bump `GEOGRAPHY_VERSION` when changing generator rules.
2. Run flight, damage, geography and living tests with `SLOPPY_NO_AUDIO=1`, `SLOPPY_THREADS=1`, and an isolated `SLOPPY_SAVE_DIR`; retain the two known living-flight failures separately.
3. Run `tools/terrain_check.jo`, the headless legacy error/motion probes, `tools/world_flight.jo` (720 frames), `tools/world_cache_check.jo`, and `tools/world_depth_check.jo`. Set DISPLAY/WAYLAND_DISPLAY empty and supply SLOPPY_SCREENSHOT for render probes.
4. Build release wasm, then run `python3 tools/package_web.py site/index.html`. Publish **both** loader and hashed wasm when publication is separately authorized. CI now performs this split and the new numeric checks automatically.
5. Repeat the saved laptop scripts under `flock ~/dev/tmp/bench.lock` and the browser memory probe. Copies of the standalone benchmark binaries/scripts are in `~/dev/tmp/aegean-world-renderer` on redfox. Do not use the desktop for comparative frame/wall timings.

The design, evidence, binaries and scripts remain in the requested scratch area for review and reproducibility. No system settings or other checkouts were changed.
