# Design: how the world lives

This is the plan for the systems behind Aegean Skies: what the simulation holds, how it runs, and
how stories come out of it. It is a working document; the code is the final word.

## Goals, in order

1. **Every person has reasons.** What anyone does follows from their circumstances (money, debts,
   job, aircraft, relationships, what they know) and from a small set of drives, never from a
   script that decides it is time for something to happen.
2. **The world runs without the player.** The whole archipelago is simulated all the time, at a
   coarse grain away from the player and in full detail around them, and the two agree.
3. **Consequences persist.** People remember; prices, debts, reputations and relationships carry
   forward; factions react to what keeps happening.
4. **Small, interacting systems.** Each system is simple. Interest comes from their coupling.
5. **Deterministic and saveable.** The simulation is a pure function of its state, the player's
   actions and a seed, so bugs reproduce, a test can run a month of world time headless, and a
   save is just the state.

## Time and scale

- The world clock: one game hour is two real minutes (a day is 48 minutes), set in one constant.
- The archipelago is about 16 km across: nine islands to start, four or five with settlements.
  A seaplane cruises at about 55-70 m/s, so the far side is three or four minutes away.
- Seasons and years are not modeled at first.

## The two levels of detail

**The world tick** (every game minute, the whole world, cheap): people decide and act, trips advance
along routes, markets clear, weather moves. Everything is abstract: a person on a trip is a route,
a departure time and a speed, and their position is computed from those.

**The scene** (every frame, near the player, about 6 km): people and craft near the player are
*materialized* as physical things: an aircraft flown by an AI pilot along the trip's route, people
walking the quay. A materialized thing drives its abstract record (position, damage, cargo); when it
leaves the scene it is folded back into its record. Fights, landings and theft happen physically
when the player is there and are resolved by rule when they are not (the same outcome odds).

## What the world holds

**Settlements** (a harbor town, a fishing village, an airstrip, a military post, the hotel):
- facilities: dock, fuel, market, workshop, inn, harbor office (police), chapel
- population: a few named persons who live there, plus a headcount that consumes
- per good: production rate, consumption rate, stock, and a price that follows stock against a
  target (scarce means dear)
- mood: prosperity, unrest, fear (of pirates), each drifting toward what recent events imply
- a faction that keeps order (or none)

**Goods** (few, each with a role): fish, wine, olive oil, grain, fuel, machine parts, medicine,
mail and passengers (time-bound), and contraband (tobacco and arms: dear, illegal, profitable).

**Persons**:
- identity: name, age, home, occupation, appearance seed
- resources: money, debts (to whom, due when), aircraft or boat, cargo carried
- traits (0..1): honesty, boldness, greed, sociability, loyalty
- drives, each a 0..1 pressure that grows or falls with circumstance: *money* (low cash, debts
  due), *duty* (job undone), *rest*, *company*, *revenge* (wronged), *ambition*
- relationships: for each person they know, affinity (-1..1), trust (0..1), and a few remembered
  events that justify them
- knowledge: facts they believe (prices seen, who attacked whom, where a shipment is going), each
  with where and when they learned it; rumors spread from person to person at inns and docks
- a current **plan**: a short sequence of steps (fly to X, buy Y, sell at Z, rest) chosen by
  utility from what they know

**Factions**: the harbor authority (order, patrols, bounties), an air-pirate band (raids for money,
needs a hidden base and planes in repair), a shipping company (wants contracts and safe lanes),
the fishermen (want fair prices and safe waters). A faction has money, members, a few standing
goals, and an attitude to every other faction and to the player that moves with events.

**Aircraft**: each a record: type (handling and capacity), owner, condition (hull, engine), fuel,
cargo, location (moored at a dock, in a workshop, in flight on a trip). Repair takes parts, money
and a mechanic's time.

**Weather**: a few moving systems (fair, windy, squalls, a storm) that drift across the map. A storm
closes harbors in its path, grounds cautious pilots, delays ships and shifts prices.

## How people decide

Three layers, in order; a lower one only fills time the one above leaves free.

