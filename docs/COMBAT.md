# Physical air combat

`src/combat.jo` is a fixed 60 Hz physical layer. The living world owns identities, sides,
engagement causes, cargo, money, rescue and strategic outcomes. Combat consumes existing
craft/person IDs and returns actual damage and survival outcomes. It never invents inhabitants.
`tools/combatlab.jo` is an explicitly synthetic acceptance fixture, not part of the game world.

## Starting and stepping an engagement

Construct one `Combatant` per existing aircraft, with its existing `CraftSpec` and `CraftState`:

```text
pilot = CombatPilot(skill=0.8, nerve=0.6, role=.fighter)
a = Combatant(craft_id, person_id, side_id, spec, state, pilot=pilot)
b = start_engagement(engagement_id, seed, place, actors, boats)
step_battle(b, environment, physical_observer)
```

- `side` defines hostility; actors on the same side cannot hurt each other. IDs are stable world
  IDs, not local array indices. Start validates unique aircraft and pilot IDs. `model` optionally
  preserves the operator's existing paint slot; otherwise it uses that type's default model.
- `skill` and `nerve` are normalized 0–1. Skill changes deflection error and control accuracy;
  nerve changes damage withdrawal and how long a burning pilot stays aboard. Roles are fighter,
  wingman (stable `leader` craft ID), strike, escort and flee. Wingmen hold an offset while joining
  distant action; strike pilots strafe moving `CombatBoat`s; escorts prioritize attackers near
  friendly boats. There is no strategic spawning, reinforcement or faction selection here.
- `CombatBoat(id, side, position, velocity)` has a configurable ellipsoid `half`, health and
  disabled flag. Its supplied velocity moves it each tick; a disabled boat stops. It is a
  physical target proxy, not a second living boat or an owner of cargo. The war/boat adapter
  must commit the proxy's actual position and damage to its existing boat.
- `external=true` means the caller integrates that body once, writes its new `state` and previous
  position before the tick, and supplies `pilot.trigger` / `gun.locked`. Combat still handles its
  guns, hits and fire. Human bodies use this path; `human=true` prevents automatic AI takeover.
- Internally owned bodies are stepped exactly once by combat. Do not also run traffic, autopilot
  or human flight integration for them. A real hit takes a passive NPC body from its route
  controller. Its configured role determines whether it flees or fights.
- `present=false` excludes an abstract/unmaterialized body from physical combat and rendering.
  Match `engagement` IDs and each actor's `rally` origin when several separate contacts share one
  Battle. Registration and `start_engagement` set the origin. Target selection cannot
  cross assigned engagement IDs. `finished` means at most one active side (flying aircraft or an non-disabled boat)
  remains in the Battle;
  a multi-engagement world should inspect each engagement's actors/outcomes instead.
- Maximum 128 aircraft and 2048 live rounds. Near AI thinks every 6 ticks, medium every 15, distant
  every 30, staggered by craft ID. Full contact physics is retained near terrain, wrecks and debris.
  Clear distant air uses the same force equations at 60 rather than 120 Hz. Observer position
  changes numerical detail; deterministic replay requires the same observer/LOD schedule.
- The caller owns lifecycle: retain disabled aircraft through the wreck/descent, consume outcomes,
  then retire an engagement or build the next one. Do not append indefinitely to an old Battle.

Guns use real forward muzzle/convergence vectors, inherited aircraft velocity, gravity and
seeded scatter. Moving aircraft are hit in local part ellipsoids, with nearest-hit ordering and
stable ID tie breaks. Terrain/sea is sampled nine times along each bullet step; this is a bounded
approximation, not an exact terrain raycast for arbitrarily thin ridges. Multiple wing decks and
separate twin engines are included. NPC guns keep their 700 rounds, aircraft-specific cadence, heat/jams and one-in-three tracers.
Human guns start with 10,000 rounds and the legacy rapid stream: 11 rounds/s combined, every
round a tracer, cooling at 0.35/s, slowing above 0.85 heat rather than jamming. The Aircraft pause
page cycles Rapid / Light / Medium / Heavy (period rates 8 / 11 / 14 rounds/s, original period
heat/jams and tracer frequency). Endless ammunition bypasses consumption/exhaustion only;
safety and period overheating still apply. Switching guns does not replenish the magazine.
`configure_player_gun` applies these settings only to human actors; its one-time magazine load
is serialized. All rounds remain physical. `bullet_scale` follows the existing
flight-speed experiment in the main game and defaults to design speed in standalone battles.

