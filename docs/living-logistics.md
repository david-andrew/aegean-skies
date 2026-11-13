# Living logistics and national orders

The settlement registry supplies stable sparse place IDs, actual counter/venue positions and
moorings. `World.place_contexts` and `World.far.districts` use those IDs as keys. The original
six harbors remain dense indices for existing trips and UI. A sparse place ID is never a core
array subscript. `assets/living-routes.bin` contains offline hull-verified sea links and registry
roads; the game validates its registry/terrain keys before publishing it.

## Goods, needs and agreements

`CargoSource` identifies the opening, produced or imported batch. Detailed `CargoLot`s and coarse
`FarStock` fragments partition the same issued quantity. A market, aircraft, person's hands,
commission or coaster holds each fragment once. Production consumes labor, wages and the
applicable finite ore/crude/owned inputs. Named far residents and crews are removed from their
citizenship cohorts when promoted or recruited. Markets and households have separate accounts.

Local errands buy the missing part of the recipient's household/boat reserve. Gifts follow real
recorded meetings. Import receipts name an actual shipment. Supply jobs require received dated
buying terms, available supplier stock and actual funds. The initial signed contracts and service
agreements are opening data; their earlier correspondence is explicitly unrecorded. There is no
fever/harvest generator behind generic medical or grain requests.

`WorkProvenance` saves the requester/supplier identities and accounts, causal need, request and
receipt times, agreement price, freight payer, deadline and source batch references/description.
`job_provenance`, `commission_provenance` and `journey_provenance` expose read-only notebook
lines. The structured record remains on the job/commission/journey. Projections never post work.

* Core supplier jobs purchase/reserve existing goods and escrow the carrier's pay. A signed
  buyer pays the invoice on physical collection; insufficient funds retain the supplier's goods.
* Far commissions purchase existing source stock for the receiving counter or explicit sponsor
  and escrow freight. Claim, pickup, aircraft loading and counter collection are separate actions.
  One pair of hands is shared with core cargo. A named sender or funded collector walks the
  same commission; a player can choose manual carriage. Perishable far commissions wait for
  a future batch-age model rather than asserting freshness from aggregate stock.
* Each reciprocal service holds a `FarRestockOrder` from its last counter visit. Departure uses
  that dated quantity/price/deadline, local stock and conditional bank authorization. The return
  journey carries the current counter's order. Empty paid rounds collect orders/quotes under
  the opening service agreement. `cargo_deliveries`, `order_rounds` and total journeys are
  separate counters. Remote live inventories do not choose a service's cargo.
* A counter remembers at most eight orders actually brought by visiting services. Those
  unfilled orders raise its upstream procurement and warehouse targets. The original need
  date, per-good deadline and visited-place ancestry travel with them (at most twelve places).
  Orders never return to an ancestor; quantities are divided among eligible upstream routes,
  served quantities are retired, and repeated arrivals cannot renew a fulfilled order.
  Factory input reserves follow actual paid output recipes. Freight covers the saved route's
  crew time and locally quoted provisions, rather than promising a 500km crossing for a flat fee.
* A manually carried commission can use any actual mooring, including walking between an
  inland counter and a neighboring port. It can be unloaded and reloaded for a transfer; its
  original receiving counter still commits collection. An assigned porter retains the handling
  leg until completion.
* A core sealed dispatch snapshots the public reports held when posted. Those reports reach
  the receiving office only with physical collection of that existing packet. Later news is
  not added in flight. Far mail likewise holds one actual received report.

The coarse economy uses funded household/industry policies rather than a general GOAP search.
Its stock reserves and dated bids can be mistaken by arrival. Disease, agriculture seasons,
household mortality and full supply-chain manufacturing are not modeled.

## Scene ownership

The shared clock runs at 60 physical ticks/second and 120 ticks/game minute. Coarse decisions
run per game minute; frame callbacks step only leased bodies. `far_transport_scene` materializes
an existing economic ship as an external `Vessel`; the vessel integrator does not move it again.
The scene adapter advances that ship's saved journey interval with a physical hull guard. Folding
retains actual pose, damage, progress and last tick. Aircraft use the existing traffic/scene lease.
Walking, wages, local scene admission and figures exclude people bound to an aircraft or boat.

Published routes are hull-verified; current ship motion follows them. Crossing-traffic policy,
independent harbor berth spacing, generic far airline services and scene cart models are separate
work. No second decorative crew or vessel is added when a ship comes into view.

## Politics, forces and war

National treasuries charter existing carriers and pay real local recruits, provisions, stores and
wages. Arsenal conversion consumes actual parts/fuel and pays actual workers. A force follows
saved route orders and carries reports; declarations and ceasefires must reach it. Signed incidents and diplomatic papers retain their original
dates for a90-day delivery window, sufficient for sea-scale correspondence; duplicate receipt
does not refresh them. A patrol revisiting its current town cannot count as another armed entry:
that evidence requires an actual traveled order. A hungry force
may attempt a return home with partially purchased provisions, while remaining unsupplied for
combat. After two actual hungry days, merchants may likewise attempt home or seek grain in a
still-current carried quote, recording the risk and continuing to consume their finite rations.
A finite charter ends through actual return and demobilization.

