# Aegean Skies: design review and milestone implementation contract

2026-11-10. Read-only review of `docs/DESIGN.md`, the previous-plan dissent, the Sky Barons reuse audit (especially §§8–9), `aegean.jo`, `src/world.jo`, the Town/building portions of `src/objects.jo`, `src/planes.jo`, and Sloppy LANGUAGE/API documentation. Repository HEAD at inspection: `f0868531dc38750c007692a3f51b60a079aaa130`. `src/flight.jo` and its WIP tests were deliberately not read. Existing working-tree changes belong to other work. This report specifies new behavior; it does not claim those systems exist or that seed sweeps have already passed.

## 1. Verdict, scope, and remaining failure modes

The revision is implementable after closing the contracts below. Its strongest change is making a person answer to someone: a missed delivery, creditor, or repair bill is both a cause and a sentence. Keep the stock economy, additive choices, physically resolved nearby encounters, and persistent aftermath. Do not add a director that invents incidents to fill silence.

The dissent was not uniformly right. Stock-based prices do not necessarily converge: stock accumulates production minus consumption, and transport involves delays, finite cash, and stale information. Those can cause shortages or oscillation even without shocks. True local prices and mistaken destination beliefs are perfectly compatible; beliefs choose the trip, the actual price decides whether it was profitable. Conservation tests do not require equilibrium. Nor does an authored routine or a shortage-triggered bounty violate emergence: the relevant distinction is a general rule applied to circumstances versus an event spawned merely because the player needs excitement. One gossip item per place is too little: the next fish delivery would either replace the raid or remain invisible forever. Keep several ranked items with deduplication.

Ranked risks below are ordered by likelihood of sinking this milestone, not theoretical severity.

| Rank | Mechanism still missing or contradictory | Failure and smallest replacement |
|---|---|---|
| 1 | Time and space use different clocks implicitly. One game minute is two physical seconds. | At 60 m/s an aircraft travels 120 m/game minute; 16 km takes 133 game minutes, not four game minutes. An implementation using 60 seconds/minute abstracts aircraft 30 times too fast. Use one integer 60 Hz clock and explicitly convert game minutes to two physical seconds. Keep the scale; all deadlines include actual route time. |
| 2 | An impossible obligation still preempts everything; vices are listed after mandatory routines. | An insolvent pilot selects “pay debt” forever, never earns or smuggles; a full workday routine consumes every choice slot. Obligations select feasible progress toward fulfillment, mark blocked items, and yield until a stated retry. Routines reserve bounded work blocks and presence windows. A vice changes the permitted method for an obligation; it never interrupts an airborne commitment. |
| 3 | No atomic ownership/claim/escrow contract for postings, aircraft, cargo, or repairs. | Two couriers accept the same crate, a poster spends the reward, damaged planes repair twice, a save pays the same arrival again. One ordered transaction path, one location per inventory, exclusive craft/manifest claims, reserved cargo, prepaid escrow, terminal states. See §§2–3. |
| 4 | Scene and world both “drive the abstract record”; old paragraph still says “same outcome odds.” | Minute advance plus physical advance doubles speed and burn; an off-screen raid fires after a visible victory; culling repairs or teleports a plane. Delete the old odds sentence. One movement owner at a time; resolve encounter identity once, and fold from actual pose with a new remaining-route origin. |
| 5 | Flights and obligations need a shared reason that can become perceptible. | A busy ledger remains a quiet quay. Every departure has a persistent reason snapshot; arrivals publish it locally; proximity speech, named board history, route sightlines, and aftermath are acceptance requirements. Seed the first crossing already in flight, rather than hoping utility happens to produce it. |
| 6 | Named production, anonymous consumption, market cash, and faction wages have no common budget. | Missing production starves all towns; purchases drain a shop and sellers freeze; wages/repairs/bounties silently mint money. Give markets accounts, external households/outside trade explicit boundary flows, named production completion rules, public-service budgets, and daily external shipments. Verify exact cents and goods separately. |
| 7 | Pirates have neither a stop rule nor a recovery path. | Hunger→raids→damage/fuel loss→immobility can absorb the crew; alternatively repeated theft drains every carrier. Captain chooses, crew claims roles, one raid/captain/day, one victim/encounter, limited loot, return reserve, 18-hour cooldown, repair and outside-credit recovery. Pressure gates raids; patrols reduce success, not intent to zero. |
| 8 | Interest, ruined pilots, closed harbors, absent mechanics, full docks, and missed passengers lack exits. | Positive debt feedback or a blocked service can permanently remove all traffic. Cap interest, default once, release failed reservations, allow paid ferry/tow and a bounded landing queue, expire exclusive repair claims, and make delays/failures explicit events. No silent respawn. |
| 9 | News has no deduplication or memory retention contract. | A repeated rumor repeatedly lowers reputation; home acquaintances instantly reveal distant facts; event eviction removes the only explanation. Sparse relationships do not copy knowledge automatically. News expires after seven days; eight-day receipts prevent repeated effects; live debts, trips, jobs, grievances and aftermath pin compact reason records. |
| 10 | Weather and random failures have no hazard units or schedule. | A per-minute “1%” aircraft failure becomes near certain during a crossing; new hourly weather closes every approach. Use hazards per physical flight hour, sample deterministic incident distances, continuous weather motion, hysteresis on closures, and known retry dates. |
| 11 | Six settlements and ten islands exist, despite the revised text still saying nine/four–five. | Renaming or rebuilding duplicate towns creates unstable references. Freeze settlement IDs 0–5 from `SETTLEMENTS`; integrate with existing Town geometry by index, not a second map. No new island/hotel work is needed. |
| 12 | Ambition, faction attitude matrix, prosperity/unrest/fear, migration, races and full passenger simulation remain broad promises. | Hundreds of lines of decorative state delay the causal loop. Milestone decisions read money, duty, fatigue, company, revenge, five traits, local regard and a faction role. Defer ambition and migration; derive mood on demand from shortages/news; support one parcel delivery and one named passenger manifest before adding races. |

### Milestone boundary

Implement 25 NPCs plus the player, all six existing settlements, nine tradable goods, three working courier aircraft, one patrol pilot, two pirate aircraft, a private racer, and the player aircraft. Boats/fishing trips are abstract working assets with visible dock/sea markers, not a second physics project. No deaths, births, recruitment population growth, court simulation, free-form planning language, seasonal economy, rumor fabrication, or scripted race generator. Joining pirates changes faction membership only; it does not create another plane. “Refuses to fly” is a temporary state with a recovery condition, not cast removal.

## 2. Data model and Sloppy ownership

### Units and identity

All IDs below are signed `int`, `-1` means absent. Persons, settlements, aircraft, accounts and factions are append-only dense arrays: ID equals index, slots are never reused or reordered, departed people become inactive. Dynamic trip/job/obligation/event IDs are monotonic counters into maps, never map-array positions. Do not save `Pool` storage internals as an identity contract. Scene-only bodies/effects use `Pool[SceneBody]` and generation-checked `Handle`; an ID→Handle map is rebuilt on materialization and is not serialized. Removing a Pool item swaps the last item, so its `items` index cannot escape the scene.

Money is integer centesimi, displayed as lire (`12000` = 120 lire). Prices are cents/package. Market/inventory quantities are integer milli-packages (`1000` = one package); fixed integer residuals handle hourly consumption/production and cents rounding. Aircraft fuel is millilitres; fuel commodity is a 10-litre can. Weights are grams. Traits, pressure, confidence and condition are 0–1000. Regard/affinity are −1000…1000. Time is fixed-step ticks, 60/physical second; 120 ticks/game minute, 7200 ticks/game hour, 172800 ticks/game day. All `*_minute` fields below are absolute game-minute counts from the saved09:30 epoch, not minutes of day. Local minute-of-day is `(minute+570)%1440`; day index is `(minute+570)/1440`. Negative fields can describe pre-start travel/deadlines.

These declarations are intended as one simulation module, imported with a namespace to avoid existing `Settlement`, `Craft`, `Player` and `World` names. Definitions contain no rendering resources or functions. `Pose` is a serialized common kinematic record; it is not a proposed change to the WIP flight implementation.

