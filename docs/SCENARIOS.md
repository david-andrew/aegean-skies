# Repeatable situations

Pause (P/F1), select **Scenarios**, then **Battle over the strait**. The button replaces the current situation and resumes immediately. P opens the ordinary pause menu again; all normal flight, weapons, bailout, weather and debug controls remain available. No restart, mission mode, victory screen or automatic return timer is involved. This does not overwrite a living-world save. Scenario notebook edits use a separate save key.

Each side's pilots have a skill, aggression and caution by formation slot (`STRAIT_PILOTS` in
`src/scenarios.jo`), and pairs fly on each other's wing: Orenthia brings a reckless ace at the
point and a cautious pair behind him. The fight is kept under the overcast's base
(`Battle.ceiling` 600 m).

The first situation starts at 09:30 on day zero. Kalyra's blue-and-white Gull flight meets Orenthia's navy-and-gold flight (both carry their national roundels) over the eastern channel. Eight aircraft per side approach from roughly six kilometres apart. The player starts at the back of a loose V, with cruise power already set. The saved weather combines an overcast deck and a mild rain cell: about 650 m cloud base, above a 440–500 m approach. The cloud layer remains the normal three-dimensional weather and can be flown through.

**How the strait ends.** A side breaks off when it has lost half its aircraft and is outnumbered
two to one by those still fighting; a side with no enemy left fighting turns for home too. Pilots
going home, or withdrawing hurt, no longer hold the fight open (`Battle.finished`). Each side's base
is its country's harbour nearest the strait (`strait_homes`: Kalyra to Ardevanti, 89 km;
Orenthia to Lyravanoria, 4 km). Its pilots form on the leader in their own slots, the player's slot
left open and marked with a faint ring; the leader flies the autopilot's approach and the rest
circle the bay, stacked, and land in turn 25 s apart, each taxiing to its own mooring along the
quay, where its pilot stands afterwards. The radio's words show over each Morse cue
(`src/homeward_view.jo`). Flying 40 s in the slot and landing at the base records
`flew_home_in_formation`; going 7 km from the fight while it is on records `left_the_fight`.

**Pilots in the water.** A pilot shot down low over the sea with the engine gone and the aircraft
still answering ditches rather than jumps (`_can_ditch`, `_ditch_controls`), and climbs out beside
the floating aircraft; others come down under the canopy. Either way they wait in the water in a
yellow life vest, a green marker dye spreading round them, waving at aircraft that come near
(`src/survivor_view.jo`), for a day. The living world's rescue takes it from there: land, taxi
alongside, F to take them aboard, moor at a harbour, F to set them ashore. A foe set ashore in the
player's own country's harbour can be handed to the guard (F) or let go (R). A few words are said
on the quay (`src/rescue_exchange.jo`), and the deeds are recorded (`src/deeds.jo`).

## Ownership and loading

`src/scenario_catalog.jo` supplies stable keys, names and one-line descriptions. `build_scenario(key, towns, models)` in `src/scenarios.jo` dispatches a builder and returns an optional `ScenarioState`. Unknown keys return none. Builders create a fresh seeded `World`; they do not edit the running world or read input/cosmetic randomness. The result contains the entire living world (including its clock, people, diplomacy, jobs, weather and boats), physical player aircraft, player mode/position, combat aircraft, vessels and camera settings. Terrain and meshes are existing shared resources.

`load_scenario` in `aegean.jo` caches the pristine result on first use. Sloppy's value semantics keep subsequent world and battle changes out of that cached snapshot. Loading installs the result, rebinds the player, reconstructs traffic projections/leases and clears UI references, pending conversations, notebook state, moorings, air events, camera springs, trails, particles and sound scheduling. It reuses graphics and synthesized audio resources. Flight/debug settings return to the authored defaults; display, input and audio preferences survive. Cosmetic walkers and their random stream also restart.

The strait's fifteen NPC pilots are promoted from real national harbor cohorts and buy registered aircraft through `register_far_aircraft`. Authored funding and full tanks are accounted for in the normal ledgers. There are no duplicate actors, free replacement aircraft or independent ammunition/economy tables. The countries' saved diplomatic relation starts at war.

