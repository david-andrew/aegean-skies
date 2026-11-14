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
a worker into one of the default two pilot slots, alongside three ordinary resident slots.
Authored mobilizations may explicitly reserve up to64pilot slots from the same finite cohorts;
ordinary settlements retain the two-pilot limit. The same
World.aircraft ID owns its empty tank, health and future payload. Saves accept8..256 bodies;
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


## Feeder tracks and opening rolling stock

The offline living-route bake preserves every authored road and accepted sea lane, then tries
at most2048 deterministic short links between disconnected transport components. An accepted
unpaved feeder uses canonical dry terrain, a bounded grade and wagon-width building clearance;
local detours use the same contact geometry as walking. The resulting samples are baked, never
searched in the game minute or frame loop. These tracks belong to the living transport catalog,
not the authored settlement road registry or chart. Unpassable candidates stay disconnected.

The current catalog adds11tracks: the largest connected component grows483→674places.
Opening services on authored roads own a1.5-ton horse wagon and one real cohort driver; narrow
feeder tracks retain the500kgcart. The ship hold remains30tons. These are declared opening
vehicles, with funded operating purses and actual crew removed from their households. Cargo
still requires actual stock, received purchase terms, payment and carried original roots.
Loading a populated save never enlarges its fleet, resizes its vehicles or replaces its routes.

A connected graph alone does not establish adequate carrying capacity. An optimistic grain-only
flow bound on the measured month snapshot improved61.6%→98.9%of import demand when route
capacities were treated as unlimited. At finite capacities, wagons and multi-day route times
remain important constraints; no claim of general economic equilibrium follows from that bound.

## Funded response to food transport shortages

A counter's staple reserve covers its known physical order round trip plus two days. Actual
arriving grain labels can teach it a longer producer/relay route: a bounded registry BFS uses
that producer's identity and mapped routes, never its current remote inventory. The four-source
learning record and maximum45-day reserve are saved. Slow-service buying quotes additionally
allow the household meals eaten before the order and food return; they distinguish this buying
target from stock currently in the store. Genuine low-staple carried bids take priority over
discretionary purchases, while price ceilings and real available supply still bind.

Counters can invest after a nearly full actual grain collection, or after a paid full grain
sale whose received order still needs another available load within its original deadline.
The seller can employ its own local teams, including when the receiving hamlet has no spare
adults. Its first paid cargo is unchanged; new drivers must buy actual provisions before that
one departure, or the investment is rolled back. Later larger loads still require actual buyers,
goods and payment. A justified parts order stays unfilled until a real supplier delivers.

Fresh worlds declare finite household spare-wagon endowments in towns AND farms: one per eight
initial workers, capped at64or32respectively. This corrects the former arbitrary exclusion of
farm equipment. Existing saves retain their declared pools; loading never adds teams or goods.
Farm investment requires actual wholesale demand or a paid sale and leaves enough productive
adults to feed its households. Every hiring leaves at least three local workers. The investing
counter buys existing wagons, hires actual adults, consumes500milli-packages of its owned parts
per unit and transfers5100cents to households plus1200cents to the crew account. It owns those
extra wagons. No person, commodity, extra speed or carrying capacity without real wagons/drivers
is created by the investment.

One saved caravan/journey can contain up to25real wagons, with one actual driver per wagon;
new units retain the road1.5tonne/narrow-track500kg payload and the original speed. A cart may
not depart without enough drivers. Acquisitions require the actual paid sale or just-collected voyage, not a
caller-supplied delivery amount; the voyage is an idempotency key. At most8records and8units
per acquisition are allowed. Spare equipment plus allocated extra wagons conserves the opening
equipment total, alongside existing cash, source-root, goods and population checks.

`living_world.caravan_provenance(w,vehicle)` returns saved cause/agreement and maintenance-batch
descriptions for notebook use. Transport reasons describe the actual wagon and crew count.
The slow farm→relay→city14-day fixture meets all staple meals in its last three days and returns
to zero hunger; the final whole-registry food/war month is measured separately.

### Border deployment and communication

Standing national charters are paid before the first merchant departures, choosing existing
frontier hulls and local recruits. A land force requires an actual international cart route;
maritime borders use existing ships. Defensive forces hold reachable home frontier stations.
Armed foreign inspections stay for three game hours. A supplied local guard with the actual
witness account can order an inspection to withdraw, allowing five game minutes before contact;
withdrawal, repairs and dispatch comply. Merchants and ordinary foreign passage do not qualify.
The saved warning identifies the original intrusion and a pair cannot resolve it twice.

