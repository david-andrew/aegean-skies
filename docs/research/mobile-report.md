# Mobile and sky implementation

Branch `t3/mobile-sky`, base `9656387`. Work in progress. All runs headless/silent,
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

Cloud/grove GPU profiling is running on redfox, using the same high/low profiles
and camera. No sky rendering changes yet.
