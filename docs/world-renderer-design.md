# Aegean-sized world: renderer design

Phase 1 completed 2026-11-11. Implementation branch `t3/world-renderer`, baseline `97eda0d`, measurement checkpoint `5ecb453`. This document replaces the initial notebook, retained as `design-initial-notebook.md` in scratch. Main checkout is untouched. No scaling of the existing islands, flight physics, clouds, or sea appearance is proposed.

## Decision

Build a hybrid heightfield world: preserve the exact existing archipelago and its validated baked surface; add authored country-scale coastlines/ridge structure and deterministic local detail, rendered through a bounded, view-dependent quadtree of shared regular grids. Keep coarse coverage available while finer tiles are prepared. CPU height queries and uploaded heights must share a versioned source and the same canonical triangulation. Publish a small separate wasm file rather than a base64 payload inside HTML.

This is a scalability change, not a promised whole-game FPS improvement. On the Intel laptop the current terrain takes only1.65–5.81ms of94–107ms GPU frames. Eliminating it entirely cannot fix the dominant frame cost. The target is to add a country-sized world without a material frame regression, while bounding memory independently of total land area. Browser memory well below today's is a measured acceptance target, not an established consequence of terrain LOD; the baseline fine atlas is already only3.91MiB.

Keep the old renderer available during the first integration step. Preserve the original10 islands, their coordinates, erosion, source quantization, canonical14m diagonals, towns and harbors. New terrain must have no influence in a protected region containing every legacy island and seabed apron. There is no reason to rebake them at a larger scale.

## Required invariants

- World footprint approximately500×400km, x east/z south, sea0. Mainland/large islands carry mountain chains; peaks near3000m only on mainland/largest landmasses,1000–2400m on selected big islands. Smaller islands mostly low hills/rock/cays, not a peak at every center.
- Existing8m source and14m canonical render surface stay unchanged. On new terrain, near geometry and collision use one deterministic sampled surface, with14m or finer grid spacing near possible contacts. Collision never follows a camera-dependent LOD.
- Every region is approachable and landable/walkable, not a skybox silhouette. Coarse visible coverage cannot be the collision authority for a nearby aircraft, boat or walker.
- Height, coast/depth, region identity and chart come from the same geography. Future country/harbor placement receives persistent region IDs and coast information; new settlements are out of scope.
- No whole-world fine bake at player startup, no paid terrain service, no network dependency for generated land. Generation/upload has a fixed per-frame work limit and a bounded cache; teleports retain coarse coverage while refining.

## Survey and what transfers

Sources below are primary papers, original source code, developer presentations or official documentation. A title's existence is not evidence of undisclosed implementation detail. In particular, public talks rarely establish bit-identical CPU/GPU collision or cross-platform determinism; those are marked unknown rather than assumed.

