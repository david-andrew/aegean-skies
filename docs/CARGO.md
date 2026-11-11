# Owned cargo and carrying

A job reserves goods that already exist. Its quantity is split into loads of at most 25 kg,
with stable cargo IDs, beneficial owners, original source IDs and source quantities recorded
at posting. Opening stock, named production and actual arriving imports are the only sources
of goods. Dispatches reserve existing correspondence; a completed import produces its receipt
before offering a report job. Posting and claiming never issue goods.

`World.cargo` describes the physical load. The existing market, personal, aircraft, salvage,
lost-property and boat inventories remain accounting projections, partitioned by these lots.
Custody can stay with an origin store while a porter carries its reserved load; it changes
when the load is actually stowed. Likewise, aircraft custody persists during collection until
the receiver signs. This keeps capacity, reservations, ledger totals and title separate from
physical position without counting the same goods twice. A consignee can sign at the aircraft
and continue walking home with the same crate. A hired collector completes the walk to the
agreed destination first.

The board and sender conversation offer sender-arranged carrying, a sender-paid licensed
porter, or player fetching. Local errands explicitly need no aircraft. Porters are named
residents with a secondary dock trade, not temporary spawned people. Selection checks their
actual location, injuries, other duties, existing carriage and affordability. Each portable
load has a funded fee (40 cents plus 2 cents/kg) reserved from its payer, paid exactly once at
handover, or refunded if cancelled. An explicit porter request waits if nobody can be hired.
Player fetching earns a funded bonus of up to 80 cents and a small relationship improvement.
The destination conversation also allows the player to take over collection.

On foot, F picks up a permitted load in reach. With full hands, walking is 1 m/s and boarding
is disabled. F at the aircraft's actual quay loading point stows it; elsewhere F puts it down
at the player's saved position. At a delivery marker it hands over the load. Purchased player
stock waits at the warehouse and follows these same controls. Personal goods have to return
to their market's handover spot before sale. Cargo aboard is inside the hold; cargo on the quay
and in a person's arms is drawn from saved records. One visible warehouse stack may represent
several restocking lots of the same owner and good. The old anonymous goods decorations and
scene-only Pending crates are removed; lamp posts, bollards and empty architectural fixtures
remain scenery.

The geometry adapter reads the actual Town quays, houses, moorings and boats. Boat deliveries
use a walkable handover point next to an actual moored boat and draw the received goods aboard
that boat. A foot delivery between same-island settlements updates the person's settlement
without moving their parked aircraft. Working fishers' production stays aboard their saved
workboat while at sea. Existing wholesale production, imports and NPC trading remain abstract
economic transactions; promised deliveries and player purchases use physical handling.

Near the observer, the one saved carriage action leases its person to the scene. Navigation
runs on a new leg using the player's `walk_step` sea, slope, quay and building collisions; frame
steps only follow that path. Far away, the same action advances by distance and walking speed.
Scene folding preserves the current pose, route, carried identity and tick, with no catch-up
or second movement owner. A blocked scene route cannot finish abstractly by leaving view.
Aircraft absence and full holds wait and retry; cancellation drops the actual load, refunds
unused porter escrow and preserves its owner. Terminal loaded cargo requires a real return
handover. Theft and ditching affect cargo actually aboard; a crate in dockside hands stays
there. Salvage preserves each client's title and source, with the loss retained historically.

Decisions, worker selection, economic rules and world ticks run per game minute (2 seconds).
The existing 60 Hz scene clock advances walking and aircraft physics. The notebook's live
entries name the worker, cargo location or blockage; it is a projection, not another scheduler.

## Accessors and save contract

- `living_portage.cargo_status(world, job)` gives the current named handling/waiting line.
- `World.cargo[id]` gives owner, source, job, contents, custody and physical location.
- `cargo_view.cargo_position(world, lot)` resolves people/aircraft/boat references for rendering.
- `World.people[id].name/pose/carrying/carriage` identifies the real carrier and load.
- `World.carriage[id]` gives task phase, walking path, payer, fee, escrow and blockage.
- `cargo_pick_up`, `cargo_person_pose`, `cargo_put_down` are the shared player hand commands;
  `choose_collection` cancels/refunds previous handling before player takeover.
- `configure_cargo_scene` adapts geometry; `step_cargo_scene` uses the shared fixed clock;
  `fold_living_scene_for_save` also folds carriage before writing a save.

Cargo schema 1 is saved with the world. Canonical serialization orders all cargo/provenance,
index, task, boat and local-tender maps. Validation checks stock partitions, sources, custody
indexes, IDs, people, locations and tasks. Pre-cargo headers/worlds are explicitly rejected
with a migration message. Reads and writes preserve both old slots; there is no silent new
game or conversion that issues extra goods.

## Verification driver

Run `sloppy check aegean.jo` and `sloppy test tests` with isolated `SLOPPY_SAVE_DIR`. On this
machine always unset DISPLAY/WAYLAND_DISPLAY and set SLOPPY_NO_AUDIO=1. The two existing scalar
wear/part-health failures in `living_scene_flight.jo` are independent of cargo.

`tools/cargolab.jo` is a deterministic scene acceptance driver. It agrees to Porto's existing
medicine job, walks the load with an actual funded resident, stows it, flies the existing
physics/autopilot, commits a real arrival and waits for collection/payment. `CARGO_PLAYER=1`
also walks the player to the load, picks up/drops/restores/stows it and completes a local boat
errand before the same flight. Physics and the world both advance at 60 Hz; batching steps
only reduces rendered frames. `CARGO_CAPTURE=quay|porter|player|collection` freezes a real stage
for `SLOPPY_SCREENSHOT=... SLOPPY_FRAMES=...`. Without capture it quits after asserting success.

The opening grain shipment now occupies its actual unloading berth, with Marta waiting;
patrol starts at the buoy. The dated pirate manifest includes handling time. These authored
opening conditions replace assumptions that unloading could complete remotely at a buoy.
Tests that formerly expected instant load/payment now wait for the physical receipt; the
occupied-berth fixture explicitly fills the desired docks.

Art is deliberately plain. Large crowds do not yet avoid each other's bodies, obstructed
routes need player intervention or cancellation, and real combat remains a separate task.
