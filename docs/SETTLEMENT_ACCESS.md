# Settlement access

The settlement lake module extends the shared inland-water contract. `lake_at` returns
`WaterSample` with flat `level`, zero `current`, `kind=.lake` and the settlement's stable ID.
`water_at` resolves it alongside rivers; `water_carve` applies its basin in canonical geography.
Do not query rendered meshes for float, walking or wet/dry contact.

`lake_data.jo` contains the surveyed centres, axes, levels and dimensions. Each basin is
1,800 by 640 metres. `LAKE_CLEAR_RUN` is the tested 1,440 m runway; `lake_craft_allowed`
exposes the conservative calm-water/default-fuel aircraft rating at the shipped player speed.
Larger craft are not rated. Presentation of that restriction belongs in the destination UI.

`lake_render.jo` retains at most four nearby meshes and calls the shared inland-water material.
Its fixed local chart is in metres, preserving the sea's dense marks and small glints at distant
coordinates. Do not increase mark scale or reduce density when changing lake colour.

`lake_access_data.jo` and `shore_access_data.jo` hold offline-validated approaches and narrow
landing geometry. A remote harbour belongs to the existing town: town centre, house plots and
market identity remain unchanged. Standard port records supply moorings, loading points, board,
boat and walking deck. `port_landing` is the explicit disembark destination for remote landings.

`settlement_access.jo` publishes the validated living catalogue into physical roads, plus local
shore spurs. The bounded vector field in `road_material.jo` paints those routes directly on the
terrain. It adds no raised road sheet. Feeder bends stay intact after validation; simplifying a
nearly straight corner can clip a house or cross a steep step.

Offline generation, with the normal project headless/silent environment:

1. `tools/inland_lake_survey.jo` surveys candidate basins. Review its output before changing data.
2. Rebuild the world asset if lake geometry changes, then `tools/bake_lake_access.jo`.
3. `tools/bake_shore_access.jo` surveys narrow island landings and refuses unsuitable shores.
4. `tools/bake_inland_connections.jo` extends the current cart graph and repairs stored paths.
5. `tools/bake_living_routes.jo` includes those connections, validates new ship lanes and writes
   the final catalogue. It may reuse existing ship lanes only for matching terrain/layout keys.
6. `tools/inland_access_audit.jo` lists every settlement and its route to a water landing.

Existing saves append new cart links without replacing old link IDs or active journeys. No
markets, money or carriers are created by this upgrade. New games seed their normal services
from the complete catalogue. The saved fleet remains unchanged when an old game gains roads.

Functional checks: `lake_test`, `lake_access_test`, `lake_flight_test`, `access_connections_test`,
`inland_access_test`, `water_field_test`, walking/contact and ordinary flight. Native and WebGL2
captures are needed for terrain/water depth agreement; desktop captures are not GPU benchmarks.
