# Weather, water and growing things

Branch `t3/nature`, based on `1ec6c12`. All work is in the implementation worktree; no main-checkout changes, no pushes. The pinned official Sloppy 0.29.2 matches Pages CI. The evidence bundle is `~/dev/tmp/aegean-skies/nature/`; artifact names below refer to that directory. Reference images and captures are not committed.

## Implementation

The living world's saved Weather records remain authoritative. New kinds are appended, preserving old enum values; `aspect=(1,1)` and `fade_minutes=0` preserve old records. Existing storm/squall scheduling remains, with smooth lifetime transitions. Moving visual cells interpolate between saved minute updates, matching the shared weather field. The same scheduler adds country-sized meltemi/tower/overcast/calm backgrounds, morning fog and occasional elongated fronts after the guaranteed fair opening. There is no separate stochastic renderer weather clock. Pure `weather_air`, `weather_weight`, `weather_gust` and `wind_at` serve the player and scene traffic; continuous bounded gusts feed FlightEnv without altering the aircraft integrator or shaking the camera.

The sky retains persistent cloud-cell identities. The alpha channel of the existing 1056² RGBA8 atlas now stores signed distance rather than density; adaptive surface search gives a crisp contour and shades the visible point once, using grouped values, cool fill, a narrow sun rim and coherent pigment variation. It permits up to 80 steps to close glancing-ray gaps. Large 26 km cells hold 10–15 km connected masses and replace small formations in those cells. Saved tick time drives 1000–1800 play-second condensation/growth/spreading/erosion cycles, with a stable condensation base; cached land-heating samples at advected world positions favor afternoon cloud clusters over island groups. These are deterministic visual envelopes, not fluid simulation.

The old wingtip-trail ordering bug is fixed by drawing ribbons after the cloud composite and evaluating cloud transmittance only between the camera and each ribbon fragment. Up to 32 local candidates fit the WebGL2 uniform budget; trails beyond 3 km are subpixel and culled. A synthetic near/inside/behind test demonstrates the distinction. The trail shader uses 135 fragment uniform rows (minimum budget 224), one sampler and two varying vectors.

 Saved weather changes cloud opacity/height and supplies continuous decks, distant rain curtains, low fog and a baked connected thunderhead/anvil. High cirrus, local fixed-mesh rain, deterministic two-pulse lightning and altitude-dependent lighting complete the visible conditions. The deck has an irregular base around 700 m and a top around 1.0–1.4 km; flight can pass through it. Storm tops reach roughly 6 km. Analytic layers use exact spherical height intersections and at most eight march samples. Isolated decks/storms/fog use a one-third-size color target; overlapping deck-plus-rain layers use one quarter. Fair medium/high use half size and low uses one third. Substantial storm silhouettes select the same one-third target even when their total screen coverage is below the broad-deck threshold. Deck value noise and its exact gradient share four hashes rather than computing three noises for finite differences. Spatial depth reconstruction and the existing full-resolution silhouette repair remain; no temporal history/trails or extra render target. Resolution switching has hysteresis.

The existing sea depth textures now carry a shelter estimate in their green channel. Nearby enclosed shallows reveal sandy bottom, rock and Posidonia-like material patches; deep water retains the existing blue. Shore break follows bathymetry and swell, with trailing foam; rain adds near-surface rings and reduces glare, and calm conditions suppress swell/crest marks. Water tint, roughness and reflected sky follow the shared weather. Fully hidden deep seabed retains its geometry/depth but skips material shading, and offshore pixels skip zero-contribution shoreline calculations.

Real saved fishing/public-boat markers now feed a read-only visual cache (24 boats maximum) and the existing wake system. Stationary boats create no wake, teleport discontinuities break trails, and old trails expire after 40 seconds. The renderer does not advance trips, invent boat routes, transfer ownership or modify the simulation. Decorative stationary boats remain stationary.

