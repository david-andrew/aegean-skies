# Settlement economy

`World.far.populated` enables the funded cohort tier. `far_scene.configure_far_economy` publishes
it once the complete settlement registry and life contexts are ready. This avoids freezing the
mainland-only catalog while streamed island generation is still running. Normal full-world games
use the tier; legacy `AEGEAN_WORLD=0` and isolated core tests retain the six-harbor simulation.

All793 settlements have saved household/market accounts, citizenship cohorts, original country,
current controller, local authority, stock, prices, production, raw reserves, shortages and hunger.
Population includes the original named people/children and actual vehicle crew exactly once.
National treasuries have explicit finite opening endowments; taxes transfer money to the current
controller without changing citizenship. Cohort wages and household purchases use existing funds.
Primary production requires labor and wages; workshops consume fuel and finite ore, arms require
parts, medicine consumes wine/alcohol, and the refinery consumes finite raw crude. No daily reset
or free replenishment. Opening reserves are simulation construction data, not new job cargo.

The six original markets alias their existing owned crates/accounts. Their old abstract household
pseudo-sales are disabled while these funded cohorts buy food. Existing detailed outside import,
export, care/credit and visitor mechanisms remain explicit ledger boundaries; this slice does not
claim the old core is a closed economy. New far accounts/services never receive outside cash.

`living_far_stock` uses the same CargoSource ledger. `far_quantity` partitions a root between
abstract stores and detailed crates. Cached totals join the goods-conservation equation; validation
recomputes stores and partitions. Tier transfers keep the exact source, with no import, production,
consumption or new title created. Only unpromised, physically present market stock may leave a
core gateway. Goods carried by a person are unavailable to abstract shipping.

`tools/bake_living_routes.jo` produces `assets/living-routes.bin`:125KB compressed,516 canonical
roads from606 candidates plus675 hull-verified sea lanes. Sea approaches/crossings are sampled every
35m against canonical terrain. Rejected chords are not services. Runtime performs no route search;
terrain, geography and sorted settlement layout fingerprints must match. After changing those
inputs, run the baker headlessly and commit the updated catalog. Stale/corrupt data fails loudly
in tools, logs once and leaves the far tier disabled in play.

Up to1280 saved reciprocal ship/cart services acquire cargo by paying the origin market from the
receiving market's real purse and paying freight to the carrier. Title then belongs to that buyer;
the vehicle owns custody of the same physical roots. Ships are sailing coasters, not fuel-free
motor vessels. Crew are removed from cohorts and provision actual grain for the full crossing;
daily meals follow them at sea. Paid delivery commits only at the actual route endpoint. Full
warehouses hold an arriving load rather than discard its identity. Journeys carry at most12 local
accounts; only actual arrival copies these to the destination's local news list.

Per-minute work is staggered: approximately14 districts each minute, one hourly work/purchase step
each. Transport advances active journeys once per minute and checks departures every30minutes.
`living_world.far_transport_views(w,observer,radius=6000)` exposes saved service ID, kind, actual
origin/destination/position/velocity, commodity/quantity and a factual reason. Existing merchant
ships are materialized through the vessel scene adapter; carts retain abstract journeys. Persistent
named residents and callers registering real aircraft share the original World identity tables.
The sparse IDs are keys, never indexes into `World.places` or the six original Towns.

Stock fragments are capped at64 per store. Production roots aggregate by producer/good/origin;
spent source audit totals survive. Temporary batches are internal to a guarded operation: do not
save/yield or expose one between taking and placing/consuming it. Full save validation checks
population/crew conservation, route/reference/custody/title/capacity and counters before indexed
helpers. Strict/recovery policy is the same as the rest of the living world.

Tests: root gateways4, funded cohorts/transport5, including seven-day combined-core replay and
malformed reference rejection. `tools/farlog.jo` exercises all793 places for seven days, with hourly
conservation and daily canonical save round-trips. Named local promotion, scene vehicles, far
aviation, political force logistics, combat/capture/refugee/rescue/contracts remain subsequent
work; district data alone is not a running war.

## Persistent local residents and carried accounts

A bounded local scan promotes up to three real adult workers of a nearby generated settlement
into `World.people` (up to3072 persistent named residents; at most24 nearby scene leases).
Their citizenship stays theirs. A population member and their actual share of household cash
leave the cohort exactly once. The original26 people remain the detailed planner prefix;
`core_person_count` keeps original dispatch/fishing/social/job planners from owning these people.
Far identities, names, accounts and poses are not duplicated in a separate identity table.

`Person.far_home/far_place` are sparse registry IDs, with legacy `home/place=-1`; use facade
`person_place`, `place_name`, `person_position`, or `far_resident_views`. The latter includes
person/name, home/place, citizenship/controller/authority, pose/target, role and a short reason.
The same four conversation signatures work for far residents; `ConversationTurn.far_news` is
optional evidence metadata. Original enum ordinals stay fixed; Occupation appends farmer/sailor.