```sloppy
const GOOD_COUNT = 9
const NONE_ID = -1
const TICKS_PER_MINUTE = 120
const EPOCH_LOCAL_MINUTE = 570      # day zero 09:30

enum GoodKind: fish, wine, oil, grain, fuel, parts, medicine, tobacco, arms
enum Occupation: player, merchant, courier, mechanic, clerk, innkeeper, fisher, patrol, telegraphist, oil_presser, miller, teacher, nurse, priest, hotelier, racer, pirate, quartermaster
enum Vice: none, smuggle, gamble, join_pirates, refuse_flight
enum PersonState: idle, working, walking, traveling, resting, injured, refusing, departed
enum Airframe: gull, heron, corsair, falco
enum CraftState: moored, taxi, airborne, approach, workshop, ditched, wrecked
enum MoveOwner: abstract_world, scene
enum TripState: preparing, active, holding, diverted, arrived, failed
enum TripMode: aircraft, boat, ferry, tow
enum Purpose: delivery, passenger, trade, fishing, patrol, raid, repair, visit, return_home, rescue
enum Activity: wait, work, fulfill, travel, rest, socialize, raid, patrol, trade, gamble, smuggle, refuse
enum ObligationKind: debt, delivery, passenger, shift, repair, rent, supply
enum ObligationState: open, blocked, fulfilled, breached, defaulted, cancelled
enum JobState: open, claimed, delivered, failed, expired, cancelled
enum CargoMode: none, commodity, sealed
enum EventKind: departed, arrived, produced, delivery, late, defaulted, theft, raid, patrol, rescue, ditch, repair, shortage, closure, refused, fine
enum SubjectKind: person, faction
enum WeatherKind: fair, wind, squall, storm
enum AftermathKind: crate, beach_wreck, workshop_plane, stranded_boat, injured_person
enum MoneyKind: opening, trade, wage, reward, escrow, refund, debt, interest, rent, fuel, repair, fine, theft, outside_import, household_sale, outside_export, subsidy, gambling, departure

struct Good:
    kind: GoodKind
    key: str
    package_grams: int
    base_cents: int
    shelf_hours: int = 0           # 0 = no spoilage
    illegal: bool = false

struct Inventory:
    qty: int[GOOD_COUNT]           # milli-packages
    reserved: int[GOOD_COUNT]      # subset of qty, never an extra stock

struct Traits:
    honesty = 500
    boldness = 500
    greed = 500
    sociability = 500
    loyalty = 500

struct Pressures:
    money = 0
    duty = 0
    rest = 0
    company = 0
    revenge = 0

struct Pose:
    pos: vec3
    vel: vec3
    rot: vec4 = vec4(0, 0, 0, 1)
    throttle: int = 0

struct Reason:
    purpose: Purpose
    actor: int = -1
    beneficiary: int = -1
    counterparty: int = -1        # victim/trading partner, distinct from beneficiary
    origin: int = -1
    destination: int = -1
    good: int = -1
    quantity: int = 0
    due_minute: int = -1
    obligation: int = -1
    job: int = -1
    source_event: int = -1
    amount_cents: int = 0

struct Action:
    activity: Activity = .wait
    purpose: Purpose
    reason: Reason
    target_person: int = -1
    target_place: int = -1
    target_anchor: int = -1
    end_minute: int = 0
    retry_minute: int = 0
    progress_minutes: int = 0
    failure_code: str = ""

struct PriceBelief:
    place: int
    good: int
    cents: int
    observed_minute: int
    learned_minute: int
    source_person: int = -1
    confidence = 1000

struct Person:
    id: int
    name: str
    age: int
    home: int
    occupation: Occupation
    appearance_seed: int
    faction: int = -1
    account: int = -1             # money is here, never duplicated as Person.money
    craft: int = -1               # preferred/owned aircraft; actual owner is on aircraft
    place: int = -1               # -1 while traveling
    local_anchor: int = -1
    pose: Pose                    # saved foot pose; aboard uses aircraft pose
    move_owner: MoveOwner = .abstract_world
    state: PersonState = .idle
    traits: Traits
    pressures: Pressures
    vice: Vice = .none
    vice_active: bool = false
    vice_until: int = 0
    fatigue = 200
    fatigue_remainder = 0
    alone_minutes = 0
    injured_until = 0
    last_raid_minute = -100000
    last_gamble_day = -1
    routine_day = -1
    routine_minutes: int[4]       # completed minutes in today's named routine blocks
    next_decision_minute = 0
    last_command_tick = -1
    last_command_sequence = -1
    trip: int = -1
    action: Action
    pocket: Inventory             # personal goods, not goods already in a craft
    obligations: int[]
    relationship_ids: int[]
    news: NewsItem[]              # <= 12
    prices: PriceBelief[]         # <= 6 * GOOD_COUNT

struct Market:
    account: int
    inventory: Inventory
    target: int[GOOD_COUNT]
    demand_per_day: int[GOOD_COUNT]
    demand_remainder: int[GOOD_COUNT]
    price_cents: int[GOOD_COUNT]
    price_remainder: int[GOOD_COUNT]
    shortage_hours: int[GOOD_COUNT]
    next_import_minute: int

struct SettlementRecord:
    id: int                      # existing SETTLEMENTS index
    key: str                     # stable save key, not displayed name
    population: int
    market_owner: int
    faction: int
    has_market: bool = true
    has_fuel: bool = true
    has_workshop: bool = false
    market: Market
    residents: int[]
    news: NewsItem[]              # <= 12
    yesterday: Reason[]          # <= 3, rendered as sentences
    harbor_closed: bool = false
    reopen_minutes = 0
    last_bark_minute = -1000

struct AircraftRecord:
    id: int
    kind: Airframe
    owner: int                   # Person ID, including pirate captain
    operator: int = -1
    fuel_ml: int
    burn_remainder: int = 0
    hull = 1000
    engine = 1000
    cargo: Inventory
    job_manifests: int[]          # commodity earmarks, sealed mail and passenger Jobs
    passengers: int[]            # actual Person IDs, <= type's seats
    place: int = -1
    dock: int = -1
    state: CraftState = .moored
    move_owner: MoveOwner = .abstract_world
    pose: Pose
    trip: int = -1
    repair_obligation: int = -1
    held_by_faction: int = -1
    revision = 0                 # scene transaction stale-write protection

struct Trip:
    id: int
    actor: int
    craft: int = -1
    mode: TripMode
    state: TripState = .preparing
    origin: int
    destination: int
    reason: Reason
    route: vec3[]                # stable semantic route, not renderer tessellation
    segment = 0
    segment_mm = 0               # distance progressed on current segment
    cruise_mm_per_sec: int
    departed_tick: int
    last_tick: int
    eta_tick: int
    incident_at_mm: int = -1
    incident_resolved: bool = false
    encounter: int = -1
    diversion_count = 0
    hold_until_minute = 0
    progress_remainder = 0
    claimed_dock: int = -1

struct Obligation:
    id: int
    kind: ObligationKind
    state: ObligationState = .open
    debtor: int                  # responsible Person
    creditor: int                # Person, or -1 for an organization account
    creditor_account: int
    place: int
    due_minute: int
    deadline_minute: int          # grace/cancellation date, >= due
    amount_cents: int = 0
    original_cents: int = 0
    principal_cents: int = 0       # debt only; unpaid principal
    interest_cents: int = 0        # debt only; accrued unpaid interest
    interest_accrued_total: int = 0
    interest_remainder: int = 0
    paid_cents: int = 0
    good: int = -1
    quantity: int = 0
    job: int = -1
    craft: int = -1
    mechanic: int = -1
    reason: Reason
    late_event: int = -1
    next_retry_minute = 0
    reserved_until_minute = 0
    blocked_code: str = ""

struct Job:
    id: int
    poster: int
    origin: int
    destination: int
    purpose: Purpose
    cargo_mode: CargoMode = .none
    good: int = -1
    quantity: int = 0
    passenger: int = -1
    created_minute: int
    npc_claim_after: int
    due_minute: int
    expire_minute: int
    reward_cents: int
    escrow_account: int
    state: JobState = .open
    carrier: int = -1
    obligation: int = -1
    source_inventory_kind: int    # 0 market, 1 person, 2 craft
    source_inventory_id: int
    loaded: bool = false
    loaded_quantity: int = 0
    delivered_quantity: int = 0
    lost_quantity: int = 0
    paid_cents: int = 0
    sealed_grams: int = 0
    cause: Reason

struct Event:
    id: int
    kind: EventKind
    minute: int
    place: int
    pos: vec3
    actor: int = -1
    target: int = -1
    actor_faction: int = -1       # membership at act time
    witnesses: int[]             # <= 8 direct witnesses
    severity: int                # 0..1000
    harm_cents: int = 0
    reason: Reason
    private_fact: bool = false

struct NewsItem:
    event: int
    kind: EventKind
    occurred_minute: int
    learned_minute: int
    origin: int
    source_person: int
    hops: int = 0
    confidence = 1000
    severity: int
    reason: Reason               # printable even after full event expires

struct RelationshipKey:
    observer: int
    other: int

struct Memory:
    event: int
    kind: EventKind
    minute: int
    severity: int
    reason: Reason

struct Relationship:
    id: int
    observer: int
    other: int
    affinity = 0
    trust = 500
    memories: Memory[]           # <= 4, salience-ranked
    grievance = 0
    last_contact_minute: int

struct ReputationKey:
    place: int
    subject_kind: SubjectKind
    subject: int

struct NewsReceiptKey:
    receiver_kind: int           # 0 settlement, 1 faction HQ
    receiver: int
    event: int

struct NewsReceipt:
    occurred_minute: int
    applied_delta: int

struct Faction:
    id: int
    key: str
    account: int
    home: int
    leader: int
    members: int[]
    player_regard = 0
    bounty_cents = 0
    bounty_escrow: int = -1
    bounty_event: int = -1
    bounty_target: int = -1
    bounty_claimed: bool = false
    next_patrol_minute = 0
    raid_cooldown_until = 0
    supply_obligations: int[]

struct Weather:
    id: int
    kind: WeatherKind
    center: vec2
    velocity_milli_m_per_minute: vec2
    radius_m: int
    severity: int
    wind_milli_m_per_sec: vec2
    born_minute: int
    expires_minute: int

struct Aftermath:
    id: int
    kind: AftermathKind
    event: int
    owner: int
    craft: int = -1
    place: int
    pos: vec3
    inventory: Inventory
    reason: Reason
    created_minute: int
    expires_minute: int           # -1 while unresolved ownership/repair persists

struct Account:
    id: int
    key: str
    cents: int                   # nonnegative, no implicit overdraft

struct MoneyEntry:
    id: int
    tick: int
    debit: int                   # payer account, -1 = outside simulation
    credit: int                  # recipient account, -1 = outside simulation
    cents: int
    kind: MoneyKind
    cause_id: int

struct Ledger:
    opening_cents: int
    external_in_cents = 0
    external_out_cents = 0
    sequence = 0
    recent: MoneyEntry[]         # <= 2048; cumulative counters never trimmed
    day_in: int[24]              # by MoneyKind numeric value (<= 24 kinds)
    day_out: int[24]

struct Encounter:
    id: int
    raider_trip: int
    victim_trip: int
    started_tick: int
    deadline_tick: int
    resolved: bool = false
    outcome_event: int = -1

struct BarkKey:
    speaker: int
    event: int

struct PresentationState:
    bark_day: {BarkKey: int}
    hailed_jobs: {int: bool}
    last_hail_tick: int = -1

struct World:
    seed: u64
    tick: int = 0
    minute: int = 0
    content_version = 1
    player = 0
    goods: Good[]
    people: Person[]
    places: SettlementRecord[]
    aircraft: AircraftRecord[]
    factions: Faction[]
    accounts: Account[]
    ledger: Ledger
    trips: {int: Trip}
    active_trips: int[]
    obligations: {int: Obligation}
    open_obligations: int[]
    jobs: {int: Job}
    active_jobs: int[]
    events: {int: Event}
    event_order: int[]
    relationships: Relationship[]
    relationship_index: {RelationshipKey: int}
    reputation: {ReputationKey: int}
    receipts: {NewsReceiptKey: NewsReceipt}
    weather: Weather[]
    aftermath: {int: Aftermath}
    encounters: {int: Encounter}
    next_trip = 0
    next_obligation = 0
    next_job = 0
    next_event = 0
    next_aftermath = 0
    next_encounter = 0

struct SaveGame:
    schema = 1
    valid: bool = false
    generation = 0
    terrain_key: int
    world: World
    presentation: PresentationState
```

### Where mutations happen, and why this stays cheap

`step_minute(w: mut World)` changes the existing value; it does not return a copied World. Scalar/person fields use `w.people[id].fatigue += ...`; market quantities use `w.places[s].market.inventory.qty[g] -= ...`; aircraft pose/fuel use `w.aircraft[c]....`; `loop mut` is appropriate for independent per-record updates. Maps use `w.jobs[id].state = ...`, never `j=w.jobs[id]` followed by a stale full-record write after callbacks. Helpers that touch multiple entities receive **World plus IDs**, not `mut w.people[id]` plus World (illegal aliasing). Call a pure read helper first, then mutate in a separate call.

Only scene bodies and two compact pose arrays are sampled at 60 Hz. Render snapshots contain ID/pose/visual state, not inventories, news, markets, or Person arrays. Save at a tick boundary, synchronously; release the serialized snapshot before resuming simulation. Normal ticks hold no `old_world=w`, old Person array, or UI copy of World. UI builds small lines/scalar views by borrowing World, then drops the borrow before a command mutates it.

Work is O(P×bounded candidates + active trips + S×G + heard news + sparse edges) per minute. Resident lists are rebuilt only on relocation. Relationships are created for actual known pairs, at most 32 outgoing/person; initial same-village acquaintance creation is a one-time cost. Price beliefs are at most 54/person. Route intersection uses 500 m spatial buckets of swept segments, not every pair of people; eight aircraft would also permit a bounded exhaustive reference implementation in tests. No relationship or news scan runs per physical frame.

Verified serialization caveat on this checkout: `to_text` of a `Set[int]` emits set notation, but `from_text` of a containing save failed at that Set field (expected a struct opening parenthesis). Therefore persistent membership/dedup uses maps such as `{int: bool}` or bounded arrays; use `Set` only for ephemeral scratch until its own roundtrip is verified. The SaveGame schema was checked with a nonempty struct-key map and the map replacement. Pool handles are likewise deliberately excluded from saved state.

Relationships are directed. Initialize both directions of a known pair; an interaction can update them differently. On a new acquaintance with 32 edges, evict the oldest neutral edge, excluding household, unpaid creditor, current employer, grievance>250, or active contract. If all are pinned, allow up to 64 and assert/report that cap; never evict a live creditor to satisfy a cosmetic limit. Events keep full records for eight game days; old events survive only if pinned by a live contract/aftermath, while all memories carry their own compact Reason. Dynamic terminal jobs/trips/obligations are pruned after eight days if unreferenced. Counters never rewind. Historical IDs inside compact Reason/Memory are optional evidence lookups, not owning references: a pruned full Event/terminal Job may be absent, and speech uses the snapshot. Live trip/job/obligation pointers must resolve, as must all Person/aircraft/account IDs (tombstones remain valid). Pins come from active obligations/trips/aftermath, not every historical snapshot. Save growth is bounded in steady state, apart from deliberately retained lifetime identities/accounts.

### Save/load contract

Use `save_value("world-a", SaveGame(...))` and `world-b` alternately with increasing generation; select the highest generation that parses, has `valid=true`, has supported `schema`, and passes invariants. Do not claim file-level atomicity from the API docs. A failed write leaves the previous generation available; load does not overwrite either slot. Use `load_value(name, SaveGame())` (`valid=false`) so a corrupt/missing slot cannot look like a fresh world. The API preserves unreadable data as `.bad`; surface a load error instead of silently starting over. Reject a newer schema read-only; do not erase it.

`from_text` matches fields by name and defaults missing fields, but that is not semantic migration. Keep old enum variant names and good/settlement keys stable; never reorder package-unit arrays without a migration. Content key order is written in `world.goods` / `world.places`; migrate old indices through keys, including inventories, beliefs, route endpoints and reputation keys. Bump schema for unit/meaning changes, content_version for revised starts/routines. Implement explicit v1→v2 conversion before changing old meaning. Validate all IDs, quantities, escrow, location exclusivity, ledger equality, route state, and tick/minute relation before accepting a save. Terrain-key mismatch requires an explicit geometry relocation migration, not mooring at the same numeric dock in a different map.

At save, persist each aircraft's current common Pose plus any extra flight-integrator state required by the integration adapter (the coordinator must add that POD extension once its schema is known). Save scene ownership as abstract ownership after synchronizing at the fixed tick; save an in-progress encounter, damage, throttle, velocities and remaining route. Restore the same state into a scene body if near the player; never regenerate a departing craft at its origin. Walking appearance/bob/animation phase and Pool handles are cosmetic and rebuilt. No offline wall-clock catch-up in v1.

## 3. The tick and actual rules

### 3.1 Clock, ordering, commands

Run physics at 60 fixed ticks/physical second. Tick is the only clock. Every 120th tick runs one world minute; `minute=tick/120` and day/hour derive from it with a saved epoch of day 0, 09:30. For a headless abstract run, advance directly to each minute boundary and process all intervening scheduled incidents in `(scheduled_tick, event_priority, ID)` order. Do not take a 120-tick jump through a materialized encounter. A pause pauses both clocks. On frame stalls use a bounded accumulator (at most .25 physical seconds accepted/frame); discard excess real time rather than fast-forwarding only the economy. A time-speed debug key must scale physics and world together or be visual lighting only.

Fixed-tick order:

1. Apply input/scene commands stamped for this tick, sorted by `(tick, actor ID, actor command sequence)`. Validate inventory, location, ownership and revision now; never let UI directly write tables. Reject stale commands with a visible reason. Player aircraft controls go to physics, not the NPC scorer.
2. Decide materialization transitions from last committed poses and swept routes (§3.8). Create/destroy only after the current scene update completes; an object has exactly one movement owner for the entire step.
3. Advance scene bodies; drain scene damage/landing/encounter outcomes in stable entity order into transactions. Update common poses and damage/fuel once. Advance due abstract incidents/arrivals to the same tick, skipping scene-owned trips and encounter members.
4. At minute boundary run the following minute procedure. Publish compact render/UI projections afterward.

