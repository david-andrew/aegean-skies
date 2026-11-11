# Settlements and roads

`src/settlements.jo` owns places without owning people or economies. Load the
legacy and geography assets first, enable geography, then call
`init_settlements()` (compact records and pending road links only). In the game
`init_world_towns(towns)` performs that call. Pass `true` only for an explicit
offline/eager topology check.
No additional world assets are shipped.

The original six settlement IDs, names, centers and mooring positions retain their
order. New IDs are sparse, derived from region/candidate coordinates or island ID.
Use `settlement_by_id` to resolve them; do not use an ID as an array subscript.
Countries are the original archipelago, Kalyra and Orenthia. Names are generated
from fictional syllables, with deterministic collision resolution.

Major coasts are searched from both sides of the authored shore and refined
against actual height. Harbor candidates need low, moderately sloping dry
approaches and deep water beside their pier. Bay shelter and a broad low
hinterland rank capital sites. Inland candidates use a jittered lowland lattice;
steep terrain and high peaks are excluded. Small islands under 380 m are left
empty; larger ones receive a suitable harbor, shoulder village, monastery or
chapel. Unsafe building parcels remain vacant.

`WorldSettlement` supplies ID/name/kind, target size, country/region, center,
seaward direction, radius, seed, local old-quarter center `old`, moorings,
verified neighbor IDs, road indices and optional
legacy index. Parcel/street/central-landmark generators describe new places; use
the original `Town.houses`, `Town.quays` and `Town.blocks` for legacy geometry.
`size` is an intended settlement class, not a promise to force
buildings onto unsuitable ground. `place_lots` gives deterministic local lot
records; `place_ground_lot` applies canonical corner checks, and `place_parcel`
resolves a stable `(i,j)` identity to an actual footprint. Negative `j` rows belong
to the old quarter; nonnegative rows are the later courtyard blocks. The grid
indices no longer imply a district: district ownership comes from the lot's
actual local coordinates, divided by 160 m. `place_to_world`/`place_to_local`
convert them, and `place_candidate_cells` supplies bounded contact candidates;
`place_streets` gives paths for a nominal 160 m district; `place_landmarks` gives
central destinations. Mooring records contain water positions, quay endpoints,
width, buoy and deck height. New harbors use 2.4 m decks (original harbors retain
1.2 m), so ordinary swells do not cut through their tops. Registry initialization does not allocate GPU resources.

Roads connect nearby places within their land region using bounded A*. Length and
height change form its cost; sea, high ground and steep grades forbid edges.
Canonical samples at intervals of at most 55 m reject sea crossings or excessive
grades missed by the coarse search. `settlement_roads` now contains stable
**candidate** indices, including rejected/pending links. Check `ready` and at least
two `points` before traversing a road. `ensure_settlement_road(index)` evaluates a
specific candidate; `prepare_settlement_roads(camera)` evaluates at most one
nearby pending corridor. The chart requests one pending link per draw, so roads
appear progressively as they are verified. `build_settlement_roads()` explicitly
finishes all candidates. No remote road geometry is generated at game startup.

Accepted paths retain only horizontal bends (within 4.5 cm of the validated
samples); paving resamples canonical triangles. A coarse 2 km index stores road
IDs, rather than copies of every fine sample. Grove tiles refresh when a new
verified road enters their bin. Rejected links retain empty `points`; they never
become bridges across channels. Verified neighbor/road lists are reciprocal and
sorted by stable candidate index, independent of evaluation order. Width distinguishes a
mule track from a road. This is a sparse network, not an all-pairs travel graph.

# Rendering and quality