1. **Obligations** come first. Each person keeps a short list of things that fall due: a debt
   payment, a promised delivery, a passenger waiting, the mechanic's bill, a shift at the harbor
   office. When one is due they act on it whatever else they would rather do. Lateness is
   remembered by whoever was owed (most drama is lateness). Debts carry interest, so an unpaid
   one grows.
2. **The day's routine** by occupation: fishermen at sea from dawn and at the fish market by mid
   morning; merchants at their stalls; pilots at the dock or in the air; everyone at the inn or the
   quay in the evening and home at night. A routine is a schedule, not a drive, so the quay is
   busy when it should be.
3. **Choices** fill the rest: the activities a person could take (work their trade, trade a price
   difference they believe in, take a posted job, repay early, visit a friend, raid, patrol...),
   scored by **adding** what each does for their pressures (money, duty, rest, company), plus
   trait leanings and a little noise. Scores add, so a bold, greedy person can prefer a risky raid
   to a safe catch; odds lower a score but do not zero it.
4. **Thresholds and vices.** Under pressure past a line (cash below what is owed and due soon,
   aircraft unrepairable) a person switches to their vice, if they have one: smuggling, gambling the
   fuel money, joining the pirates, refusing to fly. It is one visible switch, not a blend, so a
   player who sees it once understands that person.

**Commitment.** A trip, once begun, is flown to its end. Only damage, fuel, weather past the
pilot's nerve, or an attack interrupts a leg. People reconsider at docks, not in mid-air.

**Acquaintance.** People know: their household, their workmates, everyone in their own village,
and anyone they have traded with, flown for, fought or met at an inn. Relationships (affinity,
trust) exist only between acquaintances, each justified by a few remembered events (capped by
salience: the gravest are kept).

## The economy (one theory)

- Each settlement's market holds stocks. Its **prices follow its stock** against what the place
  wants; that is the true price, and trades happen at it.
- People act on **what they believe** prices are elsewhere (seen on their last visit, or heard),
  which may be stale: that is where a merchant's mistake or a courier's windfall comes from.
- Production and consumption: a settlement's background population consumes at a steady rate
  (with the hour and day); the **named people produce** (a fisherman's catch is what lands on the
  market). Named work matters.
- **Shocks keep it from settling**: the catch varies with the season and the fishing grounds;
  storms close harbors and delay supplies; engines fail; a festival or a wedding wants wine; a
  ship from outside brings goods or doesn't come. These are nature and the outside world, not a
  story director.
- Money flows are listed and tested: sources (sales to the background population, the outside
  world's buyers, wages paid by factions, bounties), sinks (purchases from outside, fuel, repairs,
  rent, fines, interest), transfers (trade, theft, debt). A test runs many seeds for thirty days and
  checks the books balance and that nothing is stuck or out of bounds; it does not ask for calm.

## News, speech and reputation

- **Events** (a delivery, a theft, a raid, a rescue, a late payment) are recorded with who, whom,
  where, when, who saw, and a **weight** (harm done, money involved, surprise).
- Each place keeps its **news**: the few weightiest recent events it has heard of, each with how
  many retellings it took to arrive (and so how sure people are). News travels with people: a pilot
  who lands carries what they know.
- **Reputation is numbers that move when news arrives**: each place's regard for each person
  (and for factions), changed when the news of what they did gets there, by how much it matters to
  that place. A clerk and the townsfolk read the same number, so they agree.
- **Speech**: people say things unprompted when one walks by (a line from the place's news or their
  own circumstances: "He should have been back before the wind turned"); a poster offers a job to
  whoever is in front of them; the harbor board lists the day's notices by name ("Marta Galli pays
  40 lire for oil to Mikra by dusk") and, each morning, three lines of yesterday's news.

## Near and far