```text
minute(w):
  derive clock; advance weather centers; expire weather at its saved time
  refresh minute-based harbor closure/reopening counters
  settle completed travel/work/repair actions in actor-ID order
  update fatigue, solitude, injuries; clear recoverable refusing states
  if hourly boundary:
    apply hourly demand/spoilage and production that actually completed
    execute scheduled external shipments (including delayed arrivals)
    set stock-derived hourly prices
    maintain supply postings and rescue/tow work
  if daily boundary:
    archive yesterday's top 3 news; expire old receipts/events/terminal records
    accrue bounded interest; schedule wages, rents, external shipments, work duties
    decay relationships/regard; reset per-day work/raid budgets
  receive direct events and arrival-carried news; update reputation once
  test deadlines; create one late/breach/default event per obligation transition
  create funded postings and schedule faction responses to newly received news
  for each eligible NPC, increasing ID:
    keep committed trip/action, else decide as in §3.2
  atomically execute chosen claims/departures/work reservations in that order
  gossip only among co-located people in current dock/inn presence window
  insert new public event news locally; queue remote learning until next boundary
  validate cheap invariants; dispatch speech/board/aftermath changes
```

“Hourly” means multiples of 60 game minutes relative to midnight, not “60 calls since startup.” Opening state is priced before the first tick. Completed production is inserted immediately at completion; the hourly routine must not insert it again. An event generated late in this tick can update its local news now but cannot trigger an unbounded same-tick reaction chain. Mark emitted event IDs and process reactions on the next minute. Simultaneous job claims favor the first valid command; NPC order rotates by day (`(ID+day)%NPC_count`) for claims only, to prevent permanent low-ID monopoly. All decision calculations use the same start-of-decision-phase market quotes; execution revalidates balances and reservations.

### 3.2 Obligations → routine → additive choice → vice method

Reconsider at an action boundary or every 15 game minutes while idle, plus immediately on a new actionable obligation, landing, damage, or job claim failure. Work/social/rest blocks last 60/30/60 minutes, and may yield at their next 15-minute checkpoint. Trips and claimed loading/landing sequences are committed. A due obligation can interrupt a work checkpoint, not an airborne route. Loading is 5 minutes and is charged once.

Pressures are recomputed, not independent ever-increasing timers:

```text
daily_cost = 1200 cents (NPC); player has no auto-choice
due = unpaid cents due within 360 minutes + cash needed for current contracted fuel/repair
reserve = daily_cost + due
M = clamp((reserve - spendable_cash) / max(reserve,1200), 0,1)
D = max over open obligations clamp((120 - slack_minutes)/120,0,1)
    slack = due - now - feasible_remaining_work_and_travel
R = clamp((fatigue - 200) / 800,0,1)
C = clamp(alone_minutes / 720,0,1)
V = largest grievance / 1000
```

Escrow and someone else's cargo do not count as cash/assets. Fatigue increases 20/hour awake, another 20/hour flying or repairing; decreases 120/hour resting, minimum 0. Below 200 removes fatigue cost; above 850 forbids new voluntary flights. Alone counter increases only with no actual co-presence, resets after a 30-minute social block (passing through a dock does not reset it). Duty is a pressure for discretionary early completion, but urgent fulfillment is selected before scores.

```text
decide(person):
  if player, injured, departed, or committed travel: return KEEP
  update vice latch from pressure; this selects methods, not a free action yet
  urgent = obligations with slack <= 30 minutes, sorted by
           (life/safety delivery before money before shift, due time, obligation ID)
  for o in urgent:
    if now < o.next_retry: continue
    a = feasible next step(o, vice_method)
    if a exists: return a
    mark blocked(o, code, retry=now+60); emit Late only on first due crossing
  r = routine block covering now
  if r is mandatory and feasible and checkpoint budget remains: return r.action
  candidates = finite activities possible HERE, plus next steps of blocked money duties
  score each as below; choose maximum, tie by (purpose enum, target ID, job ID)
  if winner.score < .10: wait 15 minutes (or rest if fatigue > 600)
  return winner, transformed to feasible vice method if latch active
```

An unpaid money obligation's next step is: pay what is affordable (keep 400 cents living reserve and required return fuel); otherwise collect completed earned payment; otherwise take a feasible net-positive local work/job action; otherwise the latched vice's feasible income action; otherwise mark blocked. “Feasible” means physical location, operational craft/boat, sufficient fuel including reserve, time window, capacity, lawful access if honest, affordable stock, and real counterparties. It does not mean guaranteed success. An impossible debt must never monopolize decisions. A destination shift starts travel early using actual ETA; if already too late, notify the employer and travel only if the remaining shift still pays more than transport.

Use float scores only at decisions; terms normalized to roughly −1…1:

```text
score(a) = 2.4*M*m + 2.0*D*d + 1.6*R*r + 1.0*C*c + 1.2*V*v
         + .50*greed*g + .55*boldness*risk + .40*sociability*social
         + .60*loyalty*ally + .45*trust + .25*affinity
         - .90*honesty*illegal - 1.1*loss - .25*duration - .8*fatigue_cost
         + noise
```

Traits here are 0…1; trust=(trust−500)/500 and affinity=affinity/1000 toward the counterparty (0 for unknown); ally=1 for helping a faction member/household, −1 for harming one, otherwise 0. Do not give trust bonuses to targetless rest. `loss=clamp((1-p_success)*exposure_cents/4000,0,2)` is an additive expected-loss cost, never multiplication of the whole score. `duration=clamp(total_minutes/180,0,2)`. Noise is deterministic uniform [−.05,.05] once per person/decision minute/candidate key, not per frame. `fatigue_cost=clamp(added_fatigue/300,0,1)`.

Candidate relief/feature constants:

| Candidate | m | d | r | c | v | g/risk/social/illegal |
|---|---:|---:|---:|---:|---:|---|
| Work or paid delivery | clamp(net cents/2000,−1,1) | 1 if progresses own duty else 0 | −.1 | .1 | 0 | g=m; risk=1−p; social=.1; illegal=0 |
| Trade believed margin | clamp(expected net/2000,−1,1) | .3 if supports debt | −.1 | .1 | 0 | as work |
| Rest | 0 | 0 | 1 | −.1 | 0 | all 0 |
| Visit / dock gossip | −.05 | 0 | .1 | 1 | 0 | social=1; others 0 |
| Patrol | actual wage net/2000 | 1 for patrol duty | −.1 | .1 | .4 toward known raider | risk=.3; illegal=0 |
| Raid | expected loot net/2000 | .6 if crew supply overdue | −.2 | .1 | 1 if target is actual grievance | g=m; risk=.8; illegal=1 |
| Smuggle | expected net/2000 | .7 if supports debt | −.1 | .1 | 0 | g=m; risk=.5; illegal=1 |
| Early debt repayment | −amount/2000, clamp −1 | 1 | 0 | 0 | 0 | ally/trust refer to creditor |

Local jobs/work candidates are enumerated in stable ID order, at most four board jobs, two trade routes, one friend, one patrol, one raid, rest and current obligation progress (max 16 total). Expected net subtracts fuel, loading fees, purchase cost, and expected loss. Agents require observed prices no older than 12 hours; uncertainty confidence decays linearly to zero at 24 hours, blending destination quotes toward base price. A trade needs expected net >400 cents; no endlessly speculative loss-making travel. Work is available only once per duty period and pays for actual completed minutes; there is no repeatable zero-time wage action.

Vice latch: enter if `M>=.80` and unpaid due<=6 hours exceeds cash, or an owned craft has engine<350/hull<350 and affordable repair is impossible. Stay active at least 120 minutes; exit when M<.45 and no due item is blocked, or after a refusal recovery block. Smuggle adds tobacco-route candidates and waives the lawful-access gate; gamble stakes `min(500, cash-400)` at an actual inn, once/day, transfers stake to inn and pays 2×stake back on a keyed 40% win only if the inn can fund it; join-pirates is available only after meeting a crew member and crew acceptance, changes faction, does not mint craft/cash; refusal cancels unclaimed new flights for 120 minutes, emits a refusal, then requires 60 minutes rest or 30 minutes trusted company before reevaluation. Under no circumstances can a vice spawn contraband, cargo, fuel, or a loan. Pirates already in the band use the crew raid pressure rule, not join-pirates repeatedly.

### 3.3 Routines, production and service recovery

Routine table (game local time); times are presence/work reservations, not animations. Service roles serve an arriving customer by a 5-minute transaction even outside a scoring window if physically present. One named absence can delay a workshop; markets use the named shopkeeper's posted price and account, with an anonymous counter assistant during 08–18, so one inn visit cannot disable all trade.

| Role | Mandatory block | Presence/free blocks | Actual production/pay |
|---|---|---|---|
| Fisher | 06–10 fishing (one completion/hour) | 10–11 dock sell; 18–20 quay | 4 fish packages/hour × catch factor; sold from pocket to local market |
| Oil presser / miller | 08–11 work | 11–12 market; 18–20 inn | 3 oil / 6 grain packages per completed hour |
| Mechanic | 08–10 + 14–16 reserved service, only if work exists | dock/workshop 08–18 otherwise free | repair customer pays labor; no extra wage for same hour |
| Clerk / patrol / telegraphist | 08–10 + 14–16 duty | workplace 10–14, choices allowed | 1200 cents/day for 240 completed duty minutes, prorated |
| Teacher / nurse / priest | 09–12 duty | quay 12–13, home/inn 18–20 | 900 cents/day prorated from public/cooperative account |
| Merchant / innkeeper / hotelier | open 08–10, 12–13, 18–20 | local choices outside these blocks | market/inn sales; no automatic extra wage |
| Courier | 08–12 + 13–14 dispatch service; at18 return home if safely reachable by20 | free for contracts 06–08,12–13,14–18, and after returning | earned job rewards only |
| Racer | 09–10 service aircraft; 16–17 practice only if affordable | hotel 18–20 | spends own cash; no purse generator |
| Pirate / quartermaster | 08–09 cove preparation; 18–20 return/service | free for captain's claims | loot sold into real black market |
| Everyone | 00–06 rest, except committed trip/urgent contracted medicine | evening company is a candidate, not forced attendance | rest/solitude as above |

Production uses labor minutes once, keyed daily fishing yield in [.6,1.4], with zero catch during closed-water conditions. Oil/grain represent harvested local background resources activated by a named worker; that creation is recorded as production, never duplicated as a settlement rate. A priest teaching or nursing does not magically produce medicine. Consumption is separate background demand, as below. Locally transferred income keeps work meaningful. Six bad-weather hours create a shortage; a bad-weather month is bounded by weather duration/import policy, not test assertions requiring calm prices.

Dispatch service means checking and claiming a feasible positive-net paid delivery when its public tender window ends, as part of doing the courier occupation; it does not compete with voluntary rest in the scorer. With no eligible job, reserve at most30 minutes of dock presence, then yield to a choice and check dispatch again at the next15-minute checkpoint. A loaded committed delivery proceeds at its scheduled loading/departure completion even when its deadline is not yet urgent. Returning home is an occupation routine for couriers, including carrying their news back; a contract, injury, closure or insufficient fuel creates an explicit overnight/recovery exception. This prevents a comfortable pilot resting forever at the last destination and makes news circulation a consequence of employment rather than an invisible broadcast.

A repair requires one exclusive mechanic and parts reservation, charged in a single transaction at completion: restore 200 condition points per 60 work minutes, consuming 0.5 parts package and 800 cents labor per 200 points, whichever of hull/engine is being repaired. Return unused parts on cancellation; never charge for nonexistent labor. Schedule engine then hull until both>=800 or funds run out. Reservations expire after 120 minutes without progress; owner gets a reason and can choose another workshop. A 50%-worn plane can still earn; new flights need engine/hull>=350. Aircraft held in workshop are visibly owned and unavailable to both controllers.

### 3.4 Markets, money and outside shocks

Only the nine commodities are stocked/priced. Mail is a sealed job, and a passenger is a Person manifest with seats/weight; neither can be sold as fungible stock.

Good data, in enum order (price cents/package, mass grams/package, shelf hours):

```text
fish      800   5000  24
wine     1200  10000   0
oil      1400  10000   0
grain     600  20000   0
fuel      800   8000   0   # 1000 milli-packages = 10000 ml fuel
parts    2400  10000   0
medicine 1800   1000   0
tobacco  2200   5000   0   # illegal outside Kryfo
arms     5000  15000   0   # illegal outside Kryfo
```

Once/hour, after completion/demand/imports:

```text
ratio = clamp(stock_milli / max(target_milli,1000), 0, 3)
desired = base_cents * clamp(1 + .8*(1-ratio), .45, 1.8)
price_next = round_to_cent(.75*price_old + .25*desired)
```

Zero stock gives the upper clamp, 1.8×base; funded outside demand changes the target before the same rule runs. Set initial price directly to desired at new-game construction, so a starting shortage is visible immediately. Reserved goods count as physically present stock until loaded; sellable is stock−reserved. No order book or bargaining market. A local transaction uses the one current hourly quote; a disclosed 2% harbor tax (0 at Kryfo) is a separate transfer to the authority account, minimum 1 cent on positive trades. Sell then buy at the same place cannot create money. Batch/trade caps prevent one actor monopolizing every unit: NPC lot<=10 packages and never knowingly sell essential fuel below their return reserve.

For fractional quantities keep integer cents residuals per transaction/accounting bucket; never drop a fractional fuel bill every frame. A trade may always be rejected for insufficient cash or stock. The market is counterparty for commodity trade; the merchant's Person account is their wage/profit draw, not a second copy of its till. At day end market owner may withdraw `min(max(till-20000,0),2000)` cents. In the content below every market starts at 40000 cents except Kryfo 12000. A market cannot buy without money. Legal markets can request a documented outside working-capital advance up to 20000 cents when till<5000, once/day; this is explicit subsidy, not a hidden overdraft.