An existing paid carrier may physically take signed accounts it has actually received to a
reachable council. No distant event index informs that council. Three independent received
reports and actual supplied forces are still required for declaration; recovery of readiness
reconsiders the council's retained evidence without needing a fourth report. Declarations must
travel back by the same report carriage system. Small border clashes remain unnamed; existing
significant-engagement/title-card APIs are unchanged. New enum values and saved fields are
appended with legacy defaults, preserving old saves and the landed war/map interfaces.

### Buying-paper ancestry

A saved buying quote separates the counter's own household/workshop quantity from a primary
forwarded lineage per commodity and at most eight additional customer lines in the entire paper.
Each line keeps its own quantity, deadline, need date and at most twelve ancestry places. Grain
gets first use of the extra slots. Unrelated histories are never unioned into a routing ancestry;
several genuine requests can nevertheless fill the same actual load. A returning component can
be rejected as a cycle without discarding its sender's own meals or other valid customer lines.

Selection and fulfillment use only components still eligible at the actual arrival time; one
expired customer's deadline never extends or invalidates another's. The bounded `need_places`
list is a human-readable description of eligible customers, not a routing path. Buying terms,
withdrawal, payment, freight and original-root provenance remain authoritative. Legacy quotes
have zero explicit local quantity and no extra lines until real visits renew them. Loading adds
neither cargo, new equipment nor remote knowledge.

Hungry merchant crews may carry their home counter's funded food inquiry under a current
reciprocal agreement even when the peer's last quote also reported no grain. They retain actual
remaining rations and hunger; the voyage only collects real new quotes or available paid cargo.
It does not observe future remote stock, invent meals or move without an actual journey.

### Carried supplier knowledge

Each counter retains at most sixteen dated inventory reports from its real reciprocal
services, independently of customer orders: a farmer with nothing to buy remains a known
supplier. Opening business contacts explicitly exchange their opening inventories. Later
updates arrive only with the actual service. Recent collected shipments also establish
throughput, recorded separately from advertised remaining stock. Reports and delivery
evidence expire using the physical route's travel time; no remote live inventory is read.

Grain, fuel and parts orders prefer credible known suppliers. Competing quotes divide the
exact requested quantity by observed surplus, price and public journey time, with stable
integer rounding. Current inventory remains a dated fact; recent collected supply supports
orders for a return load and its next replenishment. A counter includes its own real wagon
committed wagons, so adding wagons does not leave its orders stuck at the
previous smaller load. This is buying authority, not a claim that future goods exist.
Remaining need explores other real service
links: a small past delivery cannot monopolize an entire city's request. Household pantries are protected
from wholesale resale. A productive funded grain farm keeps two days of its own meals;
other places retain their route-aware household reserve. The paid trade provenance records
whether its supplier evidence was a written inventory or an actual collected delivery, and
when that evidence was obtained. Old saves begin with empty catalogs and learn on real visits.

A paid grain sale that finances real extra teams can load those wagons before its one
departure. Additional goods still require the original buyer's signed quantity, ceiling
price, deadline and remaining cash; they move from the supplier's actual surplus and are
invoiced into the same custody record. No larger quantity is assumed merely because the
carrier grew, and an unavailable extra load leaves the original paid cargo intact.

The minimum carrier purchase is 100 milli-packages. Supplier evidence uses that same
threshold. Unknown inquiries are divided into viable lots, with deterministic dated
rotation through the remaining real offices; a ten-package request cannot dissolve into
sixteen fragments that all carriers refuse. Quantities are never rounded upward.

Investment receipts are unique per voyage and counter. A seller's actual team purchase
does not prevent a different receiving counter, still short after collection, from buying
its own existing wagons and hiring its own adults. Repeating either local transaction is
refused, and both parties' parts, wages, ownership and equipment totals remain recorded.

Food urgency is written from the counter's actual household safety reserve, separately
from its commercial warehouse and wholesale targets. Each forwarded component retains
its own household urgency and deadline. A well-fed farm's storage order cannot claim
survival priority over real maintenance purchases, while a genuine downstream household
shortage keeps its priority through intermediaries. Expiring that request leaves unrelated
nonurgent orders intact. Legacy papers still recognize an explicitly empty local pantry;
precise household terms arrive with renewed physical correspondence.

Production-storage goals are distinct from purchasing goals. Farms and workshops produce
their warehouse stock through paid work; buying papers and public shortage bids cover
actual household reserves, production inputs, feasible cart refits and received customer
requests. A funded farm whose crop covers its residents does not order future household
grain as though that crop did not exist, or buy its own output back from hungry customers.
Output inventory still sets the original production ceiling and pricing reference.