## Events, survival and persistence

`b.events` is the current tick's cosmetic event stream; consume it after each fixed tick, before
another step clears it. Direct calls such as `bail_combatant` and `apply_bullet_hit` also append
immediate events, which a caller can display before stepping. Event kinds include shots, hits,
ignition, separation, downed aircraft, bailouts, landings, escape, splashes and disabled boats.

`take_combat_outcomes(b)` transfers the durable outcome queue once. Each outcome has a serial monotonic within its Battle, an engagement ID, stable craft/person/attacker IDs, actual position, remaining hull and
engine condition, and (on landing) injury and `at_sea`. Store consumed `(engagement, serial)` pairs transactionally
with the world if a coordinator needs retry/idempotency across saves. `boat_disabled` identifies
its boat in `boat`; `attacker` and the originating craft/person identify the shooter. The
cosmetic event's `other` is the boat ID. Read actor state for ongoing damage; terminal records snapshot its condition.

`bail_combatant(b, index)` releases one `Descent` for the existing person and locks the guns. The
unpiloted aircraft continues to fall, shed debris, splash, float and eventually sink. It cannot
produce a second pilot. NPCs bail when the airframe/engine/fire is hopeless; human bailout is a
choice. The canopy opens after 1.25 seconds (or manually after 0.17), settles to 7 m/s and drifts
with the actual wind. Land produces `.landed`; water produces `.swimming`. Descent steering is
world-space horizontal movement. `released=true` transfers drawing to a foot/rescue controller.
Presentation follows Sky Barons: FALL somersaults at 9 radians/s; CHUTE switches upright with
a full twelve-gore canopy (that reference has no inflation or independent sway animation).
The eye follows at 14/s, nine metres back with a 0.7 m shoulder offset, looking along the player's
aim independently of the somersault. Existing descent physics and opening times are retained.

Gun audio uses eight broadband-noise reports per family, randomly selected per shot, with a
short high-frequency crack and a wide low-frequency thump. Playback follows physical shot
events; there is no synthesized pitched gun oscillator or separate looping firing sound.
`tools/gunlab.jo OUTPUT_DIR` writes spaced shots and three-second held bursts as WAV files
without opening a window or playing sound.

The **rescue/war integration boundary is intentional**: this branch exposes bail/land/swim data
but does not choose a rescue vessel, transfer crew/cargo ownership, award a victory, set faction
relations, or teleport a survivor to a harbor. The living-world coordinator must consume those
outcomes, mark the same person as outside the aircraft, suspend their old trip/work, and advance
rescue using the descent's current position. Until that policy is connected, a bailed NPC's
physical wreck retains its scene lease and its old world trip remains pending. Do not invoke the
legacy `weather.ditch` while the person is still descending: that routine relocates the person.

Battle and Descent are text-serializable. Save the Battle (including rounds, fire, guns, pilot
controller state, serials, descent and pending outcomes) alongside the world at a completed fixed
tick. On restore, rebind the same IDs/leases and use its exact states; do not resume its aircraft
through an abstract route at the same time. Cosmetic meshes/particles/audio are rebuilt. The
existing `fold_living_scene_for_save` API saves route flight only; a war coordinator must add this
Battle extension, rather than silently discard a live fight or canopy. The current game startup
does not yet load a persistent world; pure Battle round-trip/replay is covered by tests.