Background households buy actual available stocks each hour up to `demand_per_day/24`, using `external→market` money and deleting consumed goods. Every missed milli-package increments unmet demand; it is not satisfied on credit or carried as exponential demand debt. At stock==0, there is no sale and no income. Fish loses `floor(unreserved_stock/24)` milli-packages hourly plus remainder (an exponential shelf-loss approximation, not batch freshness); reserved cargo still spoils while physically carried by the same rule and can fail its delivery quantity check. In v1 do not reserve fish for deadlines beyond 12 hours. Factory production/consumption and spoilage are separate goods-ledger reason codes.

Named-person living costs are real transfers, or their cash pressure would switch off permanently after a few deliveries. At22:00, each NPC in a town buys/consumes up to500 milli-packages fish and500 grain from unreserved local stock at actual quotes, if affordable, then pays500c lodging to the local innkeeper/hotelier/authority (innkeeper to authority, pirates to cove market). Estimate at base prices:400c fish+300c grain+500c lodging=1200c/day. Never debit nonexistent food or overdraft; missed lodging creates one500c non-interest rent invoice/day, which breaches/defaults after seven days. Named consumption is **additional** to the anonymous headcounts/demand table, whose population excludes named people. A boat/airborne NPC carries at most one day of personal rations in pocket, otherwise settles food at next safe harbor; no mid-air stock lookup. Injury care uses the same food costs with a documented public emergency transfer if needed. Player food/lodging is not automated in v1; only their stated mooring/service invoices are due. This is an explicit player-control boundary.

Outside supplies: at 06:00/day prepare one ship manifest per legal settlement, quantities `min(max(target-stock,0), cap)`: cap/day fuel 8 packages, parts 2, medicine 2, wine 3, grain 8; other commodities import only by a funded supply order. Departure and quantities are fixed then; arrival is 10:00 plus keyed 0–180 minute delay, with 15% one-day cancellation, maximum two consecutive cancelled days (third ship sails if weather permits). Closed harbor retries at +60 minutes, max 360 then returns outside with no charge. Import quote .8×base, paid from market to outside at actual arrival; partial affordable deliveries allowed. Outside buyers at 17:00 purchase local surplus above target, max 8 packages/good at .65×base, transferring outside→market. This outside spread leaves local transport useful, and does not give an instant same-town arbitrage loop. Kryfo receives a small night smuggler manifest: 2 fuel, 1 parts, 2 tobacco if funded, at 1.1×base; same delays/cancellation rule.

Production and consumption scales in §4 are deliberately small: one fisher's absence is a shortage, but a failed courier is not a month-long starvation spiral. One 20%-chance daily hotel banquet demands 3 extra wine packages at 19:00; it adds a funded hotel supply obligation in the morning and an auditable stock target until the banquet. This is an outside customer order; do not generate it because news is boring. Weather and external ships are the other initial shocks. No seasonal catch term until seasons actually exist.

Money path is **one function** `transfer(w, payer, recipient, cents, kind, cause)`: check positive amount, sufficient payer, both account IDs, then debit/credit and ledger together without callbacks. A `-1` endpoint is allowed only for enumerated outside flows. `sum(accounts.cents) == opening + external_in - external_out` holds exactly after every transaction. Escrow accounts are included. Borrowing is a transfer, principal interest accrual is a liability change rather than money creation, and principal/interest payments go to the creditor. Fuel is sold by market then consumed from tanks, repair labor goes to mechanic, parts to market, fines to authority, rent to landlord/authority, gambling to/from inn, bounty from authority escrow. None of those are boundary sinks. Wages are faction transfers; the authority receives an explicit outside subsidy of 8000 cents/day and cooperative public services 3000/day. Those amounts are initial policy, not balancing adjustments.

New loans require a willing funded creditor and explicit principal transfer; v1 NPCs cannot originate fresh loans except the outside market advance. Existing debts accrue 1%/day on unpaid original principal, simple not compound, with cents remainder. Total interest cap is 50% original. After seven days overdue: one default event, cancel growing interest, remove urgent lock, and creditor may fund a repair/repossession job; never seize the player plane automatically. This intentionally sacrifices a credit model to keep visible obligations recoverable.

For debts, original_cents is immutable initial principal; principal_cents and interest_cents are remaining balances, and amount_cents is their sum. Payment clears interest first then principal, increases paid_cents, and transfers precisely that paid amount to the creditor. Interest accrual adds only to interest_cents and interest_accrued_total; the lifetime latter enforces the50% cap even after a payment. A completed or defaulted debt cannot accrue again. Nondebt obligations use amount_cents directly and leave these debt-only fields0. Provision requests and shifts are not loans just because they mention money.

### 3.5 Job lifecycle and service failures

Supply jobs arise from a specific poster's obligation/local stock target, not knowledge of a remote price gap. On hourly review, target deficit>=2 packages and stock<.4×target can make one open supply request per `(poster,destination,good)`. Poster must know a source seen/heard within 12 hours, own that source cargo or pay to reserve it, and fund reward escrow. Poster may ask a known supplier via carried news; no teleporting contract across towns. Initial postings may already exist with correct reservations. Reward=`max(800, 8*route_game_minutes + 400*urgency)` cents, urgency=1 if slack<120 else 0, capped at poster's spendable cash. Round once; no reward without escrow.

Posted jobs have `npc_claim_after=created+90 game minutes` (three physical minutes), for **every** posting whether the player is nearby or absent. This is a public 90-minute tender window, not a secret player-presence freeze. The player may accept during it; NPCs may advertise intent and then claim when it ends. The world keeps moving; old taken jobs remain on the board for 12 hours with carrier/name/status. At least one day-zero posting has an 8-hour deadline so it remains usable during the first landing. The dissent's arrival-based freeze would let the player stop the economy by loitering; reject it.

Claim: verify at origin, free craft/seat/capacity, fuel and ETA before expiry; set one carrier and create one obligation atomically. Cargo transfers reservation→aircraft at load completion; reserve space/cargo during loading. Source loses quantity exactly once. A sealed parcel must not also be counted in commodity cargo: Job holds its quantity/ownership; the manifest references it; mass sums both. Ordinary commodity delivery jobs use cargo quantities earmarked by job and forbid selling the earmarked amount. Use either sealed or commodity mode, never both; the initial medicine shipment is commodity mode, initial mail is sealed. Destination receives quantity once on verified docking, then escrow pays carrier and job becomes delivered. Carrier cannot finish by flying past. The poster's supply duty fulfills when the destination receives, not when a pilot claims it.

At `due`, emit one late event; accepted delivery may continue for 120-minute grace at 75% reward (25% returns poster). At `expire`, terminal failure releases unloaded reservation and refunds unpaid escrow; delivered portions are not clawed back. Loaded cargo stays with its current owner, marked returnable to poster; a new return obligation uses actual location. Lost cargo creates a loss record and grief, never a replacement copy. A passenger who has not boarded by expiry stays at origin, refunds and complains about carrier only if there was an accepted promise. A boarded passenger stays a real person, can disembark at a safe alternative harbor, then receives a new return/ferry option; deadline cannot delete them.

No open public job creates blame for an NPC/player who did not accept it. Unclaimed expiry concerns the poster's unmet need. Failures caused by storms still create lateness and lost income, but do not reduce trust as much as deliberate theft: −30 versus −150 trust. Unfunded needs remain sayable (“I cannot afford a courier”), without a fake payable notice.

Cargo details: `job_manifests` lists all aircraft Jobs, while only commodity Jobs earmark quantities inside `AircraftRecord.cargo`. `Job.quantity` is the immutable promised total; loaded/delivered/lost quantities partition its physical progress. The poster owns paid cargo throughout carriage; carrier holds it and cannot spend its value as personal wealth. A raid decrements the physical craft stock and increments the affected Job's lost_quantity, choosing earmarked lots by ascending Job ID after unearmarked goods. At docking, atomically accept all available earmarked remainder, increase delivered_quantity, and pay `floor(reward*delivered_quantity/quantity*lateness_factor) - paid_cents`, never a second full reward. If known lost_quantity makes completion impossible, finalize failed-partial immediately, refund remaining escrow, and record missing quantity; do not discard the medicine that survived. If cargo is merely delayed, hold unpaid escrow until expiry. Sealed mail pays only on intact full-parcel arrival, has sealed_grams5000 for Job0, and does not use commodity quantity arithmetic. Passenger likewise pays only on actual safe disembarkation. The destination stock increment and all linked supply-duty progress use the delivered quantity once. This defines the partial-delivery bookkeeping implied by the grace rule above.

### 3.6 News, reputation, relationships and speech

Create an Event only for a meaningful transition/completion; not every minute of a flight or repeated failure to pay. Severity is clamped 0…1000:

```text
base: delivery 100, produced 20, arrival/departure 40, late 180,
      default 400, theft 450, raid 600, rescue 500, ditch 650,
      repair 120, shortage 250, closure 300, refusal 180, patrol 180
severity = min(1000, base + min(harm_cents/50,300) + (unexpected ? 100 : 0))
```

Unexpected is exactly one of: first local raid in seven days, first default by that person, previously open harbor closing. Normal production is available for circumstance dialogue but will lose the news ranking to a raid. Direct participants and actual nearby witnesses get confidence 1000/hops0; a private debt is initially known only by debtor and creditor. Choose witnesses from the settlement's co-located residents, up to eight by distance then ID. For an abstract incident use people on the same trip or on a declared nearby fishing/boat route within 1000 m at that tick. Do not auto-grant every remote town a witness.

On docking, carriers exchange up to three highest-ranked **public** news items with that place and learn up to three there. At the inn/quay each game hour, pair co-present people in ascending rotating ID order; each pair exchanges at most two items. A speaker passes `hops+1`, confidence=`floor(old*.85)`; reject hops>4 or confidence<300. Direct evidence does not increment hops just because it is posted at its origin. An inn visitor does not repeat a private debt unless its owner has made a public late-payment notice. No distorted actor names or quantities in v1: uncertainty is a confidence/hop marker, not randomized lies.

Rank by `severity * confidence/1000 * max(0,1-age_minutes/10080)`, tie newest occurrence then event ID. Keep 12 distinct IDs/person/place, expire at seven days, preserve a severe grievance's compact Memory separately. Rehearing uses highest confidence, then fewer hops; it must not refresh occurrence time or score age. Prices travel separately as PriceBelief; newest observation wins, ties prefer higher confidence then lower source ID. Learned time cannot freshen an old quote. Visits read actual local prices without revealing all other towns.

On the **first** accepted arrival of an Event at a settlement, insert an eight-day receipt keyed by settlement/event. Apply regard to the actor once:

```text
base regard delta: delivery +30, rescue +100, repair +10, late -20,
                   default -60, theft -100, raid -160, fine -15;
other event kinds 0
delta = base * confidence/1000 * (0.5 + severity/1000)
```

Round away from zero only at the final integer step; zero remains zero. In legal towns raid/theft coefficients above apply; in Kryfo a raid on non-members is +40 base and harming a member is −200 base. Apply .4×delta to the actor's event-time faction, not their current membership. A faction reads arriving news at its own HQ and applies one separate receipt to its player regard, with the same coefficient sign; no applying the same act once per remote town to a global faction meter. Daily local regard moves 1% toward zero, minimum one point; clamp −1000…1000. Higher-confidence rehearing improves speech labels but does not apply another reputation delta. This is deliberately a first-report model; corrections/exoneration require a distinct evidence event in a later milestone, rather than silently rewriting totals.

Consequences read the same place score: local regard<-300 requires prepaid service; <-600 denies new credit and adds a search on docking at a legal harbor. Cash trades/basic fuel remain available unless an actual outstanding arrest/bounty order is funded, so one rumor cannot permanently ground the player. Reputation does not grant omniscient target detection: an identified actor and local news are required. Direct victim affinity/trust update happens once at the act, independently of gossip (the victim knows what happened). Delivery +40 trust/+20 affinity; late −30/−10; deliberate cargo theft −150/−100; raid −250/−250 and grievance +400; rescue +150/+150. News recipients change public regard, not personal trust unless they directly know the victim (then at most .25×the direct affinity delta, once). Loyalty, trust and affinity enter the scorer in §3.2 and job credit/search decisions, so they are not decorative.

A Memory retains the four most salient reasons, allowing a player to ask why a pilot dislikes someone even after news expires. Grievance decays 5%/day and repair/restitution can reduce it; it cannot remain a permanently maxed revenge pressure after the culprit departed. Daily affinity/trust move 1% toward neutral only when there was no contact that day, except pinned debt/serious grievance memories.

Speech is a deterministic projection, not part of simulation RNG:

* Within 12 m on foot, a named speaker who is not occupied in takeoff/repair offers one line on entry into earshot. Maximum one bark/settlement/60 game minutes (two physical minutes), and one reuse of a given `(speaker,event)` per day. Arrival claimant may hail once within 90 seconds of physical mooring; it creates no job/claim on its own.
* Pick urgent own circumstance before top public news: accepted overdue cargo, funded job still open, engine under repair, injured friend, then best news with severity>=180. The line includes a name, destination and concrete stake. Example: “Nikos has Maria's medicine. She needed it before noon.” A generic “busy day” is not a reason.
* At day rollover select the top three events **heard here yesterday**, preserving occurrence/learned dates separately; if fewer, print fewer. Board includes current open jobs, 12-hour taken/failed/delivered history, reward/deadline, and yesterday's sentences. Never print tomorrow's omniscient event.
* News leads to the same Aftermath ID/owner on the chart when location is known. A broken plane in a workshop has owner, damaged subsystem, repair cost and expected service time; those are useful facts, not extra prose lore.