Low-tier pine/cypress/maquis crowns use fewer mesh rings/sides, and medium crowns use one fewer ring while retaining the same placement population. Six shared vegetation meshes use the existing candidate population and per-tier thinning: umbrella pine, cypress, maquis, olive, oleander and prickly pear. Olives replace candidates in broad suitable parcels and align them to constant-height rows (4.5 m steps), with bounded root moves and canonical terrain resampling. Rows use a shared orchard mask, interpolated at terrain vertices; retaining-stone/soil bands are material detail. Chapel/cemetery cypresses and square plane trees reuse bounded town props, with foliage wind bending separate from architecture. Roads/houses select some existing shrub candidates for oleander/pear. No season model exists, so the established dry summer fields remain.

Both the old islands and streamed land use the same noise-broken cliff material edge, with extra patchy edge tufts in the existing grass grid. Collision, the 14 m canonical mesh and terrain silhouettes are unchanged. This softens the green/rock transition; it does not claim to add geometric ledges, overhangs or retaining walls.

## Cost and limits

Fair harbor A/B, 1280×720, Intel UHD 620 laptop:

| Tier | Main whole frame | Nature whole frame | Main cloud GPU | Nature cloud GPU | Main groves GPU | Nature groves GPU |
|---|---:|---:|---:|---:|---:|---:|
| Low | 39.50 ms | 39.40 ms | 2.77 ms | 2.79 ms | 5.53 ms | 2.83 ms |
| Medium | 52.80 ms | 51.80 ms | 3.015 ms | 3.16 ms | 18.46 ms | 14.71 ms |
| High | 74.30 ms | 74.55 ms | 3.045 ms | 3.16 ms | 40.05 ms | 37.575 ms |

Low has no measured regression; medium improves by 1.0 ms (1.9%). High is **+0.25 ms (+0.34%)** in the paired sequence (a final shader recheck was 74.6 ms), so this is near parity, not a literal zero-regression pass. Do not hide the difference by rounding to whole milliseconds. Medians of two run medians; each run median is over the engine's steady two-second aggregates, not per-frame samples. Low order A/B/B/A; medium and high B/A/A/B. Start loads across the retained final suites range from 0.077 to 1.116, all below 1.5; every run has an individual uptime record. Each low run has three steady aggregates, medium five and high seven. Native RSS in these fair runs: baseline 123,632–125,828 KiB; nature 130,448–132,444 KiB. Startup/world construction about 14.1–14.2 seconds on this laptop.

Weather costs and the corrective recheck are in final-bench/ and weather-gradient-bench/. Some initial fast weather runs had too few intervals after warm-up; the corrective storm/front runs use 600–1200 frames to obtain several steady aggregates. The original rain 6.195 ms and front 5.46 ms exceeded budget; shared analytic noise gradients replace redundant deck-normal samples, and substantial storms select the one-third weather target. Corrective results: isolated storm 4.39 ms high / 4.35 ms low; front 4.99 ms high; rain 5.03 ms high / 4.99 ms low. This reaches the approximately 5 ms budget, with rain effectively on the boundary rather than comfortably below it. Quarter resolution applies only to overlapping deck/rain volumes; near rain streaks, trails and opaque-depth edge repair remain full resolution. The exact-gradient change alone saved only about .03 ms in the front; target selection supplied the useful gain.

Other measured cloud GPU costs before the final shared-gradient change: towers 2.115 ms, overcast below 3.19, above 3.85, inside 4.425 high / 4.45 low, fog 4.83, meltemi 1.48, calm 1.51. Isolated decks/fog use the same target size in the final version. These are specific camera samples, not a proof for every possible overlapping weather configuration. The short original low-storm run produced no steady aggregate and is excluded; its 1200-frame replacement is used above.

Cloud atlas: 1,064,079 bytes PNG, 4,460,544 bytes decoded RGBA8, unchanged dimensions/memory. The 96³ experiment was rejected: 15,366,400 decoded bytes for little visual gain. Packaged web payload at the final shader/geometry revision: Wasm 10,238,148 bytes versus 9,797,664 on main; HTML unchanged at 86,951; combined zlib level 6 estimate 5,191,462 versus 4,845,651 bytes (+7.1%). This is a compression estimate, not a captured HTTP response.