| Approach / shipped system | Height authority, storage and streaming | LOD, seams, distance appearance | Collision / determinism and fit |
|---|---|---|---|
| Losasso/Hoppe geometry clipmaps; GPU clipmaps [1,2] | Multiresolution elevation pyramid, residual compression; viewer-centered toroidal windows update incrementally. GPU version uses vertex textures and optional synthesized finer detail. | Nested regular rings, parent transitions, static XY grids. Normal maps carry shading detail when geometry coarsens. Bounded ring count and sample storage. | Height source can serve CPU queries, but the papers do not by themselves guarantee GPU-noise parity. Strong alternative with predictable cost; sparse sea and sharp legacy cliffs make an adaptive quadtree attractive here. |
| Strugar CDLOD [3] | Source heightmap with min/max quadtree; paper explicitly leaves storage/compression/streaming to implementation, with StreamingCDLOD sample provided. | Regular grid per selected node; per-vertex distance morphing collapses fine grids into coarse grids before swapping. Consistent height filtering is required on shared edges. | Do not substitute averaged mip heights for canonical ground. Collision requires an independent fine query. Fits WebGL vertex fetch and instancing; add cache/readiness rules and measured error checks. |
| Ulrich chunked LOD [4] | Preprocessed chunk meshes and quadtree texture tiles, paged from disk. Developer explicitly notes preprocessing/storage overhead. | Batched chunks and geomorphs; practical quadtree variants use skirts or stitching. Skirts hide a gap but do not make a consistent walkable surface. | Original author calls height/collision queries inconvenient. Avoid arbitrary simplified triangle chunks as the authority here; use regular sampled tiles and shared borders. |
| Outerra [5] | Sparse elevation enlarged with procedural refinement; published demonstration distinguishes bilinear source from synthesized terrain. | Multi-scale terrain detail and distant surface/vegetation representations. Published grass work shares canopy data between geometry and distant shading. | Useful hybrid precedent; public material consulted does not establish exact CPU/GPU parity or all cache formats. Keep our authoritative heights on CPU, upload quantized values. |
| Proland [6] | Original ElevationProducer consumes CPU residual tiles and generates GPU elevation; optional scale-dependent noise. ResidualProducer loads disk tiles; CPU/GPU tile caches have explicit borders and parent dependencies. | Quadtree elevation/normal producers, parent reconstruction and procedural refinement. Forest work transitions individual representations into terrain shader maps for subpixel effects. | CPUElevationProducer exposes height queries only when the tile is cached. Its existence does not prove that optional GPU-only detail is included in every query. Adopt cache dependencies and shared authority, not the entire framework. |
| MSFS2020/2024 [7,8,9] | DEM and aerial imagery, photogrammetry where available; inferred building/vegetation attributes support local reconstruction.2024 explicitly increases cloud streaming. SDK lists photogrammetry, DEM+imagery, and DEM+synthesized textures; compressed CGL stores imagery/elevation/vector data. | Geographic tile streaming and multiple data-quality fallbacks. Exact crack/collision implementation is not public in these sources. | SDK offers terrain elevation queries. This is not a tiny offline seeded world: petabyte/cloud production is unsuitable here. Borrow separation of macro elevation, local detail and fallback coverage. |
| No Man's Sky [10] | Developer pipeline explicitly covers voxel generation, polygonization, texturing, population and simulation continuously around the player. | Planet-to-ground scale; voxels allow topology beyond a heightfield. Specific compression/seam rules not established by the available synopsis. | Deterministic generated worlds require versioned seeds and edit persistence, but no bitwise collision claim inferred. Voxels cost more than needed for this brief, which does not require caves or deformation. |
| Star Citizen [11] | Official Planet Tech reports discuss virtual terrain and runtime compression work alongside authored/procedural placement. | Planet-scale rendering; hardware tessellation is mentioned in developer reports. Exact algorithms/working-set limits remain undisclosed in consulted sources. | Do not copy a reported feature name as an implementation recipe. Its compute/tessellation capabilities exceed WebGL2. |
| Elite Dangerous [12] | Frontier explains cube-face terrain patches, mathematical Horizons terrain, and Odyssey's coarse-to-fine generation using offline terrain-feature resources, stochastic sampling, orientation and blending. | Planetary regions guide finer formations and materials; detail must read from afar. Streaming is explicitly part of the redesign. Exact seam/codec implementation not disclosed. | Stellar Forge is described as deterministic; sources do not establish bit-identical GPU/CPU terrain. Strong precedent for geographic constraints and feature distribution rather than unconstrained noise. |
| Kerbal Space Program2 [13] | Procedural quad sphere; mesh generation on GPU, separate collision quad selection. Floating-origin-relative vertex data. | CPU frustum selection, stable slope/cavity shading inputs independent of tessellation; far/near representations cross-fade. | Collision coverage follows possible colliders, not camera visibility. Directly relevant. Later developer profiling shows repeated terrain passes can dominate despite LOD; GPU compute is not our portable baseline. |
| Horizon Zero Dawn / Forbidden West [14] | GPU procedural placement and world data; later deferred texturing handles foliage/alpha-tested geometry. | Bounded near population and shading work; these sources do not establish a particular heightfield compressor or seam algorithm. | Separate terrain authority from population. Do not conflate deferred texturing with terrain LOD or introduce foliage work outside scope. |
| Ghost of Tsushima [15] | Developer world rules generate texture and placement data; GPU-interpreted rule system and explicit streaming infrastructure. | Population density and draw distance are handled as bounded runtime systems, with separate grass/shading presentations. | Rules/streaming are transferable; exact terrain collision/determinism internals not disclosed. No need for a new rule language in this game. |
| Far Cry4/5 [16] | Near heightmaps plus material masks/decals; adaptive virtual textures cache expensive surface shading. FC4 described baked vista geometry/textures. | FC5 compute pipeline performs LOD/culling/stitching. | CPU/GPU height parity is not established by talk synopsis. We can use regular-grid selection and caching, but compute-driven submission is unsuitable as the sole WebGL path. Current simple terrain material does not justify full virtual texturing. |
| Just Cause3 [17] | Authored3D terrain, procedural texturing/vegetation, compiled representation supporting streaming/rendering/physics. | Developer/Intel case study describes finer patch LOD replacing coarse levels. | Offline compiled physics is explicit. Volumetric authoring and large precompiled world assets are unnecessary for our small download. |
| Unreal World Partition / HLOD / RVT [18] | Spatial cells stream world content; HLOD aggregates distant objects; virtual textures page/cache material data. Landscape uses heightfield collision. | Useful independent controls over geometry, materials and object visibility. These mechanisms do not themselves define the world's heights. | Keep heightfield collision authoritative. Do not mistake HLOD impostors for landable ground. Runtime virtual textures cache shading, not deterministic geography. |
| Recent SIGGRAPH/HPG work [19] | CoD2023 extends virtualization beyond textures;2024 concurrent binary trees adapt GPU tessellation;2024 multi-scale erosion amplifies coarse hydrologic structure; HPG2025 LidarScout explores compressed point clouds out of core. | Modern approaches reinforce bounded working sets, multi-scale representations and data-generation budgets. | CBT compute/atomics are not a WebGL2 baseline; point clouds are not a landable surface. Multi-scale erosion is useful offline, but no real-time tile budget is assumed without measurement. |

