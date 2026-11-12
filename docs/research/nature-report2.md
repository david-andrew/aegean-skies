# Nature 2: cloud lobes and the cove

Branch `t3/nature-2`, based on merged main `473d5ca`. No push; own worktree only.

## Result and acceptance

The cove defect is fixed: a narrow sand strip follows the waterline, and the low inland shelves are green again. Clouds now have a hierarchy of rounded heads, narrower unions, grouped light values, a shared cool underside and fine final-resolution grain. **The film-indistinguishability goal is not achieved.** The label-hidden self-check still identifies every source; this is an improvement to the procedural renderer, not an honest claim of matching the film.

All merged tree/prop work is preserved: no changes to `objects.jo`, instanced props, `quality_trees(lists[k])`, `PLANT_KINDS`, chapel placement or uv.x=173 tags. No UI changes.

## Implementation

`cloud_density.jo` builds 316 lobes per stamp: one foot, seven rounded main heads, 77 shoulders and 231 smaller lobes. Shoulders use a staggered spherical distribution rather than two regular rings. The three fair shapes vary their proportions/lean; the storm stamp has enlarged heads. The narrow smooth union (at most .012, formerly .065) preserves lobe shoulders. Lower displacement amplitude avoids replacing the round forms with melted noise; the normal finite-difference span is smaller. The condensation cut is flat apart from a small irregularity.

`cloud_volume.jo` uses two narrow light transitions and subtle within-band variation. Seventy percent local normal lighting preserves each head; thirty percent broad form lighting connects neighboring heads into a wash and reduces repeated dark crescents. High-tier self-shadow, warm sun response, cool storm shade, rim and aerial haze remain. Fine pigment lives in the form; paper grain is applied once after reconstruction to visible fair-cloud pixels, at the final pixel resolution, with no texture/history allocation. Dense weather keeps only form-space pigment to preserve its tighter GPU budget. The first screen-grain hash left diagonal rows, so the final hash decorrelates the axes. Final grain amplitude is 1.2%, not the much stronger trial.

The atlas remains four 64³ stamps in a 1056² RGBA8 texture. The distance marcher, reduced-target policy, weather layers and cloud count budgets are unchanged. Without sun shafts, the composite quad is restricted to the union of conservative cloud rectangles plus two low-resolution texels for reconstruction; with shafts it remains full screen. Clear pixels skip grain. This avoids paying for paper texture over empty sky or terrain. `CLOUD_BASE` is shared by the bake, initial placement, banks and lifecycle; a regression check links the actual baked floor to that constant so changing the cut cannot make a growing cloud float above its condensation level. Trail occlusion continues to read the same distance atlas.

The sand problem had two causes. Sand reached 3.5–6 m, and the vegetation height ramp exposed pale rock up to 9–17 m. More importantly, `island_height_ridge` clamps eroded inland basins at 1.5 m. A first 3 m sand cap still flooded that shelf. The final sand fade is **.65–1.35 m**, below that shelf, and only on gentle slopes (full strength below about 15°, gone by about 28°). Maquis material returns between .6 and 1.5 m. Dry sand is (.78,.71,.55), close to the existing wet-sand hue, instead of (.95,.88,.70). Geometry/collision are unchanged. The original height envelope is retained for animated meadow wash: coastal maquis does not incur the grass-gust shading cost.

## Visual comparisons and limitations

Artifacts are under `~/dev/tmp/aegean-skies/nature/nature2/`:

- `comparison-3.png`: supplied porco028, final game, previous game. Approximately matched cloud height; crop and isotropic resize only, no grading or retouching.
- `comparison-frontal.png`: an additional frontal-light comparison, with both game versions captured from the same camera. It is supplementary, not a replacement for the six-view check.
- `game-1.png` through `game-6.png`: three stamps at six headings, 14:00 lighting, ordinary game shaders and post-processing, 1280×720 headless captures. `cloud-far.png` is a separate 2× horizontal-distance/telephoto check; it is not substituted for the near views.
- `blind-12.png`, `blind-key.json`, `blind-observations.md`: six film crops from four supplied stills, six game crops, displayed at 320×320. Some are lobe details rather than whole isolated clouds. The script stores every source rectangle and random permutation. These are not twelve statistically independent clouds.
- `features.py` / `features.json`: cloud-interior texture diagnostic, described below.
- `cove-air-baseline.png` / `cove-final.png`: matched before/after camera; `cove-water-baseline.png` / `cove-water-revised.png`: waterline check.
- `storm.png`, `field.png`, `inside.png`, `trails.png`, `horizon.png`, `bank.png`, `field_sunset.png`: broader renderer checks, including reconstruction across an opaque horizon and the full-screen sun-shaft path.