Matched desktop Chromium/SwiftShader Android-viewport probes: 39 programs linked, zero JS/GL errors, complete framebuffers at 326×706, 706×326 and 640×360 after resize. Maximum texture dimension 2048. Wasm backing memory 135,004,160 bytes versus baseline 134,873,088 (+131,072). Browser-process-tree PSS was 1,048,715 KiB versus 952,400; software driver/compiler caches and different completed frame counts are included, so these are not Android RAM measurements or a controlled timing result. Earlier 77 MB Wasm probes used a different scene; do not compare them with this harbor scene.

All timed native runs use the Intel UHD 620 laptop at 192.168.1.79 under `~/dev/tmp/bench.lock`, SLOPPY_THREADS=1, headless/silent, 1280×720, 240 frames. Each run starts only with one-minute load below 1.5. The gate checks at five-minute intervals and expires after thirty minutes. Fair comparisons alternate A/B/B/A (or B/A/A/B); medians exclude the first two-second statistics interval, which includes streaming/driver compilation. Individual loads, logs, RSS, startup and captures are retained. Desktop lavapipe captures are functional checks, not timing evidence.

The medium profile initially regressed by 1.8 ms; retaining its population and removing one crown ring reduced it below main. Initial pilots exposed a low-tier regression and excessive rain/fog GPU cost, so they are not used as final acceptance results. `initial-bench/`, `layer-interval-bench/`, `material-branch-bench/`, `seabed-pilot/` and `vertex-pilot/` preserve that investigation. Sources/binaries changed between these folders; do not pool them.

Known approximations: weather lighting/wetness are sampled at the observer, wet roofs do not accumulate water, cirrus is visual only, and the legacy pure-CPU rasterizer retains its old opaque-cloud fallback. Posidonia/rocks are seabed materials, not separate geometry. Terrace bands do not modify terrain contact. There is no ecology growth/season simulation and no new thunder audio. Real phone hardware remains a separate validation step; a Chromium Android viewport is a proxy.

## Cloud reference review