### Compression, shading and horizon conclusions

Use explicit bounded height quantization, version/checksum validation and CPU decoding of the same bytes used by rendering. Parent residuals and ordinary HTTP compression are useful; block compression must not independently move collision/shore vertices. Compressed float formats and texture arrays can improve a later backend, but RGBA8 integer packing is portable now.

At distance, retain silhouettes/coast coverage and filtered material/normal information while dropping fine geometry. Far rocks/trees can become impostors or shader statistics; terrain itself must remain traversable geometry. Proland's forest work demonstrates the representation principle [6]. Do not spend far-field pixels evaluating high-frequency noise that is smaller than a pixel.

Distance-field shadows are not a free substitute for terrain LOD. Epic documents landscape as a heightfield rather than a mesh distance field and recommends far cascaded shadows for terrain in that path [20]. Large SDF atlases and tracing are poor fits for this web/UHD620 budget. Preserve current lighting initially; shadow redesign is not required to scale terrain storage.

Existing `render_space.jo` already uses radius6,371,000m and camera-relative curvature. Sea horizon from4000m is225.8km; a3000m summit can remain mutually visible at about421km. Tangent sag at500km is about19.6km. Keep a single curvature convention across sea, terrain and culling, include elevated-feature range in the far plane, and do f64 camera subtraction before f32 upload. Simulation can remain flat over this bounded domain; do not change flight physics to simulate a globe.

## Engine measurements

### Reproduction and host separation

Desktop: i7-6700/GTX1070; local hostname can misleadingly say redfox. Only instruction counts, functional checks and memory/capability probes were collected here during this phase. Actual quiet laptop: `dsamson@192.168.1.79`, i5-8350U/UHD620, Bazzite. Standalone release build copied into our own `~/dev/tmp/aegean-world-renderer`. All laptop runs held `flock ~/dev/tmp/bench.lock` and used one worker. No windows/audio on either host. Local compiler source at inspection:5b99d53; saved standalone binaries fix the measured baseline.