Persist spoken event/day keys and job hails in SaveGame.presentation, separate from global news deduplication; otherwise save/reload repeats every hail. Prune bark_day entries after two days and hailed_jobs after their job is pruned. Tests can call `say_reason(Reason)` without a renderer and assert it names actor and beneficiary/cause.

### 3.7 Trips, hazards, pirates, weather and aftermath

Aircraft type constants (capacity excludes pilot; passenger uses 75000 g and a seat):

| Type | Cruise m/s | Usable cargo g | Passenger seats | Tank ml | Air burn ml/physical sec |
|---|---:|---:|---:|---:|---:|
| Gull | 60 | 180000 | 1 | 80000 | 60 |
| Heron | 55 | 550000 | 3 | 160000 | 90 |
| Corsair | 65 | 120000 | 0 | 70000 | 80 |
| Falco | 70 | 90000 | 0 | 60000 | 70 |

Taxi burn=20 ml/physical second for all, engine off=0. These are economy/route starting constants for the integration adapter, not claims about WIP flight coefficients. If measured cruise differs, change the shared type table and re-run route/contract acceptance; never keep a fast abstract plane and a slow visible one. New departure needs estimated taxi+flight+approach fuel plus `max(5000 ml, .20*route burn)` reserve. Abstract taxi and approach take 10 game minutes each; straight route time is `ceil(distance_m/cruise_mps/2)` game minutes, so near and far durations have the same units. Interpolate movement every render frame from exact trip elapsed physical time, not a point jumping every two seconds. Abstract routes follow harbor departure/approach bearings, cruise at terrain clearance>=150 m, nominal altitude500 m. Any route over a ridge must sample shared terrain; no line through cliffs.

Use semantic route points built from geometry: dock→100 m outside quay→outbound water lane→cruise waypoints→destination approach at `center+out*1500m`→`center+out*250m`→free dock. Headless sim receives a baked HarborGeometry value (centers, out vectors, docks, holding and safe water/beach anchors) generated from the same `coast_point`/terrain version as Town, without importing Mesh constructors. No calling `build_town` in headless tests. Three Porto docks and two elsewhere are scarce resources; a legal safe offshore mooring buoy per harbor permits waiting/fuel service when all docks are occupied. Queue by emergency first, request tick, craft ID. After 30 game minutes waiting, use the buoy; do not teleport into another aircraft. Mooring can stay overnight, so a fixed finite dock wait without a buoy would deadlock normal arrivals.

An off-screen flight checks weather along swept segments and encounters at scheduled ticks, not once at arrival. For engine<600, failure hazard per **physical flight hour** is `lambda=min(1.5,.15*(600-engine)/250)`; otherwise zero in v1. At departure use one keyed draw for probability `1-exp(-lambda*planned_physical_seconds/3600)`, and one to pick incident distance conditional on failure. Store incident distance/resolved flag, so culling or loading cannot reroll. This intentionally keeps well-maintained routine flight reliable; landing accidents in scene still occur from actual physics. Arrival consumes fuel for actual elapsed active time; scene already-accounted fuel is excluded from abstract burn.

Piracy is not a random hazard on every cargo flight. Only a real airborne raider with an active raid plan can intercept. The captain (Cem) controls the shared faction raid decision, not four simultaneous argmaxes. A raid becomes feasible when cove spendable cash<12000 cents or a fuel/parts supply obligation is due within six hours, and a known victim cargo value>=3000 cents is expected on a reachable route within three hours. Captain knows only witnessed/public manifests or actual visual contacts. Other crew choose assigned preparation/repair/support as obligations; a missing wingman does not veto a solo viable sortie. Raid requires fuel to intercept and return with reserve. Choose a predictable waypoint/time intercept from known departure, then search for at most 60 game minutes if prey is absent. No teleporting to a chosen merchant.

One captain departure/day and 18-hour cooldown after contact. One raid Encounter per `(raider trip,victim trip)`; both trips join it. Abstract contact at swept separation<=800 m, combat/contact lasts 10 game minutes. Initial abstract chance:

```text
p_loot=clamp(.55 + .20*(raider boldness-.5) + .15*(engine difference/1000)
                  - .25*(patrol within 2000m) - .15*(victim has escort), .15,.80)
```

One keyed draw per Encounter. Success transfers at most `min(40% of victim unsealed base-price value, 4000 cents)` worth of whole/milli commodity units into available raider cargo space, or surrendered cash if no transferable cargo. A named medicine parcel may be damaged/lost in a separate damage consequence, never both stolen as cargo and retained as a parcel. Theft cannot exceed actual stock/cash. Raider then returns and sells only to an affordable Kryfo market. On failed raid: raider engine−100, victim engine−50; on success: victim hull−100, raider hull−50; a second keyed draw <.10 causes a victim ditch only if its resulting hull<500. All direct participants witness. This produces a reason for a workshop plane without making every encounter a cast reset. Player-present combat uses actual controls, ammunition, damage and surrender; these odds do not run there. The loot cap governs NPC looting behavior, not an arbitrary ceiling on the human pirate's actions.

At a legal HQ hearing identified raid severity>=500, reserve bounty `min(4000,authority spendable)` cents, post notice, and create Salvatore's patrol obligation for next available daylight departure within six hours. If unable to fund the bounty, still post the factual warning and patrol if viable; record unfunded bounty explicitly. Patrol routes the **reported last-known lane**, not the raider's hidden current position. One completed patrol provides an answer even if it finds nobody; do not promise a capture. A witnessed surrender and delivered offender/craft ID can fulfill bounty once and transfer escrow; merely finding a wreck is not an infinite bounty turn-in. Successful patrol adds a positive event and recent patrol coverage to subsequent raid risk. Officer continues service after a failed intercept.

One active authority bounty at a time in v1: persist its source raid Event and identified target; further reports may enlarge the funded escrow up to4000c but cannot create duplicate claims. A tow of the identified surrendered/disabled pirate aircraft to a legal harbor, with direct witnessed attribution, is sufficient to claim it; v1 has no prison model. Verify craft/target/source-event, set bounty_claimed before transfer, retain that receipt after escrow empties, and move the same craft into an authority-held workshop (held_by_faction=0, owner unchanged). The pilot remains a Person at that harbor and can work/pay release/repair through a new obligation. No new bounty on that source act and no reward merely for destroying an abandoned wreck. A later distinct witnessed raid can create a new bounty.

Weather: at new game fair with wind (3,1) m/s and no new squall in the first 180 game minutes. Each day schedule two independent cells at 07–11 and 14–18 using saved keyed draws, born outside a selected map edge, radius1800 m, lifetime180 minutes, drift12 m/game minute toward the interior. 35% storm severity850, otherwise wind/squall severity450–700; cells expire even if parked over a town. Ground wind is base plus radial linear cell falloff; sample it from saved time and position, not camera time. Harbor closes after three consecutive minutes severity>=800; reopens after 30 consecutive minutes<650. Pilot departure nerve is `350+.6*boldness` severity units (range350–950), and hull<500 subtracts100. A storm is a source of delays, not an obligation exception that flies everyone anyway.

During flight if weather exceeds nerve for three minutes, divert once to nearest safe harbor reachable with reserve; if none, use safe water anchor and request tow. An accepted delivery gets a diversion/late reason, not re-planned to a different speculative trade. If fuel runs out or hull reaches0, ditch: disable normal flight, put the actual/abstract craft at a validated water/beach anchor, set injured for 1–3 days keyed by incident severity, transfer salvage cargo to **one** Aftermath inventory and clear craft cargo. Add wreck/workshop plane, injured person and one event, then schedule a known fishing boat/tow departure. No health reset. The pilot remains injured at the pickup harbor; aircraft stays wrecked or salvageable until paid repair/tow.

Rescue fallback: public harbor service has one abstract boat per town, a daily 2000-cent authority-funded budget and a 90-minute dispatch delay; transit is real route distance at 8m/s converted by the same clock. It may rescue for no upfront payment, creating a capped 2000-cent non-interest debt. Rescue coverage is an explicit public service, not a miracle NPC appearing at the camera. If the budget is exhausted it can still move people for a recorded outside emergency subsidy; towing aircraft/cargo waits for payment. This is an intentional bounded safety valve for immortal people. It must not repair/fuel the plane. Report count of emergency subsidies in sweeps; repeated use is a tuning failure even though it conserves books.

If an NPC remains unable to fly after 48 hours, they can take local paid labor or funded ferry to a workshop. Private racer can stop practicing indefinitely; an actual open repair/debt cannot remain without a retry date. Crew obtains at most one outside night fuel/parts advance per seven days, 4000 cents, documented as debt with normal default cap; if still unable to raid it works local salvage (1200 cents/day, outside buyer) until viable. Initial raid does not depend on this fallback. Do not secretly keep a minimum faction wallet each tick.

Aftermath placement: use prevalidated HarborGeometry safe anchors, choose closest reachable shoreline to incident, attach ID/owner/reason, and reserve that site. Never put a wreck on the cruise line at y=500 or inside a cliff. A workshop plane remains until repaired/salvaged; recovered crate remains 48 hours unless collected; after 48 hours it transfers to the nearest market's lost-property inventory with an event (not disappears). Wreck materialization reads the existing record; it never duplicates cargo or creates a second owned aircraft. Injury has a date, and the person can speak while recovering.

### 3.8 Abstract world ↔ near-player scene

Use a 6 km **visibility/materialization envelope** with 500 m hysteresis, rather than implying every walker within 6 km needs physics. Aircraft enter at<=6000 m and leave beyond6500 m for 10 physical seconds. Named pedestrians get scene movement within300 m; outside that they occupy semantic home/work/dock/inn anchors and scheduled walking trips. Project all aircraft routes over the next two physical seconds; materialize before swept entry, including fast player approach, not only at minute boundaries. Aircraft already in player combat/visual contact cannot fold until the encounter ends and separation is outside hysteresis. Free camera is presentation; LOD follows the physical player's position, not a screenshot camera.

| Field | World owner | Scene owner while materialized |
|---|---|---|
| identity, ownership, account, inventory, jobs, obligations, relationships, reputation | exclusive authority | reads, submits validated commands |
| route, purpose, destination, encounter identity, deadline | exclusive authority | reads desired route/controller role; can report obstruction/diversion |
| common pose, fuel burn, damage, taxi/air/landing phase | abstract integration when abstract | physical integration; commit once per fixed tick |
| physical hidden state (angular velocity, contact/controller state) | serialized common/extension record | exclusive mutable instance while active, synchronized for save |
| animation, meshes, propeller phase, bob, figures, sounds | no simulation role | scene only |

Materialize: at fixed-tick boundary evaluate exact abstract pose/velocity/phase and already-spent fuel, create body and ID→Handle binding, initialize controller from trip route/reason/encounter, set move_owner=scene, then skip abstract movement, burn, hazard and arrival for this body. If the exact pose intersects newly loaded geometry, **do not relocate it silently**: block materialization, validate against same geometry, log invariant failure in tests. Initial route construction is responsible for valid terrain clearance. Rendering may begin at a distance with a compact aircraft projection while its full body initializes that tick.

Fold: copy actual pose/vel/condition/fuel once, project onto remaining route forward from last confirmed semantic waypoint, prepend actual position as the new route origin, recompute ETA from remaining distance and actual cruise state, set move_owner=abstract, remove scene body/handle after the step. Do not snap to nominal elapsed-route position; do not restore fuel/damage from an old snapshot. If aircraft is stalled, taxiing blocked, being attacked or contacting geometry, hold scene ownership or convert to an explicit obstruction/ditch event before folding. Fixed scene motion can differ from abstract outcomes; culling alone must not change an already resolved outcome.

Physical landing reports `(craftID,dockID,tick,revision)`; World verifies safe contact, destination, capacity and no previous terminal arrival, then processes delivery/payment once. In abstract mode the matching scheduled arrival calls the same transaction function. A scene airport controller may extend ETA; the world still tests deadlines against actual arrival, creating believable lateness. Shared person/craft relation means boarding removes a walker, not its Person, and exiting creates a walker for that same ID. Existing decorative Walker instances must be replaced, not left wandering beside duplicate named inhabitants.

Determinism contract: same fixed inputs, same LOD decisions/physical presence schedule and same seed produce the same state. Two different observer paths are allowed different physical encounters; demand conservation, identity and one-resolution invariants across both, not identical casualty/arrival hashes. Headless abstract sweeps are fast. Separate fully physical route tests must establish that ordinary visible NPCs can take off, land and recover reliably; the aftermath policy does not excuse an AI that crashes whenever watched.

## 4. Initial content: loadable data and imbalances

### 4.1 Frozen place/faction/account keys

Settlement indices exactly match `src/world.jo:283–290`:

```text
0 porto_vecchio  "Porto Vecchio"    island 6   port       owner 1  population 80  market 40000c workshop yes
1 kalamos        "Kalamos"          island 0   village    owner13  population 36  market 40000c workshop no
2 agios          "Agios Nikolaos"   island 3   monastery  owner17  population 20  market 40000c workshop yes (visiting mechanic)
3 mikra          "Mikra"            island 5   village    owner19  population 24  market 40000c workshop no
4 selene         "Hotel Selene"     island 9   hotel      owner20  population 12  market 40000c workshop no
5 kryfo          "Kryfo Cove"       island 8   cove       owner25  population  8  market 12000c workshop yes

Faction 0 authority  HQ0 leader5   members[5,9,10]    cash150000c
Faction 1 company    HQ0 leader1   members[1,2,3,8,11] cash200000c
Faction 2 fishermen  HQ1 leader12  members[7,12,13,14,18,19] cash50000c
Faction 3 pirates    HQ5 leader22  members[22,23,24,25] cash4000c
```