`src/world_towns.jo` keeps a maximum of 40 full districts and generates at most one
per render preparation. At most 8–24 nearby/far place plans are resident, selected
by distance and density; distant plans are generated on first approach and evicted
outside that set. There are no worldwide resident house-instance arrays. Eight
shared house meshes cover one to four floors with tiled/flat roofs and balconies;
17 street-furniture meshes are also instanced. Reused GPU buffers hold paving
for each district, while its CPU vertex array is released after upload.
Ground ribbons clip against canonical terrain triangles; stairs remain on
steep narrow alleys. New-town shaders use the terrain renderer’s relative origin
to avoid depth precision loss at country-scale coordinates. The 17 prop meshes cover cafes, shops, pergolas/laundry, benches, flowers,
nets, cats, windmills, churches, fountains, plane trees, cars, bicycles, olive
terraces, beached boats, lighthouses and statues. Cars occur only in capitals.

Capitals and larger towns choose an old-quarter shoulder using the terrain.
Irregular broken lane bands climb around a hill church, with narrow rotated lots.
Later quarters have several boulevards, rotated courtyard blocks, gardens, taller
harbor frontage and gradually thinner outskirts. Small villages cluster tightly
around their church/cove instead of covering a large grid. The terrain is never
flattened for a town. Footprints reserve civic/warehouse areas and the main
approach; collision uses the same warped coordinates and house orientations.

Distant buildings use these same lots, inexpensive white walls and tiled/flat
roofs, varied colors and heights, and lit-window strips. Their heights use the macro land profile; full
parcels use canonical corner checks and replace those blocks by district. Distant
harbor silhouettes retain the piers and capital moles, and hill churches retain
an aerial silhouette. Actual lots/civic precincts and verified road corridors
exclude wild groves; gardens and empty outskirts can retain vegetation. Low cameras in the original protected archipelago bypass
expanded-town rendering. Original town meshes and layouts remain intact nearby;
farther than 1.8 km they use simpler buildings. Original towns also receive
frontage paving, cafe furniture, flowers, vines/laundry, nets and bicycles. Their
enrichment now uploads only the nearby town, using shared prop instances instead
of duplicating prop vertices into large meshes.

Set `world_town_density` from a quality tier, or use `AEGEAN_TOWN_DENSITY=0..1` at
startup. It changes decoration, full-detail radius (180–530 m), and far visibility
(12–45 km). It never changes IDs, roads, collision, or economic data. Zero retains
buildings and principal landmarks. Changing the knob invalidates the bounded
near cache. Original-town enrichment is suppressed at zero. The number of far
plans is also capped at 8 (zero) through 24 (full).

# Living-world integration

The game still seeds exactly the original six living harbors. New places have no
invented persons, stock, jobs or money. Port/mooring data and walking contact are
ready, but the player docking/market/flight adapter must adopt new harbors before
those interactions operate there. Inland places must not become seaplane docks.
Use `(origin_id, destination_id)` route keys, or maintain a deliberate dense
index mapping; replace six-harbor multipliers and `SETTLEMENTS[id]` lookups, and
version/migrate saves before expanding the simulation. `SETTLEMENT_VERSION=2`
preserves place IDs/names/centers/harbors but changes parcel layouts and road
indices: migrate any saved new-world addresses/routes before adopting it. Coordinate facilities,
population, bicycle riders and routines with the living-world implementation.
Display produce and parked scenery are not owned tradable cargo.

The chart draws faint roads and settlement dots, prioritizes capital names, and
suppresses overlapping smaller labels. The local archipelago chart keeps its
existing labels and interaction. No new menus or HUD controls are introduced.

# Validation

Run `tests/settlements_test.jo` for registry/dock/geography/road/determinism
contracts and lazy/eager request-order equivalence; `tests/town_layout_test.jo`
checks varied deterministic quarters and collision/render footprint agreement;
`tests/town_paths_test.jo` checks gap-free canonical paving.
`tools/settlement_check.jo` prints places and distribution;
`SLOPPY_SOFTWARE=1 sloppy --release tools/town_probe.jo` checks bounded streaming,
quality changes, capital building counts, grounding and district reproducibility.
Use the usual headless/silent environment and one worker. Integration evidence,
paired laptop measurements and captures are in the task's external report.