`laptop-baseline.sh` renders360frames at1280×720, fixed camera and hour, SLOPPY_STATS=log and AEGEAN_LOD_STATS=1. Medians exclude the first compilation/warmup window. Scenes are harbor85m, crossing100m and high4000m. Reproduce the same exact camera coordinates for after comparisons.

| Laptop scene | Frame ms | CPU frame ms | GPU frame ms | Terrain CPU ms | Terrain GPU ms | Peak RSS KiB |
|---|---:|---:|---:|---:|---:|---:|
| Porto harbor |109.4|2.3|106.5|0.38|5.81|125552|
| Crossing |96.8|2.1|94.1|0.40|1.65|108996|
| High4000m |96.3|2.0|93.6|0.41|3.94|108564|

These are headless GPU measurements, not a claim about windowed presentation. Terrain consumes roughly2–6% of GPU time. Current harbor selection has103visible patches,12draws,172176triangles,4120instance bytes; crossing125patches,18draws,196796triangles,5000instance bytes. A full-world renderer must avoid O(world-area) traversal/upload, not merely lower today's modest selection time.

CPU-only desktop selection/culling workload in `tools/terrain_cost.jo`,360moving-camera frames, no window/audio. Callgrind was found in an existing scratch installation. Fixed setup0frames:488205123instructions;360frames:890740024; difference402534901, approximately1,118,153instructions/frame. Includes selection, culling and language/runtime overhead; excludes driver/GPU submission. Counter files and binary are retained; compare the same workload after changes.

### Native/WebGL capabilities

| Feature | Evidence | Design consequence |
|---|---|---|
| Vertex texture fetch / texelFetch | Current terrain; Sloppy shader API; browser reports32vertex texture units | Shared displaced grids work without new graphics features |
| Instancing | API supports per-call arrays and persistent InstanceBuffer; WebGL glue drawElementsInstanced | Batch by shared grid/stitch family; keep static grids resident |
| Compute | Native gpu_compute=true; forced OpenGL=false; Sloppy GpuBuffer dispatch falls back to CPU on WebGL | Never rely on compute for portable frame budget |
| Fragment-pass GPU arrays | Sloppy GpuArray supports float texture passes; tested browser R32F/RGBA16F renderable with extensions | Potential later synthesis acceleration, not authoritative physics |
| Texture arrays | WebGL reports2048layers, but current Sloppy Texture/glue has no texture3D/array upload abstraction | Use2D atlas or bounded textures; do not require compiler/runtime changes |
| Texture limits | Forced native GL32768; tested browser8192 | Use small bounded atlases; do not allocate to maximum |
| Uploads | glTexSubImage2D and glBufferSubData exposed; persistent meshes/instances available | Region updates are possible; baseline instances only4–5KB/frame. New tile upload budget initially≤64KB/frame, to validate on laptop |
| Float textures | Browser framebuffer checks pass RGBA8,R32F,RGBA16F; OES_texture_float_linear reported | Extension results belong to this backend, not universal WebGL guarantees; RGBA8 remains baseline |

Browser probe: headless Chromium1248, ANGLE SwiftShader, fresh profile, no audio. `tools/measure_web.mjs` runs the actual build, captures console/errors, wasm memory, JS heap, WebGL capabilities and process-tree RSS/PSS/private pages. Software GPU results are valid for memory comparisons under identical conditions, not hardware frame performance predictions.

Baseline snapshot: wasm68,485,120bytes (65.31MiB); JS used heap1,382,152bytes; browser-tree RSS1,455,016KiB (double-counts shared pages), summed PSS945,790KiB, private clean+dirty771,984KiB. GPU process is a large component. These are snapshots after startup, not peak/private wasm allocation reports. Browser memory acceptance will use PSS and wasm separately and repeat the same backend/configuration.