The first hard-ramp trial looked like stacked cutouts. Reducing contrast, varying the shoulder radii and adding the broad wash improved it. The final shadows remain more regular than the reference, the small lobes are limited by the 64³ field and reduced render target, and the procedural pigment is not hand-painted brushwork. The film's sky/scan texture also differs from the game's. No reference pixels enter the assets.

For the label-hidden self-check I recorded descriptions/guesses before reading each random key. Both the first check and the broad-wash check scored **12/12 correct**, so the target failed. This is **not an independent blinded reviewer**: I wrote the renderer and had seen its other images. Two small foreground fragments in the first set were removed for the later set; background hue still reveals provenance. The final grain-only adjustment retains the later permutation for a reviewer; the 12/12 score belongs to the earlier broad-wash version, not a new independent trial of the final pixels.

The separate one-feature check masks bright low-chroma cloud interiors, erodes the mask four pixels, computes luminance RMS after a sigma-1.2 Gaussian high-pass, then uses leave-one-out nearest class mean. It excludes most sky and silhouettes. Six samples per class, scan/JPEG versus native captures, and crop resampling confound it; it measures separability of these images, not artistic quality. Final film/game RMS means are **0.00244 / 0.00260**, versus **0.00244 / 0.00365** in the broad-wash trial. The final one-feature classifier scores 3/12 (its class means overlap enough that the leave-one-out decision is unstable). **This is not held-out validation**: the metric was used to tune grain strength on these same crops. It only shows that grain energy was brought closer; it does not overturn the failed visual match.


### Comparison sheets

![Film, revised cloud, previous cloud](/var/home/david/dev/tmp/aegean-skies/nature/nature2/comparison-3.png)

![Frontal comparison with both game versions at the same camera](/var/home/david/dev/tmp/aegean-skies/nature/nature2/comparison-frontal.png)

![Cove before and after](/var/home/david/dev/tmp/aegean-skies/nature/nature2/cove-comparison.png)

![Twelve shuffled film and game cloud crops](/var/home/david/dev/tmp/aegean-skies/nature/nature2/blind-12.png)