Provisioning prefers a two-day reserve beyond the next leg. Its minimum covers actual daily
meal boundaries through arrival, with at least one transit ration per person even on a short
crossing. Failure to refill that preferred reserve does
not strand a crew already carrying enough owned food. A smaller paid purchase may cover the
leg; an ordinary underfed departure still refuses. Rescued people count in those meals. Cargo
selection rechecks the remaining sale surplus after a grain ration purchase, so an earlier quote
cannot withdraw or invoice that same grain again.

Blockades require an actual supplied hull at the lane mouth. Privateers need paid, dated letters;
boarding transfers a finite part of an existing enemy-owned load. The prize rides home before a
funded local sale and treasury share. A convoy binds an actual merchant voyage and a paid nearby
charter, each retaining its crew and stock. The escort follows with a 150m progress gap; scene
leases still own each body independently. Arrival and interruption are saved outcomes.

An actual hostile contact records one ID, seed and outcome. `WarContact.name` is optional:
only significant state engagements receive a period title at creation, based on supplied forces
and an actual nearby capital/port operation, substantial convoy or fleet concentration. Pirates,
privateers and ordinary skirmishes receive none. `war_engagements` and `engagement_name` expose
that saved decision to the title-card UI; observing a contact never creates or names it.

An actual hostile contact records one ID, seed and outcome. Offscene resolution consumes finite
ammunition and damages the original hulls. When both ships are present, the combat/vessel
adapter commits physical hits to those same records. Occupation requires an arrived supplied
force and ends if it cannot hold the place. Citizenship and private title survive a flag change.
Displaced households pay actual passage and move their original population and money. Downed
airmen and disabled crews remain original identities/cohorts, with finite rescue seats and an
actual shelter arrival. Passing real coasters can stop to pick them up.

The player contract facade offers escrowed escort, reconnaissance, rescue, mail and smuggling.
Escort evidence belongs to one actual voyage and requires enough remaining distance for the
promised mile. Reconnaissance requires a dated observation and a return to the office. Rescue
credits its exact survivor receipt. Medicine smuggling additionally requires a received medical
supply request. Received reports and actual sight determine the player's war knowledge.

## Save boundary and limits

At one completed tick, call `checkpoint_war_scene` for the full fleet and combat state, fold the
other scene owners, then call `save_world`. Restoring uses `restore_war_scene` and rebuilds visual
bindings. No save operation belongs on the render path. Startup/save-menu presentation is owned
by the game UI.
The save owner must also persist the string returned by `snapshot_air_events(events,w)` at that
same completed tick and restore it as `AirEvents`. This folds the race pilots into World but
keeps their course, entries and lap/gate progress in the separate AirEvents value; the naval
checkpoint does not contain race progress.

Schema3 keeps readable metadata in each `-a`/`-b` bank and raw deflate bytes in its `-data` key.
The body is written before its checksum/header commits. The other latest valid bank remains
available after a failure. Schema1/2 remain readable. Route/procurement versions requiring a
migration are refused while preserving their files. The browser runtime base64-encodes the raw
bytes once, avoiding the former double expansion. The browser compatibility layer packs only
`sloppy:...-a-data` / `-b-data` values into a reversible fifteen-bit BMP alphabet in localStorage;
its byte API still reads/writes the exact native compressed body. Legacy base64 bodies remain
readable. New headers use encoding3 so older builds refuse these banks explicitly. Ordinary
settings and metadata are unaffected; each bank retains its own complete independent body.

The simulation bounds the registry at1024 places, carriers at1280, local people at24 and visible
economic ships at16 (the phone tier can choose6). Commissions are bounded96; political evidence,
reports, contacts, survivors, missions and ordnance have separate saved limits. Graph search for
sea lanes is offline; force decisions and cohort work are staggered. Tests use strict invariant
failures. The game opts into logged transaction recovery and retains the last sound state.

`sync_far_vessels` still steps leased motion, commits damage and folds ships leaving view on
every call. The game requests new admission four times per second with `refresh`; standalone
callers default to a fresh admission scan. This adds no saved cache or second motion owner.
An explicit vehicle lease looks up its own journey directly, and reverse travel indexes the
immutable route without copying it. Identical idle poses need no repeated write.

In game mode the minute clock validates mutable far-state inputs once before the guarded
economy/transport pair; standalone transport calls validate their own inputs. Strict tests
retain both full validations. Published route points have no game mutation path: construction,
load and save always validate every point, and strict minute tests also retain that scan.
Only that immutable point scan is omitted from the game minute's validation; route dimensions,
endpoints, journey references and progress remain checked. Future route replacement must pass
full validation before publication. The game-mode save-boundary test still refuses NaN routes.