Other NPCs are unaffiliated; authority cooperates with public teachers/nurse/priest without making them police. All legal places use faction0 for law; Kryfo uses faction3. A public/inn place is not a separate full Faction. Add neutral paid accounts for each market (IDs26–31 if Person accounts are 0–25), factions (32–35), each job's escrow appended after those, and service/lost-property accounts only as needed. Account IDs are stable once allocated; keys, not the suggested numeric range, are the save migration identity. Person account0 is player. Market owner is a role, not ownership of all till cash as pocket cash.

### 4.2 People (25 NPCs; 26 records including player)

The following is data, not illustrative pseudonames. `money_lire` is converted once to integer cents. Trait order is honesty/boldness/greed/sociability/loyalty, all on 0…1000. Aircraft `-1` means none; fishers have a work boat resource tied to their job, not an aircraft. Every record starts home except the explicit overrides below. No unnamed pilot silently supplies these people.

```sloppy
struct PersonSeed:
    id: int
    name: str
    age: int
    home: int
    job: Occupation
    traits: Traits
    money_lire: int
    aircraft: int
    vice: Vice
    obligation_keys: str[]

PERSON_SEEDS: PersonSeed[] = [
    PersonSeed(0, "The Pilot", 29, 0, .player, Traits(600,600,500,500,500), 120, 0, .none, ["player_mooring"]),
    PersonSeed(1, "Eleni Vassiliou", 44, 0, .merchant, Traits(850,400,650,700,800), 260, -1, .none, ["agios_medicine","mikra_medicine"]),
    PersonSeed(2, "Nikos Arvanitis", 32, 0, .courier, Traits(700,800,650,650,700), 18, 1, .smuggle, ["dispatch_bag","nikos_engine_bill"]),
    PersonSeed(3, "Marta Bellini", 39, 0, .merchant, Traits(750,550,750,700,750), 180, -1, .gamble, ["marta_grain"]),
    PersonSeed(4, "Paolo Conti", 51, 0, .mechanic, Traits(850,450,450,550,850), 110, -1, .none, ["dario_service","paolo_shift"]),
    PersonSeed(5, "Yannis Markou", 48, 0, .clerk, Traits(900,350,300,650,900), 90, -1, .none, ["yannis_shift"]),
    PersonSeed(6, "Sofia Marinou", 46, 0, .innkeeper, Traits(650,500,550,950,700), 150, -1, .none, ["inn_wine"]),
    PersonSeed(7, "Petros Laskaris", 57, 0, .fisher, Traits(850,550,300,650,900), 32, -1, .refuse_flight, ["petros_rent"]),
    PersonSeed(8, "Dario Ferraro", 36, 0, .courier, Traits(800,650,600,600,800), 65, 2, .refuse_flight, ["marta_grain_delivery"]),
    PersonSeed(9, "Salvatore Greco", 41, 0, .patrol, Traits(900,750,250,450,900), 80, 4, .none, ["salvatore_shift"]),
    PersonSeed(10, "Leila Demir", 27, 0, .telegraphist, Traits(850,450,350,850,800), 55, -1, .none, ["leila_shift"]),
    PersonSeed(11, "Marina Kallergi", 30, 1, .courier, Traits(850,700,550,700,850), 75, 3, .smuggle, ["hotel_wine_delivery"]),
    PersonSeed(12, "Kostas Pappas", 53, 1, .fisher, Traits(800,600,350,750,850), 28, -1, .none, ["kostas_rent"]),
    PersonSeed(13, "Despina Ralli", 49, 1, .oil_presser, Traits(850,400,550,650,850), 95, -1, .none, ["oil_work"]),
    PersonSeed(14, "Yusuf Kara", 42, 1, .miller, Traits(800,450,500,600,800), 60, -1, .gamble, ["grain_work"]),
    PersonSeed(15, "Irene Mavrou", 26, 1, .teacher, Traits(950,450,200,850,850), 35, -1, .none, ["irene_shift"]),
    PersonSeed(16, "Maria Sarris", 34, 2, .nurse, Traits(950,700,150,750,950), 42, -1, .none, ["clinic_supply","maria_shift"]),
    PersonSeed(17, "Father Andreas Petrou", 62, 2, .priest, Traits(900,350,150,800,900), 55, -1, .none, ["andreas_shift"]),
    PersonSeed(18, "Dimitris Vrettos", 47, 3, .fisher, Traits(750,650,450,650,800), 24, -1, .join_pirates, ["dimitris_rent"]),
    PersonSeed(19, "Aylin Yilmaz", 38, 3, .merchant, Traits(850,550,650,750,850), 110, -1, .none, ["mikra_clinic_supply"]),
    PersonSeed(20, "Lucia Moretti", 45, 4, .hotelier, Traits(750,500,700,900,750), 220, -1, .none, ["hotel_wine"]),
    PersonSeed(21, "Enzo Ricci", 25, 4, .racer, Traits(500,950,650,850,450), 85, 5, .gamble, ["enzo_mooring"]),
    PersonSeed(22, "Cem Aydin", 40, 5, .pirate, Traits(200,850,850,650,800), 12, 6, .none, ["crew_supply"]),
    PersonSeed(23, "Rocco Esposito", 33, 5, .pirate, Traits(300,800,800,700,700), 9, 7, .smuggle, ["rocco_repair"]),
    PersonSeed(24, "Farid Haddad", 50, 5, .mechanic, Traits(450,600,600,450,900), 17, -1, .none, ["rocco_service"]),
    PersonSeed(25, "Nefeli Drakou", 35, 5, .quartermaster, Traits(350,650,850,800,850), 14, -1, .smuggle, ["crew_fuel"]),
]
```

Petros's refusal vice applies to setting out in his fishing boat as well; otherwise the trait would never execute for him. Replace the internal name with `refuse_departure` on first implementation if desired, but migrate saved variant names once shipped. Mediterranean names are fictional residents, not assertions about historical identities or jurisdictions. Money is a common game numeraire, not a currency-exchange model of the Aegean.

### 4.3 Aircraft and initial locations

All payload amounts below are actual inventory at save start, not additions after a departure. No initial craft has overlapping occupants or trips.

```text
id owner type     home/location            fuel ml hull engine  cargo/manifests
0    0   gull     Porto dock0               24000   650  550     empty
1    2   gull     AIR: Agios→Porto          38000   850  850     dispatch bag, Job0 (sealed, 5000g)
2    8   heron    Porto buoy, customs       70000   800  700     grain 3000 milli-packages, earmarked Job1
3   11   gull     Kalamos dock0             45000   900  850     wine 3000 milli-packages, earmarked Job2
4    9   corsair  Porto dock1               55000   900  900     none
5   21   falco    Selene dock0              35000   900  850     none
6   22   corsair  Kryfo dock0               30000   750  750     none
7   23   gull     Kryfo workshop            10000   650  300     none
```

Nikos starts on a legitimate inbound crosswind gate of Porto's shared harbor route. Define `P=HarborGeometry[0].center`, `out=...out`, `tangent=(-out.z,out.x)` in the horizontal plane; lane is P+out×[100,2000] at aircraft altitude. Inbound gate waypoints are `P+out*900−tangent*500`, `P+out*900+tangent*500`, then Porto's inbound approach. Validate all as safe water/air anchors from terrain; if a shoreline blocks them, move the shared pattern outward in 100m increments, at most 2000m, or reject the geometry build. This is a common crosswind entry rule for Porto arrivals, not a route generated around the player.

Set Trip0 route progress 600m before its intersection with the lane; at 60m/s the crossing occurs at +5 game minutes, with 300m altitude. It is already in flight at t=0; declared departure was before the save epoch and fuel is remaining fuel. No incident draw for a healthy engine and no initial weather can erase this crossing. Validate that from the start quay the crossing is within6km and not occluded by terrain. If it is, change the **shared harbor pattern/start quay geometry** during content construction and record that choice; do not fail silently or force the aircraft to teleport. From geometry alone, the current start island is Porto Vecchio, not Kalamos (`home=towns[0]` in `aegean.jo`).

Dario is already late with Marta's grain, waiting 10 more game minutes for a customs release/inspection, then 5 to unload; emit lateness at startup from his existing missed obligation, not a newly invented storm now. His engine service is an optional 60-minute slot after unloading, and cannot erase his cargo or occupy Paolo forever. Marina has a claimed hotel wine delivery with slack, providing second-lane traffic. The player begins walking beside dock0 as in the existing shell, with a 12-lire mooring invoice due17:30, not an auto-accepted fetch quest.

### 4.4 Market stocks, targets and demand

Arrays in GoodKind order, **whole packages in this seed table only**, multiply by1000 on load. Market stock excludes all aircraft cargo above. Illegal goods at legal markets have target/demand0 and cannot be sold at the public counter.

```text
place  stock                             target                            background demand/day
0      [10,12, 6,22,14,5,10,0,0]         [16,10, 8,24,16,6,6,0,0]         [10,3,3,12,2,0,1,0,0]
1      [18, 4,22, 8, 5,1, 1,0,0]         [12, 8,16,18,10,3,3,0,0]         [ 8,2,3, 8,1,0,1,0,0]
2      [ 3, 3, 4,14, 3,1, 0,0,0]         [ 6, 6, 6,12, 8,3,6,0,0]         [ 3,1,2, 6,1,0,1,0,0]
3      [14, 3, 3, 5, 3,0, 0,0,0]         [10, 6, 6,16, 8,2,6,0,0]         [ 6,1,2, 8,1,0,1,0,0]
4      [ 2, 2, 2, 6, 2,0, 1,0,0]         [ 4,12, 8, 8, 5,1,2,0,0]         [ 2,3,2, 3,1,0,0,0,0]
5      [ 1, 2, 1, 3, 1,0, 0,3,1]         [ 4, 4, 3, 8, 6,3,1,4,2]         [ 2,1,1, 3,0,0,0,0,0]
```

Porto/Agios medicine imbalance, Kalamos oil surplus, Mikra grain shortage, Selene wine demand and Kryfo parts/fuel scarcity each has a real owner/action. Essential fuel is not consumed by headcount at the same scale as aircraft: background fuel numbers represent boats/lamps, and tank burn remains additional. Parts have no anonymous consumption; only repairs consume them. Agios's workshop is a physical service location where Paolo/Farid can travel, not a third unlisted mechanic producing labor.

### 4.5 Explicit initial obligations/postings

All offsets are game minutes from day0 09:30. Loader assigns monotonically increasing IDs in the following key order and resolves key references before validation. The compact data DSL below is a content table: `debtor→creditor; due/grace; amount or goods; state/next step`. It specifies facts to load, not scripted future outcomes.

```text
player_mooring       0→authority; +480/+600; 1200c; open, pay at Porto clerk
dispatch_bag         2→10; +60/+180; Job0 sealed dispatch, destination0; claimed/in flight
nikos_engine_bill    2→4; +600/+1800; 7000c principal; open debt, 1% simple/day
marta_grain          3→3; -30/+90; 3000 grain, destination0; supply waiting Job1
marta_grain_delivery 8→3; -30/+90; Job1 reward1600c; claimed, loaded, customs until+10
dario_service        8→4; +180/+420; engine+100, 400c labor + .25 parts at market; unclaimed repair slot
paolo_shift          4→4; daily08–10/14–16; service availability, not a duplicate wage
yannis_shift         5→authority; daily08–10/14–16; 1200c/day prorated
leila_shift         10→authority; daily08–10/14–16; 1200c/day prorated
salvatore_shift      9→authority; daily08–10/14–16; 1200c/day prorated
agios_medicine       1→16; +480/+600; 2000 medicine, destination2; source Porto market, Job3 open
clinic_supply       16→16; +480/+600; receive 2000 medicine through Job3, shared need, not a second stock transfer
mikra_medicine       1→19; +480/+600; 5000 medicine, destination3; source Porto market, Job4 open
mikra_clinic_supply 19→19; +480/+600; receive 5000 medicine via Job4, shared need
inn_wine             6→6; +630/+750; 2000 wine from Porto market to inn inventory; no aircraft job required
petros_rent          7→authority; +1890/+3330; 800c
kostas_rent         12→fishermen; +1890/+3330; 800c
dimitris_rent       18→19; +450/+1890; 2000c (due tonight, plausible pressure for vice)
oil_work            13→fishermen; daily08–11; oil labor, sale income only
grain_work          14→fishermen; daily08–11; grain labor, sale income only
irene_shift         15→fishermen; daily09–12; 900c/day prorated
maria_shift         16→authority; daily09–12; 900c/day prorated
andreas_shift       17→fishermen; daily09–12; 900c/day prorated
hotel_wine          20→20; +570/+690; 3000 wine, destination4; waiting Job2
hotel_wine_delivery 11→20; +570/+690; Job2 reward2000c; claimed/loaded at Kalamos
enzo_mooring        21→20; +510/+630; 1000c
crew_supply         22→25; +180/+900; 12000c provision request backed by faction3 need, not personal loan
crew_fuel           25→faction3; +180/+900; 3000 fuel +1000 parts to cove reserve; open supply
rocco_repair        23→24; +1440/+2880; engine+500, parts1250 milli-packages +2000c labor
rocco_service       24→23; +1440/+2880; counterpart service claim, same repair ID/cargo/bill, not duplicate repair
```

Special repair amounts above use the standard prorated 200-points/hour recipe, so 100 points needs30 minutes and .25 parts; no separate bespoke fast repair rule. Daily shifts list schedule semantics; the loader creates today's partial remaining duty and next day's full duty once, with day keys preventing duplicate wages. Home duties already completed before09:30 may influence opening inventory/balances but are not replayed as new production.