### Current asset/storage baseline

Fresh unscaled bake and terrain check pass:511914canonical vertices,424patch bounds,96stitch families; shared grid756096bytes, atlas4095312bytes. Source quantization max0.000122070m; grounded residual0. Archived original source bytes preserve exact cliffs/beaches/erosion.

| Artifact | Raw bytes | zlib6 bytes (HTTP estimate) |
|---|---:|---:|
| HTML |14723862|7204341|
| Embedded wasm |10984246|6281813|
| terrain.bin |3366128|1898694|
| terrain_lod.bin |4114200|3077753|

A whole500×400km grid at8m is3.125billion samples/5.82GiB at16bits. At14m it is1.02billion samples/3.80GiB atRGBA8. The present23.4375m sea-depth spacing over the world would need about364million texels,1.36GiB RGBA plus2.71GiB temporary f64 samples. Both fine terrain and depth must be local or sparse. The legacy atlas is small enough to retain unchanged initially; the danger is multiplying it by world area.

## Candidate costs and selected implementation

| Candidate | Estimated working set / work | Main risk | Decision |
|---|---|---|---|
| Hybrid quadtree with deterministic new-land source, protected legacy bake | Example256tiles×33²×8bytes≈2.13MiB sample payload plus atlas rounding/metadata. Static stitch grids shared. Limit selected triangles and tile work explicitly; source queries have bounded regional lookup. | Cache readiness, borders, multi-scale error and fast flight must be validated; CPU generation can hitch if unbudgeted. | Selected; smallest change to legacy guarantees and best sparse-sea fit |
| Geometry clipmap |10levels×255²×8≈4.96MiB before staging; roughly1Mtriangles if all rings active, less with height/frustum culling. | Wastes coverage over sea; regular rings may overdraw or undersample cliffs unless carefully tuned. | Fallback if measured quadtree submission dominates |
| Fully baked sparse fine tile pyramid | Even20%land at8m16bit is≈1.16GiB before other data. Compression/streaming reduces residency, not total world download. | Exceeds web/download budget; external hosting/requests and large offline bake. | Reject as default |

Start with existing legacy render data retained. Packaging alone removes base64 inflation and frees approximately0.9MB of compressed-transfer headroom in this baseline before loader overhead; measure actual final bundle. Aim for new geography/code/coarse data below that headroom. If necessary, pack or derive legacy render attributes without changing canonical heights, but do not rewrite preserved terrain merely to pursue speculative savings.

New geography may combine a small authored regional description (polygons, mountain chains, low island field) with a compact sampled macro field and deterministic band-limited residuals. A500m16bit macro grid is1.53MiB raw before compression; a coarser896m grid aligned to64×14m is about0.5MiB raw, with separate explicit features for small islands/coasts. This is a starting cost bound, not a fixed visual-quality choice. Measure silhouettes and shoreline resolution before committing to a macro spacing. Avoid unconstrained circular noise mountains on every island.

The near source is either a deterministic analytic field or a locally sampled8m refinement of the macro representation. It must be evaluable without loading an entire continent. Quantize once, share it with canonical14m triangle interpolation and sea depth. Tile generation order must not alter results. Seed, generator version and authored data hashes belong in cache keys. Bounds must include procedural residual amplitude; do not call a few sparse samples a proven maximum-error bound.

Keep coarse roots resident. Select children only when their data are ready; pin needed parents and nearby physical-contact tiles. Edge samples share integer world coordinates and quantization. Prefer a2:1 balanced tree and explicit stitching/morphing; use skirts only as a conservative fallback and validate that they cannot create exposed coast walls. Never draw a fine edge against an unavailable/coarser neighbor without reconciling both endpoints. Near-contact LOD is finest; optional far refinement yields first when memory/work budget is reached.

At200m/s a1km tile is crossed in5s. Lookahead must cover generation latency, but each frame's CPU/upload allocation is small. Teleport tests must check coarse continuity and eventual local readiness. Chart queries and distant living-world routing use the same macro coast/regions without forcing every fine tile resident. The sea retains its appearance; a bounded local coast/depth window and coarse fallback replace any proposed full-world fine texture.

