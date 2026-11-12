# Tuning the Aegean geography

The original ten islands remain defined by `ISLANDS` in `src/world.jo`. Their coordinates, profiles, erosion bake and canonical vertices are unchanged. Near coasts, contact and rendering now add sub-source refinement to their triangles; see [coast-refinement.md](coast-refinement.md). New geography lives outside the protected ±20 km square. Coordinates are metres at query boundaries; the authored region/range/group controls in `src/geography.jo` are kilometres, with x east and z south.

## Authored controls and seeded variation

- `LAND_REGIONS`: nine major outlines. Their vertices define the large gulfs, headlands, channels, peninsula fingers and large islands. Kilometre-scale noise refines the signed-distance coast before the 896 m macro bake; a smaller three-octave perturbation adds coves at query time. Narrow channels must leave room for those perturbations.
- `MOUNTAIN_CHAINS`: region, endpoints, width and peak envelope for 33 range segments. Noise bends the spines; overlapping segments form several ranges instead of a single stripe. Only mainland envelopes approach 2,950 m; the largest southern island is near 2,400 m.
- `LAND_BASINS`: 12 region-specific river/basin corridors with width and terminal floor. They lower the existing relief, with warped coordinates and varying width/floor. They are a procedural drainage approximation, not a hydraulic simulation.
- `PRINCIPAL_ISLANDS`: a dozen larger drowned summits placed before the random tail. The existing archipelago sits inside the central group and retains its own protected water space.
- `ISLAND_GROUPS`: six elliptical arc/corridor controls: centre, radii, angular interval, scatter and orientation. One random candidate in three goes to the central plateau; the remainder rotates through all five other corridors. A test requires every group to receive islands.
- Remaining radii follow a truncated Pareto proposal with exponent 0.95, minimum 100 m and maximum 8 km. Minor axes are 30–70% of major axes; orientations follow their group with bounded variation. Candidates overlapping the legacy reserve, mainlands or other islands are rejected. Consequently the accepted distribution is not an unmodified analytic power law; inspect the measured bins when tuning.
- Large candidates use moderate peak envelopes; many small ones are low rocks/islets. Small islands select the existing `.cliffs`, `.hills`, `.rock` or `.cay` profiles from their size/height class. No new island material style is introduced.

The final v4 seed 7319 produces 660 accepted principal/seeded islands. Major-radius bins are 475 below 300 m, 147 from 300 m to 1 km, 15 from 1–2 km, 13 from 2–5 km and 10 at least 5 km. The six groups contain 269, 72, 65, 93, 91 and 70 islands. These are generated counts, not a list of real named Greek islands.

## Shared ground and vegetation rules

`src/landforms.jo` contains the original island coastline and height-profile arithmetic, extracted into public functions. Small islands use it directly. Mainland coasts blend the same hill and cliff profiles according to signed-distance curvature: concave sheltered bays favour hills/beaches; convex exposed headlands favour cliffs. The original slope/elevation shader then selects limestone, sand or vegetation. Coast curvature, depth and region outlines remain available for future harbor-site searches; this change places no harbors or towns.

The 8 m authoritative source includes erosion height and ridge data. Computing the original filter per query was too expensive, so the bake creates a 98,304-byte periodic directional basis using that same filter: original 1,000 m units, 0.13 scale, 0.2 strength, three resolved octaves, eight slope directions, 64² samples at 8 m. Runtime blends neighbouring directions, shifts phase by seed and fades amplitude off flats/beaches. This approximation uses a moderate reference slope and neutral ridge/valley fade; it does not reproduce the complete five-octave, locally oriented legacy bake. The 512 m repeat is a known tuning limit. Original island erosion remains unchanged.

The source is quantized, interpolated on 8 m cells and projected onto the same 14 m canonical triangles used by rendering/contact queries. A bounded render-thread memo accelerates repeated samples; physics and parallel chart queries are pure and do not depend on cache order. The macro interior gradient shortcut is checked against the finite-difference footprint.

New terrain supplies the original shader's 5 m normal footprint, fbm/noise tint and erosion-ridge channel instead of a constant ridge value. The only new elevation policy fades vegetation from 900–1,800 m into the existing bare limestone material. The old islands never reach that range. There is no snow, new palette or new lighting model. On new land, existing limestone bands are filtered by their screen-pixel footprint to prevent distant aliasing; resolved nearby bands retain their original values and unresolved ones approach their mathematical means. The original-island shader specializes the same function with these extensions disabled, preserving its shading and cost.

`src/world_groves.jo` streams the existing pine/bush meshes, grove ecology thresholds, shade/scale variation, instancing shader, wind and aerial perspective. The shared ecology helper preserves the original islands' random draw order. New candidate cells use independent deterministic seeds on the original 26 m grid. No houses means no house-adjacent cypresses. Above the original islands' height range, the same 900–1,800 m vegetation fade is used.

Grove residency is capped at 64 reusable buffer sets; one new grove is prepared per update. Only fully published canonical near tiles within 700 m receive trees. This is intentionally a shorter tree range than the original whole-island grove draw distance, to bound cost over a continent. Far forest representation remains the shared ground material. The original island groves and their draw range are unchanged.

## Rebuild and check

Bump `GEOGRAPHY_VERSION` when changing generator behavior, not only authored data. Run `sloppy --release tools/bake_world.jo` to regenerate the ignored `assets/world.bin`, including the erosion basis. It contains the validated macro field plus basis, not a country-wide fine terrain bake. The full bake command remains `tools/bake.jo`.

Relevant checks are `tests/geography_test.jo`, `tests/world_detail_test.jo`, `tools/terrain_check.jo`, `tools/world_cache_check.jo`, `tools/world_depth_check.jo`, and the 720-frame `tools/world_flight.jo`. Use the headless/silent environment in the README. `tools/geography_stats.jo` reports sampled region area/peaks and the native/wasm fingerprint. The game's `AEGEAN_WORLD_CHECK=1` prints the same fingerprint in either backend.

The whole-world chart omits subpixel erosion at its roughly 780 m horizontal pixel spacing; its coastline/profile geometry uses the same source. The local chart remains unchanged. The sea's exact near-water queries retain authoritative source heights, while wholly dry/deep cells can skip erosion. Neither the sea material nor the sky/cloud implementation is changed.
