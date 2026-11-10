# Aegean Skies: seamless distance rendering and painted cloudscapes

Research and proposed design, 10 November 2026. Repository inspection was read-only. No renderer changes, builds, runtime benchmarks, commits, or pushes were performed. Numerical performance figures below are **engineering targets and workload estimates**, not measurements of a prototype. The reference images were inspected, including every image in `refs/starred/` through a contact sheet and the seven `user_ref_*.png` files individually.

## Recommended direction

Use **CPU-selected, error-bounded terrain patches with continuous geomorphing and explicit edge constraints**, a curved ocean that reaches its actual geometric horizon, and one atmosphere/visibility contract shared by every world material. Use **a low-resolution, temporally reconstructed volumetric cloud field**, with authored cloud masses and a deliberately painted lighting model. Keep cloud identity and density in world coordinates; change the sampling footprint with distance, rather than replacing nearby clouds with unrelated background clouds.

KSA is a useful quality reference for continuity across scale. Its particular planetary mesh solution is more machinery than this archipelago needs. Emulate its stable sampling and integrated terrain/ocean/atmosphere behavior. Do not build an orbital renderer, runtime erosion system, or Vulkan-only GPU-driven terrain pipeline to solve a 22 km island world.

Start with a **100 km visibility specification**, but provide at least **180 km geometric coverage** at 1,500 m altitude. A 100 km ocean disk does not reach an Earth-sized horizon from that height. Leave coverage derived from altitude so a later 5 km ceiling does not expose a new ring. For clouds, include their height in the visible-distance calculation: elevated clouds can be visible well beyond the sea horizon.

The principal uncertainty is the 3–5 ms cloud target on an integrated laptop GPU. The first cloud milestone must establish whether a reduced-resolution marcher can meet both the artwork and motion requirements. It must not become a months-long implementation justified by console timings.

## 1. What is in the repository now

| Area | Inspected behavior | Consequence |
|---|---|---|
| `src/terrain.jo` | One mesh per island; 14 m grid; normals sampled from finer heights; cells entirely below −40 m omitted | Geometry cost and silhouette quality do not adapt to view. There is no terrain LOD transition to fix yet; a new hierarchy is needed. |
| `src/world.jo`, `tools/bake.jo` | Eroded heights/ridge baked at 8 m; runtime interpolation; fallback procedural evaluation outside the bake | Keep erosion offline. Preserve this source of truth across all geometry levels. |
| `surface_height()` | Explicitly evaluates the current **14 m triangulated surface**, including the b–c diagonal | Changing rendering to 8 m without migrating this function and grounded objects causes floating/sunken props and collision disagreement. |
| `assets/terrain.bin` | Parsed header/data: 10 islands, 1,121,984 samples, 3,366,128 bytes; decoded height+ridge arrays ≈8.56 MiB; baked heights −60 to 439.2 m | This world is small enough to keep all canonical terrain heights resident. Streaming is optional, not the first architectural dependency. |
| `src/sea.jo` | 160 angular segments, camera-centered rings ending just below 22 km; displacement only within roughly 260 m; fragment swell/ripple/detail shading | The mesh has a real outer edge. At altitude, sky-colored pixels below that edge cannot recreate correct ocean geometry or occlusion. |
| `src/clouds.jo` | Many instanced opaque spheres; 34 km camera-centered wrap; edge puffs **shrink** from 72% to 97% of half-width | Visible disappearance and field boundary are designed into the vertex shader. Independent sphere normals expose the construction. |
| `src/sky.jo` | Screen triangle, directional gradient, sun/glow; below-horizon sea-color fill | A useful starting full-screen pass, but not a geometric horizon or altitude-dependent atmosphere. |
| `src/look.jo` | Common palette; `aerial()` uses distance and the lower endpoint altitude | Endpoint fog overestimates long low-altitude portions of a slanted path and is not a consistent optical-depth integral. |
| `aegean.jo`, `src/pilot.jo` | 30 km far; near 1 m free camera, 0.5 m chase, 0.3 m walking; clouds opaque; sea/wakes transparent with depth writes off | Increasing far alone fixes neither precision nor compositing. Low clouds must also occlude the sea correctly from above. |

The working tree already contains unrelated edits, including `src/sky.jo`; the design is based on the files as observed, not an assumption of a clean checkout.

### Sloppy capabilities and actual gaps

Inspected `~/dev/slop-lang/docs/API.md` (“3D”, “GPU programs”, “GPU buffers and compute”), `docs/GRAPHICS.md`, and the relevant implementation files under `lib/game/` and `compiler/`.

Available today: custom Sloppy vertex/fragment shaders, fixed loops/arrays, instancing, persistent instance buffers, `sample`, `sample_lod`, `texel`, derivatives through `fwidth`, offscreen color targets, CPU access to baked data, and explicit depth/blend state. GPU buffers are usable from shaders; compute/indirect operations have CPU fallbacks outside Vulkan. **Do not make per-frame density generation or GPU terrain selection depend on compute under WebGL.**

Important implementation facts:

- `texture(Image)` allocates RGBA8, sets nearest/linear filtering, and creates **no mip chain**. `sample_lod()` being documented does not make missing mip levels exist. `glGenerateMipmap()` currently returns immediately on Vulkan. Prefer explicit packed level atlases initially, or add a real cross-backend mip API.
- `render_target()` creates an RGBA8 texture and a D24 **renderbuffer**. Its `depth` integer is not a sampleable `Texture`. There is a separate internal depth-texture helper for shadows; no public main-scene-depth accessor was found.
- Shader fragment functions return one `vec4`. MRT outputs and a fragment-depth builtin are not documented/exposed in that shader interface. These are engine work, not game shader calls that can simply be written today.
- Vulkan uses D32 float internally, but the shader compiler currently transforms the returned GL-style clip position with **`z_vk = (z_gl + w) / 2`**. A proper native zero-to-one reversed-Z path must also address that conversion; changing only the projection matrix is insufficient.
- The default 3D pass restores `LEQUAL`, clears depth, and handles transparents itself. An explicit world-pass sequence is needed for split frusta and cloud composition; callback ordering alone is brittle.
- Public shader textures are 2D. WebGL2 supports 3D textures and MRT, but this does not imply Sloppy exposes them. A 2D slice atlas is an immediately understandable portable representation. [WebGL2 specification](https://registry.khronos.org/webgl/specs/2.0.0/)

Required engine capabilities are identified in milestone F1 below. There is a functional RGBA8/two-pass route; higher quality adds float targets/MRT where supported. Float **color rendering** is an extension capability, separate from ordinary float texture sampling. [EXT_color_buffer_float](https://registry.khronos.org/webgl/extensions/EXT_color_buffer_float/)

## 2. KSA: documented facts, transferable principles, and unknowns

**Direct developer evidence:** Dean Hall’s official Year One recap describes “spherical billboarding”: prebuilt libraries of subdivided spheres, concentrated subdivision near a reference vertex for close views and more uniform subdivision at distance. The reference vertex follows the viewer with snapping to prevent vertex swimming. It also describes procedural terrain/erosion work by Linx and Blackrack and changes toward bindless rendering. This is actual displaced sphere geometry, not evidence that the planet is merely a textured camera-facing quad. The forum version is dated 30 October 2025; the news mirror has a later date. [Official developer recap](https://forums.ahwoo.com/forums/kitten-space-agency/developer-updates/development-recap-one-year-one.75/)

The released BRUTAL framework is explicitly a foundation without a game renderer. Its public source is therefore not a public implementation of KSA’s complete terrain, cloud, or atmosphere algorithms. [BRUTAL source and scope](https://github.com/ahwootech/BRUTAL)

An earlier **direct post by Dean Hall** supplies useful precision detail: position values use doubles, rendering uses floats, and the camera renders at the origin. It also describes selecting among prebuilt XML-configured spherical meshes as the observer approaches a planet, with data retained on the GPU. This supports a camera-relative rendering recommendation; it does not reveal every detail of the current origin/rebasing or mesh-transition implementation. [Developer’s seamless-terrain explanation](https://www.reddit.com/r/KerbalSpaceProgram/comments/1gg5106/ksa_the_ksp_replacement_from_rocketwerkz_seamless/)

KSA developer communications establish that Blackrack built atmospheric scattering for the game. However, the December 2024 statement available in this search is a **community transcription of a Discord update**, not an independently inspected official shader or technical paper. It corroborates the intent, not a particular scattering algorithm. [Transcribed developer update](https://www.reddit.com/r/kittenspaceagency/comments/1hfxfel/20241216_development_update_from_dean/)

**What is not established:** the exact current terrain selection algorithm, patch sizes, LUT dimensions, cloud step counts, reversed-Z implementation, detailed origin/rebasing scheme, and hardware cost. Do not label ordinary CDLOD, Bruneton scattering, a particular rebasing algorithm, or a particular cloud renderer “what KSA uses” without stronger evidence. Early reverse-depth reports exist as community-relayed updates, but are not enough to describe the current implementation.

**Our inference:** stable, camera-adaptive geometry plus consistent light transport is the important lesson. A closely relevant published precedent is Michelic et al.’s persistent projected planetary grid and integrated terrain/ocean/cloud/atmosphere work; it explicitly addresses continuity from ground to space. It is a useful research reference, **not evidence of KSA’s undisclosed implementation**. [TU Wien research abstract](https://www.cg.tuwien.ac.at/research/publications/2019/kerbl_2019_planet_poster/)

## 3. Long-range technique selection

| Technique | What it buys | Fit here |
|---|---|---|
| CDLOD | Fixed regular grids selected through a quadtree; vertex morphing tied to distance; carefully coordinated ranges avoid stitching | Strong reference. Pure distance bands are predictable but may retain unnecessary detail on flat islands while underserving cliff error unless calibrated conservatively. [Author’s paper/code](https://github.com/fstrugar/CDLOD) |
| Geometry clipmaps | Nested, viewer-centered grids; incremental data updates and blended boundaries | Excellent for broadly continuous terrain and ocean. More complex coverage and empty-water handling for a handful of separated islands. [Original GPU Gems chapter](https://developer.nvidia.com/gpugems/gpugems2/part-i-geometric-complexity/chapter-2-terrain-rendering-using-gpu-based-geometry) |
| Chunked/geomipmapped terrain | Independent error bounds, frustum culling, easy baked data; skirts or stitching close edges | **Recommended**, with geometric morphing, shared-edge rules, and 2:1 balancing. Slightly more boundary machinery than pure CDLOD, but useful control of cliffs and tiny islands. [Ulrich’s original chunked-LOD work](https://tulrich.com/geekstuff/chunklod.html) |
| Skirts alone | Cheap crack concealment | Good temporary debug safeguard below seabed. Visible vertical curtains at silhouettes and transparent shores make them unsuitable as the seam solution. |
| GPU-driven patches / indirect draws | Lower CPU submission cost with large worlds | Vulkan enhancement later. WebGL CPU compute fallback and this small world make it a poor initial dependency. No mesh/tessellation shader baseline. |
| Distant terrain impostors | Very cheap very distant scenery | Optional for tiny buildings/trees. Keep island topography as coarse geometry: it is inexpensive and preserves moving silhouettes/parallax. Never substitute an unrelated island panorama. |
| Reversed-Z | Excellent large-range precision with float depth and zero-to-one projection | Preferred Vulkan path and capable WebGL path; needs renderer changes and a portable fallback. |
| Logarithmic depth | Nearly uniform relative precision over huge ratios | Viable portable alternative, but requires fragment-depth output for correct large triangles and may reduce early-depth efficiency. [Outerra implementation notes](https://outerra.blogspot.com/2013/07/logarithmic-depth-buffer-optimizations.html) |

The recommendation is a **chunked terrain design informed by CDLOD**, not a claim that adding arbitrary per-patch morph values to CDLOD preserves its crack-free proof. The edge constraints below are explicit because they are needed when using local screen-error selection.

### 3.1 Coordinates, horizon, and curvature

Keep simulation and collision in the existing flat island coordinates for this overhaul. Introduce a render transform, shared by terrain, water, objects, cloud sampling, and shadows. Use Earth radius `R = 6,371,000 m` as the initial art setting, not a tiny globe that makes the archipelago visibly bend.

For a camera-centered local tangent chart, the short-range approximation is:

```text
q = world_position - camera_position             // subtraction before GPU f32 conversion
drop(q.xz) ≈ dot(q.xz,q.xz) / (2 R)
render_q = (q.x, q.y - drop(q.xz), q.z)
```

This is a **render-space approximation**, not spherical physics. Use it consistently and regard the current camera as the tangent anchor. Local vertical directions vary with position by approximately `(x/R, 1, z/R)`; use the corresponding tangent basis for normals and directional lighting. For cloud rays, evaluate density through the inverse chart: given rendered ray point `(x,y,z)`, sample the flat cloud field at approximately `(x, y + drop(xz), z)`, with the camera’s absolute altitude restored. Never bend cloud positions but march an unrelated flat slab.

For the analytic sea horizon and atmospheric altitude integration, use a spherical model, evaluated stably in camera-local coordinates. At altitude `h`, ray/sphere coefficients can avoid subtracting two squared Earth radii:

```text
a = dot(d,d)
b = (R+h) * d.y
c = h*(2*R+h)
solve a*t² + 2*b*t + c = 0
```

Choose the nearest positive ocean intersection; use a cancellation-resistant quadratic root calculation near tangency. Prefer km units for atmosphere math. The parabolic chart error must be compared against the sphere at the horizon; if it causes >1 pixel mismatch, use the spherical chart for all distant passes, not a hand-tuned horizon line. At 100 km the leading parabolic drop is about 785 m; at 22 km it is about 38 m, so curvature cannot be applied only to water.

For a stable render origin, use `f64`/integer CPU world coordinates and a 1,024 m snapped horizontal origin. Upload patch origin minus render origin and camera minus render origin separately. Keep shader procedural phases stable through integer cell IDs or origin-modulo-period offsets. Do not first put huge absolute positions in a `vec3` and then subtract; the precision is already lost. Existing simulation uses `vec3` positions, so this is initially a rendering precision improvement; migrating simulation coordinates can wait until the playable area warrants it.

Horizon distance to sea level is `sqrt(2Rh+h²)` (straight-line distance; close to surface distance at these heights):

| Camera altitude | Sea horizon |
|---:|---:|
| 2 m | 5.05 km |
| 10 m | 11.29 km |
| 100 m | 35.70 km |
| 1,500 m | 138.26 km |
| 5,000 m | 252.46 km |

Elevated terrain/cloud visibility is approximately the sum of the observer and feature horizon distances. A 2 km cloud top viewed from 1.5 km can be visible at roughly 298 km in clear air. Thus “100 km view” means assured readable content to that distance, not deleting everything at 100 km. Choose cloud integration limits from opacity/atmospheric contrast and geometry, with conservative coverage beyond that point.

### 3.2 Terrain data and selection

Keep the current 8 m bake as canonical data. Add a versioned render bake containing a per-island hierarchy. Pad each island domain to leaf-patch boundaries, including enough seabed for safe edge removal; do not make a 22 km square of dense terrain.

Proposed structures (logical fields, not an imposed Sloppy ABI):

```text
TerrainIsland:
    grid_origin_f64, canonical_spacing, atlas_rect, root_ids[]
TerrainNode:
    island_id, integer_grid_origin_xz, level
    child[4] / leaf flag
    min_height, max_height
    max_error_to_parent, max_error_to_canonical
    shore_flag, material_range
TerrainDraw:
    node_id, origin_relative_to_camera, spacing
    morph_alpha, edge_mode_bits, neighbor_morph_data
    height_rect, normal_rect, material_rect
```

Use a **33×33 vertex / 32×32 cell patch**: 2,048 triangles before stitching. Base spacing 8 m gives a 256 m patch; successive levels use 16/32/64/128/256 m spacing. Keep integer grid alignment and the same b–c triangle diagonal across every level. During migration, a 14 m-base compatibility mode can retain the current visible surface until props/collision are re-grounded; 8 m is an explicit content change, not an accidental side effect.

Compute node error offline by comparing the canonical surface with the actual candidate coarse **triangulated** surface, not an averaged mip or bounding-box range. Include cliff/shore errors and conservatively bound between sample points. Parent heights are nested source samples: an unconstrained average height mip changes shared vertices and shorelines. Store separately filtered normal/material levels for shading.

Each frame, walk CPU nodes and frustum-cull against height-aware bounds, conservatively bent for curvature. Select using:

```text
focal_px = viewport_height / (2*tan(vertical_fov/2))
error_px ≈ max_error * focal_px / max(distance_to_node_bounds, near)
```

Start with split above 2 px, merge below 1 px, and evaluate 1–1.5 px as the desired settled error. At grazing views or with large vertical displacement relative to distance, use a conservative projected-error calculation rather than treating this approximation as a proof. Use actual full-resolution viewport dimensions even when clouds render smaller.

Balance selected neighbors to differ by at most one level; retain coarse ancestors while finer data is unavailable. A hard draw budget may raise the allowed error gradually, but must never reveal holes. Keep tiny islands that contribute a visible silhouette: a coarse node need not be replaced by water just because its area is small.

### 3.3 Morphing and edge agreement

For fine vertex `(x,z)`, let `Hf` be its source height and `Hp(x,z)` its parent triangle height. With local parent-cell coordinates `u,v` and corners `a,b,c,d`:

```text
if u+v <= 1: Hp = a + u*(b-a) + v*(c-a)
else:        Hp = d + (1-u)*(c-d) + (1-v)*(b-d)
H = mix(Hf, Hp, alpha)                // alpha 0=fine, 1=parent
```

This design morphs heights without moving horizontal positions. At `alpha=1`, children lie exactly on the parent's triangles. New child groups appear fully parent-shaped, then reveal fine detail over about 0.2–0.35 s; merging reverses the process. Keep all four children ready before retiring the parent. Do not independently crossfade opaque parent and child meshes: it causes depth fighting and doubled shorelines.

An explicit boundary contract makes this work:

1. Keep 16 precomputed edge-stitch index patterns for the combinations of four coarse neighbors. On a coarse-facing edge, triangles use the shared even vertices; fine odd edge vertices are not boundary vertices of the rendered mesh.
2. Shared vertices on same-level edges use the **same morph state**, derived from a shared edge record. For example, use the larger parent-morph alpha of the two patches and ease the constraint into the first two interior rows. Use shared corner records as well.
3. A fine/coarse boundary’s even vertex height is the coarse neighbor's **currently rendered height**, including that neighbor's own parent morph and boundary constraints. Copying its unmorphed height is wrong during simultaneous transitions. Evaluate constraints from coarsest to finest; a common corner is owned by the coarsest incident representation.
4. Restrict topology swaps to times when the outgoing and incoming surfaces agree. Shared-edge/corner records persist across the swap. Keep parent/child transition groups and adjacent constraints synchronized; do not reuse a patch slot while neighbors still reference it.
5. Interpolate filtered normals/materials continuously too. Use the geometric normal for coast/cliff classification where necessary; blend appearance at the same transition state so geometry does not stay continuous while vegetation bands pop.

This is more boundary bookkeeping than unmodified distance-based CDLOD, but it gives a testable equality: **the two sides of every shared edge evaluate identical positions**. Skirts can temporarily sit below the seabed to catch bugs; no visible seam may rely on them.

Grounded props need a stable nearby surface. Force maximum detail in a modest radius around walking/landing activity (initially 350–500 m), use the same triangle evaluator for collision/placement, and migrate every `surface_height()` caller before enabling the new base grid. Do not make collision follow distant camera LOD.

### 3.4 Portable implementation and budgets

Upload one reusable grid/stitch family plus selected patch parameters. Height sampling can use an RGBA8 atlas: two channels encode a 16-bit height, one ridge, one material/flags. Decode with a fixed global scale or agreed border-compatible scale. With linear filtering, decode the weighted channel values **without rounding each byte**; linear decode commutes with interpolation. Use exact texel lookup for canonical corner values where needed. Add gutters and explicit texel-center addressing.

Read categorical material/flag values with nearest/texel access; only continuous fields such as height and ridge use interpolated decoding. Parent height sampling uses the stated triangle interpolation rather than an ordinary bilinear four-corner filter.

Alternatively bake `Hf`, `Hp`, normals, and tint into cached patch VBOs; this uses more memory but avoids extra vertex texture fetches. Make that a measured implementation choice. Do not rebuild visible terrain meshes or erode terrain every frame. For WebGL, start with ordinary CPU culling and batched `draw_instanced`; group by island/atlas/stitch mode. Fixed arrays for a small number of edge values are safer than large uniform tables exceeding device limits.

Initial ceilings, to tune after measurement:

| Resource | Terrain target |
|---|---:|
| Visible patches | Typically 40–100; soft cap 128; allow a documented cliff-view exception |
| Triangles | 80k–205k typical; 262k at 128 full patches |
| Submission | Prefer <100 draws, hard investigation threshold 160 |
| CPU selection + parameter preparation | <0.5 ms p95 on the target laptop |
| GPU terrain, including its material shading | 1–2 ms at 1280×720 target |
| Incremental GPU memory | 24–48 MiB, depending on cached vertices vs atlas |
| Additional CPU terrain data | <16 MiB over existing world data |
| Normal-frame uploads | <64 KiB patch data; exceptional cache upload ≤256 KiB/frame |

An entire 2048² RGBA8 height atlas is 16 MiB even if only 1.12 million source texels are useful. Pack carefully; do not quote source height bytes as actual GPU allocation. A smaller normal/material atlas or explicit coarser levels avoids another unnecessary pair of 16 MiB textures. Root data can remain resident; bounded refinement uploads make recovery after teleports predictable.

### 3.5 Ocean continuity

Keep the near swell system initially, but replace its outer boundary with an explicitly shared ocean surface.

- Render a near/middle curved ring mesh out to at least 8–16 km, with enough angular/radial samples that curvature interpolation stays below one screen pixel. Its center follows a snapped chart origin; world wave phase does not snap.
- Render the **far ocean analytically** by ray/sphere intersection in the sky/background pass, all the way to the geometric horizon. Shade it with the same sun, sky/atmosphere, Fresnel convention, and far roughness. It provides real surface distance for occlusion/cloud clipping, not merely a dark color below screen center.
- In the overlap, the mesh must converge to the same sphere. Fade actual displacement to zero before handing over; blend residual normal variance/material detail rather than the whole ocean color. The existing near displacement already dies out around 260 m, making this easier.
- Make the ocean opaque away from the shore, writing its effective distance. Composite shallow water against the seabed where needed; record the water surface as the atmospheric/cloud endpoint. A fully transparent sea pass over completed clouds is wrong when viewed from above.
- Derive wave/ripple filtering from projected footprint, retaining normal **variance** as unresolved waves disappear. Simply dropping all distant normal variation makes a visible roughness ring and overbright specular horizon. Filter the material’s glitter/strokes too.
- Sample depth-map exterior as deep sea, and fade depth-driven color using seabed depth, not the rectangular map border. The current 24 km depth map must not become a far-water color rectangle.

The analytic ocean needs fragment depth only if it participates in the raster depth buffer. In the initial split-frustum design it can instead supply background color plus a separate encoded surface-distance target; actual island/aircraft geometry overlays it, and the cloud pass clamps against the nearest effective endpoint. Validate overlap and coastline ordering explicitly.

### 3.6 Depth precision: a portable plan

Forward D24 perspective precision is approximately `delta_z = z² / (near*(2^24−1))` when far is much larger than near. For near 0.5 m it is about 0.12 m at 1 km, 11.9 m at 10 km, 298 m at 50 km, and 1.19 km at 100 km. Moving the far plane out does not fix that distribution. Floating-point position precision and depth-buffer precision are separate problems.

**Preferred path:** reversed-Z with a D32 float attachment and native `[0,1]` clip space. Clear depth to zero, use `GREATER/GEQUAL`, update sky depth, all reconstruction helpers, shadow conventions where appropriate, and compiler/backend clip conversions. Leave conventional shadow maps conventional unless there is a reason to migrate them. Do not expect reversing a fixed D24 buffer to add precision. [NVIDIA depth analysis](https://developer.nvidia.com/blog/visualizing-depth-precision/)

WebGL can optionally expose `EXT_clip_control`; test it rather than assuming it is universally absent or universally present. A D32F target plus zero-to-one clip control can use the preferred route. Without those capabilities use the baseline below. [Khronos clip-control extension](https://registry.khronos.org/webgl/extensions/EXT_clip_control/)

**Portable baseline:** two depth frusta, rendered far to near into one world color/distance result:

1. Far geometry with `near=2048 m`, `far >=180000 m` at the current altitude; adjust far with coverage.
2. Clear raster depth only; preserve world color and encoded effective distance.
3. Near geometry with `near=0.3–0.5 m`, `far=2048 m`.
4. Clip consistently at the same view-space plane; submit intersecting nodes to both. Both passes use identical world-space material/atmosphere parameters. Do not bake separate color palettes/fog per frustum.
5. Composite clouds only after the final opaque/water endpoints are known. Keep transparent wakes and particles in the correct partition or use the combined distance explicitly; they cannot test against the near-only depth buffer for far occlusion.

At 100 km, D24 with near 2048 m has about 0.29 m depth steps, adequate for a distant island/water silhouette. Depth crossing the partition requires dedicated tests. This costs extra submission for crossing objects and explicit pass control, but preserves ordinary early-depth tests and does not require custom fragment depth.

If two-frustum complexity proves worse, add a cross-backend fragment-depth builtin and use `Dlog=log2(1+C*z)/log2(1+C*far)` (`C≈1 m⁻¹` as a starting choice). For 180 km far, D24’s log quantization is roughly 7 cm at 100 km. Interpolate linear view depth to the fragment and write it there; vertex-only logarithmic depth produces incorrect interpolation on large triangles. All participating shaders must agree. Benchmark the potential early-Z loss before choosing it over split frusta.

### 3.7 Shared atmosphere and aerial perspective

Use one `AtmosphereState` with planet radius, observer altitude, Rayleigh/Mie density profiles, sun direction/radiance, exposure, artist palette, and weather haze. Use physical transport to join distances; use artist-controlled colors to achieve the film palette. The `Light` struct remains the artistic interface, but its fog/sky fields must no longer describe independent incompatible worlds.

First replace endpoint fog with the analytic integral of exponential height density along a straight local ray:

```text
rho(y) = exp(-y/H)
tau = beta0 * exp(-y0/H) * s * (1-exp(-k))/k
k = dy/H
T = exp(-tau)
```

Use a series near `k=0`: `(1-exp(-k))/k ≈ 1-k/2+k²/6`. Clamp/segment below-sea portions appropriately. This is a local validation/reference model, not enough for sunset, curvature, or a 150 km grazing ray.

The destination is a compact **Hillaire-style atmosphere**, with sky-view/transmittance lookup tables and aerial-perspective integration. Start sizes for prototyping: 256×64 transmittance, 32×32 multiple-scattering, 192×108 sky-view, and 32×32×16 aerial perspective stored as a 2D slice atlas. Use logarithmic/nonlinear distance slices out to the full visible range; refine near the horizon as needed. Generate/update through fragment passes or bake parameterized tables, not CPU-fallback compute. These are proposed sizes, not claims about KSA or mandated paper values. [Hillaire paper and reference implementation](https://github.com/sebh/UnrealEngineSkyAtmosphere)

Bruneton’s implementation is a useful correctness reference and has a WebGL2 demo; it demonstrates that atmosphere scattering is not inherently desktop-only. Its full precomputation/interface need not be ported wholesale. [Bruneton implementation](https://ebruneton.github.io/precomputed_atmospheric_scattering/)

Every material uses the same transfer function:

```text
C_observed(s) = A(0,s) + T_air(0,s) * C_surface
```

Here `A` is integrated in-scattering, not just an arbitrary horizon tint. Sea reflections should use the same sky evaluator. Sunlight on clouds/terrain should share atmospheric sun extinction so sunset does not give a white midday cloud in an orange sky. Keep all transport in linear color; convert swatches to linear, apply tone mapping once at the end, and audit existing shader/post-effect assumptions before tuning palette values.

Atmosphere may reduce distant contrast, but it must not be used to conceal a defective geometric join at a fixed radius. In a clear high-altitude debug mode, the geometry must still join.

## 4. Cloud art analysis and technique survey

### What the supplied images actually require

`user_ref_3.png` and `porco-rosso-1661-x-900-wallpaper-6oxyq7nadjhf3yhv.jpg` show cathedral-scale connected heaps: deep cool bodies with selective warm edge light. `user_ref_4.png` and `porco007.jpg` require sunset layers, purple/slate shadow masses, and narrow gold openings. The low-water flight frames show separate distant cumulus groups, but those groups share a flat condensation level and belong to a sprawling cloudscape. The large foreground cloud in `...-nrfrruzockymwms4.jpg` is a strong silhouette/scale reference.

Key constraints:

- Three scales: 1–6 km formations, 150–800 m lobes, and restrained roughly 10–80 m painted edge breakup. Do not fill the screen with equally sized puffs.
- Tops are warm cream; sides and interiors form **large slate-blue/violet shadow shapes**. Two-tone means organized value masses, not literal hard posterization at every density sample.
- Bases are broadly flat and darker, with a thin irregular edge. A dark smooth sphere underside is not the same silhouette.
- Interior variation is broad and low contrast. Bright rims are selective and illumination-driven, not a glowing outline around every cloud.
- Atmospheric depth compresses distant contrast and detail without changing the identity of a formation. At sunset, thin transmitted edges warm before dense interiors do.
- Painted texture belongs to the advected cloud field; screen-space grain may be a subtle finishing pass, but it must not replace form or boil under a moving camera.

### Survey and decision

| Approach | Evidence / strength | Limitation for this game |
|---|---|---|
| Opaque cloud masses rendered offscreen, then blurred/distorted | **Sea of Thieves shipped this.** Rare describes per-vertex illumination, reduced-resolution filtering, depth-assisted composite, and distortion. Strong artistic control and integrated-GPU intent. [Rare SIGGRAPH paper](https://history.siggraph.org/wp-content/uploads/2022/09/2018-Talks-Ang_The-Technical-Art-of-Sea-of-Thieves.pdf) | Excellent cheaper candidate, but surface meshes need substantial additional work for interior flight and cloud/aircraft intersection. Their wrap strategy should not be copied into an altitude sandbox unchanged. |
| Raymarched volumetric density | Natural overlap, self-occlusion, view from above/below, and fly-through. Nubis established production authoring; later work explicitly addresses fly-through cost and temporal artifacts. [Guerrilla 2017](https://www.guerrilla-games.com/read/nubis-authoring-real-time-volumetric-cloudscapes-with-the-decima-engine), [Guerrilla 2022](https://www.guerrilla-games.com/read/nubis-evolved) | **Recommended core**, heavily simplified/stylized. Those console costs do not establish a WebGL laptop budget. |
| Analytic SDF/metaball clouds | Good mass authoring and smooth union; can create flattened bases and nested lobes | Treat as an offline/limited local density authoring tool. Looping over hundreds of spheres per ray sample is prohibitive. A density field is not necessarily a safe sphere-tracing distance bound. |
| Layered/depth impostor billboards | Very cheap distant imagery, potentially attractive painted appearance | Parallax, ordering, fly-through, above-cloud views, and relighting are weak points. Use only for very distant subpixel structure or a clearly labeled low tier, from the **same source field**. |
| Cloud maps / 2.5D height profiles with screen-space shading | Cheap macro coverage and controllable silhouettes | Good input data and far approximation. A flat sky map alone fails when the plane enters or rises above a tall cumulus. |
| Ghibli-style texture/mesh/sky demos | Kids With Sticks describes painted backgrounds and a textured animated sky; Lightning Boy Studio demonstrates authored Ghibli cloud forms. [Developer art breakdown](https://kidswithsticks.com/creating-stylized-art-inspired-by-ghibli-using-unreal-engine-4/), [artist tutorial](https://www.youtube.com/watch?v=RgRPUlFBHH4) | Valuable art workflows, not evidence of full unrestricted flight or measured 3–5 ms WebGL rendering. |
| Stylized browser/Godot raymarch demos | Demonstrate palette shaping, volume rendering, and reduced resolution. [Maxime Heckel’s runnable explanation](https://blog.maximeheckel.com/posts/real-time-cloudscapes-with-volumetric-raymarching/), [Godot stylized shader](https://gameidea.org/2025/01/22/making-a-stylized-sky-shader-with-volumetric-clouds/) | Useful study examples, not a complete engine architecture. In particular, sky-plane division by `ray.y` is not a robust horizon or inside-cloud solution. |
| Genshin | Primary GDC session discusses crafting an anime open world. [miHoYo GDC presentation listing](https://gdcvault.com/play/1027539/-Genshin-Impact-Crafting-an) | Use as an art-direction comparison. I could not verify an exact current cloud shader from an accessible primary technical source; do not copy community guesses as a proven shipped pipeline. |

The selected volume renderer can still borrow Rare’s **image-level cohesion**: controlled filtering, shared mass lighting, and subtle distortion. It should not preserve the current ~23k independently shaded sphere surfaces underneath a blur and declare the overhaul complete.

## 5. Concrete cloud pipeline

### 5.1 Data: one advected world field

Use a deterministic world seed, an absolute wind displacement, and a common weather snapshot. The rendering field is an appearance representation, separate from detailed weather simulation. Cloud samples and sea shadows consume the same snapshot/time.

```text
CloudState:
    seed, wind_displacement_f64, evolution_time
    weather_origin/cell_scale, weather_texture, weather_level_rects[]
    shape_atlas, detail_atlas, palette/ramp_texture
    base_height_range, top_height_range, extinction_m_inv
CloudHistory:
    color_and_transmittance
    first_hit_distance, representative_distance, validity
    previous_camera_basis/origin, previous_wind_displacement, previous_time
```

Initial portable assets:

- A **2048² RGBA8 macro weather map over a 256 km square**: about 125 m/texel. Channels carry coverage/mass, base height, top height/thickness, and type/evolution control. Use smoothly connected authored bands and tall formations, not an independent random cloud at every texel. Outside this authored domain, deterministic coarse weather tiles continue the field; no camera-centered destructive wrap. At the 100 km viewing specification, distant micro-lobes need not all be explicitly painted into this map.
- Explicit filtered levels of weather/optical coverage, and a separate conservative occupancy hierarchy. Average density/coverage is for appearance; maximum coverage/height bounds are for skipping. Confusing the two either deletes thin clouds or prevents useful skips.
- A **64³ RGBA8 base-shape/noise volume**, stored in an 8×8 2D slice atlas with one-texel gutters: density/form plus a low-frequency gradient or shape controls. Add a 32³ detail volume. These cost roughly 1.2 MiB including gutters before variants. Choose broad cellular lobes and domain warping; avoid procedural multi-octave hash noise inside every ray step.
- Optional 2–4 authored local SDF/density stamps for hero towering cumulus, baked from smooth unions of ellipsoids/hand-shaped volumes. Reserve at most about 4 MiB initially. A tile/stamp index selects one candidate or a small fixed set; do not scan every formation at every sample. Bake connected formations where possible.
- Artist lighting ramps and masks. Store spatial form, not a fixed noon-color cloud sprite; sunset must relight correctly.

A slice-atlas sample uses two bilinear 2D fetches and interpolation between the neighboring z slices. Index the slice and UV rectangle explicitly. Clamp at the interior texel centers; gutters prevent adjacent-slice bleed. Ordinary hardware atlas mips are unsafe unless packed/guttered per level. All level rectangles are explicit so Vulkan’s missing auto-mipmap path does not silently change the cloud silhouette.

World position sampling uses `p_cloud = world_p - wind_displacement`; keep both terms precise with integer tile IDs plus local coordinates. Tile regeneration/promotion preserves density on shared borders. Slow evolution moves/deforms internal lobes coherently; it does not reseed the field when the camera moves. Let condensation height vary slowly by formation, approximately 600–900 m initially, with 1–3 km ordinary tops and a few taller authored masses. The aircraft’s possible 1,500 m flight is therefore **inside and above some clouds**, not always below a ceiling.

### 5.2 Density and painted form

One useful starting density model, to be art-directed rather than treated as physical meteorology:

```text
W = sample_weather(p_cloud.xz)
b = decode_base(W.g)
t = max(b + minimum_thickness, decode_top(W.b))
u = (height_above_curved_sea(p) - b) / (t-b)
P = smoothstep(0, base_feather/(t-b), u)
    * (1 - smoothstep(top_start(type), 1, u))
B = low_frequency_shape(p_cloud, type)       // texture samples, not dozens of sine hashes
q = saturate((B - (1-W.r)) / max(W.r, epsilon))
rho0 = q * P
rho = max(0, rho0 - detail_amplitude * detail(p_cloud) * edge_weight(rho0))
sigma_c = extinction_m_inv * rho
```

Set density to zero outside the height interval. Base feather of roughly 10–30 m gives a largely flat base rather than a diffuse kilometer-thick underside. Add clustered top lobes and overhangs through the base shape/hero volume, not just a global flat `P(u)`. This formula is a starting profile, not proof that random noise plus a ramp will match the references.

Preserve a low-frequency macro field and add details as a residual. As sample footprint grows, fade/filter the residual while keeping macro coverage and total optical depth. Never morph an entire near formation into an unrelated far texture. Account for opacity nonlinearity: average transmittance or calibrated optical-depth statistics is preferable to a mip chain that simply averages a binary density threshold.

### 5.3 Render passes and order

1. **World surfaces/background:** render sky, analytic distant sea, island terrain, objects/aircraft, and near/shallow sea in their explicit passes. Produce final world color and an effective nearest **ray distance** `s_scene`. It must include the water surface; cockpit/aircraft must be represented. With MRT this can be simultaneous; without it, a distance-only geometry pass is a valid more expensive fallback.
2. **Cloud visibility/distance reduction:** conservatively reduce scene distance to cloud resolution, keeping min/max/edge information. A plain bilinear average lets clouds leak across wings and coastlines. Do not sample a depth attachment while it is attached for writing.
3. **Cloud march:** full-screen triangle, low resolution, fixed bounded loops. Reconstruct rays from camera basis/FOV (avoids an ill-conditioned inverse of a huge-range projection). Intersect the curved cloud layer/height bounds and clamp to `s_scene`; handle zero, one, or two shell intervals and cameras already inside the layer. Output cloud radiance/transmittance and first/representative distances.
4. **Temporal reconstruction:** reproject in world/cloud space using representative distance, previous camera transform, and wind displacement. Clamp history to a current neighborhood; reject on depth, coverage, sun/weather changes, camera cuts, and origin resets. Newly exposed pixels get current samples. Use first-hit depth to protect edges; weighted depth alone causes halos.
5. **Full-resolution bilateral reconstruction/composite:** use full-resolution scene endpoints to choose valid low-resolution neighbors. Thin geometry must occlude clouds; avoid taking a nearby cockpit depth and erasing a whole low-res sky pixel. Use a small edge refinement mask/current extra samples at strong silhouette disagreement if necessary.
6. **Correctly ordered transparent effects:** cloud-attenuate particles/wakes according to their own depth, or render them into the surface result before volume integration as appropriate. Draw cockpit glass/HUD according to the intended visual convention. Tone map/grade once.

Use RGBA16F for cloud radiance+transmittance when supported and RG16F/encoded targets for auxiliary values. **Do not store raw 100 km distances in half-float:** its maximum is 65,504 and its precision becomes coarse much sooner. Encode `log2(1+s)` or normalized log distance, with consistent decode; use RGBA8 packing where float color targets are unavailable. A portable one-color-output version can do an auxiliary pass, but repeating the whole march twice is a significant cost; MRT support is the preferred small compiler extension.

### 5.4 Marching, horizon, and work bounds

Use front-to-back integration with physical lengths in meters:

```text
alpha_i = 1 - exp(-sigma_c_i * ds_i)
L_cloud += T_cloud * alpha_i * source_color_i
T_cloud *= 1-alpha_i
```

Early-out when remaining cloud transmittance is below about 0.01. Jitter the first sample with blue noise and a deterministic frame phase; do not independently jitter formation identity. Bounds/occupancy skips must be conservative with respect to detail and animation.

Initial spatial resolution: **1/3 of each output dimension at 1280×720** (about 427×240), **1/4 at 1920×1080** (480×270), with temporal reconstruction. This is roughly 11% or 6.25% of output pixels, respectively; “quarter resolution” must always specify whether it means dimensions or pixel count. Try half dimensions only on a faster tier.

Start with 32 integration samples plus bounded occupancy traversal; high quality 48–64. Use small metric steps near visible boundaries and footprint-dependent steps in the distance. Intersect occupied macro columns/tiles and skip empty ranges; a uniform 100 km/32-step march simply misses clouds. Near-surface steps should be roughly 20–60 m, with optional refinement at the first opacity rise; farther sampling can grow with projected footprint.

**A necessary bound:** 32–64 samples cannot resolve every disconnected 20 m feature along a 100 km ray. Use a hierarchical interval representation that merges only subpixel/low-contrast structure, and integrate far residual optical depth rather than silently stopping when the loop ends. Separate the occupancy traversal budget (initially ≤48 cheap hierarchy visits) from the expensive density budget. If significant, resolvable cloud structure remains beyond either budget, mark overflow in a debug view and refine/reuse valid far history; do not make the remaining sky empty. If overflow is common, the chosen density/traversal scheme has failed its prototype gate.

For the distant tail, allow a coarse **column/profile integral** of the same weather field once fine structure is below the pixel/contrast threshold. Use filtered optical coverage, the same base/top and light palette, and a smooth footprint-based blend of optical depth/source terms. An initial experiment may overlap detailed and coarse estimates over roughly 12–24 km, but **distance alone is not the production switch**: a giant hero cloud at 20 km may still require full form. Weighting must be a partition of unity over the same ray interval; do not alpha-blend two complete cloud images and double their opacity.

At and beyond the sea horizon, continue atmospheric/cloud geometry rather than pinning clouds to a screen band. A distant cloud below the curved planet is occluded; one with a high top may remain visible. Below the cloud layer, grazing rays can be extremely long; above it, downward rays must reveal upper cloud surfaces and terminate on islands/sea. These cases determine the data hierarchy, not just a pretty upward-looking test.

Do not initially add camera-facing cloud cards to save a weak marcher. If distant caching is needed after measurement, cache radiance **and transmittance plus distance** from the same field, reproject it, and refresh invalid tiles. It remains a sampling cache, not a second independent sky population.

### 5.5 Lighting: cream tops, slate sides, selective golden rims

Separate **transport/coverage** from **artistic source color**. Keep Beer–Lambert attenuation smooth; quantize/remap the lighting signal rather than density or final image luminance.

For the broad form, use a low-pass density gradient/author normal, not noisy detail gradients. A starting signal:

```text
n_form = normalize(-gradient_of_low_frequency_density)
under = smoothstep(b+20, b+180, local_height)
sun_visibility = exp(-tau_to_sun)
paint_signal = 0.65*dot(n_form, sun_dir) + 0.35*sun_visibility
lit = smoothstep(threshold-width, threshold+width, paint_signal + brush_bias)
lit *= mix(0.2, 1.0, under)
C_source = mix(C_slate, C_cream, lit)
```

Use a broad hand-tuned ramp; optionally add a third low-contrast transition color. Palette defaults should be sampled from the supplied reference **in linear working space**, then adjusted under the final exposure. `C_cream` responds to solar extinction/temperature; `C_slate` responds to sky fill and time-of-day, keeping some violet/blue identity instead of turning all cloud shadow orange at sunset.

For low cost, pre-bake gradients with shape data and approximate local self-shadow with a short 2–3-tap increasing-distance light probe, evaluated only at opacity-carrying samples (e.g. every fourth occupied step, interpolated between). Use a coarse global optical-depth/coverage lookup for larger-scale sun blocking. The expensive high tier may use more light steps. This is an approximation: do not advertise a fully accurate multiple-scattering solver under the proposed laptop budget.

Selective edge light can use a bounded forward-scattering term:

```text
mu = dot(ray_from_camera, sun_dir)    // looking toward sun => positive
HG(mu,g) = (1-g*g)/(4*pi*pow(1+g*g-2*g*mu,1.5))
rim = bounded_phase(mu) * thin_optical_depth_mask * sun_visibility
```

Start `g≈0.5–0.65`, strongly art-limit the amplitude, and add warm rim light only where the optical path is thin. A constant Fresnel rim on every lobe recreates the plastic puff look. Fill/multiple-scattering approximation keeps the interior blue rather than black; make its strength an art parameter.

Brush bias is a low-amplitude, cloud-space field with elongated/nonuniform features (tens of meters, slower than shape motion), not high-frequency speckle. Distort outlines by a small world-space amount, filtered by projected size. Preserve crisp large outlines; a global Gaussian blur cannot recover a painterly form from badly composed masses. Temporal validation must include fast banking so these features do not drag behind the camera.

### 5.6 Atmosphere/cloud composition without double fog

An unfogged cloud over an independently fogged sky/sea creates a join even with perfect geometry. Conversely, `L_cloud + T_cloud * already_fogged_background` incorrectly attenuates the air **in front** of the cloud.

Use ordered transfer segments. For air cumulative tables `A(s), Ta(s)`:

```text
T_air(a,b) = Ta(b)/Ta(a)
A_air(a,b) = (A(b)-A(a))/Ta(a)
combine((L1,T1),(L2,T2)) = (L1 + T1*L2, T1*T2)
```

Accumulate air and cloud segments along the ray, then the surface/background tail. Guard divisions when transmittance is already tiny; stop when contributions are negligible. Evaluate air at occupied interval boundaries and reuse it within short segments so atmospheric LUT cost does not multiply every density fetch unnecessarily. Thin-layer approximation is acceptable for a low tier but must be labeled as such.

For example, approximating a cloud as a layer at `s_c` over a background that already includes air gives:

```text
C = A(s_c) + Ta(s_c)*L_cloud + T_cloud*(C_background - A(s_c))
```

This retains foreground air and is much better than double fog, but fails for long distributed cloud intervals at sunset. The final tier should use interval segmentation and be tested against a slow reference integration. Terrain, sea, clouds, and sky all share the same atmosphere state and color pipeline.

### 5.7 Flying through clouds

The marcher starts at the eye if the eye is inside density; it must not discard the entire volume because the front surface is behind the near plane. Nearby cloud opacity naturally obscures the aircraft according to pixel depth. Stable noise and short near steps provide coherent motion without sphere interiors or billboard planes.

Treat the player’s eye and the visible plane independently: a chase camera outside a cloud can see the plane disappear into it; a camera inside should see local low-contrast extinction, not a white overlay abruptly switched by the plane position. Optional cockpit droplets/fog are a separate art decision, not necessary for this renderer.

Use geometric neighborhood density for gameplay/cloud-entry cues, but do not require the CPU to reproduce every fragment noise sample. A cheap macro-density query suffices unless gameplay explicitly depends on exact visibility. Ensure hidden cockpit details and near clipping do not make the cloud vanish as the camera crosses its base.

### 5.8 Cloud shadows on sea and islands

Render a low-resolution sun-space optical-depth shadow field from the same density/coverage, through fragment passes. Begin with two camera-relative, texel-snapped maps: **512² over 16 km** and **512² over 64 km**. Store optical depth, not fixed black color; use 4–8 vertical/light samples and a 5–10 Hz update, amortized if needed. Actual sun direction gives the lateral displacement: for a cloud point at height `h`, its flat-chart sea shadow is approximately `xz - sun.xz*h/sun.y`. Use curvature-aware intersections farther out.

Sea and terrain sample `T_sun=exp(-tau_shadow)`. Attenuate direct sunlight and glitter; retain sky fill. Do not multiply the final sea color uniformly black, since sky reflection survives cloud cover. Keep existing aircraft sea shadows separate, then combine their direct-light visibility with cloud visibility. Distant shadow detail fades to an averaged direct-light reduction with the same weather field, not to a sharp square border.

At low sun, `sun.y` approaches zero and shadow footprints become enormous. Clamp the local-map validity, use the coarse field for grazing rays, and smoothly reduce unreliable local detail. No enormous projection divisions, spinning dark bands, or map edge should appear at sunset. This shadow approximation does not include full cloud godrays; defer those until the main clouds pass the budget/art gates.

### 5.9 Cloud budgets and explicit quality tiers

Assume a quiet laptop in the `redfox` class (Intel UHD 620) as the **conservative validation machine**, and report a newer integrated GPU separately if available. Do not infer performance from the desktop GTX 1070. Browser, resolution, power state, host, and backend belong on every result. No timings were measured during this research.

| Component | Target GPU time at 720p output |
|---|---:|
| Reduced-resolution density/lighting | 2.2–3.2 ms |
| Temporal resolve + full-resolution edge-aware composite | 0.6–1.0 ms |
| Amortized cloud-shadow update + lookups | 0.2–0.4 ms |
| Total cloud subsystem | **3–5 ms**, p95; overflow/rapid-motion views included |

At 427×240 and 32 samples there are about **3.28 million density evaluations** if every ray uses its full budget; at 480×270 there are 4.15 million. Two atlas fetches for shape, one weather lookup, and detail/light probes can push this into tens of millions of texture fetches per frame. This is a real bandwidth/latency risk on UHD 620, not “only one screen quad.” Occupancy skips, early termination, detail gating, and limited light probes must earn their cost in measurements.

| Tier | Proposed behavior |
|---|---|
| Baseline portable | RGBA8 with encoded auxiliary values; roughly 1/3 dimensions at 720p / 1/4 at 1080p; 32 samples; conservative temporal history; cheap form light; coarse far optical integration |
| Enhanced | Float color targets + MRT; 48 samples; stronger local self-shadow; optional half dimensions if measured affordable |
| Emergency performance floor | Same macro field, fewer detail/light probes, lower cloud resolution, slower shadow updates. Keep horizon coverage, stable identity, fly-through, and scene occlusion intact. |
| Alternative architecture if volume gate fails | Connected baked density-isosurface meshes into offscreen color/depth with controlled painted filtering, plus local density extinction for entry; same macro field and distant placement. Budget a distinct fly-through validation effort. This is a scope/quality choice, not a free equivalent replacement. |

Cloud GPU allocation target: **32–48 MiB** including 16 MiB weather map, explicit coarse/occupancy levels, shape/detail/hero atlases, shadows, and history/auxiliary targets. Aim for <0.3 ms p95 CPU bookkeeping and no full-volume CPU regeneration per frame. A weather map is not re-uploaded every frame just to move the wind. Combined incremental world-rendering allocation should initially fit around **96 MiB**, with a hard investigation threshold of 128 MiB, excluding pre-existing game content and browser overhead. Account separately for the full-resolution scene color/distance attachments introduced by composition.

## 6. Implementation plan with acceptance gates

These are implementation chunks for a later coding task; none was implemented here. Effort ranges assume an engineer familiar with Sloppy and an artist/designer available for comparisons; they are planning estimates, not delivery promises. Each chunk should be reviewable independently. Total scope is several weeks, with performance/art prototypes deliberately placed before content-scale work.

### F0 — Baseline captures and bounded feasibility tests (0.5–1 day)

Owned future files: small renderer diagnostic harness/tool and capture configuration; read existing scene sources. Capture the current renderer at sea-level, 100 m, 750 m, 1,500 m, and an exploratory 5 km; noon and sunset; looking toward/away from sun; narrow and wide FOV; under/inside/above clouds.

Add counters for triangles, draw calls, patch selection, density evaluations, hierarchy visits, history rejection, and memory allocations. Use asynchronous GPU timer queries where available, discard disjoint results, and read results on subsequent frames without blocking. [Khronos timer extension](https://registry.khronos.org/webgl/extensions/EXT_disjoint_timer_query_webgl2/)

Acceptance: named reproducible camera paths and reference crops; median/p95 timings on quiet `redfox`, one timing job at a time; clear statement of hardware/backend/resolution. No desktop wall-clock/GPU timing claims. Limit test workers to the machine-wide policy. Do not run a visual app with display/audio enabled on the shared desktop.

### F1 — Explicit world render targets/pass contract (1–3 days)

Owned future areas: Sloppy `lib/game/draw3d.jo`, target/texture API, shader compiler outputs only as needed; game wrapper module. Keep unrelated engine features out of scope.

Implement sampleable or explicitly encoded world distance, offscreen target format selection, state restoration, and pre/post-surface hooks. Preferred: public MRT fragment output support. Fallback: color plus distance-only draw, with its extra cost measured. Add capability reporting for float color targets, depth format, optional zero-to-one clip control, and timer queries. Explicit atlas levels avoid making mips/3D textures prerequisites. Do not pretend `RenderTarget.depth` can already be sampled.

Acceptance: same simple geometry produces matching world distances on Vulkan/WebGL2; thin wing occludes a test volume; water endpoint works from above; resizing, target orientation, post effects, MSAA resolve, and context recreation are correct. Float extensions disabled still gives a valid RGBA8 image. No target samples itself while attached.

### L1 — Terrain hierarchy bake and canonical surface migration (1–2 days)

Owned: `src/world.jo`, `tools/bake.jo`, a new versioned bake asset/tool; placement callers audited. Preserve existing gameplay/world data formats where unrelated.

Build hierarchy, min/max/error/shore metadata, fixed grids, parent triangle samples, and byte/atlas validation. Start in 14 m compatibility mode if needed, then make 8 m surface migration explicit.

Acceptance: canonical samples match source bake within quantization; parent reconstruction matches its triangles; no border sampling outside a tile; grounded docks/buildings/vegetation and walking/landing queries agree with the chosen near surface. Bake mismatch fails visibly/degrades intentionally rather than invoking massive runtime erosion unnoticed.

### L2 — Selection, morphing, and constrained edges (2–4 days)

Owned: `src/terrain.jo` and a small terrain LOD module. Implement CPU selection, hysteresis, 2:1 balancing, ancestor retention, morph transitions, and shared-edge/corner records.

Acceptance: no holes or T-junction exposure with haze disabled and wireframe/contrasting sea; numeric boundary positions agree within 1 cm near the camera; no one-frame >1 px jump on normal-speed paths; settled error around 1–1.5 px except documented budget excursions. Fly rapidly across a split, bank, climb, reverse, teleport, and zoom. CPU p95 <0.5 ms, ordinary draws <100, geometry within target; if not, measure vertex texture cost versus cached patch VBOs before adding GPU-driven machinery.

### L3 — Shared curved horizon/ocean (1–3 days)

Owned: `src/sea.jo`, `src/sky.jo`, common render-coordinate helpers, object world-position transforms.

Add analytic far ocean and matching curved near ocean; apply one chart/curvature to all rendered world content. Remove sky-colored fake sea as a correctness mechanism. Keep the existing swell/stroke art initially.

Acceptance: uninterrupted horizon through a full yaw sweep at all baseline altitudes; no visible 22 km edge; clear-air island silhouettes meet the same sea from above and below their horizon; distant high cloud/terrain bounds are not prematurely culled. No visible geometry/material ring in the overlap at noon or sunset. Rebase/snap does not jump waves, shadows, textures, or objects. At 5 km, coverage expands rather than exposing a disk.

### L4 — Depth paths (1–3 days)

Owned: renderer projection/depth state helpers, shader compiler convention hook if doing native reversed-Z, camera setup.

Land the split-frustum baseline first or native reversed-Z if engine support makes it equally small; keep both on a controlled capability path. Log depth remains a measured alternative rather than a third simultaneously maintained default.

Acceptance: no shoreline/silhouette depth shimmer through 100 km; a test object straddling the 2,048 m split stays continuous; transparent effects use correct far occlusion; sky, picking, `world_to_screen`, and distance reconstruction agree. Compare precision debug geometry at 1/10/50/100 km and verify the actual attachment formats. A camera/plane near the sea must not lose its local precision to improve the horizon.

### A1 — Shared aerial perspective (2–4 days)

Owned: `src/look.jo`, `src/sky.jo`, common material uniforms/helpers and atmosphere assets. Start with exponential integral tests, then compact LUTs and palette controls.

Acceptance: endpoints and split passes evaluate the same `A,T`; sunrise/sunset color and aerial perspective remain continuous during altitude changes; sea/cloud/terrain at equal distance share haze behavior. Clear high-altitude views remain readable to the specification without a visible fog wall. Validate horizon rays and LUT interpolation against a slow offline/reference integrator; no NaNs or bands at zero slope/low sun. Atmosphere target ≈0.5–1 ms GPU excluding clouds, subject to measurement.

### C0 — One hero formation: art and GPU gate (1–2 days, before large cloud tooling)

Owned: cloud experiment module/assets and explicit cloud render passes. Make one tall connected cumulus, flat base, and a second overlapping mass using the proposed density assets. Include noon, sunset, above-cloud, and entry paths. Implement the minimum real reconstruction/occlusion needed to test moving views; a static low-res screenshot is not a performance success.

Acceptance: designer comparison to the supplied reference crops: large cream/slate masses, flat base, selective rim, no bubble pile or gray fog bank. Match output-resolution silhouette/lighting quality while the complete cloud experiment stays under 5 ms p95 on `redfox` at 720p. Inspect normal rendering speed, rapid bank/turn, and in-cloud flight; no persistent trails (>roughly 2–3 frames), edge leaks, or horizon dropouts. If it fails, reduce probes/detail and retest once; then choose the mesh alternative or revise the hardware/quality target **before** building the entire cloud world.

### C1 — Persistent field, hierarchical distance sampling (2–4 days)

Owned: `src/clouds.jo`, bake/data tools and cloud assets. Replace wrap/shrink spheres with deterministic authored macro weather, occupancy hierarchy, world sampling and explicit detail levels. Add coarse far optical integration and debug overflow views.

Acceptance: a cloud remains the same formation when circled/approached; wind does not follow the camera; no square wrap or 17/34 km boundary; horizon contains consistent formations through 100 km where atmospheric contrast permits. Giant towers retain silhouette until their actual projected detail is negligible. New tile boundaries and far/detail transitions pass noon/sunset motion checks without double opacity. Significant traversal overflow is rare and visible in diagnostics, never silently erased.

### C2 — Painted light, robust temporal reconstruction, fly-through (3–5 days)

Owned: cloud shading/reprojection/composite and shared atmosphere integration. Integrate low-frequency normals, light probes, broad palette ramps, brush bias, history rejection, and correct air/cloud composition.

Acceptance: no flat-white bloom or uniformly blue cotton balls; inspect color/value crops alongside the references at matched exposure. The plane disappears progressively into cloud; the chase eye can stay outside; cloud base/top crossings have no near-plane pop. Shadowed internal lobes remain organized; clouds are illuminated consistently with sunset sky/sea. Temporal history is tested at 30/60 fps, acceleration, camera cuts, zoom, and origin shifts. RGBA8 and float paths differ in precision, not basic behavior.

### C3 — Cloud shadows and scene integration (1–2 days)

Owned: cloud-shadow passes, `src/sea.jo`, terrain light sampling, transparent-effect integration.

Acceptance: cloud footprint tracks the same visible formation under changing wind/sun; glitter dims under cloud while sky reflection remains; aircraft shadows still work; no shadow-map square, snapping, low-sun streak, or shadow lag visible at normal flight speed. Clouded islands/sea are correctly occluded from above. Full subsystem remains within 3–5 ms target, including amortized map updates.

### V1 — Final scene/path review and limits (1–2 days)

Owned: diagnostic scenes/settings and measured budget documentation; routine fixes in the modules above. No unrelated gameplay or UI overhaul.

Acceptance: repeat the F0 matrix, plus at least a sustained 10-minute route through cloud and coastline, on quiet `redfox`; compare WebGL2/Vulkan images with allowance for small arithmetic differences. Record p50/p95/max GPU/CPU, density/hierarchy counts, upload spikes, history resets, memory, and thermal/power conditions. Check resize/context recovery and both capability tiers. Designer approves moving reference comparisons, not just selected stills. Remove development-only artifacts/toggles from ordinary player flows; retain useful renderer diagnostics.

## 7. Main risks and decisions to keep explicit

| Risk | Early evidence / mitigation |
|---|---|
| UHD 620 cannot do attractive fly-through volumes in 5 ms | C0 precedes field tooling. Count density/texture/light work; validate motion at real output resolution. Mesh+local extinction is an alternative with a different quality envelope, not a promise of equivalence. |
| Morphing fixes cracks but changes coastline silhouette | Canonical nested heights, shoreline error bounds, edge equality checks, conservative offshore coverage. Never average away a small island or fade alpha at the sea join. |
| Terrain upgrade breaks props/collision | Explicit 14→8 m migration, shared triangle evaluator, fixed nearby detail; audit `surface_height()` callers. |
| Render-only curvature disagrees with local flat gameplay | One chart for every rendered object/volume/shadow; verify camera orientation and visibility. Full spherical simulation is out of scope; revisit if flight becomes orbital or travel covers hundreds of km. |
| Different atmosphere/fog per layer creates a band | Shared `A,T`, solar extinction, linear color/exposure; interval-based cloud composition. Reference integration at sunset. |
| False “reverse Z” gives no precision benefit | Inspect format, zero-to-one clip mapping, compiler remap and reconstruction. Keep split-frustum fallback. |
| Low resolution loses crisp painted silhouettes / trails during turns | Small world-space edge detail, first-hit and weighted depth, history rejection, edge refinement. Raise sampling locally before applying indiscriminate blur. |
| Clouds become expensive because each sample evaluates everything | Baked shape/noise, fixed candidate count, sparse occupancy, bounded light probes, early termination; fragment passes for updates, no WebGL CPU compute volume regeneration. |
| Coarse distant density changes total cloud opacity | Filter optical statistics, common macro field, overlap weights on coefficients/intervals, reference rays. Never blend duplicate complete volumes. |
| A ray budget turns the horizon into holes | Conservative bounds, explicit overflow, coarse residual integration and invalid-history refresh; fail C1 if resolvable structure is routinely dropped. |
| Engine changes exceed game change | F1 is a small explicit prerequisite with portable fallback. Keep texture3D, bindless, GPU culling, compute weather and a general render graph out of the critical path. |
| A still resembles the film but motion exposes procedural construction | Shared cloud advection/brush coordinates, large authored mass composition, moving-camera approval in every cloud gate. |

The practical architectural choice is therefore **stable, error-bounded geometry plus shared light transport**, and **cloud volumes whose form is authored before their noise is embellished**. Spend the first implementation days proving continuity and the cloud art/performance envelope; the high-cost failure would be building a planet engine or elaborate cloud editor before either has been demonstrated.

## Source index and evidence limits

Primary technical sources were preferred. All accessed 10 November 2026; dates in search metadata were not treated as publication dates when the source itself gave a different date.

1. RocketWerkz/Dean Hall, official Year One recap: https://forums.ahwoo.com/forums/kitten-space-agency/developer-updates/development-recap-one-year-one.75/ — direct spherical-billboarding description. Mirror: https://ahwoo.com/news/6309887/kitten-space-agency/development-recap-year-one
2. BRUTAL official source: https://github.com/ahwootech/BRUTAL — framework scope; not KSA renderer source.
3. Community-transcribed December 2024 developer statement: https://www.reddit.com/r/kittenspaceagency/comments/1hfxfel/20241216_development_update_from_dean/ — corroboration only; indirect provenance.
4. Filip Strugar, CDLOD paper/code: https://github.com/fstrugar/CDLOD — terrain selection/morphing reference. The proposed local-error/edge-contract system in this report is an adaptation, not a literal transcription.
5. Asirvatham and Hoppe, GPU geometry clipmaps: https://developer.nvidia.com/gpugems/gpugems2/part-i-geometric-complexity/chapter-2-terrain-rendering-using-gpu-based-geometry
6. Michelic et al., I3D 2019 research abstract: https://www.cg.tuwien.ac.at/research/publications/2019/kerbl_2019_planet_poster/ — integrated planetary continuity precedent; no asserted KSA lineage.
7. Nathan Reed/NVIDIA, depth precision: https://developer.nvidia.com/blog/visualizing-depth-precision/
8. Outerra developer notes, log depth: https://outerra.blogspot.com/2013/07/logarithmic-depth-buffer-optimizations.html
9. Hillaire, atmosphere reference implementation and linked paper: https://github.com/sebh/UnrealEngineSkyAtmosphere ; author bibliography: https://sebh.github.io/publications/ — standalone paper download was not accessible through the research fetch, so no claim is based on inaccessible implementation detail.
10. Bruneton, precomputed atmosphere implementation and WebGL2 demo: https://ebruneton.github.io/precomputed_atmospheric_scattering/
11. Rare, The Technical Art of Sea of Thieves, SIGGRAPH 2018: https://history.siggraph.org/wp-content/uploads/2022/09/2018-Talks-Ang_The-Technical-Art-of-Sea-of-Thieves.pdf
12. Guerrilla, Nubis 2017: https://www.guerrilla-games.com/read/nubis-authoring-real-time-volumetric-cloudscapes-with-the-decima-engine
13. Guerrilla, Nubis Evolved 2022: https://www.guerrilla-games.com/read/nubis-evolved
14. Kids With Sticks, developer art breakdown: https://kidswithsticks.com/creating-stylized-art-inspired-by-ghibli-using-unreal-engine-4/
15. Lightning Boy Studio, authored Ghibli cloud tutorial: https://www.youtube.com/watch?v=RgRPUlFBHH4 — demonstration/tutorial, not shipped WebGL performance evidence.
16. Maxime Heckel, WebGL volumetric cloud demos/explanation: https://blog.maximeheckel.com/posts/real-time-cloudscapes-with-volumetric-raymarching/
17. gameidea, stylized Godot cloud shader: https://gameidea.org/2025/01/22/making-a-stylized-sky-shader-with-volumetric-clouds/
18. miHoYo, GDC session listing: https://gdcvault.com/play/1027539/-Genshin-Impact-Crafting-an — does not establish an exact cloud implementation here.
19. Khronos WebGL2 specification: https://registry.khronos.org/webgl/specs/2.0.0/
20. Khronos float color extension: https://registry.khronos.org/webgl/extensions/EXT_color_buffer_float/
21. Khronos optional clip control: https://registry.khronos.org/webgl/extensions/EXT_clip_control/
22. Khronos asynchronous timer queries: https://registry.khronos.org/webgl/extensions/EXT_disjoint_timer_query_webgl2/
23. Dean Hall’s direct early explanation of KSA mesh selection and camera-relative precision: https://www.reddit.com/r/KerbalSpaceProgram/comments/1gg5106/ksa_the_ksp_replacement_from_rocketwerkz_seamless/
24. Thatcher Ulrich, original chunked-LOD work: https://tulrich.com/geekstuff/chunklod.html

Local primary evidence: `src/terrain.jo`, `src/world.jo`, `tools/bake.jo`, `assets/terrain.bin`, `src/sea.jo`, `src/clouds.jo`, `src/sky.jo`, `src/look.jo`, `src/pilot.jo`, `aegean.jo`; Sloppy `docs/API.md`, `docs/GRAPHICS.md`, `lib/game/draw2d.jo`, `draw3d.jo`, `gl.jo`, `vk.jo`, `vkgl.jo`, and `compiler/spirv.jo`. The density equations, memory limits, atlas layout, pass sequence, milestones, and cost allocations above are proposed engineering designs for this project, not benchmarked claims about those sources.