## Acceptance gates and implementation sequence

1. Preserve baseline tests and images. Salvage only reviewed packaging/LOD-bound fixes; measure them on today's archipelago first. Existing sea/sky/cloud/flight visual behavior remains the comparison reference.
2. Introduce the world height/region data and bounded renderer behind a test switch. Validate canonical query agreement, repeated/tile-order determinism, shared borders, absence of NaNs, maximum cache size and per-frame upload/generation counts. Test origin, far corners, coast, high mainland, fast traversal and teleport.
3. Enable expanded geography without altering legacy land/source bytes. New mainland/large islands must have broad coherent shapes and a realistic uneven elevation distribution. Verify all existing harbors/routes remain on original geography. Expose region/coast records for future countries/settlements.
4. Integrate depth and chart at full extent. Validate boats/aircraft/walkers against the same authority and retain current legacy chart readability. Country-scale f32 positions need explicit precision checks; CPU terrain math/camera subtraction uses f64.
5. Capture Porto, crossing and4000m mainland views, plus near coastline/ground views. Run terrain source/LOD/morph checks and flight/damage/living tests with isolated SLOPPY_SAVE_DIR. Record known pre-existing wear failure separately.
6. Repeat laptop cameras under lock and report total/terrain CPU/GPU, startup and memory. Target no statistically material total-frame regression; use repeated paired runs if within a few percent. Budget additional far geometry against measured current terrain time, not a guessed triangle count alone.
7. Build/package web; verify exact wasm payload, real browser startup, cache bounds, wasm/PSS and total compressed bytes. Hard download gate≤7,204,341bytes zlib6 estimate for the whole bundle; actual HTTP transfer can differ. Aim≥20%PSS reduction on the same browser test, but disclose if unmet; terrain alone cannot guarantee it. No multi-minute runtime bake, no CDN terrain service.

Frame time/upload budgets and memory gains must be measured again after implementation. No architecture can honestly guarantee equal frame time for every possible camera merely from these baseline samples. If country-scale horizons exceed the budget, reduce far sampling/shading work first, preserve near ground fidelity, and report the quality/cost boundary rather than silently degrading the legacy islands.

## Sources