## Existing scene bridge

`Traffic` accepts an optional enabled Battle; disabled/default preserves its previous behavior.
`combat_bridge.jo` registers leased craft, binds already physical pirate/victim contacts, suppresses
the old timed abstract surrender roll for those contacts, and commits actual pose/fuel/damage exactly once on
the scene clock. Combat-owned motion suspends route progress and queued route incidents until
the route controller resumes. Zero-fuel/zero-hull recovery is also deferred for combat-owned
poses, so a canopy cannot trigger the old harbor-relocation recovery. The human physical body
also keeps its lease when its tank empties, allowing an actual glide/landing/bailout.
`scene_motion` exposes default-true `progress` and `recover` flags; the command layer also has a
default-true `recover` flag, so existing callers retain their recovery behavior. Surviving pilots return to their route when the physical contact ends. Current
legacy raid completion is “raid failed”, without abstract loot/damage; strategic victory,
surrender/loot and rescue belong to the parallel living-world work. Mixed/abstract contacts retain
the old world owner. No extra aircraft/person is spawned by the bridge.

`combat_owns(b, craft_id)` is the ownership check used by traffic. Part damage survives returning
to route flight; legacy wear projection is bypassed for that airborne combat-damaged body and
re-enabled at mooring. The bridge gives civilian operators the flee role and patrol/pirate
operators fighter; a war coordinator may override the role, skill and nerve before binding.

## Player controls and presentation handoff

- **Z** continues the throttle lever below idle to deploy proportional air brake. **Shift** raises
  it again; negative lever never commands reverse engine thrust.
- **G** locks/unlocks guns. Safety defaults on; entering a town's 1,200 m protection sphere below
  300 m or mooring locks it once. A deliberate unlock works inside that area. Leaving does not
  silently arm it. There is no war-status policy yet; the faction system can call `gun_safety`.
- **V** toggles cockpit camera. Three physical, aircraft-mounted dials show airspeed (0–130 m/s),
  altitude (0–1,000 m) and engine throttle. Existing look-around input works. This is one shared
  compact panel fitted to the existing cockpit seats, not sixteen individually detailed interiors.
- **T** aboard an unmoored aircraft bails out; during descent it requests early chute opening.
  Movement keys steer the canopy/swimmer. A land arrival transfers to existing walking control.
- **X** toggles the existing amphibian landing gear control (Albatross).
- Existing fire input is Space in air / captured left mouse. Safety, cooldown, heat, finite ammo
  and a live pilot all gate it. Fire input resets when leaving flight control.

No new HUD/menu layout is included. UI still needed: safety state, ammo/heat/jam feedback, lever
negative/brake range, cockpit/gear/bail bindings (including touch controls), a deliberately placed
bail command, parachute/swim/rescue state and strategic engagement/outcome presentation. Existing
2D gauges are hidden inside the cockpit; the coordinator may refine dial labels/ranges and panel
layout. Pilot appearance in parachutes currently uses a shared procedural pilot mesh; connect the
world person's appearance seed if outfit continuity is required.

`combat_view.jo` uses existing WebGL2 shaders/instancing and bounded particles. Distant healthy
craft are 96 triangles or fewer, batched by type. `combat_sound.jo` synthesizes three gun families,
wood/metal hit snaps, canopy opening, fire and chute wind. No new external assets or shader
uniform/texture limits are introduced.

## Acceptance commands

Use `SLOPPY_THREADS=1`, `SLOPPY_NO_AUDIO=1`, unset `DISPLAY`/`WAYLAND_DISPLAY`, and a private `SLOPPY_SAVE_DIR`.

