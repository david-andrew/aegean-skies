# Local render coordinates

Geography, living-world identities, audio sources and charts remain in world coordinates.
The on-foot player keeps a CPU-f64 `WorldPoint`; its published vec3 is a compatibility snapshot.
Townsfolk keep f64 interpolation state and re-sample canonical contact while moving nearby. GPU geometry uses `render_origin(camera)`, snapped to 1024 m in x/z (y remains sea
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
Coarser glint anchors derive from the finest lattice by exact power-of-two integer quotient/
remainder. Sea band calls use constant indices and wavelengths to avoid dynamic uniform reads
and retain shader constant folding on Intel GPUs.
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

On foot, `FollowCamera.target` and `shown_target` are local to `FollowFrame.origin`.
Only `update_local_follow` and `place_local_follow` may update/place this camera; do not pass its
local target to an absolute camera overload. `render_eye_low` carries the exact camera's residual
through local view construction. Reset it before choosing a camera for a new draw. Geometry,
clouds and material camera uniforms use `render_eye(origin)` to retain that residual.

Articulated figures and carried cargo remove the world root before composing limb/hand offsets.
`obj_local_params` accepts such a completed local model without subtracting origin again. The
actor offset map is view-only: it shares the figure's interpolation offset and sub-centimetre correction with held cargo.
Buoyancy composes rotation at the local model root instead of multiplying cancelling world pivots.

The new-world terrain renderer pins nine canonical contact tiles around a low camera before
streaming the distant quadtree. A cold arrival is bounded by nine tile uploads; steady frames
retain the ordinary generation budget. A fragment-space contact rectangle clips overlapping
coarse fallback terrain. These pins protect nearby player/prop contact while the rest of the
quadtree arrives; they do not change the authoritative physical surface or distant depth encoding.

`AEGEAN_WALK_TRACE=1` logs actual on-foot contact, selected terrain and nearby prop-root errors.
`AEGEAN_WALK_FRAMES=directory` saves frames 120..180 every two frames, after the scene and HUD have
rendered. It is opt-in diagnostic work; normal play does no readback. The far-port contact test
also samples emitted quay triangles independently of the walking query.