```text
Job0 poster10 origin2 dest0 sealed mail, 5000g, due+60 expire+180 reward1200c, carrier2, loaded
Job1 poster3  origin3 dest0 commodity grain3000, due-30 expire+90 reward1600c, carrier8, loaded
Job2 poster20 origin1 dest4 commodity wine3000, due+570 expire+690 reward2000c, carrier11, loaded
Job3 poster1  origin0 dest2 commodity medicine2000, due+480 expire+600 reward4000c, open, npc_claim_after+90
Job4 poster1  origin0 dest3 commodity medicine5000, due+480 expire+600 reward2800c, open, npc_claim_after+90
```

Fund rewards from poster accounts into separate escrow accounts before opening-ledger total is recorded; buy/reserve Job3/4 medicine from Porto market at its initial true quote, paying from Eleni's money. Until loaded those seven packages are part of Porto's stock and marked reserved. Job2 wine is already in Marina's aircraft, so Kalamos stock does not include it. Initial medicine destination receiver is nurse Maria/merchant Aylin; transferring the goods fulfills both linked supply duties with **one** destination stock increment.

Give Dario a price/manifest belief for Job4 at startup and capacity/fuel for it. At +90 his earliest-deadline valid company job tie-break prefers Job4 (explicit company assignment preference +.15 score for Mikra based on an existing trusted customer relationship), while Marina is still committed to Selene and Nikos may take Job3. This is a standing customer preference, not a scheduled launch command. Cem knows the previously announced Mikra medicine tender and likely 11:05 departure (+95) because Nefeli heard Eleni's public request at Porto yesterday; confidence850, observation−600. That knowledge is a Reason/NewsItem, not access to Job4's future claim. Cem patrols an intercept waypoint on that expected route when his supply pressure makes it feasible. If someone else accepts or weather closes the lane, he can search and fail; tests require an attempted sortie/answer, not guaranteed theft of Dario.

Initial acquaintances: every pair within a home village, all company couriers↔Eleni/Paolo/Leila, Marina↔Lucia, Dario↔Marta/Aylin, Nikos↔Maria, Salvatore↔Cem (prior identified offender, no current bounty), Nefeli↔Eleni/Sofia, Dimitris↔Nefeli. Seed affinity+150/trust650 for workmates, household+300/800 if later added, otherwise acquaintance0/500. Nikos↔Paolo has trust600 and unpaid bill Memory, not automatic hatred. Each Person knows current home prices; couriers know last route destinations observed within the previous six hours. News that a person “knows everyone at home” never shares another town's quotes automatically.

One small contraband channel is sufficient for the smuggling vice: Sofia and Lucia can each discreetly buy at most one tobacco package/day at1.4×base, funded from their Person account, only through a direct trusted contact (trust>=600). Public markets refuse it. Docking a craft carrying illegal goods at a legal harbor triggers a search with probability `.10 + .20*(local regard<-300)` once per arrival; officer must be present. Detection transfers illegal stock to authority lost-property, levies `min(cash,2000c)` fine, emits an identified event; unpaid fine becomes an obligation. This is a general law transaction, never a random deletion of money. Player smuggling uses the same channel and search, with visible confiscation/receipt.

The four first faces should be Nikos, Marta, Paolo and Yannis on/near the start quay; Leila can speak the incoming mail line. Current dwellers need no extra opening conversation script: their loaded obligations are sufficient. Marina's committed departure and Dario's late arrival supply ongoing motion after the initial crosswind pass. No initial race or bounty is invented; a bounty must follow locally received raid news.

Semantic placement contract: extend the graphics-free HarborGeometry bake with stable anchors `home[PersonID]`, `counter`, `office`, `inn`, `workshop`, `quay_wait`, `buoy`, `rescue_water` and `beach_wreck`; they are points/routes on the same walkable surfaces Town renders. Assign homes by `houses[id % houses.len]` only at content construction and persist the resulting anchor mapping/key; a later house-generation change requires geometry migration. The office/counter/inn/workshop use assigned existing houses or quay positions; no new building mesh is required for v1. Place Marta, Paolo, Yannis and Leila initially at four walkable quay/office anchors within12m of the player's starting path; Nikos is the visible passing pilot. Their initial 30-minute wait/service actions refer to their existing promised delivery/customer/shift. Then routines take over. All other persons start at their role's09:30 work anchor. Four pirates can share a three-house cove.

Person.pose/local_anchor hold the saved abstract or last scene foot position. A local walking action targets an anchor and advances at1.4 physical m/s using the baked quay/path segments, with the same2-physical-seconds/game-minute conversion as aircraft. While materialized the pedestrian controller owns pose only and reports anchor arrival; folding resumes from actual position, then follows the remaining walk path. It cannot instantly move someone from the workshop to an inn while within300m. Aboard Person uses aircraft pose and is not also a scene walker; aircraft.operator and manifest are authoritative. The player's on-foot pose is saved here too; aboard mode derives from operator0, so reloading cannot strand a second player walker at an old dock.

Worked economy check for the day-zero raid: base-price value of five medicine packages is9000c, so the40% loot cap is3600c. At p≈.60 expected gross is2160c. A reachable roundtrip of at most14km at65m/s burns about17231ml plus taxi, costing roughly1500c at base fuel price. That leaves a small positive expected cash gain before repair risk; the due crew provision/duty term supplies the rest of the motive. At candidate construction calculate the **actual** route/burn and bounded repair exposure: if the net is negative or return reserve fails, it is not a viable raid, and the content/known route must change rather than faking fuel. This worked bound is why the initial Mikra shipment is five packages and loot is capped at40%, not a token crate whose value is less than reaching it. Loss scoring counts expected incremental repair/cargo exposure, not the whole resale value of an aircraft for an ordinary nonlethal encounter. A physical player can, of course, inflict a much worse outcome.

Actual home quotes matter: Kryfo's starting medicine quote is1.8×base, so3600c of base-valued medicine loot (two packages) can sell for6480c if the market still has cash. Expected gross at p=.60 is3888c; fuel scarcity also raises replacement fuel cost to about1.67×base. Score the known expected resale minus the actual expected replacement/repair costs; the base-price loot cap is not the sale price and is not an omniscient destination quote. A successful sale transfers money from the Kryfo market rather than creating it.

## 5. Acceptance tests, exact assertions and seed sweeps

These are required test cases for the implementation, not results claimed by this review. Use `tests/living_world_test.jo` importing only the simulation/data modules; no application import, `window`, renderer, audio, `time()`, or global `random()`. Use one process at a time unless the machine's four-worker budget is reserved. Set `DISPLAY= WAYLAND_DISPLAY= SLOPPY_NO_AUDIO=1`, and isolate `SLOPPY_SAVE_DIR` under `~/dev/tmp/aegean-skies/`. Every failure prints seed, absolute minute, actor/job IDs, Reason, and a compact account/stock trace so it can reproduce as a one-seed run.

Reference seeds: smoke `[0,1,7,42,127]`; release `0..128` (128 seeds, exclusive upper bound). Long sweep runs 30 game days =43200 minute steps/seed, headless abstract except explicit adapter tests. Count game days relative to the starting clock; midnight scheduling must still use local midnight. Run the full sweep once per behavior/constants change after smoke passes, not over and over to produce a nice quota number. A failing seed is an ordinary bug/tuning datum, not grounds to remove the assertion or permit negative wallets.

| Named test | Setup and exact required assertions |
|---|---|
| `seed_content_is_self_consistent` | For each smoke seed at t0: exactly26 persons (IDs0–25),25 named NPCs, six places matching current SETTLEMENTS names/indices, eight aircraft; all owned IDs valid; every active trip has one operator/craft pair; player has12000c before paying fee; all job escrow equals promised unpaid reward; reserved<=stock; every loaded job has exactly one cargo location; every obligation reference resolves. Sum initialized account balances equals ledger.opening, external counters0. |
| `first_two_hours_cross_start_lane_for_sayable_reason` | For each of128 seeds with idle player at actual start quay, run0..120 game minutes. Collect swept **airborne** segments and require at least one named NPC has a transverse intersection with Porto lane P+out×[100,2000] during this interval, altitude50..700m, within6000m of player, and clear line of sight from player eye to crossing using shared terrain. For Trip0 require crosswind transverse direction (`abs(dot(normalized_horizontal_velocity,tangent))>.5`) and crossing in minutes[0,15]. Its nonempty Reason must reference actor2, beneficiary10, Job0, destination0 and due+60. `say_reason` contains “Nikos”, “Leila”, and a delivery/mail cause; it must not reference nonexistent goods or expired actors. A co-located actual speaker (Leila or harbor clerk) has this line eligible before minute30. At t0 at least Job3 is funded/open, and board history at minute120 names any carrier who took it. A route-line intersection at an unrelated time is insufficient. |
| `reason_survives_failure_and_eviction` | Inject ditch for Trip0 at minute20. Require one ditch event, one aircraft wreck/ditch record, one rescue schedule, injured Nikos, no death/new Person, one cargo location. Advance9 days; the initial full departure Event may be pruned, but pinned job/Memory/aftermath reason still prints actor, beneficiary and cause. |
| `money_book_balances_after_every_transaction` | In all128×30-day sweeps, transaction observer independently accumulates every boundary entry by allowed MoneyKind and compares to ledger cumulative counters. After **each** transfer and minute, require all accounts>=0 and `sum(cents)==opening+external_in-external_out` exactly. Every internal transfer preserves sum; interest accrual changes no account; tax/repair/fuel/fine/debt/gambling/reward are internal. Boundary -1 is forbidden except opening/import/household/export/subsidy/departure. Require zero unexplained adjustments and zero calls to a “rebalance” wallet function. |
| `goods_have_one_location_and_conserve` | For each good maintain independent opening + production + imports − consumption − spoilage − exports − physical burn/destruction total. Compare to sum of market/pocket/craft/aftermath stock, counting reserved only as a subset and sealed payload separately. Use micro-packages to compare fuel exactly: `market_milli*1000 + tank_ml*100` plus other fuel inventory; one10L package equals1000000 micro-packages. Refuel transfers this quantity exactly, actual integer ml burnt is ledgered, remainders carry. Theft/delivery/tow/salvage/materialization preserve total. All quantities/reservations nonnegative, reserved<=stock. |
| `claims_are_atomic_and_dont_pay_twice` | Queue two valid NPC claims and a player claim for same Job at same tick. Exactly one becomes carrier, exactly one obligation/escrow exists, losers keep money/cargo. Call arrival/claim/deliver again and repeat across save/load: destination stock/reward changes only once, escrow0 only after terminal transfer/refund. Test partial unloading is either a committed atomic delivery or still onboard, never both. |
| `tender_window_is_public_and_board_keeps_history` | Create job at minute10, NPC claim at99 fails, at100 succeeds if feasible. Player claim at11 succeeds if otherwise valid. Run identical world with player far/near/loitering: eligibility times identical. Claimed status/carrier remains on board until12 hours after status change. Mere absence of player never expires escrow early. |
| `debt_cannot_deadlock_income_or_compound_forever` | Set Nikos cash0 with due debt7000c and a feasible positive-income action. Within60 game minutes he starts a feasible income/vice action or a specifically timed committed pickup, never repeatedly selects impossible payment. After30 days unpaid interest<=3500c, exactly one default event, no interest after default, no negative cash, no new NPC/aircraft. Pay a partial amount and require remaining principal/interest liabilities and creditor cash reconcile. |
| `routine_does_not_consume_all_choices` | On a fair day with no urgent duty, each courier has at least one free 15-minute choice window between09 and18 and cannot remain dock-readiness-locked all day. A noninjured fisher with available boat and open water completes four hours of labor and produces exactly `16*keyed_catch_factor` packages up to integer remainder; skipping a work hour reduces production by the corresponding amount. No settlement rate secretly fills the difference. |
| `vice_latches_and_recovers` | Push each non-none Vice to M=.85 with a real due obligation. At next eligible dock decision, vice_active true; supported vice candidate appears only with funded physical prerequisites. No money/cargo generated. Reduce pressure to M=.30, clear blocked duties, advance minimum120 minutes: latch false at next choice. Refusal ends after stated rest/company recovery; cannot stop a current airborne leg. Gambling executes once/day, funded transfers exactly, and cannot stake the400c reserve. |
| `news_is_local_and_reputation_idempotent` | Inject raid at Kryfo with known participants, no traveler to Porto. Porto regard stays unchanged. Land a witness at Porto: score changes exactly once by formula using carried confidence. Repeat arrival/retelling100 times: no further delta (except scheduled daily decay), one receipt. Higher confidence improves stored news without multiplying regard. After7 days reject another copy based on occurrence age; after8 days receipt may be dropped safely. An acquaintance not co-located learns nothing automatically. |
| `news_ranking_cannot_erase_ongoing_grievance` | Create one severity800 raid and20 severity20 production events, same age/confidence. Raid remains among top12, and affected relationship retains its compact Memory even after full Event expiry. Receiving new low-weight items cannot clear its unpaid/restitution reason. Daily board contains at most3 distinct events actually heard yesterday, never unknown distant events. |
| `pirates_try_and_authority_answers` | For each128 idle-player starts, within3 game days require at least one captain raid **departure with a reachable known target/time**, and at least one actual encounter or an explicit “prey absent/search expired” outcome; not just an idle `.raid` plan. Within24 game hours of the first identified raid news reaching Porto require one funded bounty notice or explicit unfunded-bounty warning, and Salvatore starts a patrol or a recorded fuel/repair recovery step with retry<=6 hours. In this funded initial state require actual patrol departure within those24 hours. No raid bounty is posted before relevant news. Require at least one actual pirate-victim Encounter per seed by day7; an empty search alone cannot satisfy the milestone. A successful theft is not required on every seed. Over30 days captain raid departures<=30, each same-victim encounter resolves at most once, and no raid removes more than cap or available stock. |
| `closures_and_broken_aircraft_recover` | Force all harbors closed for180 minutes, engine300, full docks and mechanic absent. No illegal departure/dock overlap or negative fuel. Closure expires/reopens by policy, reservations with no progress expire within120 minutes, waiting arrival uses buoy by30 minutes, and each blocked service has retry<=60 minutes or a committed named journey. By48 hours operator has begun repair/local labor/ferry, or is injured with finite recovery date; never an idle active obligation with no scheduled next step. |
| `offscreen_ditch_places_real_aftermath` | Force fuel exhaustion away from scene. One incident, no negative fuel, one known owner/aircraft, no new plane. Nearest validated water/beach/workshop anchor is used; no terrain penetration. Re-materialize/fold three times: same Aftermath ID, same cargo quantity, same damage. Rescue moves the same Person, charges/debts/subsidy exactly once, and leaves wreck unrepaired. |
| `lod_boundary_owns_motion_once` | On a fixed windless route use a scene adapter that exactly follows abstract kinematics. Switch at5999/6501m and back100 times. Final position differs by<=1m and ETA<=1 game minute from no-switch reference; exact fuel/cargo/money/damage and encounter-resolution count match. Each fixed tick has exactly one movement/burn owner. Handle removed by Pool deletion fails `has`, new body cannot be found with old Handle. No identity refers to a Pool index. |
| `observer_presence_does_not_reroll_incident` | Save an abstract pending engine failure at its stored distance; materialize/fold before/after boundary. Distance and incident_resolved are unchanged, and outcome is committed once. A physical resolution may differ from the abstract reference; both must preserve one craft/Person/cargo owner and valid balances. Do not assert matching crashes for different observer paths. |
| `physical_routes_work_when_watched` | Integrator-owned test, not this audit of WIP flight: for each ordinary lane and each representative Gull/Heron, ten fair-weather seeded visible runs at intended fixed timestep. Require every run either reaches correct mooring without hull loss or makes a bounded documented retry, and at least9/10 first-attempt completions; all10 eventually complete within2×nominal ETA+60 game minutes. A retry cannot teleport/respawn or pay delivery early. Add a full-dock arrival and a storm diversion. This gate blocks scene integration if bots ditch on observation. |
| `save_roundtrip_mid_every_state` | Roundtrip at t0, loaded preparing, airborne, physical taxi, injured, workshop reservation, active raid, partial debt, and waiting passenger. Canonical serialize after reload equals before (excluding specified cosmetic caches/slot generation); continue1440 minutes with identical inputs/LOD schedule and require exact canonical state equality. ID counters strictly exceed all allocated IDs; no reopened paid jobs. Corrupt newest slot: older valid slot loads. Unsupported schema: no writes. Missing field gets documented default, changed semantic units require migration fixture. |
| `thirty_days_no_silent_absorbing_state` | All128 seeds: prices within[.45,1.8]×base plus1c rounding tolerance, all condition0..1000, no invalid references, active jobs have funded escrow and feasible/rescheduled terminal date. No same Person.action sits beyond end+60 without progress or explicit retry/recovery; no blocked item next_retry in the past for>60 minutes; no noninjured courier who has an operational fueled craft, an accessible funded job and remaining daylight goes48 hours without a decision/attempt. At least one NPC flight per rolling48 hours after initial grace if any reachable service lane is open; otherwise require explicit closure notices explaining all blocked lanes. Emergency subsidies <=1/person/week; failing the count means recovery/economy tuning is unfinished, not a money mismatch. |
| `deterministic_seed_and_cosmetic_rng_separation` | For all smoke seeds, two identical30-day abstract runs have identical canonical hash after each day; inject10000 cosmetic `random()` calls/render snapshots between minute steps in one and require equality. Reverse insertion order of an equivalent initial map then canonicalize/sort IDs: same outcomes. Save/load and day rollover cannot consume a different decision-noise stream. |