1. Losasso/Hoppe, SIGGRAPH2004: https://hhoppe.com/proj/geomclipmap/
2. Asirvatham/Hoppe, GPU Gems2: https://hhoppe.com/gpugcm.pdf
3. Strugar CDLOD paper and original implementation: https://github.com/fstrugar/CDLOD (paper downloaded/read; storage and streaming explicitly outside paper scope).
4. Ulrich, Chunked LOD: https://tulrich.com/geekstuff/chunklod.html
5. Outerra developer articles: https://outerra.blogspot.com/2009/02/procedural-terrain-algorithm.html and https://outerra.blogspot.com/2012/05/procedural-grass-rendering.html
6. Proland original source: https://gitlab.inria.fr/neyret/proland (access denied); original authored source inspected through mirror https://github.com/davidljung/proland — ElevationProducer, ResidualProducer, CPUElevationProducer, TileCache. Forest paper: https://diglib.eg.org/items/9de7c594-877a-4d97-a2e0-bcab5acb10bf
7. Blackshark2020 developer announcement: https://blackshark.ai/wp-content/uploads/2020/08/Blackshark.ai-Flight-Simulator-Announcement.pdf
8. MSFS2024 SDK: https://docs.flightsimulator.com/msfs2024/html/1_Introduction/Using_The_SDK.htm ; CGL: https://docs.flightsimulator.com/msfs2024/flighting/devmode/editors/project-editor/file-formats/cgl-files/
9. Official MSFS2024 FAQ: https://www.flightsimulator.com/microsoft-flight-simulator-2024-faq/ ; shared2020/2024 DEM/imagery discussed at https://forums.flightsimulator.com/t/dev-livestream-transcript-april-2024/640294/1
10. McKendrick, Continuous World Generation in No Man's Sky: https://www.gdcvault.com/play/1024265/Continuous_World_Generation_in__No_Man_s_Sky_
11. RSI official report: https://robertsspaceindustries.com/en/comm-link/transmission/20537-Star-Citizen-Monthly-Report-March-2025
12. Frontier developer Q&A,22Feb2021 official Steam announcement: https://store.steampowered.com/news/posts/?appids=359320&enddate=1614874210&feed=steam_community_announcements
13. KSP2 developer insights12: https://forum.kerbalspaceprogram.com/topic/205930-developer-insights-12-%E2%80%93-planet-tech/ ; performance diary18: https://forum.kerbalspaceprogram.com/topic/214806-developer-insights-18-graphics-of-early-access-ksp2/
14. Guerrilla placement talk: https://gdcvault.com/play/1024700/GPU-Based-Run-Time-Procedural ; deferred texturing: https://www.guerrilla-games.com/read/adventures-with-deferred-texturing-in-horizon-forbidden-west
15. Sucker Punch: https://www.gdcvault.com/play/1027352/Samurai-Landscapes-Building-and-Rendering ; streaming slides: https://media.gdcvault.com/GDC%2B2021/ghost_streaming_gdc2021.pdf
16. Ubisoft FC4: https://media.gdcvault.com/gdc2015/presentations/Chen_Ka_AdaptiveVirtualTexture.pdf ; FC5: https://www.gdcvault.com/play/1025261/Terrain-Rendering-in-Far-Cry
17. Avalanche SIGGRAPH abstract: https://history.siggraph.org/wp-content/uploads/2022/10/2015-Talks-Nilsendahl_A-Landscape-Engine-for-A-New-Generation-of-Open-World-Games.pdf ; Intel case study: https://www.intel.com/content/dam/develop/external/us/en/documents/optimizations-enhance-just-cause3-on-systems-with-intel-iris-graphics-684945.pdf
18. Epic HLOD: https://dev.epicgames.com/documentation/unreal-engine/world-partition---hierarchical-level-of-detail-in-unreal-engine ; RVT: https://dev.epicgames.com/documentation/unreal-engine/runtime-virtual-texturing-in-unreal-engine ; heightfield collision: https://dev.epicgames.com/documentation/unreal-engine/landscape-overview
19. SIGGRAPH2023: https://advances.realtimerendering.com/s2023/ ; CBT2024: https://advances.realtimerendering.com/s2024/content/Intel/large_scale_cbt_slides_siggraph_advances_2024.pdf ; erosion2024: https://research.adobe.com/publication/terrain-amplification-using-multi-scale-erosion/ ; HPG2025: https://philipperler.net/2025/08/22/lidarscout-hpg-2025/
20. Epic heightfield/distance-field distinction: https://dev.epicgames.com/documentation/unreal-engine/distance-field-ambient-occlusion-in-unreal-engine

