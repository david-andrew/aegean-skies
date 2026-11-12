# Vessels and sea lanes

`vessel_types.jo`, `sea_routes.jo` and `vessels.jo` are a serializable physical
extension to the living world. They do not import rendering, create economic
stock, mint people or choose national fleet sizes. Distances are metres, speeds
metres/second, and yaw is radians with the bow along local +z.

## Ownership and registration

The caller supplies stable `Vessel.id`, `owner`, `side`, `cargo` (existing lot IDs),
`crew` (existing person IDs), `convoy` and `escort` (leader vessel ID). IDs below
700,000,000 are available to fleet callers; the scene reserves 700,000,000 + Trip
ID for existing fishing trips. Match `side` to the combat caller's faction scheme.
`spawn_vessel` rejects duplicates, missing owners, capacity overflow and a lane
whose start, draft or beam clearance does not fit the hull. `spawn_convoy` is
atomic: failure leaves the original fleet unchanged. Capacity is 128 hulls.

A typical voyage:

```sloppy
lane = request_harbor_lane(fleet, origin_place, destination_place, .coastal_steamer)
if lane >= 0:
    route = fleet.lanes[sea_lane_index(fleet, lane)]
    port = world_settlements[settlement_by_id[origin_place]]
    ship = Vessel(id=existing_ship_id, kind=.coastal_steamer,
        owner=existing_owner_id, side=country_side, cargo=lot_ids, crew=person_ids,
        lane=lane, position=vec3(route.start.x, 0, route.start.y),
        yaw=atan2(f64(port.out.x), f64(port.out.y)))
    spawn_vessel(fleet, ship)
```

Registration is not permission to teleport an existing ship to that start. Use
its actual position with `request_sea_lane` for subsequent voyages, and
`set_vessel_route` once docked, anchored, stopped or captured. This validates the
new start against the existing pose. Choose initial yaw from the berth's outward
vector when materializing a new owned hull. `vessel_berth` derives a water berth
from the settlement registry's actual quay, sampling the full hull length so a
long hull cannot straddle a breakwater; deep hulls may receive an anchorage
instead. It does not reserve a quay slot or resolve a strategic harbor blockade.

## Navigation and motion

Use a completed, stable settlement catalog for navigation (`settlement_registry_ready`;
headless callers can use `finish_settlement_registry()`). A route must not race
the renderer's initial incremental pier catalog.
Call `step_sea_navigation(fleet, 64)` once per frame (32 on the phone tier).
Its return value is the number of canonical depth queries, never above the
supplied budget. It runs one search at a time, capped at 12,000 nodes and 32
resident lane records. Requests for identical endpoints and clearances share a
lane. `retire_sea_lane` removes an unused route after its search finishes.

Route status progresses through queued, searching, validating, then ready or
blocked. Only ready routes contain published points. Coarse A* includes checked harbor-mouth approach candidates and checks water and
piers; final checks sample the full candidate every 7 m on its center and both
clearance edges. Rejected edges are blacklisted and searched again, at most 64
retries. A long inter-capital route can take thousands of small batches. Queue
it in advance; do not complete the search synchronously in game startup.
Navigation is deterministic across budgets and survives a save mid-search.
These sample bounds are not a proof of continuous swept-hull clearance.

`step_vessels(fleet, wind_velocity_xz, elapsed_seconds)` advances fixed 30 Hz
motion, with acceleration, arrival braking, wind-dependent sail speed, same-lane
traffic spacing and runtime hull-corner guards. A failed footprint guard stops
on the last pose and emits blocked. These working sail craft use auxiliary
propulsion in adverse wind rather than inventing unvalidated tacks. No crossing
traffic policy or naval tactical controller is implied by `escort`; its stable
leader ID is available to the war controller. Do not call with huge catch-up
intervals on the render thread: every elapsed fixed tick is deliberately retained.

An `external` hull reads an existing owner's pose and never integrates again.
The scene currently binds only real fishing trips from `query_boats`, including
their dawn departure, stationary fishing period and morning return. It does not
start fishing or award catches. Public ferry/tow tasks have no suspendable vessel
lease yet and are deliberately not bound: their passenger is not a ship owner.
The trade/war adapter must register its saved ships and transfer movement
ownership explicitly; the game does not seed a second decorative trading fleet.

## Combat, damage and durable outcomes

`publish_vessel_targets` exposes oriented `CombatBoat` hulls within 6 km. Their
`external=true` flag prevents combat from integrating them again. After the
combat step, `receive_vessel_hits` returns health loss and attacker ID to the same
vessel. Existing CombatBoat callers retain their previous defaults.

`stop_vessel`, `resume_vessel`, `capture_vessel`, and `damage_vessel` report state
changes. Capture changes the supplied physical owner/side but preserves cargo and
crew identities; the world controller must commit their legal/economic custody.
Damage can burn, flood and sink a hull. Lifeboats release the same crew IDs once,
after six seconds; hulls with no lifeboats retain a crew-in-water record with
zero boats. The hull finishes sinking after 65 seconds. No passengers,
rescue money, cargo salvage or replacement ships are created.

`take_vessel_events` transfers the pending queue (monotonic serial, vessel ID,
kind, position, owner, attacker, previous owner where relevant). Persist the
consumed serial together with the corresponding world transaction. A damaged
fishing boat holds its existing actor's scene movement lease; the living adapter
must resolve production, rescue, custody and eventual lease release; the existing
labor accounting does not itself read physical ship losses.
`resume_workboat_trip` releases a stopped fisher's lease without elapsed-time
catch-up. Sunk or captured trips need their strategic terminal transaction.
`take_vessel_survivors` transfers/removes a crew-survival record once.
`retire_vessel` is for identities whose outcome has already been committed.

Save the entire version-1 `VesselFleet` with World in the same checkpoint,
including pending navigation, accumulator, event serials and survivor records.
Graphics caches and `VesselBindings` are rebuildable and must not be saved.
The main branch here only reconstructs fishing projections; full fleet save
integration and the trade/war transaction consumer belong to that adapter.

## Aircraft and rendering

`collide_vessels` sweeps an aircraft body against oriented hull ellipsoids and
applies aircraft contact damage and a mass-scaled hull impact. The main game
calls it for the player and through an optional traffic contact callback before
each NPC scene commit. It approximates the body with a span-derived margin,
not every wing contact. `find_vessel_mooring` / `vessel_mooring_point` find a slow,
large vessel's water-side berth, verify water under the aircraft and release it
when the ship departs or sinks. Existing F interaction moors beside it; boarding
and deck walking are not implemented.

`VesselView` is observer-only: one new model type built per frame, shared meshes
and instance buffers, 6/16 near hulls on low/normal tiers, 2/6 wakes capped at 24
points, and cheap far hulls to 10/24 km. Ship shaders use camera-relative
projection and existing world curvature. Sails fill/furl with wind and motion;
three swell samples pitch long hulls, sailing hulls heel, funnels trail smoke,
and night windows/navigation lamps emit light. There are no shadow-map or
screen-space reflection passes. The chart reads nearby ships and verified lanes;
only lanes actually requested by the world appear.

`tools/vessellab.jo` contains explicit synthetic acceptance scenes, never loaded
by normal startup. `VESSEL_SCENE` selects morning, steamer, schooner, convoy,
night, catalog, or sinking; `VESSEL_QUALITY=0` selects phone bounds;
`VESSEL_MOVE=1` advances the scene. `tools/vessel_route_check.jo` verifies real
harbor routes, reports bounded navigation cost and exercises 128 bodies; wall
measurements belong on redfox under its shared benchmark lock.