The “no silent absorbing state” test distinguishes a purposeful retired racer, a three-day injury, a storm closure and a bankrupt repair wait from a lost scheduler. It does **not** require every NPC to prosper, every price to be calm, or every seed to produce the same story. Report metrics (flights, delays, breaches, distinct counterparties, failed/successful raids, injury days, public deficits, subsidies) separately from hard invariants, then inspect seed traces for monotonous repetition. Do not turn a desired raid success rate into a magic-success rule.

### Deterministic random keys

Never call global `seed_random` inside the world: Town generation currently calls it, which could otherwise alter NPC choices. Use a stateless local integer mixer with keys `(world seed, subsystem tag, entity/encounter ID, scheduled minute/day, candidate ID)`. For decisions, key noise by the saved `next_decision_minute`; re-reading a UI score cannot advance a stream. Freeze numeric subsystem tags and the mixing algorithm as part of save version1. A suitable explicit primitive in Sloppy is:

```sloppy
mix64 = (x: u64) -> u64:
    let x = x
    x = (x xor (x >> 30)) * u64(0xbf58476d1ce4e5b9)
    x = (x xor (x >> 27)) * u64(0x94d049bb133111eb)
    x xor (x >> 31)

draw1000000 = (seed: u64, tag: int, id: int, minute: int, candidate: int = 0) -> int:
    x = mix64(seed xor u64(tag))
    x = mix64(x xor u64(id))
    x = mix64(x xor u64(minute))
    int(mix64(x xor u64(candidate)) % u64(1000000))
```

Tags:10 decision,20 catch,30 outside shipment,40 weather,50 engine incident,60 raid outcome,70 injury duration,80 gambling,90 search. Inputs can be negative pre-start times cast to u64 deliberately; integer wrapping is defined. Store pending engine/encounter draws as distance/resolution state rather than recomputing against changing minute. Canonical test hashes sort map entries by stable key; same-platform replay is the v1 exact float contract. Cross-platform physics may need quantized pose hashing; do not promise cross-CPU bit-identical quaternion integration solely because the abstract world is seeded.

## 6. Implementation order and reviewable chunks

Line counts are targets for each commit-sized patch, excluding static roster tables; do not implement all systems in a single thousand-line tick. The coordinator can apply these as uncommitted review units unless explicitly told to commit. Suggested module names avoid changing existing renderer/flight code until the adapter gates.

| Chunk | Approx lines and owned scope | Acceptance before next dependent chunk |
|---|---|---|
| 1 | 200–300, `src/living_types.jo`: units, identity/core records, type constants, pure clock/mixer helpers. Split the full schema into identity/economy and social/travel declarations if needed. | Declarations compile headlessly; ID/unit conversion, epoch09:30 and wrap/mixer fixtures pass; no graphics/audio import. |
| 2 | 200–300, `src/living_money.jo`: accounts, atomic transfers, escrow, residuals, stock transfer helpers. | Internal/external balance and one-location goods tests pass, including10L↔tank exact conversion and insufficient-cash rollback. No UI or AI yet. |
| 3 | 200–300, `src/living_seed.jo` plus data tables: roster, keys, existing-place mapping, opening stocks/claims, sparse acquaintance initialization. | `seed_content_is_self_consistent` passes; constructor prints named jobs and expected initial prices. Source repo remains graphics-independent. |
| 4 | 200–350, `src/living_travel.jo`: HarborGeometry input, route geometry, stable trips, time-distance conversion, fuel/arrival transaction, boat schedules. | Trip0 crosses swept start lane within15 minutes with printable Reason; one sealed delivery and one commodity delivery pay once. Ten repeated abstract trips consume expected fuel and do not accumulate minute rounding drift. |
| 5 | 200–300, `src/living_duties.jo`: obligation transitions, lateness/default, bounded blocked retries, routine block/day accounting and labor completion. | Impossible debt yields to income; missed deadline emits once; partial-day shift pays once; named production equals completed labor. |
| 6 | 200–350, `src/living_market.jo`: hourly stock price, consumption, spoilage, outside manifests/budgets, import delay; initially no choice AI. |30-day smoke-seed accounting/goods checks pass. Stopping one fisher removes their output; outside ships can fail without producing negative fuel/stock or silent wallet adjustment. |
| 7 | 250–350, `src/living_choices.jo`: candidate enumeration, actual score constants, commitment, vice latch/recovery, trade-belief validation. | Deterministic action fixtures for debt, rest, company, bad information and vice; couriers get choice windows. Job competition test and48-hour no-decision detector pass. |
| 8 | 200–300, `src/living_jobs.jo`: funded postings, tender history, claim/load/unload, late/failed grace, simple passenger/parcel manifests. | All claim/payment/expiration tests pass; the board has named open/taken history with real escrow. If schedule overflows, ship parcels first and add passenger state as a separate200-line patch; do not fake passengers as goods. |
| 9 | 250–350, `src/living_news.jo`: event→public/private news, carry/gossip, receipts/reputation, relationship memories, pure sentence builders. | News-locality/dedup/retention tests pass; Trip0, Dario lateness and repair all render specific true lines without UI. |
|10 | 200–300, `src/living_weather.jo` and recovery: cells/closures, incident scheduling, diversion, tow/rescue, aftermath anchors. | Forced storm/engine/fuel/full-dock scenarios recover with one owner and one bill; saved incidents do not reroll. |
|11 | 250–350, `src/living_pirates.jo`: captain supplies/claims, prediction/search, encounter registry/abstract resolution, cooldown, news-funded bounty/patrol. | Every smoke seed attempts a real reachable sortie and patrol answer; failures leave named consequences. Expand to128-seed30-day sweep and resolve all invariant failures before scene work. |
|12 | 200–300, `src/living_save.jo`: two save slots, validation/migration rejection, canonical test serialization, pinned-record pruning. Can be started after chunk3; finish once all records exist. | Mid-state roundtrip fixtures, corrupt-slot fallback and continuation equality pass. No UI-triggered World copy survives the save boundary. |
|13 | 200–350, `src/living_scene.jo`: ID↔Pool Handle adapter, ownership handoff, compact pose snapshots, commit outcomes, save synchronization. **Integration coordinator owns this and WIP flight; bulk world implementer must not edit flight.** | Pure mock LOD handoff passes100 switches; then physical takeoff/landing gate passes. Do not wire two independent aircraft arrays into the HUD. |
|14 | 200–350, coordinator shell integration: replace decorative walkers with named Person anchors, board/market commands, proximity speech, named wreck/workshop props; no new visual design required by this report. | From the existing start quay, idle two game hours: visible named crossing, sayable line, funded/taken board history, then get into same saved owned craft. Close/reopen game and continue same obligations. |

Dependencies: shared schema/transaction helpers precede consumers. Jobs and obligations may call each other through World+IDs, but keep one transaction owner; chunk8 can begin in parallel as design work only after chunk2's API is fixed. This report does not authorize spawning agents. If a cheaper bulk implementer needs a smaller brief, give one row, its owned module and tests, the preceding API contracts, and forbid speculative next-row work. A test harness must run World without importing the application, because the current `aegean.jo` executes `window(...)` and builds meshes at top level.

### Integration acceptance and what can wait

Do not gate first visible flight on all30-day content tuning. Gate it on chunks1–4 with a healthy seeded courier and truthful line. Then keep the abstract smoke sweep green while adding contracts and economy. Full milestone completion requires the128-seed sweep **and** watched-route gate; one cannot substitute for the other. A numeric world that balances but never speaks fails this spec. A lively visible scene that creates a second grain cargo at every save also fails it.

Defer aspiration/ambition, complex faction diplomacy, population migration, persistent rumor lies, multi-leg speculative planners, automated races and a second transport physics model. Preserve extendable records/keys, but do not write placeholder decision weights or empty UI tabs for those systems. The completed core loop is specific: a named need funds a job, a real carrier commits resources, someone else can interfere, an actual arrival or failure changes stocks/accounts/trust, the news travels, and the player can see or hear why.

## 7. Verification performed for this report

* Extracted the declared Sloppy schema, all26 PersonSeed rows and stateless mixer into a temporary headless source under the requested scratch directory. They compile on the installed Sloppy; roster ID ordering and mixer range/repeatability assertions pass.
* Checked every roster obligation key against the initial-obligation table: all30 resolve. Tested text serialization/deserialization with nonempty persistent map fields and corrected the Set roundtrip failure described in §2. No save slots or game files were overwritten.
* Loaded the existing terrain data through the graphics-free `src/world.jo` helpers. The proposed Porto gate's three crosswind points are over water; a101-sample terrain sightline from the start-side eye position to the300m-high crossing is clear. Distance from that start-side point is870m. This establishes terrain visibility, not final aircraft rendering size or speech presentation.
* Measured the straight cruise intercept via the midpoint between Porto and Mikra1500m outer approach anchors from Kryfo:12879m roundtrip,17452ml Corsair fuel including taxi allowance,1396c at base fuel quote. It fits30000ml initial fuel with5000ml reserve. The final shared route must still validate approach geometry and timing; this was not a flight-physics playtest or a benchmark.
* No world implementation or30-day sweep was run: those are the acceptance work specified above. No repository files were edited, no flight-WIP source was inspected, no agents/windows/audio were launched. Temporary verification sources were removed; this report is the sole new deliverable.