```sh
sloppy test tests/combat_test.jo --release
sloppy test tests/combat_scene_test.jo --release
sloppy build --release tools/combatlab.jo -o combatlab
COMBAT_SCENE=burning COMBAT_SEEK=360 COMBAT_FREEZE=1 SLOPPY_FRAMES=2 SLOPPY_SCREENSHOT=burning.png ./combatlab
COMBAT_SCENE=chute COMBAT_SEEK=360 COMBAT_FREEZE=1 SLOPPY_FRAMES=2 SLOPPY_SCREENSHOT=chute.png ./combatlab
COMBAT_SCENE=cockpit COMBAT_KIND=0 SLOPPY_FRAMES=2 SLOPPY_SCREENSHOT=cockpit.png ./combatlab
# CPU timing: quiet redfox only, inside flock ~/dev/tmp/bench.lock
SLOPPY_FRAMES=1 SLOPPY_SCREENSHOT=unused.png COMBAT_COUNT=30 COMBAT_BENCH=3600 ./combatlab
SLOPPY_FRAMES=1 SLOPPY_SCREENSHOT=unused.png COMBAT_COUNT=30 COMBAT_FAR=1 COMBAT_BENCH=3600 ./combatlab
```

The duel test must reach a flying winner inside 240 simulated seconds. The thirty-aircraft test
bounds bullet-pair work, brains, physics, storage and finite states. Other tests cover replay
through serialization, cosmetic-RNG independence, nearest-hit ordering, terrain occlusion,
boat attack/escort selection, land/sea parachutes, real air-brake drag, gun safety, single
scene ownership, damage persistence, human fixed-substep hits and finite/distinct sound waves.

## Combat presentation budgets and cockpit

The presentation pass keeps simulation ownership unchanged. `combat_trails.jo` holds a fixed,
reused ribbon history: 960/1600/2400 segments on low/medium/high, sampled every 0.65/0.4/0.25 s.
Smoke lives up to 22 s, rises, expands and drifts with wind. A small minimum angular width
keeps distant trails from disappearing below a phone pixel. Hard-cap eviction gives thirty
burning craft about twenty seconds even on low. Healthy aircraft pulling/rolling in an engagement
leave shorter pale wingtip trails; these stop when the aircraft starts smoking. Teleports and
inactive sources break trails. Effects never consume `combat_noise` or feed back into physics.

Each of the four particle pools has a hard cap of 240/500/900. Muzzle and impact flashes last
several frames, muzzle glows follow their actual moving mount, tracers use a bounded angular width
and longer range-visible streaks. All effects stop emitting outside 11 km. Detailed aircraft give
way to batched silhouettes at 450/750/1000 m; separated wings and tumbling debris retain separate
silhouettes. Parachutes bloom over 0.65 s. Low uses half as many canopy gores; beyond 450 m the
hanging pilot is a twelve-triangle silhouette.

`Round.serial` is the shot event's stable identity. `combat_near_passes` runs after each physical
combat tick, checks the swept round segment within 12 m of the listener, excludes their aircraft,
and remembers 128 pass IDs. Whizzes are globally spaced by 90 ms. Hits on the occupied aircraft
produce a damped camera jolt and a separate low body thump. Wing marks sit on both fabric skins;
engine damage produces oil drops/streaks on the cockpit windscreen. Repair removes these through
the existing damage state. Target controls and additional instruments are described below.

Each aircraft has a named wood or metal panel fitted behind a stitched leather coaming, a thin
windscreen frame, five engraved instruments, a stick and gloved hands. Existing wings, cowling,
engine placement and props retain each design's silhouette. The first-person fuselage has a clipped
cockpit well, and the box cabanes become thin round tubing in that view. Running propellers resolve as narrow
blade-tip arcs; stopped engines retain their blades.
Exterior models and collision solids are unchanged. All cockpit geometry is camera-relative before
projection so millimetre gauge details survive remote world coordinates.

The instrument scales are 0–400 km/h true airspeed, a 10,000 m altimeter revolution, 0–4000 RPM
(engine-family rated speed, throttle and engine health), 0–4 oil pressure and a north-pointing
compass. RPM/oil are indicative engine gauges, not an additional engine simulation. The physical
ring sight and neutral camera aim at the guns' 450 m convergence, including level-flight gravity
drop at the selected bullet speed. Bank, range, wind and pilot aim still require correction.