Both paid sellers and actual receiving counters can request the real parts needed for a
feasible expansion before the refit succeeds. The plan is bounded by owned spare teams,
available adults, retained farm labor and actual funds. Missing parts remain missing until
an existing supplier sells them; they cannot silently freeze the counter at its original
two refits. The saved maintenance target also keeps this need separate from a parts
factory's much larger production-storage goal.


Carriage refits compare the outstanding load with one marginal wagon's payload, after
subtracting space already free in the existing group. A large group does not need another
whole group-sized backlog merely to hire one driver/wagon. Seller-funded teams can load now,
so their signed buying deadline is checked at this departure's arrival, not a third future
crossing. Existing parts, cash, drivers, equipment and repeat-acquisition limits still apply.
`tools/cart_audit.jo` replays a bounded interval from a real saved bank and prints optional
process-local refusal/flow counters. The observer does not change RNG, transactions or saves;
it is disabled in the game. Its counts are attempted decisions, not unique households.


A dated supplier receipt also retains the actual carrier payload observed at that visit.
A later request can seek two observed carrier loads, bounded by its real remaining need,
instead of being permanently capped at twice a tiny remainder. This is buying authority,
not supplier inventory: invoices still require actual available stock, cash and capacity.
Unknown routes seek the residual need. A remote refit never updates the saved observation;
an actual later visit does. Old saves default the observation tozero until a visit.


Fresh worlds describe established reciprocal offices, rather than offices that never sent a
buying letter before the opening scene. Construction records both ends' actual stock-gap
requests and their bounded carried customer ancestry. At most12synchronous correspondence
generations use only the preceding generation's genuine requests on real assigned service
links; convergence may stop earlier. Customer books, minimum lots, deadlines, stock observations
and loop exclusions keep their normal limits. These dated opening agreements add no goods,
cash, people, elapsed time or traveled distance; all subsequent sales are paid physical loads.
An already populated save returns before this construction, so loading never resets its papers.


A detailed gateway's far-market offer is bounded by BOTH physically unpromised local crates
and aggregate unreserved inventory. A workshop reservation or charter-fuel reservation can
exist without a job-marked crate; those goods remain unavailable to far households, production
and carriers. The paid-repair regression consumes all genuinely free parts and then completes
the original repair once, preserving exact inventory, source-root and reservation partitions.


### Household fields and the growing season

The optional field register gives each district at most eight globally unique, dry, gently
sloped1kmparcels outside all registered town footprints. IDs encode the fixed physical grid;
changing a field's centre or giving the same parcel to two districts fails validation. The
baker records eligibility once from canonical terrain. Households own the land; their actual
counter operates the crop and pays their labor. Planted area cannot exceed registered land.

The civil opening is Monday14May1928. Winter grain is sown in October/November and ripens in
June after at least180worlddays. New sowing first reserves actual grain stock, pays real hands,
then consumes the seed when planting finishes. A growing crop is not inventory. Only paid
harvest of a mature crop creates traceable grain. Missing seed, land, funds or labor cannot be
replaced by a request. Uncollected crop expires after the finite harvest window; unplanted seed
returns if the household cancels after its food outlook recovers.

Fresh catalog data can declare existing autumn-sown household plots, targeting up to20%of an
annual household ration. These are bounded by real land, seed withdrawn from existing opening
supplier stocks, actual supplier/carrier payments and recorded paid sowing/earlier care. The
opening ledger does not gain seed or harvested grain. The standing crop's previous-autumn dates
are explicit opening history; later expansion must pass through the real sowing window and
wait for its later harvest. Already populated saves return before founding transactions and
retain their own crops, equipment and stock. Existing specialist-farm cohort production remains
its earlier aggregate model; these additional household plots have the explicit seasonal cycle.

Households plan against a year's own food need; a seed delivery is not mistaken for a permanent
recovery. Fieldwork subtracts the SAME workers from their usual production, capped at half the
available cohort. The saved foregone-output counters compare actual feasible production before
and after that allocation; an already full warehouse does not count imaginary lost output.
Completed/abandoned work releases the hands, and a genuinely recovered food outlook can cancel
unplanted expansion. A ripe, funded harvest is completed rather than abandoned because its first
basket temporarily refilled the pantry. Every paid hour and seed root remains in the crop/receipt.

Each harvested source records its exact plot, sowing and ripening dates, seed roots and signed
agreement; separate crop years never alias the same source. Physical parcels and onward cargo
retain those sources. Household meal/need counters exclude seed and furnace consumption, so a
food replay cannot pass by counting planted grain as eaten food.

