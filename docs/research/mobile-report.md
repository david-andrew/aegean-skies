# Mobile and sky implementation

Branch `t3/mobile-sky`, base `9656387`. Part 1 committed as `51db62e`; Part 2 implementation committed as `53f2af3`; final horizon-edge repair and
measurement follow-up described below. All runs headless/silent,
one test process at a time, SLOPPY_THREADS=1. No main-checkout changes or pushes.

## Part 1: phone startup

Found a concrete portable-limit violation. Sloppy 0.29.2 generates one large
LitParams uniform struct and passes it through functions. Chromium/ANGLE reports
all 240 vector slots active, including bones[192], even in unskinned programs.
The WebGL2 minimum fragment capacity is 224. Sea uses only 69 (three samplers).
Generated vertex/fragment float/int precisions match (highp); largest varying
interface is five vectors. The engine eagerly creates the lighting/shadow programs
at startup, so unused skeletal drawing can still prevent startup.

Implemented a game-local web compatibility pass: specialize read-only uniform
parameters, expose fields as independent global uniforms, preserve upload layout
and translate uniform-name lookups. This avoids changing the pinned engine or
reducing skeleton capacity. Shader-link diagnostics now retain stage entrypoints,
limits and explicit empty-driver-log explanation. Exact phone confirmation remains
necessary: no access to that handset, so the limit violation is a reproduced
portability bug, not yet proof of the phone driver's precise failure.

Primary specification: https://registry.khronos.org/webgl/specs/2.0.0/ and
https://www.khronos.org/files/webgl20-reference-guide.pdf .

The actual linked ordinary lighting program now uses 46 conservative vector rows,
44 for its instanced counterpart. All 58 embedded shader stages pass the CI budget
audit. Maximum vertex/fragment rows are 207/60 (49/164 below guaranteed limits),
varyings 5/15, attributes 9/16, samplers vertex 2/16 and fragment 3/16. The full
64-joint skin palette remains supported. The actual browser has linked all 35
programs needed by the first drawn scene, with no errors.

### Startup rendering profiles

Auto selects low for mobile devices or minimum-limit GPUs, medium for recognized
integrated/software GPUs, high otherwise. Explicit `AEGEAN_QUALITY=low|medium|high`
works as a URL parameter or native environment variable; no menu changes. Low/
medium/high pixel ceilings: 230400/518400/2600000. The page's original adaptive
resolution continues underneath the ceiling. Phone contexts request no MSAA.
Cloud fields: 28/45/70; sphere tessellation: 6x4 / 8x5 / 12x7. Tree stride: 3/2/1;
legacy grove visibility: 2.5/5/9 km; streamed grove radius: 450/550/700 m; grass:
24/32/42 m. Terrain error budgets increase on weaker tiers, while near-contact
14 m geometry remains canonical and shared edges remain balanced. The complete
country and horizon silhouettes remain visible; detail distance changes, not
physical geography or travel. Original tree random draws and roots are preserved.

### Measurements (redfox, Intel UHD 620, under shared bench lock)

Native headless 1280x720, 240 frames/view, median reported frame windows excluding
first warmup window. All runs one worker, silent, no desktop timing comparison.

| View | Main 9656387 | High | Medium | Low |
|---|---:|---:|---:|---:|
| Harbor | 110.9 ms | 110.8 ms | 60.55 ms | 38.8 ms |
| Mainland grove | 53.0 ms | 53.0 ms | 23.4 ms | 13.8 ms* |

*Low mainland completed too quickly for a post-warmup statistics window: 13.8 ms
is the sole window, includes cold work, and is not a steady-state comparison.
Native RSS after warm driver cache: 102864–104624 KiB across profiles. The first
baseline harbor run peaked at 120404 KiB; shader-cache state differs, so this is
not presented as a memory saving from the patch.

Hardware WebGL2 Chromium/ANGLE Vulkan, 65 s each, fresh profiles, harbor view;
frame gaps exclude the first 5 seconds of drawing. Android emulation: 844x390 CSS,
DPR 3, touch and Android UA; this still uses the laptop GPU, not a real phone.