`tools/combatlab.jo` also accepts `COMBAT_DISTANCE=1500`, `AEGEAN_QUALITY=low`,
`COMBAT_SCENE=stress` (thirty continually firing/burning aircraft), `COMBAT_HIT=1` with cockpit,
and `COMBAT_PITCH=-0.25` to inspect the lower cockpit. It initializes the same WebGL compatibility
and resolution tier as the main game. Stress is an explicitly synthetic acceptance fixture and is
never loaded into the living world.


## Battle response, timing and target view

The live frame budget (`frame_budget.jo`) accepts at most 50 ms and three 60 Hz ticks per
render frame, discarding older catch-up time. Camera position/look use exact damped springs.
`Combatant.previous`/`previous_rotation` and `Battle.render_alpha` provide presentation-only
interpolation through `combat_render_state`; external/human poses bypass it. Always use the
current authoritative state for collision/world commits.

Combat NPC specs set `combat_flight` so their pure-scale lift, gravity and energy equations
match the player. Ordinary route traffic keeps its existing calibration. The off-by-default
**Sky Barons energy and response** Tweaks option raises the load limit to 8 g, roll authority
by 1.125, key smoothing to 9/s, and scales both thrust and drag by the pure speed scale without
changing equilibrium speed. It applies equally to player and combat NPCs. Chaotic stalls now
contribute only near low airspeed, separation or reverse flow; attached flight retains normal
kinematic response.

A swept 128 m spatial grid reduces bullet/body candidate tests while preserving narrow-phase
hit ordering. Exceptional long sweeps fall back to the bounded complete list. Firing order
rotates each tick to avoid side bias when the round budget fills. Detailed mesh counts are
capped at 6/10/16 on low/medium/high; further aircraft use instanced silhouettes. Expired smoke
ribbons are compacted, not retained until the hard cap.

**Tab** cycles targets and **C** toggles target-follow camera; right mouse keeps free look.
Mouse/drag flight steering stays independent of the viewed target. Touch **Look** cycles on
release after a tap, or toggles follow after a .45-second hold. Combat candidates include all
hostiles without a cap, sorted by immediate threat then distance, followed by nearby friends.
Outside combat, at most six relevant aircraft, job destinations/ships and nearby landmarks
are offered. Candidate refresh is 2.5 Hz; selected moving positions track every render frame.
Stable IDs survive reorder; losing the selected object releases follow. A small bracket/name
or edge chevron marks the selection.

All panels now include attitude and turn/slip instruments. The ball follows apparent gravity
using true acceleration; a coordinated turn centers it. Third-person gauges expose the same
state. Compass card and radio dial are camera-relative panel meshes; radio touch hit testing
projects that same relative rectangle. The station card remains a HUD element.

Near-pass audio consumes `Battle.sweeps` after each fixed tick, including rounds consumed by
hits/water, clipped at impact. The occupied aircraft is the listener, and pass/own-hit sound is
listener-relative so chase-camera distance cannot mute it. Nearby water strikes have their
own attenuation. Synthesis uses Sky Barons' short two-band noise crack/whizz.

`build_scenario(key,towns,models,per_side=8)` supports up to 64 per side. For captures use
`AEGEAN_SCENARIO=strait AEGEAN_BATTLE_SIDE=64`; the normal button remains eight per side.
`AEGEAN_TWEAKS=energy` or `stalls` enables the corresponding comparison. `Start of the game`
rebuilds the initial seed, quay/player, weather, handling and title while preserving rendering
options and loaded resources.

Regression tools: `tools/scenario_soak.jo` (`SOAK_SIDE`, `SOAK_SECONDS`, `SOAK_TIMING`) and
`tools/combat_bench.jo`. Run timing only on the quiet laptop under its benchmark lock.