UI data: living_world.household_fields(w,place) returns geometry, stage, dated crop, actual
workers, owners/operators and reason; field_provenance(w,place,id) returns the saved input and
payment history; field_date(day) formats its civil date. Use these live facts locally; distant
news still requires actual carried reports. No existing talk/contract signature changes.


Opening plot agreements use the area a real supplier can actually seed; they never assume
one granary can fill a whole100hectareparcel. Further registered parcels can be planted from
other suppliers, while unsupported land remains fallow. Actual full-registry opening proof:
5038parcels,334standing crops,1372.13hectares and10290975milli-packages of existing seed
consumed, with no opening harvest and no increase in the opening commodity ledger.

The producer primitive also checks the paid but not-yet-recorded harvest work before issuing
any field grain. Merely changing a crop to ripe cannot obtain a free harvest. Crop validation
requires the exact relation between its work units, paid cents and saved wage fraction.
Observed local field-register notices can enter troubles/market speech; unvisited new notices
do not become knowledge. Talk questions, replies and work-offer signatures remain unchanged.


Staged scene publication may occur after the clock has started. Founding crops use the actual
civil date when a NEW far component is published, including the most recent autumn sowing;
an already expired harvest is not recreated. Their actual seed receipt also informs the
counter's physical replenishment lead time. A loaded, already populated legacy world instead
publishes only verified arable titles once: it keeps growing crops, goods, money, people and
source IDs exactly, and receives no retrospective sowing, seed, wages or harvest. Repeated
land publication is idempotent. The raw save decoder still round-trips the recorded state;
the terrain/registry adapter performs this explicit land-only migration.


A physically exchanged signed armistice closes earlier evidence. Restored readiness alone
cannot redeclare the same war from the same three settled reports. Saved minute plus separate
FarNews/coreEvent ordering also distinguish genuinely later incidents in the SAME minute.
Old banks reconstruct a missing cutoff from the councils' actual retained signed notices and
already accepted incident dates. New post-settlement breaches still count normally; peace is
neither a permanent immunity nor a scheduled reset. Out-of-order reports cannot rewind the
last actual incident date. Existing named-engagement/title-card APIs remain unchanged.


### Opening paid voyages

Fresh registry construction includes a founding voyage book. Existing reciprocal carriers
may begin on actual routes carrying actual paid stock, rather than every office having
waited until the opening minute to dispatch its first inquiry. The initializer selects a
load from the two real signed counter orders, uses the ordinary funded departure transaction,
and declares a deterministic20–80%route position for that existing vehicle and crew. Its
original stock roots, payer, price, carriage and destination are unchanged. Nothing is
unloaded early and no elapsed minute is added. The declared starting distance is saved;
abstract or scene ownership then advances the body exactly once per game tick as usual.
Standing national hulls are reserved before merchant starting positions are assigned.

This is explicit opening history, not a later speed increase or route reset. It runs only
once for the newly published component at its birth minute, before any played journey or
scene lease exists. Loaded old banks default to no pending initialization. An already moving
or played component keeps every position, cargo root and account unchanged. Restored moving
vessels use their authoritative route heading when checking the real wet footprint.


### Seasonal acceptance replay

The frozen simulation98d8355 (maina509c91 merged) completed a fresh30dayseed42replay:
last-three-day staple meals8415652 /8975971milli-packages (93.7576%); both capitals100%.
All30daily full invariant, canonical decode and durable bank checks passed without a game-mode
recovery. Actual paid field harvest was2738894.54kg from205819.50kgofexistingseed. Trade still
completed6583actualcargoarrivals to533places, plus60coreaircraftdeliveries across the month.
Three natural frontier engagements occurred and received evidence led to formal war onday15;
this does not claim a named major campaign or a naturally changed capital in this window.

`tools/worldlog.jo` is the expensive full-registry acceptance tool. With a private
`SLOPPY_SAVE_DIR`, run headlessly/silently with `SLOPPY_THREADS=1`, `WORLD_DAYS=30`,
`WORLD_REQUIRE_FOOD=1` and a fresh `WORLD_CHECKPOINT` prefix. It checks the actual household
meal counters, not seed/furnace consumption, and separately checks each capital. The final
three-day threshold is80%; actual cargo must arrive every day and natural battles must occur.
Use `--release`. Focused regressions are living_fields, living_trade_opening, living_war_pacing,
living_war_peace and living_far_delivery_month; they also exercise saved continuation.