| Probe | Selected tier/canvas | Median / p95 frame gap | Wasm memory | Browser-tree PSS |
|---|---|---|---|---|
| Desktop weak GPU | Medium, 960x540 | 50.0 / 66.7 ms | 56623104 B | 537452 KiB |
| Android proxy | Low, 706x326 | 33.2 / 33.4 ms | 56623104 B | 523049 KiB |
| Android proxy, CPU 4x | Low, 705x326 | 50.0 / 83.4 ms | 56623104 B | 519665 KiB |

Maximum texture dimension observed: 2048, within the WebGL2 minimum. PSS includes
the entire Chromium process tree and driver, not just the game. It cannot predict
an Android driver's memory budget; actual phone confirmation is still required.
The 4x CPU-throttled Android proxy completed 625 frames with no exceptions: median
50.0 ms, p95 83.4 ms, 56,623,104 B Wasm memory and 519,665 KiB browser-tree PSS.
That is about 20 fps at the median, with visible slow frames: usable as a weak
proxy, but not a claim of 30 fps on a mid-range phone. Sky work will target more
GPU savings; simulation/startup CPU work can still limit weak phones. All observed
color attachments are RGBA8; the largest allocation is the 2048-square depth map.
The profile does not require float color targets or textures larger than the
WebGL2 minimum.

### Validation and handoff

24 native tests pass: quality (2), flight (16), shared terrain/groves (6).
The quality contact test checks all three tiers at ground level and verifies
canonical height, contact triangles, cache cap and neighbor level balance. JS
regressions cover unused oversized arrays, nested helper/constructor calls,
read-only requirements, repeated specialization and tier selection. Native and
web release builds compile. Profiling zones were added around clouds and groves
for the next phase; benchmark profiles above precede those diagnostic labels. Screenshots and JSON probes are under `part1/`.

`docs/research/mobile-shaders.md` gives the compiler/runtime maintainer handoff;
no changes were made to the shared slop-lang checkout. The Pages workflow audits
all embedded shaders and runs the new compatibility and quality tests. Touch
flight/walking axes, throttle, action buttons and menu/chart access remain UI work
for the coordinator. Low resolution also softens existing HUD text; no UI layout
or control design was changed.

## Part 2: sky

### Implementation

Replaced the default 22,878 opaque puff meshes with connected density formations.
Four original 64³ density/normal stamps share a 1056² RGBA8 slice atlas (one-pixel
slice gutters, manual interpolation between adjacent slices). Smooth unions and
procedural erosion give each stamp one body, common condensation base, shoulders
and rising lobes. No reference-image pixels or film designs were copied.

The field is deterministic in 6.5 km world cells, with coherent coverage bands,
breaks, ordinary banks and occasional towers. Rotated bounds fit disjoint cells;
there is no camera-relative 34 km wrap. Wind advects the same identities on every
quality tier. A cached neighborhood extends 150 km, fading from 125 km before its
edge. Formation bases are roughly 650–950 m; tallest tops reach about 4 km. The
same curved-Earth chart and analytic sea intersection hide clouds below the sea
horizon. Frustum bounds include curvature across the complete rotated box.

Each visible formation draws an instanced screen rectangle, integrates density
front-to-back, then composites formations back-to-front. A half-resolution RGBA8
target is reconstructed with four depth-aware taps at full resolution. Where all
four guide taps disagree with the full-resolution depth, a sparse full-resolution
raymarch resolves that pixel. This repairs cracks through near clouds at a far
sea horizon without leaking cloud color over thin foreground silhouettes. An
equal-depth nearest-tap check rejects the extra pass cheaply over open sky.
Conservative density-support bounds (guarded by the atlas test, including filter
margin) skip the empty outer part of each stamp. No additional targets are needed.
Near steps
are 40 high/medium and 24 low, declining continuously to eight far away. Early
transmittance termination bounds dense interiors. High/medium get one secondary
sun-density probe nearby; low uses the baked normal and shared lighting. No float
targets, MRT, temporal history, or new engine features are required.

`cloud_depth.jo` adapts the engine's post target: attach a sampleable 24-bit depth
texture before scene geometry; sample it only from the separate cloud target;
temporarily restore the original renderbuffer when compositing into scene color.
The scene depth texture is reattached afterward. This avoids WebGL feedback loops
and preserves actual terrain/aircraft intersections during cloud entry. Targets
resize with the scene; the browser cap now uses the CSS aspect to avoid one-pixel
allocation oscillations as the engine changes its adaptive resolution.