Earlier research remains in `nature/cloud-design.md`: the [Genshin GDC presentation](https://media.gdcvault.com/GDC+2021/2021GDC+_+Haoyu+Cai+_+presentation+file.pdf), the [Vertex Fragment stylized-puff investigation](https://www.vertexfragment.com/ramblings/stylized-puff-particles/) and the [SDF-cloud renderer article](https://blog.uhawkvr.com/rendering/rendering-volumetric-clouds-using-signed-distance-fields/) motivated compact reusable shapes and grouped shading. This implementation does not claim to reproduce those games' sky pipelines.

## Validation

- Six sky tests pass, including atlas gutters, connected support, bounds and the new bake/lifecycle floor check.
- Thirteen nature tests pass, including deterministic weather, lifecycle continuity, large banks and analytic weather geometry.
- Native and packaged Wasm builds pass. The existing chart unused-variable and living_geometry web-file warnings remain outside this change.
- Generated GLSL minimum-resource audit and web compatibility checks pass. Browser shader and resize details follow below.
- Headless inside-cloud/trail captures use the same distance field and render ordering as main; no trail compositing code was changed.
- No unrelated multi-day replay or flight-physics suites repeated: simulation and flight integration are unchanged.

## Performance and delivery

All reported timing is from the **redfox laptop, 192.168.1.79, Intel UHD620**, 1280×720. Each run holds `~/dev/tmp/bench.lock`; `uptime` is logged before each run and load1 must be <1.5. A/B order alternates ABBA/BAAB. Benchmark runs are serialized, with `SLOPPY_THREADS=1`. Desktop captures are headless and silent. Frame/GPU values are medians of the engine's two-second aggregates after discarding the first interval, then medians across runs where repeated; they are not individual-frame medians or real-phone timings. Fair low/medium/high each use two runs per version (ABBA/BAAB); the final storm/cove/rain follow-ups use one alternating A/B pair each, so those have less replication than the earlier complete comparisons.

`bench/` is the superseded pilot-5 comparison. `final-bench/` is an explicitly stopped partial grain trial. `accepted-bench/` is the superseded full-screen-grain comparison: it exposed a consistent ~.2 ms cost and was rejected despite the provisional directory name. **`bounds-bench/` is the final-code comparison.** The earlier cove terrain regression (~.34 ms GPU) was the grass-wash issue fixed above; the later full-screen grain cost motivated bounded compositing and the clear/dense-weather grain skips.

Final measurements follow below. The cloud atlas source changed, so after merging run `SLOPPY_THREADS=1 sloppy --release tools/bake_clouds.jo` (the PNG is ignored) before native/web builds. No terrain/world rebake is needed. The shoreline commit is `1ee5966`; clouds are a separate commit so the cove fix can be reviewed/landed independently.

## Final measurements

Final gate: 20 runs, starting load1 **0.247–0.772**. One five-minute lock wait preceded the suite; no high-load run was started. All runs exited successfully.

| Scene / tier | Main frame ms | Revised frame ms | Main cloud GPU ms | Revised cloud GPU ms |
|---|---:|---:|---:|---:|
| Low · fair | 44.72 | 44.42 | 2.79 | 2.69 |
| Medium · fair | 57.45 | 57.00 | 3.17 | 3.07 |
| High · fair | 79.85 | 79.88 | 3.21 | 3.10 |
| High · storm | 16.50 | 16.40 | 4.36 | 4.25 |
| High · cove | 70.60 | 69.10 | 1.40 | 0.43 |
| High · rain | 48.00 | 47.80 | 5.01 | 4.91 |
| Low · storm | 16.00 | 15.90 | 4.35 | 4.23 |

The measured cloud medians are below the approximate 5 ms budget. High fair whole-frame time differs by only +0.025 ms (below the engine aggregate’s 0.1 ms reporting resolution); the other final cases improve. This is no material measured regression, not a worst-frame or real-phone guarantee. Cove terrain itself is 6.43 → 6.33 ms; most of its total gain comes from skipping empty composite pixels (cloud zone 1.40 → .43 ms).

| Storage / observed memory | Main | Revised |
|---|---:|---:|
| Cloud PNG bytes | 1,064,079 | 737,057 |
| Decoded atlas bytes | 4,460,544 | 4,460,544 |
| Packaged HTML + Wasm bytes | 11,268,377 | 10,944,010 |
| zlib level-6 transfer-size proxy, bytes | 5,487,073 | 5,159,440 |
| Native peak RSS, scene medians KiB | 114,752–117,522 | 105,834–110,706 |
| Browser Wasm memory snapshot, bytes | 131,203,072 | 124,583,936 |

Native RSS is measured by `/usr/bin/time -v` in the paired laptop runs. The browser memory figures are desktop Chromium/SwiftShader snapshots, not Android memory measurements. Browser-tree PSS varied from 936,069 KiB in the baseline probe to 1,014,386 KiB in final verification, with different warm-up/resize/frame counts and shader caches; that difference is not an isolated causal memory delta. The firm GPU-storage result is no new atlas/target allocation. The compressed build is smaller.

Browser correctness: **41/41 programs linked**, no captured JS/GL errors. The portrait/landscape checks produced 326×706 and 706×326 canvases with complete framebuffers and GL error 0; final-code verification linked all programs again. Generated shader audit: **68 stages, zero violations**; cloud FS 19 uniform rows, composite FS 10, both with two samplers; composite VS two rows. These fit WebGL2 minima.

Native final binary SHA-256: `1556009c19af07fe6aad2afd5144c296e0ebbe1a9404281457a877842a40d4a7` (verified identical locally and on redfox). Official pinned Sloppy 0.29.2; build/test commands and raw logs are in `nature2/`.

## Remaining gap

Do not describe the cloud film match as complete. The cheapest next focused experiment would be a baked, artist-controllable broad shadow/brush field per formation, compared with the current broad-normal approximation. That could replace a channel using packed normals rather than add a texture, but it needs a measured prototype and new all-angle/lifecycle review. Simply adding more screen grain failed; increasing atlas size alone was not justified by this pass. A real Android hardware performance result is still unavailable; browser correctness and laptop low tier are proxies.