Away from the player a trip is a departure and an arrival, and what happens on it is decided by
rules (weather, pirates on the route, the aircraft's state) when it happens, and its **aftermath is
placed in the world** (a wreck on a beach, an aircraft towed to the workshop, a merchant short of
goods, news at the next harbor). Near the player, aircraft are flown by the flight model and the
outcome is what happens. There is no attempt to make a die and a flight model agree: the player
sees consequences either way.

## People are not killed (at first)

A pilot shot down ditches and is picked up, injured for some days, and their aircraft is wrecked
or salvageable. People can leave the archipelago (ruined, or rich), and newcomers arrive now and
then, so the cast can change without death.

## The start

The world starts out of balance, with its situations already under way: one island short of
something, a pilot whose debt falls due tonight, a pirate crew low on money and fuel, a merchant
whose courier is overdue, and the player with a little money, an old aircraft and a mooring fee
owed. These are starting conditions; what happens next is the simulation's.

## The player

The player has the same kinds of records as anyone (money, an aircraft, debts, regard in each
place, acquaintances), but they are not run by the simulation: the player writes into the world
from outside (trades, deliveries, fights) and the world reacts as it would to anyone. Nothing waits
for them, but people near them notice them: they speak to them, offer them work, and remember them.

## Vessels on the water

Caiques are the first: lofted low-poly hulls, sails set when out at work with a flag flapping at the
masthead, furled at the quay. Later, other vessels with their own work and routes, so the sea has
traffic of its own beside the aircraft: little old-fashioned motor yachts, ferries running between
the islands on a timetable (a reason to race one, or to meet it), schooners carrying freight.
Moving vessels would need their own wakes and their own place in the living world.

## Personal aircraft: paint and markings

Owning an aircraft includes making it one's own, more freely than Sky Barons allows:
- **Paint by part**: every part of an aircraft's low-poly model (fuselage, each wing, floats or
  hull, struts, cowling, tail, rudder) takes its own color, or a simple two-color gradient or
  stripe pattern along it.
- **Decals**: numbers, letters, roundels, flags, stars, animals, stripes and a few period motifs,
  plus shapes of one's own (circles, bands, chevrons). Placed at the usual spots (rudder, fuselage
  sides, wing tops and bottoms, cowling) with a snap, or anywhere at any size and angle,
  projected onto the surface where they are put.
- **Where**: at a paint shop or a mechanic's workshop, for a price and a little time (the
  aircraft is in the shop meanwhile, and people notice a new livery). Liveries are saved with
  the aircraft, and other pilots' aircraft carry their own (generated from the same tools), so
  a pilot can be recognized by their colors at a distance.

## Sandbox settings

A settings page for playing more freely, each a separate switch: paint any time anywhere, any
aircraft at any time, unlimited money, no damage, no fuel, and the like. The simulation keeps
running as usual; the switches only lift the player's own constraints.

## The first milestone

A small, complete living archipelago:
- three or four settlements on different islands, a hotel on an islet, a pirate cove
- about twenty-five named persons, most on the start island and its neighbor: fishermen,
  merchants, three courier pilots, a mechanic, an innkeeper, harbor police, a pirate crew of four
- working seaplanes for the player and the NPC pilots: take off from water, fly, land, taxi, moor
- getting out at a dock and walking along the quay, talking to people
- a market and a job board at each harbor; fuel and repairs
- rumors at the inn; pirates who raid when they are short of money, and a bounty that follows
- unprompted speech on the quay, the job board with names, yesterday's news each morning
- headless tests over many seeds: within two game hours of the start, someone is in the air on a
  route that crosses the start harbor's lane for a reason someone can say; in thirty days the
  books balance and nothing is stuck; the pirates raid at least once and are answered

## Backlog

Things agreed to build, roughly in the order they'll come:

- Clouds closer to the Porco Rosso references, and an atmosphere to go with them: scattering
  (distance going blue, the sun's warmth low in the sky, shafts of light), haze over the islands.
  Plan in docs/research/longrange_clouds.md.
- A world the size of the real Aegean (about 500 by 400 km): the present archipelago kept exactly
  as it is (its sizes and distances feel right), with much more land around it: a mainland the size
  of a country, large islands, many small ones. Conflicts between real societies need country-sized
  places, and all of them are places one can fly to and land at. Mountains as they really are:
  the highest (near 3000 m) on the mainland and the biggest islands, most islands a few hundred
  meters. This needs a new world renderer, far lighter per square kilometer than today's baked
  terrain (research and design under way).
- Bailing out under a parachute, brought over from Sky Barons: from a damaged or falling aircraft
  the pilot jumps (seat freed, thrown clear with the aircraft's velocity), falls, the chute opens,
  drifts down on the wind, and lands on foot on land or swims in the sea; the wreck goes on
  without them. See docs/SKYBARONS_REUSE.md, "Bailouts and parachutes".
- More vessels on the water (above).
- Paint shop and markings (also from the pause menu); sandbox settings (above).
- Cargo that really exists: every box on a quay belongs to someone; a delivery's goods were already
  somewhere in the world, and someone (the sender, a hired porter, or the player) carries them to
  the aircraft; some errands are on foot, on the same island.
- Maps as things one owns, not one convenient zoomable chart: a hodgepodge collected over the game
  (an island's map, a group's, a country's, a sea chart of the Aegean), bought at chandlers,
  harbour offices and booksellers, given or found, each with a diegetic title, its own coverage,
  detail, landmarks, style and errors. The map doesn't show which way one faces: a compass is
  carried beside it, and a compass rose is drawn on the maps that have one. (Data: Sol; drawing
  and browsing: the coordinator.)
- A radio in the cockpit: period music, news, weather and shipping reports, each country's
  propaganda, reception by distance, height and hour (Astra, t3/radio).
- Scenarios (a pause-menu page): buttons that each load a prepared situation at once, like a save
  state: where one is, in what aircraft and paint, the state of the people, the countries and the
  weather, set up in code rather than by playing there. E.g. "a battle between the two countries":
  flying in one country's colours in a formation heading for the other's, under a dark overcast
  with light rain. Others on foot, mid-errand, in a storm, at a feast. Added one at a time, each
  polished before the next, about as often as a judging round.
- The overcast climb: from a dark, rainy sea, up through the cloud deck, breaking out into blue sky.
- Battle title cards: when one joins a battle that matters (the war's named engagements, like the
  Battle over the strait), its name comes up over the scene the way the game's title does at the
  start, then fades. Which fights earn a name and a card (size, sides, stakes, the war's own events)
  is for the war simulation to decide; skirmishes and pirates don't.
- Errands with real provenance: every request traces to someone who needs the thing (and why), a
  supplier who has it (produced or bought), and a negotiation that happened, as if every person
  pursues their own goals (survive, then get ahead) and the economy is all of them together under
  the world's constraints.
- Air brakes (perhaps a negative throttle); a way to lock and unlock the guns; a cockpit view.
- Many more aircraft, especially the WWI-era seaplanes of the references.
- A moon with phases, rising with the right phase for the sun; water green and clear as crystal in
  chosen coves.
- Prettier clouds, foliage and towns: stone paths and alleys between houses (bare earth on the small
  islands), open-air cafes, shops, fountains, statues, benches, people on bicycles, a very few cars
  in the busiest places only, musicians: a world lived in.
- War: battles that play out whether or not one joins them, leaning on Sky Barons (its AI pilots,
  smoke and fire when hit, parachutes); a larger overhaul of errands and the world's liveness.

## Daily life, conversation, and a wider society

The original islands are now a protected neighbourhood inside a roughly 500 by 400 km world
(see `world-geography.md`). They remain the detailed economic core while settlement generation
is extended. Country-sized land is a prerequisite for country-sized societies, not evidence
that a complete national economy or war simulation already exists.

### A person has a day, not an idle animation

A saved daily intent asks for a kind of place: home, quay, market, cafe, church, square, fields,
workshop, shelter or school. Town data supplies stable named, walkable anchors; the simulation
does not pick a building mesh by appearance. Existing quays and house entrances are fallbacks.
Actual work, promised carriage, flying, wounds and repairs take precedence. Going to work is
part of a person's day; it does not issue a second wage or substitute a decorative worker for
the person who produces the goods. Fishermen prepare before dawn, boats depart before the
ordinary catch interval and return by mid-morning. Production still counts only actual named
labour in its established interval.

Free hours make a recognisable place: morning business at the market, an afternoon pause,
Sunday worship, the evening walk, company at the cafe and music in the square. Feast days are
calendar observances, not a director inventing an emergency. Children belong to named
households within the existing background headcount. They do not create an extra consumer
population, cash accounts or free cargo. Some adults use a bicycle for local journeys. A
musician has the same record and duties the rest of the day; music does not spawn an actor.
Weather can make shelter preferable to a social visit.

Meetings require bodies to reach a shared place. Groups are small and temporary. Participants
exchange a few things they actually know, with the existing occurrence dates, confidence,
privacy and receipt rules. Nobody learns a distant raid merely by sharing a settlement index
with a witness. Acquaintance and remembered company accumulate through meetings and committed
conversation. Strong grievances can keep people at different tables. A meeting is a short
commitment, interruptible by a real obligation, not an all-day dock-readiness lock.

Scene walking and abstract walking advance one saved plan. The scene leases the person's
movement and follows collision-checked routes; folding preserves the actual pose and unspent
route. Blocked routes cannot complete because the observer left. Town geometry can publish
new anchors without relocating a person. Rendering reads intent, pose and movement ownership;
it cannot choose a different daily life on each camera visit.

### Speaking is an action; inspecting dialogue is not

Topic lists and previews are pure queries. Committing a spoken turn records its words, subject,
listener and source; selecting a reply consumes a pending question once. Saved recent-use
memory stops repeating the same line or question within the defined bounded window. Exhausting
a subject leads to an honest refusal and then silence, rather than another invented fact.

Voices differ in rhythm and habits: an old fisherman can answer in six words, a clerk can make
courtesy an obstacle, a young courier can leave an anxious question at the end, a shopkeeper
can notice the price and the person in the same breath. Age, trade, temperament, fatigue,
circumstance, acquaintance, actual relationship memories and where the day has brought them
all matter. They need not make a confession whenever the player comes within earshot. Debts
are not announced to a stranger in a crowd. A friendly answer is not a money cheat or a means
to promise a delivery without reserving its goods.

Public news, private knowledge, stale quotes and interpretation are distinct. A speaker uses
what they heard, not a global event query. Second-hand accounts keep their source and date;
uncertainty is part of the sentence. A price last heard yesterday can lead someone to a bad
bargain today. A person's opinion of a late courier need not explain the courier's real delay.
Speech must not quietly turn a guess into a verified Event or multiply reputation on retelling.
Useful transaction details stay in structured data and notebook content; spoken lines do not
recite minute counters, escrow rules or scheduler retries.

People are not information kiosks. A greeting or a remark in passing is short and comes from the
speaker's own day (where they're going, their work, their children, the wind on their trade).
Asking about a subject brings a personal view first ("medicine has gone dear; I paid through the
nose"), asking again brings a particular, rounded and dated the way people carry it ("near enough
nineteen lire, yesterday evening, so Yannis said"), and after that a referral to a neighbour who
would know ("ask Eleni at the store"), then an honest end. Speech never says centesimi, clock
minutes, packages or record words; `living_talk_words.jo` turns figures into spoken forms and
`tests/living_speech_style.jo` samples greetings and answers across towns to keep it that way.
A notice is retold in a sentence with who it came from, never read out. Fourteen voices (by
trade, age and temperament) carry the same facts differently.

The coordinator owns conversation presentation: choosing topics, showing questions/replies,
maintaining a short conversational pause, and deciding how much source/uncertainty information
to show. The simulation supplies this material without prescribing a new panel or control.

### Small stories remember what happened

A story is a compact journal of a situation and its evidence, not a script with a guaranteed
ending. A courtship can begin with two adults repeatedly finding time at the same cafe; a
modest gift has to be bought from actual stock and somebody has to carry it. Missed promises
and older grievances can become a feud; improved dealings can let it cool. A boat becomes a
concern because a real journey is overdue. A watcher learns of its return by seeing it or by
hearing a carried report, not by reading the boat's hidden global state. A debt develops through
actual partial payments, settlement or default. A household errand remembers whether the goods
reached the promised door or stayed with their owner after cancellation.

Keep living situations and a bounded history of outcomes. Preserve the compact reason in
relationship memory after the full event is gone. Stories can offer work only through the same
funded job, owned cargo and validation paths as ordinary business. The world owes nobody a
happy ending or a new quest every evening.

## Countries and conflict: scale and implementation plan

### Identity and the three simulation tiers

The two mainlands support **Kalyra** and **Orenthia**, country IDs 1 and 2 in the
settlement registry. Country 0 is the neutral **Archipelago**, including the six original
harbours. Stable country keys are `archipelago`, `kalyra`, `orenthia`. Country membership,
citizenship, faction membership and occupation are different fields: a pirate from an eastern
port is not automatically an officer acting on the eastern government's orders. Settlement
country IDs come from the catalog, never a mesh array index or a change in coastline.

The town catalog supplies stable settlement ID/key, name, country/region, kind, building target,
position, facilities, optional harbor geometry, roads/neighbours and semantic local anchors.
It owns **where places exist**, not all of their economic state. Adopt it in three tiers:

1. **Far districts**, reviewed hourly/daily: sparse stock, capacity, households/labour cohorts,
   treasury/payroll, infrastructure condition and road/sea neighbours. A farmstead does not need
   twenty fully ticking Persons or a full Town mesh. Only real facilities produce, consume or
   repair; population and the active detailed people must not be counted twice.
2. **Active settlements and routes**, reviewed per game minute: named residents with current
   business, owned lots, sparse transport schedules, prices, obligations and carried knowledge.
   Visiting a new place can select persistent residents from its saved cohort; it cannot issue
   them a second share of the district's wallet, goods or day's labour.
3. **The scene**, fixed ticks: leased physical aircraft, boats and people. No independent second
   fleet, dock occupancy table, cargo pool or fighting force. Fold the actual remaining route,
   resources, wounds and pending encounter back into the same IDs.

Version the catalog and the core-to-catalog mapping. Preserve the six legacy IDs, original
positions, commitments and owned cargo. A v2 save should use stable settlement IDs in all
Person/Job/Trip/Obligation references and a sparse `place_by_id` registry, with an explicit
`core_slot_by_id` cache for active records. Catalog-row indexes are not save identities. Do not
silently reuse an array slot whose previous ID is still referenced by a cargo lot or journey.
Existing six-place v1 validation is a migration boundary, not proof that an arbitrary catalog
can be passed to the current constructor.

Replace `origin*6+destination` with ordered ID-pair route addresses and retain an explicit old
key decoder for cargo-era saves. Cache routes on demand by endpoint IDs, mode and geography
version; never build N*N routes for hundreds of places. A sparse graph of service hubs supports
multi-leg trips, real fuel stops and actual timetables. The old protected-island water corners
are not a navigation solution for a 500 km sea. New long-range routes need water connectivity,
terrain clearance and bounded asynchronous baking, with a valid coarse route while detail is
prepared. AIRFRAMES supplies range/capacity; a new nation is not an excuse for an old Gull to
cross a continent on one unchanged tank.

Materializing/dematerializing economic detail is a transfer and a time lease. Extract named
workers' stock/pay from their district, suppress that cohort's overlapping output/consumption,
and return the same balances and elapsed work later. Keep coarse warehouses as actual cargo
stores/provenance owners; moving them into a detailed market must not call `record_creation`.
A market price is a stock-derived local quote, never a replacement quantity that appears when
a town is rendered. Limit active people, route bakes, meetings and meshes independently of
world area. No far simulation loop runs per camera frame.

### Implemented foundation and evidence

The life branch supplies country records with optional real treasury/authority seats, explicit
core-country mapping, a bounded national incident ledger, duplicate receipts and sparse
bilateral tension. Reports must actually be heard at the country's seat. Private facts,
low-confidence tales and unknown targets do not become national incidents. One public Event
has one effect even if it travels by five pilots. Civilian/privateer harm has smaller weight
than attributed state action; public opinion can be strained without proving a government's
orders. Quiet days allow tension to ease. No money, military units or world goods are minted
by this foundation, and it does not claim that a running war has been implemented.

### From tension to a war with real costs

The next conflict slice should introduce national goals and funded orders. Pressure comes from
security, trade access, treasury, infrastructure, food, political commitments and remembered
losses. Multiple recent independent incidents, contested access and an actual government's
choices can produce mobilization; a calendar threshold alone cannot declare a war. Require
credible state attribution or an explicit political decision to blame a country. Local people
can disagree, evade the question, benefit from smuggling or defend a friend across the border.

Mobilization reserves real crews, aircraft, fuel, parts, food and wages from government-owned
stock/accounts. Recruitment transfers a worker out of civilian labour; repair and replacement
consume time and existing parts. Bounded loans/imports use explicit outside accounts. No free
reinforcement appears because the player saw an empty sky. Orders have issuer, purpose,
resource escrow, expiry/retry, route, participants and a printable reason.

Convoys are actual saved manifests aboard owned vessels, with escorts and departure windows.
Blockades require supplied patrols at a real lane, not a global invisible boolean. A customs
search/seizure names the legal owner, patrol, cargo and authority, and records custody; privateers
need a saved letter of marque with issuer, pay, targets and expiry. Pirates retain their own
motives and can be disowned. Higher prices follow real disrupted supply, requisitions or
transport risk; they are not a flat war surcharge painted over untouched stocks.

Raids and battles can proceed without the player. Resolve the same saved encounter once,
with recorded fuel/time, risk and resource losses, using abstract rules outside the scene and
physical participants inside it. Observing a battle cannot re-roll it or spawn another wing.
The player may join, escort, carry, report, smuggle, rescue or leave; participation uses the
same aircraft identity, damage, cargo and legal/reputation evidence as any other person. A
pilot shot down follows the existing ditch/rescue policy; civilian injury and displacement
must have persistent households and costs, not decorative casualty counters.

Occupation requires a force that actually reaches and can supply a place. Keep sovereign
country, current controller, infrastructure damage and civilian attitudes separate. Transfer
public custody/receipts without erasing private title or old relationships. Open/closed roads,
harbors, shortages and danger alter real choices and routines. News about a captured town
travels; remote people do not acquire the new map state before hearing of it. Counterattacks,
exhaustion and negotiated terms can end an occupation or war through the same obligations
and resources that sustain one.

Implement and test in slices: catalog/core migration; district conservation/LOD leases;
national orders/treasuries; convoys and interception; supplied blockades; political escalation;
physical battle participation; occupation and peace. Gates include no double production,
conserved provenance/payroll, no war from an unheard rumor, no double encounter resolution,
finite funded retries, stable saves through tier switches, and a month with the player absent.
UI orders, map overlays, topic presentation and participation prompts remain coordinator work.

The merged towns registry is adopted through `publish_settlement_life` and the CPU-only
`publish_place_contexts` contract. `World.place_contexts` is keyed by the actual sparse IDs;
793 identity/venue contexts, reciprocal road neighbours, real country capitals and optional
aviation facilities survive canonical saves. Inland churches, cafes and squares use authored
`place_landmarks`; legacy venue fallbacks use original houses/quays, and the legacy cafe and
square match the enriched furniture coordinates. `life_place_name` resolves sparse IDs.
This catalog is the far tier's **context**, not a claim that it already has a funded economy:
no far households, inventories, military actors or flights are fabricated by publication.
National `capital_id` is independent of an optional detailed economic `seat`; the evidence
policy cannot read a sparse capital ID as one of the six core array slots. Far-stock/cohort
initialization and v2 travel/market promotion remain the next simulation migration.

Speech keeps all utterances/questions/replies from the preceding four game hours, up to 64
lines per person. At that bound a persistent conversation becomes silent until old lines age
out; it never drops fresh history to repeat a phrase. Rendering previews are pure. Existing
contact/news actions commit utterances; topic/reply selection remains a coordinator UI task.