House door anchors come from the same accepted canonical parcels as town rendering/collision,
baked offline alongside the routes (catalog now93KB compressed). Named residents keep those
home doors, go to the actual market/fields/workshop/quay, cafe, evening square and Sunday church,
and disappear indoors at night. Scene walking shares the existing single navigation-start
budget per frame. A saved route survives folding; the abstract walker skips scene-owned ticks.
Obstructions stop the walk rather than phase through a wall. Worked minutes at the destination
fund real wages; named people buy and consume their own grain from their own purses.

Local counter quotes are witnessed snapshots, not live remote market queries. Departures and
committed deliveries create actual dated local accounts. Only physical arrivals carry the
origin's recent accounts to another place. A named resident hears counter accounts when present;
conversation copies the selected report to the listener with occurrence date, source, confidence
and hop count. World journal<=2048; each person carries<=12 snapshots, surviving journal pruning.
`heard_notes` includes actually heard far reports. Preview never transmits information.

The shared conversation UI has three small data-wiring changes: sparse place-name lookup,
Any-work dispatch through ask_for_work, and a guard against opening the six-port trade panel
for a sparse counter. Its layout/controls stay the coordinator's. Far bulk trade, named aircraft,
cart drawing and generic far airline services remain subsequent work; see the national logistics
implementation and UI contracts in [living-logistics.md](living-logistics.md).

## Sparse harbor commissions and aircraft callers

`far_scene.configure_far_harbors` publishes `World.far.harbors` from the actual registry's
MooringPlace records. They are sparse keys, with water docks and walkable quay anchors;
inland places never acquire invented aircraft facilities. `living_commissions` reserves
existing root stock before publishing an offer, pays its seller from the receiving market,
and puts the real carriage reward in escrow. At most96 records exist. Counter queries and
conversation previews are pure; `refresh_far_work` is an explicit offer publication action.
The minute worker considers one district per minute, rather than all settlements per frame.

`living_world.commission_views(w,place=-1,actor=-1)` exposes ID, kind/phase, real endpoints,
poster/carrier, reward/deadline, owned mass/position and why. `claim_commission`,
`pickup_commission`, `load_commission` and `collect_commission` implement actual custody.
Pickup requires foot proximity, loading requires the player's own moored aircraft at
an actual published dock beside the holder and free payload capacity, and payment requires collection at the actual
receiving counter. Those goods are a single FarStock partition while carried, included in
`craft_grams` aboard; never copied into a second anonymous hold. A missed deadline refunds
the reward but retains the buyer's title/cargo until collection or a funded local resale.

Automatic/sender/porter handling uses persistent promoted residents. Their existing route
and movement lease walk to pickup, the real quay and the receiving counter; they do not also
perform daily work while carrying. Paid collectors reserve60cents from the carrier, paid
from actual escrow at completion. Player carriage remains explicit. `WorkOffer.commission`
and `ConversationTurn.commission` are optional separate IDs; `.job` retains its core meaning.
The UI should dispatch those IDs to the commission methods, not the six-port job methods.

`living_far_aircraft.register_far_aircraft(w,place,kind,funder,key)` is a guarded, idempotent
registration for scene/event callers. It consumes two owned packages of parts and transfers
the actual AIRFRAMES purchase price to the local yard. It reserves a real berth and promotes
a worker into one of two pilot slots, alongside three ordinary resident slots. The same
World.aircraft ID owns its empty tank, health and future payload. Saves accept8..64 bodies;
no duplicate far aircraft tank/hold is introduced. `fill_far_tank` purchases owned local fuel,
`reserve_far_berth` and `release_far_berth` own sparse berth metadata. Scene callers still
commit actual flight motion once; no headless flying or rendering is implied by registration.

## Current logistics contract

See [living-logistics.md](living-logistics.md) for the consolidated ownership, received-order,
war and save contract. The earlier sections describe the staged implementation. Bulk cargo now
requires a dated counter order actually carried back from a visit (initial orders are declared
opening agreements). Each service carries new local orders on arrival. Counters procure for
bounded, received downstream customer orders as well as their own households and factory inputs.
Original per-good deadlines and ancestry survive forwarding; no echoed demand or renewal from
repeated handling. Separate cargo_deliveries and order_rounds counters keep empty paid visits
from being reported as goods deliveries. WorkProvenance exposes the real need, supplier, negotiated
price/deadline/payer and existing opening/production/import batch references.

National charters, supply/arsenals, received political evidence, convoy binding, finite naval
contacts, occupation/withdrawal, refugees, rescue and player missions operate on those same
accounts, population, goods, routes and vessels. War is contingent on received incidents and
supplied forces; a date or camera does not spawn a fight. Significant national engagements alone
can carry a saved optional title, exposed on WarContact.name and through war_engagements.

Native/browser saves use schema3 readable metadata and a raw compressed body for each bank.
Keep both banks and their -data keys together. Schema1/2 remain readable; incompatible old far
procurement/navigation versions are explicitly refused without replacing the saved world.