Cloud lighting uses the existing sun, blue-grey shade and haze palette, softened
bases, self-shadowing and a forward-lit rim. The atmosphere integrates mean density
through the existing height-exponential air instead of treating the entire ray as
being at its lowest endpoint. The solar horizon has directional warmth; an eight-
tap (four on low) screen-space shaft pass uses cloud transmittance and scene depth,
only around a low visible sun. It is an inexpensive screen-space approximation,
not volumetric multiple scattering or terrain/ground cloud shadows.

The Sun now follows a continuous 24-hour orbit (east at dawn, west at dusk). Stars
are compact antialiased points. The Moon is a lit sphere projected as a disk:
its illumination and crescent orientation follow the actual Sun direction, with a
29.53059-day synodic cycle driven by living-world days and a small inclination.
The initial age is ten days. Full Moon is opposite the Sun; new Moon is near it;
quarter phases are roughly 90° away. This is a fixed-season, twelve-hour-day model,
not a real-date ephemeris, tide model or eclipse simulation. It changes ground
lighting direction too; the old clamped nighttime Sun path was not continuous.

Primary lunar references: [NASA Moon phases](https://science.nasa.gov/moon/moon-phases/),
[USNO phases](https://aa.usno.navy.mil/faq/moon_phases), and
[NASA orbital inclination](https://eclipse.gsfc.nasa.gov/SEhelp/moonorbit.html).
Renderer direction: `docs/research/longrange_clouds.md`, bounded pilot first.

### Measured bound and pilot

Redfox Intel UHD 620, headless Vulkan, one worker under `~/dev/tmp/bench.lock`.
The old high-quality harbor scene spends about 40.2 ms GPU on clouds, 40.2 ms on
groves, 17.4 ms on near sea and 5.9 ms on terrain: clouds were about 37% of the
110 ms frame, not the whole bottleneck. A sub-5-ms replacement had a useful bound.

The full-resolution 32³ pilot cost 11.72 ms cloud GPU from outside and 23.42 ms
inside; that resolution was rejected. Half-resolution 64³ stamps with depth-aware
reconstruction cost 4.01 ms outside, 3.35 above, 6.90 inside and 7.03 during entry.
The full field has much smaller screen footprints in normal game views.

The shared development compiler changed to Sloppy 0.30.0 during work. Consequently
old-baseline/new-engine comparisons are exploratory, not the final paired result.
Final primary measurements use the isolated official **0.29.2** compiler and
library pinned by Pages CI, with both baseline `51db62e` and this branch rebuilt
from the same generated land assets. Release archive SHA256:
`29ce86c3a5674c84d6c935adbb76fe294550409d773bcec4a2ec09010c17b77e`.

Initial paired sky measurements, before the final horizon-edge repair: 500 native
frames/view, 1280×720; medians of reported windows after the first:

| Harbor | Phone commit baseline | New sky | Cloud GPU baseline/new |
|---|---:|---:|---:|
| High | 111.25 ms | 73.50 ms | 40.20 / 2.27 ms |
| Low | 41.90 ms | 40.55 ms | 3.67 / 2.08 ms |

Peak RSS high: 103204 / 111800 KiB; low: 103396 / 105660 KiB. High frame time
improves about 34%. These are laptop bench-lock measurements, but background
projects were later found running CPU-heavy builds outside that lock. Do not treat
small frame/RSS differences as isolated effects. The large cloud GPU reduction is
consistent across the pilot and full-scene runs.

Initial paired Android browser proxy (before the edge repair), before resize,
excluding five seconds after first
real draw: baseline/new median gaps 33.3 / 16.7 ms, p95 33.4 / 33.4 ms, mean
27.42 / 24.50 ms. The new run alternates 16.7 and 33.3 ms gaps; its median does
not mean a steady 60 fps. All 35 baseline and 36 new scene programs link, no JS
errors. Wasm memory 56623104 / 65667072 B (+8.63 MiB); browser-tree PSS
491365 / 526996 KiB. Native/browser resize checks stay framebuffer-complete and
report GL error zero in portrait, landscape and wider viewports.

Severe CPU4x samples were contaminated: background Sloppy (four CPU threads),
Dewy/Python workers and indexing were active despite the held bench lock. A
counterbalanced profiling attempt observed 1-minute loads 6.06 and 6.71. Their
50–98 ms medians/means are not an isolated sky comparison. Following the user's
instruction, a bounded quiet-window gate checked load under the bench lock at
five-minute intervals, starting only below 1.5 and stopping after thirty minutes.
From **2026-11-11 21:57:29 to 22:27:28 UTC**, observed one-minute loads were
**6.89, 2.71, 4.55, 3.68, 4.04**; the last check found the lock busy. No qualifying
window occurred and no throttled laptop comparison was started. Raw checks:
`quiet-compare/gate.jsonl`.

Final edge-repair native coverage, under the laptop lock but **not** a quiet CPU
comparison: high **74.6 ms frame / 3.17 ms cloud GPU**, low **42.6 / 3.53 ms**.
Start loads were **4.26 high / 3.33 low**. The high result remains about 33% faster
than the phone-commit baseline. The observed low result is 0.7 ms slower than its
41.9 ms baseline; this small difference is not isolated from background CPU work,
so the low-tier no-regression timing gate remains inconclusive. Raw final logs:
`finished-check/`. The large high-tier cloud saving is clear; a clean low-tier
comparison and actual phone run remain follow-up checks.

Desktop fallback: i7-6700 desktop, Chrome for Testing 151.0.7922.34, Android 844×390/DPR3 emulation,
CPU throttle 4×, low tier, actual canvas **706×326**. Both machine hostnames happen
to report `redfox`; these desktop results are **not** from the Intel UHD 620 laptop
at 192.168.1.79. The NVIDIA ANGLE/Vulkan attempt lost its WebGL context on both
versions (`GL_CONTEXT_LOST_WEBGL`, 0x9242), producing a null shader compile log
before gameplay. Those four attempted runs are excluded. This is a different
failure from the uniform-budget violation in Part 1; its desktop driver/resource
cause was not established.

The completed fallback uses **SwiftShader**, fresh profiles, 90 seconds each,
order **A/B/B/A**, A = phone commit `51db62e`, B = final sky with edge repair.
Intervals exclude five seconds after first real draw and anything after 90 seconds.
This is a software-rendering stress proxy, not a clean hardware-GPU CPU comparison:
GPU work consumes desktop CPU too, and other projects remain active.

| Order/version | Load before → after | Samples | Median gap | p95 gap |
|---|---:|---:|---:|---:|
| 1 / A baseline | 8.07 → 16.09 | 24 | 2141.6 ms | 3416.6 ms |
| 2 / B sky | 16.09 → 13.41 | 49 | 1183.2 ms | 1616.6 ms |
| 3 / B sky | 13.41 → 14.93 | 39 | 1416.7 ms | 2799.9 ms |
| 4 / A baseline | 14.93 → 17.06 | 29 | 1733.3 ms | 3783.2 ms |

Equal-run median of medians: **1937.5 ms baseline / 1300.0 ms sky**.
Neither is playable under this software-GPU stress. This does not establish a
phone frame rate or close the clean low-tier hardware timing gate. All runs linked
every scene program (35 baseline / 36 sky), with no JS errors and final GL error
zero. Wasm memory stayed 56623104 / 65667072 bytes. Browser-tree PSS ranged
600197–606915 KiB baseline / 627162–631765 KiB sky.

Raw logs, captures and probes: `desktop-software-proxy/`; launch loads and end
loads: `desktop-software-driver.log`. `desktop_software_compare.py` reproduces
this sequence; `summarize_proxy.py` computes per-run medians from the frame arrays.
The failed NVIDIA probes are retained separately in `desktop-proxy/`.


Additional 0.30.0 development-runtime coverage (engine `90e7daf`): high/low harbor
73.8/39.8 ms, sunset toward the Sun 45.6/17.35, night 43.0/15.9; cloud GPU costs
2.27/2.04, 5.16/3.77 and 3.66/3.30 ms respectively. Entry and rapid-bank pilots
complete without errors; bank cloud GPU 4.01 ms, entry 7.51 ms. These are separate
compatibility/coverage measurements, not mixed into the pinned-version comparison.

### Assets, memory and portability

Atlas PNG: **769707 bytes**, decoded/GPU RGBA8 **4460544 bytes (4.25 MiB)**.
Redfox cloud-only bake: **2.40 seconds** (0.30 development runtime); the pinned
0.29.2 bake produces the identical SHA256. The atlas is generated by the normal
`tools/bake.jo`; `tools/bake_clouds.jo` rebuilds it alone. No baked PNG is committed.
Additional GPU targets at 1280×720: about 3.52 MiB depth plus 0.88 MiB half-size
color, with implementation-specific depth padding. At 706×326 these total about
1.10 MiB. The original scene renderbuffer is retained for legal attachment swaps.

Pinned 0.29.2 packaged web baseline/new:
- Wasm: 8689261 / 9510787 bytes.
- HTML: 86571 / 86951 bytes.
- Combined zlib level-6 transfer estimate: **3961347 / 4741724 bytes**, +780377
  bytes (+19.7%). Actual hosting compression can differ.

All **60** embedded stages pass WebGL2 minimums: max vertex/fragment uniform rows
207/60, varying rows 5, attributes 9, samplers 3. New volume fragment program uses
18 rows/two samplers; reconstruction eight/two; sky thirteen/zero. No new texture
exceeds the minimum maximum dimension. The development 0.30 library adds PBR/morph
programs: its 68 stages also pass (207/60 rows, seven varyings, eleven attributes,
nine samplers), but those engine changes are not part of this branch.

### Validation, captures and remaining limits

Six new tests cover solar wrap/lunar phase geometry, cell separation and RNG
independence, atlas gutters and unclipped boundaries, atmospheric reciprocity,
world identities across cache movement/wind, and projected curvature bounds.
The atlas check also verifies that over 99.5% of solid voxels belong to one
six-connected body in each stamp and that all filtered nonzero density fits the
tightened support bounds. Both quality tests pass with the
pinned release. Flight tests and JS specialization/quality checks pass. Release
native/web builds and shader audits pass. Pages CI runs the sky tests after baking.
Native GPU and hardware WebGL captures verify a cube in front of, inside and behind
a volume. The final `horizon` pilot also checks a far opaque slab edge crossing
a near cloud, with a nearer red cube: the cloud stays continuous and the cube
remains unobscured. Crescent, quarter and full-Moon captures verify terminator orientation.

The engine's pure CPU rasterizer cannot sample scene depth through its GL texture
API. Software-only/CI runs therefore retain the old opaque cloud path; GPU-native
and WebGL use volumes. `AEGEAN_LEGACY_CLOUDS=1` also selects it for comparison.
The software smoke run completes with two frames. The depth adapter uses private
Sloppy post-target globals; recheck it when upgrading the pinned engine.

The field is bounded at 150 km. At very high altitudes it can thin before the most
distant physically visible elevated clouds; a coarse far bank would extend that
cheaply. Four rotated/scaled stamps give finite shape diversity. Thin frontmost
transparent effects do not supply their own depth, so their cloud attenuation is
approximate; opaque aircraft, terrain and water use the real scene endpoint.
There is no temporal reprojection, so no history ghosting, but half-resolution
edges and low-step distant detail can shimmer during fast movement. Screen-space
shafts cannot account for off-screen occluders. Browser context-loss recovery
remains the engine's reload behavior, not a new recovery system. Actual Android
handset confirmation remains necessary; emulation is not the handset GPU.

All artifacts are under `~/dev/tmp/aegean-skies/mobile/`: paired pinned results in
`sky-029-results/`, development-runtime coverage in `sky-030/`, initial pilots in
`part2-pilot-v1/` and `part2-pilot-v2/`, and `moon-crescent.png`, `moon-quarter.png`,
`moon-full.png` (4° inspection FOV). `tools/cloud_pilot.jo` reproduces front/above/
inside/entry/bank/horizon/field/field_sunset/moon views via `CLOUD_VIEW`, with `AEGEAN_HOUR`
and `CLOUD_DAY` for celestial checks. Main captures use `AEGEAN_VIEW` as before.

No UI was changed. Phone controls still need the Part 1 UI handoff. No new sky UI
is required; artistic tuning lives in `look.jo`, `cloud_density.jo` and
`cloud_field.jo`. Merge the phone commit first, then the separate sky commit
and horizon-edge follow-up. After merging, run
`sloppy --release tools/bake_clouds.jo` to create the new ignored atlas (the normal full bake and CI
already include it). Shared `aegean.jo` edits are confined to cloud initialization/draw and lunar time.
Nothing was pushed and the main checkout was untouched.
