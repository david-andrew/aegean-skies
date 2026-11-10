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

Every few game minutes each person who is free re-plans:

1. Score candidate **activities** for them: work at their trade, trade a price difference they
   know of, take a posted job, rest at home, visit a friend, repay a debt, raid (pirates), patrol
   (police), go somewhere they have heard of an opportunity.
2. Each score = drive pressure x how well the activity relieves it x odds of success (from their
   skills, aircraft, weather, danger they know of) x trait modifiers (an honest person scores
   theft near zero, a desperate one a little higher).
3. Take the best, with a little randomness so people are not clockwork.

The same machinery serves everyone: a fisherman's "work" is to fish and sell, a merchant's is to
buy cheap and sell dear, a courier's is to take jobs, a pirate's is to raid. No activity exists
only for the player's benefit.

## Where opportunities come from

Opportunities are posted by people with needs, and the player sees the same postings that NPC
pilots do (they compete for them):

- **Delivery**: a merchant has stock where it is cheap and knows a price where it is dear; the
  margin pays a courier. Urgency (a shortage) raises the pay and sets a deadline.
- **Passenger / mail**: people want to travel; mail piles up at harbors.
- **Bounty**: posted by the authority (and by victims) when a pirate's raids pass a threshold.
- **Escort**: a merchant who has heard of raids on their route.
- **Repair, rescue, search**: a downed pilot, a missing boat.
- **Smuggling**: contraband is dear where it is banned; a smuggler needs a pilot who will not ask.
- **Races**: settlements host them now and then, with a purse and entrants.

What the player does feeds back into the same state: delivering relieves a shortage and lowers a
price; robbing a merchant gives them a grievance, makes them poorer (they may borrow, then fall
behind), raises the fear in their town and pushes the authority to patrol.

## Memory and reputation

- An **event** (a delivery, a theft, a fight, a rescue, a broken promise) is recorded with who did
  it, to whom, where and when, and who saw it.
- Those involved remember it and change their relationship; witnesses remember it as fact; others
  hear it later as a rumor (a little less trusted, sometimes distorted).
- **Reputation** is not a number the game keeps: it is what the people of a place know about you.
  A town where many people know you helped them treats you well; one where you are only known
  from rumor of piracy is wary.

## The player

The player is a person in the same tables: money, an aircraft, debts, relationships. They can do
whatever any person can (with their own hands on the controls). Nothing waits for them.

## The first milestone

A small, complete living archipelago:
- three or four settlements on different islands, a hotel on an islet, a pirate cove
- about forty named persons: fishermen, merchants, two or three courier pilots, a mechanic or two,
  an innkeeper, harbor police, a pirate crew of four
- working seaplanes for the player and the NPC pilots: take off from water, fly, land, taxi, moor
- getting out at a dock and walking along the quay, talking to people
- a market and a job board at each harbor; fuel and repairs
- rumors at the inn; pirates who raid when they are short of money, and a bounty that follows
- a headless test that runs thirty game days and reports the economy's health (no runaway
  prices, no one stuck, money conserved apart from known sources and sinks)