Research notes and primary-source links are in cloud-design.md. Inspected Genshin's GDC cloud slides, the Sky art presentation, an author's Zelda puff-particle breakdown (not a claim about Nintendo's sky architecture), SDF cloud rendering and the supplied Porco Rosso stills. The dedicated Castle in the Sky storm-wall still comes from a third-party distribution, not the official Ghibli gallery; provenance is recorded. No film pixels or reference images enter the game or repository.

**The film-indistinguishability goal is not met.** Compare cloud-comparison-day.png and cloud-comparison-storm.png. Crops and uniform resizing only; cloud_comparisons.py records coordinates/scales. The daytime clouds have clearer contours and broad warm/cool regions, but still have large smooth sculptural bulges and too little fine irregular painted structure. The storm is a connected rolling/anvil formation, but does not reproduce the Dragon's Nest's enormous layered walls, depth and negative-space channels. Self-review is not an independent blinded test. This limitation is a remaining aesthetic acceptance gate, not a claimed success.

Large banks and the five-stage lifecycle sequence are implemented and captured. The geographic heating is a cached broad preference, not a full mesoscale model; wind can advect the formations away from their source islands. There are three fair stamps plus one storm stamp, so repetition remains possible. The next visual step should be authored multi-scale form/light structure (more distinct formation profiles and calibrated painted light masks), not a larger voxel atlas: the 96³ pilot did not justify its memory cost.

## Validation and captures

13 nature tests and 6 sky tests pass after the final cloud geometry change. Native and Wasm builds, WebGL2 uniform/varying/sampler audits and web compatibility tests pass. Flight tests (16), quality (2), world detail (6), existing living weather (3), save first-three checks and all five 30-day replay seeds (0, 1, 7, 42, 127) passed during this implementation; the long replay was split into serial seed batches after the combined invocation timed out. The two documented pre-existing living_scene_flight failures were not represented as fixed.

No UI was changed. The coordinator may later expose weather observation/forecast/debug choices using the shared WeatherAir data; no new menu is required to see naturally scheduled weather.

Explicit capture fixtures: `AEGEAN_WEATHER=fair|towers|overcast|front|rain|storm|fog|meltemi|calm`, optional `AEGEAN_WEATHER_CENTER="x z"`, `AEGEAN_WEATHER_CLOCK=seconds` for a fixed lightning/rain phase. These inject ordinary Weather records only when explicitly requested. `AEGEAN_VIEW="x y z yaw pitch hour"` and `AEGEAN_QUALITY=low|medium|high` remain the existing camera/profile controls. `tools/nature_sites.jo` prints reproducible original-island cove/terrace/cliff viewpoints.

## Captures and reproduction

- Day film/game comparison: `cloud-comparison-day.png`; storm comparison: `cloud-comparison-storm.png`; exact crop/resize script `cloud_comparisons.py`. Full supplied film frames stay in the sibling refs directory. Full game contexts: `bank-field-final.png`, `cloud-painted-final.png`, `cloud-storm-wall.png`.
- Growth sequence: `life-contact.jpg` and `life-080.png` through `life-950.png`, at 1.9/5.8/11.7/17.5/22.2 minutes since condensation phase. Camera and shape identity remain fixed.
- Cloud/trail controls: `trail-both.png`, `trail-only.png`, `trail-cloud-only.png`. Three ribbons are in front of, inside, and behind a 50 m test cloud. The foreground ribbon remains fully visible; the inside ribbon attenuates; the rear ribbon is strongly attenuated. A kilometre-scale cloud is much more opaque. This is a visual regression fixture, not a measured percentage of optical accuracy.
- Every weather type: numbered captures in `final-bench/`; corrected fronts/rain in `acceptance-bench/`, corrected storms in `weather-gradient-bench/`. Deck views include below/above/inside; `country-deck.png` checks a cloud layer over the mainland nearly 200 km from its record center. `lightning.png` freezes a flash.
- `cove-air.png`, `cove-water.png`, `olive.png`, and `cliff-before.png` / `cliff-after.png` cover the original nature brief. These show stylized materials and existing terrain geometry; terraces are material/placement rows, not newly cut landforms.

For the cloud-only regression fixture: build `tools/cloud_pilot.jo`; use `CLOUD_VIEW=comparison|field|storm|storm_wall|inside|life|trails`, `CLOUD_SECONDS`, and optional `CLOUD_NO_TRAILS=1` / `CLOUD_NO_CLOUDS=1`. Capture scripts, host/load logs, raw zone stats and summaries are preserved in the evidence bundle. Pure CPU software fallback also starts and renders two headless/silent frames.

## Remaining acceptance work

1. Aesthetic review is still required: the comparison does not meet the user's film-indistinguishability bar. The largest missing elements are the fine hierarchy of painted billows and the storm-wall composition; color/rim tuning alone does not solve them.
2. Test on the actual Android phone. Shader minima and desktop browser linking/resize are checked; no phone GPU timing or Android process memory is claimed.
3. High-tier harbor frame time is +0.34% in the paired measurement. The low tier is at parity; do not describe all profiles as an exact zero-regression result. The final low-tier recheck is 39.5 ms and high 74.6 ms; medium is 51.8 ms versus 52.8 ms on main after its crown-ring reduction.

## Merge

Merge the branch normally; shared-hub edits are small hooks in aegean.jo, pilot.jo and traffic.jo. Rebuild the changed cloud atlas with `sloppy --release tools/bake_clouds.jo` before compiling. Fresh checkouts use `sloppy --release tools/bake.jo`, which already includes that atlas. Terrain/world source assets do not need a new bake for this branch. No generated assets or reference images are committed. Pages CI adds the nature tests and retains the generated WebGL2 shader audit.

## References

HNMS describes the warm-season Aegean northerlies/Etesians: https://www.emy.gr/en/the-climate-of-greece . Met Office cloud classifications distinguish layered stratus/cirrus and towering cumulonimbus with anvils/rain: https://weather.metoffice.gov.uk/learn-about/weather/types-of-weather/clouds and https://weather.metoffice.gov.uk/learn-about/met-office-for-schools/other-content/other-resources/understanding-weather . EU habitat guidance places Mediterranean Posidonia beds from shallows to roughly 30–40 m: https://op.europa.eu/en/publication-detail/-/publication/87a62291-df43-11f0-8439-01aa75ed71a1/language-en . These inform a bounded stylized renderer, not a meteorological/ecosystem model.


Cloud-rendering sources inspected:

- [miHoYo GDC 2021 presentation](https://media.gdcvault.com/GDC+2021/2021GDC+_+Haoyu+Cai+_+presentation+file.pdf), cloud growth and packed lighting slides 26–28.
- [Vertex Fragment's original stylized puff investigation](https://www.vertexfragment.com/ramblings/stylized-puff-particles/), light/rim/depth/mask channels. This concerns Zelda-like particles, not a verified Nintendo sky renderer.
- [UHawk VR signed-distance-field cloud renderer](https://blog.uhawkvr.com/rendering/rendering-volumetric-clouds-using-signed-distance-fields/), bounded empty-space stepping and static-field tradeoffs.
- [Cyanilux cloud plane shader](https://www.cyanilux.com/tutorials/cloud-shader-breakdown/), layered noise and transparency limitations.
- [Yuichiro Tanabe, Art of Sky](https://media.gdcvault.com/gdcsummer2020/presentations/Tanabe-Yuichiro-Art%20of%20Sky_%20Children%20of%20the%20Light.pdf), composition and color families; it does not publish a cloud-shader implementation.
- [Ghibli's official Castle in the Sky stills](https://www.ghibli.jp/works/laputa/) and the [third-party storm-wall reference](https://images4.alphacoders.com/690/690654.jpg). The latter is not represented as an official studio download.
- [NOAA cloud formation](https://www.noaa.gov/jetstream/clouds/how-clouds-form), [NWS thunderstorm lifecycle](https://www.weather.gov/spotterguide/life), and [Met Office convection](https://weather.metoffice.gov.uk/learn-about/weather/how-weather-works/what-is-convection) inform the visual stages.

All source checks are serial and headless/silent with `SLOPPY_THREADS=1`. Development and benchmark binaries use the pinned official Sloppy 0.29.2. The matched fair browser probe and a separate final rain probe both link all 39 programs; the final rain probe also exercises the quarter-size weather target.


Final medium B/A/A/B: 51.8/52.8/52.8/51.8 ms, five steady aggregates per run; cloud GPU 3.17/3.01/3.02/3.15 ms. Final browser rain check: 39/39 programs linked, no JS/GL errors, portrait 326×706 and landscape 706×326 framebuffers complete, Wasm 135,004,160 bytes. The resize probe now waits for orientation to settle instead of assuming three seconds is sufficient on software rendering. Final package: `aegean.bd8323da6ab28e51.wasm` (10,238,148 bytes), HTML 86,951 bytes, combined zlib-6 estimate 5,191,462 bytes.

Direct artifact links: [day comparison](/var/home/david/dev/tmp/aegean-skies/nature/cloud-comparison-day.png), [storm comparison](/var/home/david/dev/tmp/aegean-skies/nature/cloud-comparison-storm.png), [lifecycle](/var/home/david/dev/tmp/aegean-skies/nature/life-contact.jpg), [near/inside/behind trails](/var/home/david/dev/tmp/aegean-skies/nature/trail-both.png), [browser rain capture](/var/home/david/dev/tmp/aegean-skies/nature/mobile-final-verified.png), [full research notes](/var/home/david/dev/tmp/aegean-skies/nature/cloud-design.md).