`Battle` owns NPC physics at the existing fixed tick; `commit_scenario_aircraft` commits its sparse aircraft poses, finite fuel and damage back to the same world records, plus actual descent positions for bailed pilots. `scenario_air_traffic` is a **read-only presentation projection**, used for engine audio, exhaust, glints and shadows. Never give that list to `update_traffic`: that would create a second flight owner. The player remains externally integrated by the usual controls.

`CombatPilot.formation` is an opt-in approach controller. Heading, speed, leader ID and a unique offset define the slot. The existing autopilot supplies controls. Terrain danger, damage/withdrawal or a hostile within 1.4 km releases the slot permanently to combat AI. There are no attitude/position animations and no time-triggered attack. Existing engagements leave this flag false and retain their prior behavior.

## Add the next scenario

1. Add **one** metadata record to `SCENARIOS`, with a permanent key. The menu renders this list automatically.
2. Add a builder and dispatch that key in `build_scenario`. Return a complete `ScenarioState`, starting from `living.build_world` with an explicit seed. Initialize the cargo/life catalogs before placing sparse residents. Account for fixture money/fuel edits; use existing registration/ownership APIs for additional people and vehicles.
3. Set `mode = .walking`, `.aboard` or `.free`, physical player state and camera fields explicitly. Foot/quest scenarios set jobs, cargo, people and their positions inside `world`; they need no menu changes or special update loop. Put additional combat bodies in `battle`, not in both battle and traffic. If a new persistent subsystem is added to the game, add its authored state/reset to the loader too.
4. Add builder/invariant/replay and bounded simulation tests, then inspect captures of the actual game. Do not add a catalog button until that situation is ready.

## Capture and audit hooks

Run a native build headlessly with `SLOPPY_NO_AUDIO=1 SLOPPY_THREADS=1`, unset DISPLAY/WAYLAND_DISPLAY, and use a private `SLOPPY_SAVE_DIR`.

- `AEGEAN_SCENARIO=strait` calls the **same loader** as the menu before the first frame.
- `AEGEAN_CAPTURE_PANEL=scenarios` opens that pause page for a capture.
- `AEGEAN_CAPTURE_TRACE=1` prints the initial world/battle hashes, flight poses and per-second battle counts. Equal initial hashes after a UI reload check the cached snapshot, not just the builder.
- `AEGEAN_SCENARIO_TIMING=1` reports load milliseconds; benchmark only on the designated laptop.
- `AEGEAN_SHOTS="/absolute/dir 120 600 900"` saves those frames as `dir/<frame>.png` and prints a `SHOT` line for each (mode, position, open panel, minute, purse): one scripted `SLOPPY_INPUT` session, many captures.
- `SLOPPY_SCREENSHOT=/absolute/path.png SLOPPY_FRAMES=N` captures frame N with fixed 1/60-second updates. `SLOPPY_INPUT` can exercise the actual menu and flight controls.

This is an in-situ battle fixture, not a national-war campaign or a new save-slot UI. No surrender/scoring screen or strategic fleet replacement has been added.

`canal` — **Canal takeoff** starts a repaired gull with its engine running on the cradle at the
head of Neravessa's workshop slipway (`ScenarioState.slipway`; the loader runs
`start_slip_launch`). It slides down the ways, splashes in, and the yard swings it to the canal's
heading before the pilot has it, about eleven seconds in, near the old launch point. The original winding canal has stone, iron and low
pedestrian bridges, working barges, launches and moored rowing boats. Two real
registered hostile aircraft approach behind the quarter; an allied courier is
already departing ahead. Boats brake for the player's path, but remain physical
obstacles. The builder resets the whole world, aircraft, finite combat state and
vessel fleet through the existing Scenarios page loader.
Orenthian riflemen and machine-gun posts hold roofs, the iron and pedestrian bridges and the
promenades along the run (`src/canal_ground_fire.jo`). They are the scenario Battle's
`ground` guns, not living-world people, and hold fire until the hand-over. The pursuers start far
enough back to reach gun range a few seconds into the water run.