Evidence is beside this document: baseline bake/check logs, baseline-sizes.txt, laptop-baseline/*.log/png and summary JSON, baseline-web-memory.log/png, capabilities logs, Callgrind files, sources/, and preserved standalone baseline executables. Repo tools/terrain_cost.jo and tools/measure_web.mjs reproduce the new probes. Initial design notebook is retained for provenance, not used as the current recommendation.

### Phase2 step1 evidence

Reviewed LOD projection/neighbor-bound fixes applied without any geography scaling. Laptop paired cameras: harbor109.5ms total/5.84ms terrain GPU, crossing96.7/1.74, high96.6/4.46 versus baseline109.4/5.81,96.8/1.65,96.3/3.94. Total differences under0.4%; high-view terrain cost rises for the corrected bound. No claim that this fix speeds up terrain.

Lossless split of the same baseline wasm loads in Chromium. PSS falls from945790KiB to905468KiB (about4.3%); wasm stays68485120bytes. It does NOT achieve the20%memory aspiration alone. Measurement remains a software-GPU snapshot; preserve this limitation in final reporting. Initial new-world macro asset is1259469bytes raw and its actual compressed size is recorded alongside implementation measurements. Legacy source and render assets remain unchanged.

### Phase 2 prototype checkpoint

Implemented an opt-in `AEGEAN_WORLD=1` world: eight authored land regions/ridge sets, 347 seeded smaller islands, protected ±20 km legacy square, 896 m quantized macro data (1,259,469 bytes raw / 407,728 zlib6), deterministic quantized 8 m source and 14 m contact triangles. Four geography tests pass, including exact old-height preservation, bounds/peak distribution, corrupted-asset rejection and query-order independence. No change to the original terrain assets.

The new renderer uses 512 slots of 17×17 RGBA8 height/material samples (1,183,744 GPU bytes), shared stitch grids, at most four new tiles / 9,248 sample-upload bytes per frame, pinned coarse ancestors and a 2:1 selected tree. Initial radius 3.5×tile width exceeded the cache and stalled refinement: rejected. At 1.5×tile width the fixed 4 km mainland camera settles to 164 cached / 104 drawn tiles, 53,824 triangles. These are desktop functional counts, not timings. Seam/motion and laptop costs remain under validation; no claim of a proven new-terrain screen-space error bound yet. Source samples are independent of cache state.

Depth integration adds a fixed coarse world map plus a double-buffered 256² / 6 km local window (original 23.4375 m sampling), four rows generated per frame; publication is atomic. The original 24 km depth texture remains authoritative over the old islands. Chart now has whole-world and original local views, switched with Tab; original town labels stay readable in local view. These changes compile; screenshots and performance validation are next. World remains opt-in until gates pass.

Pilot laptop results (redfox, exclusive bench lock, 360 frames each, medians excluding first shader-compilation window): harbor110.7ms vs109.4baseline, crossing97.55vs96.8, old high97.6vs96.3; new mainland4000m51.95ms total,1.8CPU/49.55GPU, new terrain0.73CPU/4.45GPU. New terrain costs0.32–0.41ms CPU and0.07–0.59ms GPU at original cameras. This is a measurable ~0.8–1.4% regression, so it is not yet a no-regression result. Startup3.20–3.31s vs2.42–2.44s; RSS112–130MiB-ish (KiB values in JSON), not lower than native baseline. Local depth high-altitude update was still disabled in this pilot. Final measurements must use the final binary.

Streaming acceptance tool `tools/world_flight.jo` passes a720-frame deterministic high/ground/200m/s/teleport path: cache496/512, max191 selected tiles/98,736triangles, six near-contact checks, maximum shared-edge residual0.00015626m. It checks overlapping domains, 2:1 adjacency, sample upload bound, actual shared edge-owner morph states and canonical ground agreement. This verifies seams and residency, not a proven screen-error bound or arbitrarily fast teleport warmup.

Memory/download follow-up: keep legacy source in its original i16/i8 form (3,365,952 sample bytes versus8,975,872 expanded f32 bytes; explicit f32 conversion preserves old arithmetic) and macro data in its validated packed bytes. Derive each legacy island's render data at startup instead of embedding a second4.1MB asset. A CPU-only locked laptop pilot reproduces all4,114,200 bytes exactly in1.959s, RSS28,924KiB. The runtime uploads one island at a time to bound staging memory. Full legacy numeric check still passes511,914 vertices/424 error bounds/96 stitch families with zero grounded-surface error. The existing bake/check artifact remains available for validation; its bytes have not changed.

The compact browser build is8,243,564bytes wasm plus78,770byte loader (before the small fingerprint probe addition), versus10,984,246byte baseline wasm and14,723,862byte base64 HTML. Browser startup reported7.945s in this functional software-GPU run; desktop elapsed values are not comparative wall-clock benchmarks. Final laptop startup, compressed size, wasm residency and browser PSS are being collected. The substantial PSS baseline includes SwiftShader/JIT/browser overhead, which source compaction alone cannot remove.
