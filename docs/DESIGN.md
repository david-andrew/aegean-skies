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
