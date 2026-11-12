# Local render coordinates

The simulation, geography, living-world identities, audio sources and charts remain in world
coordinates. GPU geometry uses `render_origin(camera)`, snapped to 1024 m in x/z (y remains sea
level). `render_view_proj(origin)` constructs the translation from the local camera and view
axes. Do not derive it by multiplying an absolute view-projection by `translation(origin)`:
the original matrix has already rounded its translation.

`obj_params` now returns a local model, local camera, local warp anchor, local gust displacement,
and separately reduced pigment/animation phases. Instance buffers retain their world translations;
vertex shaders subtract `u.origin` from the matrix translation **before** multiplying the vertex.
An already-local dynamic mesh must use `params.model = mat4()`. A camera-relative cockpit must
explicitly retain its own local model and zero origin. `ObjOut.world` and `GroundOut.world` mean
flat coordinates in the render chart, not absolute geography. World-dependent coarse material
lookups may add the separate origin; derivatives, curvature, distances and projections must not.

Cloud centres are made local at upload; persistent cloud records stay absolute. Thin ribbons,
cloth, rope, particles, splash rings and tracer geometry are expanded after subtraction. Sea shadow
quads carry their own chart origin, then are converted into the current sea chart.

Sea swells/ripples carry their wave vectors and CPU-f64, modulo-tau anchor/time phases. The CPU
water query uses the same vectors and f64 phase. Detail marks and glints carry integer cell IDs
separately from fractional cell origins; their centre distances never subtract large floats.
Main's original circular mark sizes and ripple bands are preserved. Legacy puff-cloud wrapping,
rain displacement, foliage pigment and vegetation sway also retain phase through chart changes.

The renderer still uses conventional perspective depth, including its cloud depth decoder.
This change does not implement reversed Z or fragment-correct logarithmic depth. Sloppy's current
public portable shader/render-state API does not expose the complete facilities needed for those
changes. Vertex-only log depth is not a valid replacement for coarse shoreline triangles. A
future depth change must cover terrain, sea, all effects, clear/test state, cloud endpoints and
all native/WebGL/software backends together.

World `vec3`/`mat4` values are f32. Existing CPU state and baked absolute geometry retain their
original quantization (1.5625 cm at 250 km); this render chart preserves model detail but cannot
recover bits already lost before upload. Full f64 state/RTC mesh authoring is a separate migration.

Validation: `sloppy test tests/precision_test.jo --release`; `tools/precision_view.jo` renders the
actual sea detail at a fixed metric footprint, with `PRECISION_AT='x z'`, `PRECISION_MARKS=1`, and
optional `PRECISION_BEFORE=1` for the frozen main-2b8f391 implementation. The tool's baseline code
is a test reference only, not a second production renderer.
