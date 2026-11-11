# Settlements and roads

`src/settlements.jo` owns places without owning people or economies. Load the
legacy and geography assets first, enable geography, then call
`init_settlements()`. In the game `init_world_towns(towns)` performs that call.
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
seaward direction, radius, seed, moorings, neighbor IDs, road indices and optional
legacy index. Parcel/street/central-landmark generators describe new places; use
the original `Town.houses`, `Town.quays` and `Town.blocks` for legacy geometry.
`size` is an intended settlement class, not a promise to force
buildings onto unsuitable ground. `place_parcel` gives actual footprints;
`place_streets` gives paths for a nominal 160 m district; `place_landmarks` gives
central destinations. Mooring records contain water positions, quay endpoints,
width and a buoy. Registry initialization does not allocate GPU resources.

Roads connect nearby places within their land region using bounded A*. Length and
height change form its cost; sea, high ground and steep grades forbid edges.
Canonical samples at intervals of at most 55 m reject sea crossings or excessive
grades missed by the coarse search. A rejected link stays absent; it is never a
bridge across a channel. Neighbor lists are reciprocal. Width distinguishes a
mule track from a road. This is a sparse network, not an all-pairs travel graph.

# Rendering and quality

`src/world_towns.jo` keeps a maximum of 40 full districts and generates at most one
per render preparation. House and street-furniture meshes are shared; reused
instance buffers hold the current set. Ground ribbons clip against canonical terrain triangles; stairs remain on
steep narrow alleys. New-town shaders use the terrain renderer’s relative origin
to avoid depth precision loss at country-scale coordinates. The 17 prop meshes cover cafes, shops, pergolas/laundry, benches, flowers,
nets, cats, windmills, churches, fountains, plane trees, cars, bicycles, olive
terraces, beached boats, lighthouses and statues. Cars occur only in capitals.

Distant buildings use the same bent parcel grid, inexpensive white walls and red
roofs, and lit-window strips. Their heights use the macro land profile; full
parcels use canonical corner checks and replace those blocks by district. Distant
harbor silhouettes retain the piers and capital moles. Near new towns and indexed road corridors exclude
streamed wild groves. Low cameras in the original protected archipelago bypass
expanded-town rendering. Original town meshes and layouts remain intact nearby;
farther than 1.8 km they use simpler buildings. Original towns also receive
frontage paving, cafe furniture, flowers, vines/laundry, nets and bicycles.

Set `world_town_density` from a quality tier, or use `AEGEAN_TOWN_DENSITY=0..1` at
startup. It changes decoration, full-detail radius (180–530 m), and far visibility
(12–45 km). It never changes IDs, roads, collision, or economic data. Zero retains
buildings and principal landmarks. Changing the knob invalidates the bounded
near cache. The separate original-town enrichment mesh is suppressed at zero.

# Living-world integration

The game still seeds exactly the original six living harbors. New places have no
invented persons, stock, jobs or money. Port/mooring data and walking contact are
ready, but the player docking/market/flight adapter must adopt new harbors before
those interactions operate there. Inland places must not become seaplane docks.
Use `(origin_id, destination_id)` route keys, or maintain a deliberate dense
index mapping; replace six-harbor multipliers and `SETTLEMENTS[id]` lookups, and
version/migrate saves before expanding the simulation. Coordinate facilities,
population, bicycle riders and routines with the living-world implementation.
Display produce and parked scenery are not owned tradable cargo.

The chart draws faint roads and settlement dots, prioritizes capital names, and
suppresses overlapping smaller labels. The local archipelago chart keeps its
existing labels and interaction. No new menus or HUD controls are introduced.

# Validation

Run `tests/settlements_test.jo` for registry/dock/geography/road/determinism
contracts, and `tests/town_paths_test.jo` for gap-free canonical paving.
`tools/settlement_check.jo` prints places and distribution;
`SLOPPY_SOFTWARE=1 sloppy --release tools/town_probe.jo` checks bounded streaming,
quality changes, capital building counts, grounding and district reproducibility.
Use the usual headless/silent environment and one worker. Integration evidence,
paired laptop measurements and captures are in the task's external report.
