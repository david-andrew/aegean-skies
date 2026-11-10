# Sky Barons → Aegean Skies: source reuse audit

Audited 2026-11-10, against `~/dev/slop-lang` HEAD
`5b99d537e2684f1e416cec2f690a48e23a74e943` (clean working tree at the start).
This is a static source/docs/history audit; no game was built, launched, or playtested.
Historical timings below are commit-message measurements, not measurements on this machine.

Citation convention: `sim.jo`, `skybarons.jo`, `models.jo`, and `world.jo` mean files under
`~/dev/slop-lang/examples/skybarons/`; `aces.jo` means `examples/aces/aces.jo`.
`docs/...`, `lib/...`, `tests/...`, and `tools/...` are relative to `~/dev/slop-lang`.
Ranges refer to this exact checkout, not the lines in historical versions.
Recommendations and calculations are explicitly identified; they are not existing features.

**Best starting point:** extract the ordinary winged flight and steering, the person/vehicle
separation, interpolation, procedural mesh helpers, and selected effects. Build a new world and
simulation shell around them. Copying the whole match simulator would import extensive rules,
respawn, two-team, carrier, fantasy-craft, and rollback assumptions.
(`sim.jo:638–909`, `sim.jo:1439–1509`, `sim.jo:3138–3305`, `sim.jo:3335–3526`.)

**Largest missing systems:** usable seaplane water contact, docks, enterable settlements,
persistent identities/saves, civilian routes/landings, economy, needs, relationships, and weather.
The existing people are persistent during a match, not simulated inhabitants between sessions;
the villages are decorative meshes. (`sim.jo:874–908`, `sim.jo:1065–1090`, `sim.jo:3446–3459`, `world.jo:512–546`, `skybarons.jo:171–218`.)

## 1. Architecture map

### Files and useful reading order

| File | Contents and entry points |
|---|---|
| `world.jo` — 581 lines | Map selection, cached height grid, terrain queries; two airfields and their stands/sites; decorative terrain/villages/tree/cloud generation. Read `ground` first. (`world.jo:32–160`, `world.jo:181–340`, `world.jo:440–581`.) |
| `sim.jo` — 7,094 lines | All match state and deterministic 60 Hz simulation: people, vehicles, flight, weapons, collisions, rules, bots. No model/render dependency; imports world with `use`. (`sim.jo:1–15`, `sim.jo:623–1090`, `sim.jo:1439–1509`.) |
| `models.jo` — 7,280 lines | Procedural, flat-shaded mesh geometry and caches; also articulated part animation/drawing helpers for special craft. Constants duplicate simulation attachment geometry. (`models.jo:1–98`, `models.jo:4023–4044`, `models.jo:5385–5398`, `models.jo:7168–7280`.) |
| `skybarons.jo` — 5,502 lines | Application shell: input bindings/settings, matchmaking/lobby, fixed tick accumulator, interpolation, camera, drawing, particles, sound, HUD, menus. (`skybarons.jo:109–218`, `skybarons.jo:342–966`, `skybarons.jo:967–1977`, `skybarons.jo:2400–5502`.) |
| `examples/aces/aces.jo` — 2,480 lines | Original smaller dogfight game; useful historical comparison. Sky Barons explicitly identifies its winged physics and fighter bot as Aces-derived. (`sim.jo:3334–3335`, `sim.jo:6807–6808`; origin commit `0f4d68e`.) |

Recommended narrow reading sequence: state definitions → `tick` → `fly_air` → `steer` →
`my_pad` → `view`/`place_camera` → terrain contact. This covers the critical flight loop without
reading the fantasy weapons, lobby, or match modes.
(`sim.jo:638–909`, `sim.jo:1439–1509`, `sim.jo:3335–3526`, `sim.jo:5668–5708`,
`skybarons.jo:972–988`, `skybarons.jo:1170–1306`, `skybarons.jo:1724–1908`.)

### Main types and invariants

| Type | Key fields / meaning |
|---|---|
| `Seat` | Local-space `at`; `dir` zero for ordinary pilot/fixed guns, otherwise gun rest direction; `arc` is a cosine, not radians; `weapon` integer. (`sim.jo:621–636`.) |
| `Kind` | Stall speed, thrust acceleration, quadratic drag, pitch/roll/yaw rates, velocity grip; hull, guns/cadence/heat/ammo; ellipsoid `half`; seats; contact `gear` height and parked `tilt`; `lighter`, collision `mass`, helicopter controls. (`sim.jo:638–664`.) |
| `Pad` | Integer pitch/roll/yaw −100…100, throttle step −1/0/+1; weapon and interaction buttons; seat request; world aim angles in milliradians; bot flag and match-specific actions. (`sim.jo:756–777`.) |
| `Craft` | Kind/team, position/velocity, quaternion orientation, throttle, health, gun heat/cooldowns/ammo; occupant indices and gun aims; landed/down/gone/free lifecycle; home/owner, target and last damage attribution. (`sim.jo:779–818`.) |
| Extra craft state | Helicopter lean/spin; boulders/drones/cannons; crew calls; carrier hooks/stored craft/gasbags; mother/recovery/tether/balloon anchors; Turncoats bonuses. Almost all can be omitted initially. (`sim.jo:790–795`, `sim.jo:819–850`.) |
| `Person` | Team, `player` (−1 bot), pos/vel/yaw, state, craft/seat indices, timer, previous button bits; kill/death counts, craft choice, flag/gun target, chute state, local deck position/velocity, crew-call state. No money, inventory, needs, relationship graph, job schedule, or long-term memory. (`sim.jo:866–908`.) |
| `Bullet` | Pos/vel, source person/craft/team, remaining ticks, damage, special flags and extra hit width. (`sim.jo:910–923`.) |
| `Shot` | Rocket/bomb/flak/healing pack/boulder/cannon/fire pot/iron/stone; pos/vel, attribution, life. (`sim.jo:925–942`.) |
| `Building` | Kind/team, pos/yaw, health; gun aim/cooldown/crew/heat/shots; respawn timer for targets. Not an enterable building or economic business. (`sim.jo:944–956`.) |
| `Boom` | Event pos/kind/tick/who/by, for view/audio; retained for two seconds. Despite the name, includes boarding/landing and many non-explosions. (`sim.jo:966–1031`, `sim.jo:1505–1508`.) |
| `Rules` | Match mode, friendly fire, ground start, rockets, score/time limits, attacking side, allowed craft, marker policy, Boss/Turncoats options. (`sim.jo:1033–1045`.) |
| `Near` / `Parked` | Compact per-tick projections for airborne avoidance and ground bot queries; avoid repeatedly fetching array-rich craft records. (`sim.jo:1047–1063`, `sim.jo:1443–1452`.) |
| `Game` | Arrays of crafts/people/bullets/shots/buildings/flags/booms; rules, bot skill, scores/tick/winner; cached goals/air/crew/ground; mode-specific balls/gold/stand/waves. (`sim.jo:1065–1090`.) |
| `Field` / `Stand` / `Site` | Static airfield origin/direction/team; vehicle parking placement/kind; building placement/kind. Generated for two sides, not general settlements. (`world.jo:39–69`, `world.jo:181–273`, `world.jo:293–340`.) |
| `Deck` | Local collision/floor boxes, optional slope direction, elliptical footprint, draw flag. Useful concept for boats/docks, but existing data describe fantasy aircraft. (`sim.jo:1886–1898`, `sim.jo:1900–1998`.) |
| `Scenery` | Ground/village meshes and persistent GPU buffers of tree/cloud instances, cached by map ID. Lives outside `Game`. (`skybarons.jo:1910–1917`, `skybarons.jo:1942–1977`.) |

Coordinates are meters, +Y up, aircraft forward −Z and right +X. `Craft.rot` is a quaternion
stored as `vec4`; `point_of` transforms attachment positions into the world. (`models.jo:1–6`, `sim.jo:782–784`, `sim.jo:1390–1396`.)

Person and craft identity are separate: a person can walk, enter either side's aircraft, change
seats, bail out, or leave a landed vehicle. An aircraft's paint (`team`) can differ from its
crew's side. `crew_team` takes the first occupied seat's side, otherwise paint; perceived side
can remain paint until witnessed firing. This is a useful seed for ownership/disguise, not a
complete faction model. (`sim.jo:1402–1435`, `sim.jo:2845–2905`, `sim.jo:4880–4901`.)

Craft lifecycle flags overlap: `alive` means `!free && gone == 0`, so a shot-down craft can
still be alive; `whole` adds `down == 0`; `flying` also requires `!landed`. Do not equate
`alive` with undamaged or piloted. (`sim.jo:1398–1400`.)

Arrays use integer indices as references, with several negative sentinels: usually −1 empty,
but `SHUT = -2` means an unavailable hook seat. Removing/reordering live array elements would
invalidate many references. (`sim.jo:289–290`, `sim.jo:800–809`, `sim.jo:881–903`.)

### Start, tick, update, draw

`new_game(pilots, skill, rules, kinds)` normalizes match rules, constructs buildings/stands,
then people; `pilots` maps person slots to player pad indices, with −1 for bots. Ground-start
people start dead with short staggered timers; `respawn` materializes them. (`sim.jo:1181–1243`, `sim.jo:2709–2800`.)

One `tick(g, pads) -> Game`, in actual order:

1. Copy/value-bind `g`, increment tick; calculate each team's ground mission target.
   (`sim.jo:1439–1442`.)
2. Rebuild `crew`, `ground`, and `air` projections; choose AI targets.
   (`sim.jo:1443–1453`.)
3. Select each person's human pad or `bot_pad`, then run `person` for everyone; crew calls.
   (`sim.jo:1454–1462`.)
4. Skip idle unmanned parked craft; otherwise fly drones, special cat, piloted aircraft,
   or unmanned aircraft. Update gunners/carrier/screw/tethers after movement.
   (`sim.jo:1463–1491`.)
5. Re-place walkers on moving decks, resolve craft collisions/rams and mode balls.
   (`sim.jo:1492–1499`.)
6. Advance/hit-test bullets and shells; update ground guns, flags, and match rules.
   Trim event history older than 120 ticks; return the new game.    (`sim.jo:1500–1509`.)

`update(dt)` handles networking/UI, mouse look and transitions, then adds frame time to
`spare`, capped at 0.1 s in local play / 0.25 s online. Each 1/60 s it captures previous craft
and person arrays and calls `tick` locally or `s.play(my_pad())` online. Effects and sounds run
once per frame after ticks. Local practice pause returns before advancing simulation.
(`skybarons.jo:1432–1574`, especially `1485–1487`, `1559–1574`.)

`view()` value-copies the current state and interpolates craft pos/rot (`lerp`/`slerp`) and person
positions by `clamp(spare/DT,0,1)`. It avoids blending teleports >20 m and lifecycle/state changes.
Weapons are interpolated separately when drawn. Keep this for smooth motion at any frame rate.
(`skybarons.jo:967–988`, `skybarons.jo:2697–2700`.)

`draw()` obtains cached scenery and interpolated state, places the camera, generates picker
thumbnails if needed, sets lighting/fog/post effects, submits scenery/buildings/craft/people/
weapons/particles, then HUD and menus. The model module also submits articulated parts.
(`skybarons.jo:2400–2750`, `models.jo:4023–4044`, `models.jo:5385–5398`.)

### Determinism boundary and what to drop

The sim takes pads and fixed ticks, not raw devices/frame time. Random-looking combat/AI uses
`hash(tick/id)` and deterministic sine offsets; visual randomness/audio/camera use `random()`
outside it. Same-tick state hashing is an explicit cross-platform regression contract.
(`sim.jo:1–5`, `sim.jo:3218–3222`, `sim.jo:4031–4044`, `sim.jo:6882–6886`, `tests/t/skybarons_sim.jo:1–16`, `skybarons.jo:1681–1685`.)

World data is an important exception to “everything is in Game”: `map_id`, `attack_side`,
`heights`, fields and rings are globals. They are established before a match and assumed stable
during replay. The world file also contains mesh creation, but headless sim paths never call it.
(`world.jo:32–35`, `world.jo:62–69`, `world.jo:110–118`, `world.jo:477–581`.)

For single player, remove the following rather than preserving their interfaces:

- `net`, `netplay`, `invite`, match server/room state, lobby exchange, peer timeout/stand-in
  handling and desync/ping HUD. (`skybarons.jo:29–37`, `skybarons.jo:342–966`,
  `skybarons.jo:3861–3878`.)
- Session construction/transport, `max_ahead=20`, lag injection, online-only hidden-tab ticking.
  (`skybarons.jo:708–718`, `skybarons.jo:1435–1440`, `skybarons.jo:1567–1568`.)
- `VERSION = version_print()` startup match simulations and manual `RULES_REVISION` compatibility
  hash. Useful as test inspiration, unnecessary for a saved single-player world.
  (`skybarons.jo:330`, `sim.jo:7070–7094`.)
- Rollback event deduplication if events become a single-consumption queue; the current key is
  tick/kind/who, deliberately not one unique ID per emitted event.
  (`skybarons.jo:2752–2756`, `skybarons.jo:2870–2873`, `skybarons.jo:3206–3210`.)

Keep the fixed simulation clock, device-independent `Pad`, testable pure-ish update boundary,
render interpolation, and events. These are useful in single player independently of rollback.
(`sim.jo:756–777`, `sim.jo:1439–1509`, `skybarons.jo:972–988`, `skybarons.jo:1559–1574`.)

## 2. Flight model

### Scope: an arcade model, not a rigid-body aerodynamics solver

The complete ordinary airborne integrator is `fly_air`, 63 lines. Rotation is commanded
directly by stick and rates; velocity turns toward the nose; gravity changes speed and supplies
unsupported vertical fall. There is no wing-area/air-density lift equation, angle-of-attack
curve, prop torque, rotational inertia, fuel mass, or wind-relative airspeed for these planes.
Collision `Kind.mass` does not enter this flight equation. (`sim.jo:3335–3397`, `sim.jo:638–664`, `sim.jo:3884–3890`.)

The following equations reproduce the ordinary plane path, with `h=DT=1/60`, controls divided
by 100, and mode bonuses disabled. `smoothstep(a,b,x)` clamps `u=(x-a)/(b-a)` and returns
`u²(3−2u)`. All order dependencies below matter. (`sim.jo:7`, `sim.jo:3335–3397`, `lib/core/math.jo:130–132`.)

### Orientation, authority, stalls and bank response

1. Start with old total speed `s = length(c.vel)` and
   `auth = clamp(s / (stall*1.45), 0.25, 1)`.
   Thus there is always at least 25% direct angular authority, even at zero speed.
   Turncoats multiplies authority separately; do not carry that bonus into normal flight.
   (`sim.jo:3338–3339`.)
2. Apply local quaternion increments **in order**: X pitch `P*pitch_rate*auth*h`,
   Z roll `−R*roll_rate*auth*h`, Y yaw `−Y*yaw_rate*auth*h`, each post-multiplied.
   There is no angular-velocity state for ordinary aircraft. (`sim.jo:3340–3343`.)
3. Rocketeer and cat alone auto-roll upright when roll input is zero, at a rate derived from
   `atan2(right.y,up.y)`, clamped bank correction and half roll rate. Ordinary planes do not
   get this unconditional physics assist. (`sim.jo:3344–3350`.)
4. From the rotated nose `f`, use old velocity direction `d=vel/s` if `s>0.1`, otherwise `f`.
   Compute `L=smoothstep(0.75*stall,1.15*stall,s)`. This is the model's “lift” factor.
   It is speed-only, not an aerodynamic coefficient. (`sim.jo:3351–3355`.)
5. When `L<1`, rotate nose toward `normalize(d+(0,−0.7,0))` about their cross product by
   `(1−L)*1.6*h` radians. This increment is world/pre-multiplied.
   `quat_axis_angle` normalizes the axis internally. (`sim.jo:3356–3358`,
   `lib/game/vmath.jo:325–328`.)
6. For ordinary winged kinds, `tilt=1−max(up.y,0)`; nose drops toward world down by
   `tilt*L*0.5*yaw_rate*h`. Then compute lateral wing-up component against the flattened
   forward direction and yaw toward the lower wing by `−lean*L*0.5*yaw_rate*h`.
   This explicitly adds bank-to-turn behavior and rudder-to-hold-height gameplay.
   (`sim.jo:3359–3372`.)
7. Normalize the resulting quaternion. Recompute forward and up for translation.    (`sim.jo:3373–3375`.)

The bank drop/turn and steering compensation are a matched set. Copying only one changes mouse
aim and bot behavior materially. These were added in separate playtest fixes, not present as a
full aerodynamic system from the beginning. (`sim.jo:3359–3372`, `sim.jo:5694–5698`; commits `82e703c`, `3b79f0b`.)

### Thrust, drag, gravity, velocity and altitude

Throttle integrates at `0.6*h` per held up/down step, clamped 0…1: full travel takes about 1.67 seconds. (`sim.jo:3376`.)

Engine factor `thin = clamp((CEILING+300−altitude)/600,0,1)`, with `CEILING=1600`.
Full power through 1,300 m, half at 1,600 m, zero at 1,900 m. This is absolute world height,
not clearance over ground. (`sim.jo:15`, `sim.jo:3379`.)

Let `p=abs(P)*auth`, using stick pitch, not measured load factor. Then:

```text
acc = thrust * throttle * thin - drag * s² * (1 + 0.9*p) - 9.8*d.y
s1  = max(s + acc*h, 0)
t   = min(grip * L * h, 1)
d1  = normalize(d + (forward - d)*t)
vel = d1*s1
level = max(up.y,0)
sag = 9.8*(1-L) + 9.8*L*(1-level)
vel.y -= sag*h
pos += vel*h
```

Source: `sim.jo:3377–3394`; the real thrust also multiplies `pull_of(g,i,c)`, whose only
non-unit values are Turncoats/last-stand bonuses (`sim.jo:612`, `sim.jo:531–556`).

Consequences: climbing costs longitudinal speed, diving gains it; hard pitch adds up to 90%
drag at ordinary full authority; stalled velocity hardly follows the nose; vertical wings
provide no modeled vertical support. There is **no** mass-dependent lift, sideslip force,
ground effect, or weather force in `fly_air`. (`sim.jo:3335–3394`.)

Rocketeer/cat replace sag with `2*(1−level)`, ignoring the speed-stall term in that final
vertical correction. They also have separate ground launch/bounce behavior. Exclude both from
seaplane handling. (`sim.jo:3390–3393`, `sim.jo:3407–3426`, `sim.jo:3540–3559`.)

### Exact winged-kind tuning

Rates are rad/s at full input/authority; thrust is acceleration m/s²; drag multiplies speed²;
grip is per second. These are kind differences, **not** different flight equations. (`sim.jo:638–664`, `sim.jo:668–698`.)

| Kind | stall | thrust | drag | pitch | roll | yaw | grip | hull | gear / tilt | mass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| Scout 0 | 24 | 17 | .0035 | 1.45 | 3.6 | .55 | 2.8 | 45 | 1.3 / .16 | 1 |
| Fighter 1 | 26 | 13 | .0042 | 1.15 | 2.6 | .45 | 2.4 | 100 | 1.6 / .17 | 1.3 |
| Light bomber 2 | 22 | 8.5 | .0048 | .55 | .9 | .3 | 1.6 | 600 | 2.6 / .08 | 5 |
| Ultra bomber 4 | 21 | 7 | .0055 | .32 | .5 | .2 | 1.3 | 2600 | 4.5 / .05 | 14 |
| Rocketeer 6 | 10 | 34 | .0045 | 2.4 | 5 | 1.2 | 4 | 12 | .95 / π/2 | .3 |
| Ornithopter 7 | 16 | 11 | .006 | 1.3 | 2.4 | .6 | 2.6 | 70 | 1.4 / .05 | .8 |
| Cat 10 | 10 | 122.5 | 122.5/455² | 7.9 | 15.75 | 4.55 | 12.25 | 21 | .3 / 0 | .15 |
| Drone 11 | 20 | 20 | .004 | 2 | 4 | .8 | 3 | 25 | .25 / .1 | .2 |

Per-row sources: scout/fighter `sim.jo:669–670`; bombers `671–677`; rocketeer/ornithopter
`683–685`; cat/drone `697–698`. Model choice by paint changes appearance, not these parameters (`models.jo:7168–7183`).

Calculated ideal straight-level full-throttle speeds `sqrt(thrust/drag)` are about 69.7 m/s
scout, 55.6 fighter, 42.1 light bomber, 35.7 ultra, 42.8 ornithopter. These are equation
equilibria with no turning/altitude loss, not measured cruise speeds. (`sim.jo:669–677`, `sim.jo:685`, `sim.jo:3381`.)

### Ground contact, takeoff, landing and water

Air contact triggers when `pos.y−gear < ground(x,z)` at the new position. It samples the
vehicle center/gear, not wheel/float points or a swept airframe. After >900 downed ticks the
winged path also calls touchdown for cleanup. (`sim.jo:3395–3397`.)

`touch_down(g,i,c,gy)` accepts a normal dry landing only when all are true:

- Not shot down; downward speed `sink=−vel.y < 4.5 m/s`.
- Total speed `< stall*1.9`; `up.y>.82`; `forward.y>−.25`.
- `gy>0`, `flatness>.93`, and horizontal forward length `>.1`.
  (`sim.jo:3427–3433`.)

Accepted landing sets `landed`, preserves horizontal speed along flattened nose, snaps yaw and
half parked tilt, and sets `pos.y=gy+gear`. It is an abrupt mode transition, not a suspension or bounced landing. (`sim.jo:3434–3445`.)

`roll_on_ground` integrates signed forward speed with:

```text
throttle += throttle_step*.6*h, clamped
brake = 4 if throttle_step<0 and throttle==0 else 0
acc = thrust*throttle*1.1 - drag*speed² - (.6+brake)*sign(speed)
speed += acc*h; clamp to [-2,1000]; snap near zero when throttle shut
turn = clamp((yaw_input+roll_input)/100,-1,1)*.7*min(1,abs(speed)/6+.25)
yaw -= turn*h
```

Source: `sim.jo:3487–3505`. It follows terrain height directly and raises the tail by
reducing parked tilt using `smoothstep(0,stall,speed)`. (`sim.jo:3506–3511`.)

Takeoff requires `speed>stall*1.12`, `Pad.pitch>10`, and `down==0`; it adds 1.5 m/s up and
sets nose-up pitch .12 rad. For a fighter, the speed threshold is 29.12 m/s (calculated). (`sim.jo:3508`, `sim.jo:3521–3524`, `sim.jo:670`.)

Ground roughness is `flatness<.9 OR gy<=0`. Rough ground or a building hit crashes the plane
above 9 m/s. Slow building contact reverts position and stops it. `bumped` checks building
rectangles using `0.8*half.z` as craft radius; craft/craft contact is handled later by `collide`.
The comment above `bumped` mentions craft, but its body only loops buildings. (`sim.jo:3512–3526`, `sim.jo:3528–3536`, `sim.jo:3813–3896`.)

**Water is not usable seaplane contact.** Gentle wet touchdown emits `DITCHED`, ejects all
occupants into `WALK`/swimming at y=−1.1, empties seats, stops the craft and sets `gone=WRECK/4`
(150 ticks = 2.5 s). Other wet contacts crash. There is no buoyancy, float drag, planing,
water rudder, spray wake, mooring, or takeoff run on water. (`sim.jo:10`, `sim.jo:3431–3461`, `sim.jo:3513–3516`.)

`ground` already clamps all submerged ground to sea level 0, `is_water` uses <=.05, and people
swim. Rendered water is at .3 m, so physical and visual surfaces differ. New water queries
should distinguish seabed, mean sea level, and wave surface. This is a recommendation.
(`world.jo:122–149`, `sim.jo:2517–2532`, `skybarons.jo:2412`.)

### Damage handling and other flight families

Ordinary planes have one hull counter; partial damage does **not** reduce thrust, authority,
grip, wing lift, or add imbalance. Below 65% they smoke, below 30% they burn visually; those
effects are not additional damage-over-time physics. (`sim.jo:4810–4849`, `sim.jo:3335–3397`, `skybarons.jo:2813–2816`.)

At zero hull, airborne craft set `down=1`. `fly` overrides input to pitch −40, roll ±100,
yaw 0, throttle −1. Although the comment says engine dead, the fixed-wing integrator still
computes thrust from the decaying throttle; it does not explicitly zero thrust on `down`.
Preserve or deliberately change this behavior, not the comment alone. (`sim.jo:3172–3175`, `sim.jo:3376–3381`, `sim.jo:4845–4849`.)

Helicopters (`hover`, `sim.jo:3564–3642`) use eased lean, +up thrust and gravity/velocity drag;
lean limit .62 rad, throttle changes 1.2/s, altitude fade as planes. Generic acceleration is
`up*lift+(0,−9.8,0)−vel*(drag+.004*speed)`. These are optional inspiration, not seaplane code. (`sim.jo:39–44`, `sim.jo:3580–3614`.)

| Helicopter kind | thrust / drag | pitch / roll / yaw | hull / mass | gear | specials |
|---|---|---|---|---:|---|
| Galleass 8 | 16 / .12 | .5 / .5 / .3 | 2200 / 24 | 26 | half side lean |
| Carcopter 9 | 15 / .1 | 1.3 / 1.3 / 1.1 | 260 / 3 | 1.63 | standard lean |
| Screw 12 | 16 / .55 | .35 / .35 / .3 | 700 / 10 | 3.05 | standard lean |
| Castle 13 | 12.2 / .35 | .15 / .15 / .08 | 120000 / 400 | 94 | tip .1; drive .45; inertial spin |
| Carrier 14 | 13 / .25 | .06 / .06 / .09 | 4500 / 150 | 30 | tip .12; drive 4; gasbag lift |

Sources: `sim.jo:691–703`, `sim.jo:710–742`, `sim.jo:190–195`, `sim.jo:293–295`.
Castle horizontal drag and turn inertia are explicit special cases, not general mass effects
(`sim.jo:3574–3579`, `sim.jo:3593–3602`). Carrier lift scales by bags remaining:
0/.3/.62/.86/1 for 0…4 bags (`sim.jo:4330–4335`, `sim.jo:3590–3591`).

Balloon `drift` follows altitude-dependent wind with .4/s horizontal easing and ±3.5 m/s
climb target; its up/down easing rate is .5. Zeppelin `float` targets 21*throttle m/s,
yaw .13 rad/s and ±6 m/s climb; it is not a fixed-wing plane.
(`sim.jo:750–752`, `sim.jo:3647–3675`, `sim.jo:3769–3808`.)

### Minimal transplant dependency list

Copy/adapt `Pad`, reduced `Kind`/`Craft`, `DT`, orientation helpers, `fly_air`, `steer`, and
selected ground functions. The integrator currently accepts `mut Game` and craft index only
to fetch kind/state, apply mode bonuses, write back, and call touchdown; it does not require
networking or model code. (`sim.jo:756–850`, `sim.jo:1390–1396`, `sim.jo:3335–3397`,
`sim.jo:5668–5699`.)

Replace `turncoat_flown`/`stand_of` with no bonus and `pull_of` with 1; specialize ordinary
plane branches; return vehicle state and contact/events instead of invoking the whole match
lifecycle. Supply `ground`/slope/water/contact adapters. For the existing dry rolling path,
also supply building collision or replace `bumped`. (`sim.jo:531–556`, `sim.jo:612`,
`sim.jo:3401–3536`.)

Do **not** copy all of `fly`: its boundary autopilot, respawning stands, scoring, weapon rules,
crew waits, automatic field repair, and special kinds make it much less self-contained than
`fly_air`. (`sim.jo:3138–3305`.)

## 3. Controls, camera and game feel

### Device input → aim → Pad → physics

| Action | Default keyboard / mouse behavior | Source |
|---|---|---|
| Pitch | W/up dives, S/down climbs; inversion setting reverses it | `skybarons.jo:113–114`, `skybarons.jo:138`, `skybarons.jo:1234–1236` |
| Roll | A/left and D/right | `skybarons.jo:115–116` |
| Rudder | Q/E; gamepad shoulder buttons | `skybarons.jo:117–118` |
| Throttle | Shift raises, Z lowers; touch slider target; wheel/power controls also exist for helicopters | `skybarons.jo:119–120`, `skybarons.jo:1239–1248`, `skybarons.jo:1295–1301` |
| Guns / rocket / bomb | Space or left mouse / X or right mouse / B or middle mouse | `skybarons.jo:122–124`, `skybarons.jo:1220–1233` |
| Enter / leave | F / T; numbered seats, V next seat; U stand on a supported deck | `skybarons.jo:125–135`, `skybarons.jo:1191–1204`, `skybarons.jo:1501–1511` |
| Look / cycle target | C toggles target tracking, Tab cycles targets | `skybarons.jo:130–131`, `skybarons.jo:1372–1378` |
| On foot | WASD relative to look; Shift run, Z jump, Space/left mouse pistol | `skybarons.jo:1205–1215` |

Input actions also bind sticks/buttons; the generated `Pad` quantizes axes to integer hundredths
and world aim to milliradians. These are networking-oriented encodings, but they keep human and
bot control paths identical. (`skybarons.jo:113–135`, `skybarons.jo:1170–1175`,
`skybarons.jo:1302–1305`, `sim.jo:756–777`.)

Locked mouse delta changes aim by .0025 radians per reported unit; touch drag uses .006.
Nonpilots' right stick adds `2.2*dt`; pitch clamps to ±1.45 rad; scope sensitivity is ×.25.
`aim_dir` converts yaw/pitch to world forward. (`skybarons.jo:1015–1020`,
`skybarons.jo:1515–1525`.)

Mouse flight is **direction-seeking**: `steer(c,aim_dir())` generates pitch/roll/rudder.
Keyboard/stick axes override corresponding aim-derived axes while held. While keys fly, the
aim follows the nose; after release the mouse retains the direction then flown and the steering
levels the wings. It is not a virtual joystick displaced from the screen center.
(`skybarons.jo:1067–1073`, `skybarons.jo:1284–1289`, `skybarons.jo:1512–1514`,
`skybarons.jo:1536–1541`; hard-won fix `903b89a`.)

On the ground, mouse aim supplies rudder toward the flattened aim direction; aim.y>.1 supplies
full climb if the pitch keys are neutral. Actual takeoff remains speed-gated in physics.
(`skybarons.jo:1290–1294`, `sim.jo:3508–3524`.)

Control smoothing is `stick=approach(stick,want,30,DT)` under aim steering, otherwise rate 9.
This is exponential easing, `target+(current−target)*exp(−rate*dt)`, **not** a fixed linear
slew-rate limit. The smoothed vector is quantized into the pad.
(`skybarons.jo:1302–1305`, `lib/game/gameutil.jo:117–119`.)

### Assists: distinguish what actually changes flight

- Mouse `steer` supplies roll leveling near aim and compensating skyward rudder in a bank.
  This is the primary ordinary-plane assist. (`sim.jo:5678–5698`.)
- Ordinary keyboard-only aircraft do not automatically level themselves with released roll.
  Rocketeer/cat do; helicopter lean also eases back to zero. (`sim.jo:3344–3350`,
  `sim.jo:3580–3585`.)
- Boundary assist takes over pitch/roll/yaw beyond the arena edge, turning toward the center
  with an altitude bias. Remove it for an archipelago. (`sim.jo:3176–3183`,
  `world.jo:151–160`.)
- Target C-look changes the camera, not bullet direction or a magical gun lock. Guns fire along
  nose or gun aim; HUD shows a predictive lead ring. There is no ordinary bullet bending.
  (`skybarons.jo:1819–1863`, `skybarons.jo:3680–3682`, `sim.jo:3204–3230`.)
- Target selection prefers distance and forward position. In global “plain/no markers” mode,
  it permits only a visible on-screen craft within 1,500 m, with sampled terrain and cloud
  ellipsoid occlusion. This visibility restriction is a HUD feature, not the bots' general
  perception model. (`skybarons.jo:1317–1378`, `sim.jo:5733–5777`.)
- Scoped ornithopter is an exceptionally fast projectile (12,000 m/s), not a hitscan API;
  physics still segment-tests it. Do not mistake its ease of aim for general aim assist.
  (`sim.jo:104–108`, `sim.jo:3223–3229`, `sim.jo:4932–4949`.)

Helicopter player controls are higher-level than plane controls: WASD requests velocity,
Shift/Z climb/sink, power sets maximum rates, released climb holds an altitude. With mouse look,
movement is relative to the view; nose normally stays put except during firing/throwing, or
always follows look if the setting enables it. (`skybarons.jo:1239–1278`,
`sim.jo:6187–6229`; commits `427c45d`, `d50d53f`.)

### Camera pieces worth extracting

`place_camera` is a state dispatcher: dead/killer view, ground gun, walking/falling/chute,
hook-carried aircraft, gunner, scope, or normal chase. Reuse its ordinary branches, not its
full dependence on all match state. (`skybarons.jo:1724–1864`.)

Chase orientation uses `slerp(cam_q,c.rot,1−exp(−6*dt))`; desired camera is behind/up in that
smoothed frame, aiming about 30 m ahead. Scout/fighter baseline is 15 m back / 4.2 up; bomber
38/9, ultra 75/16, zeppelin 110/26. Distances are tuned by vehicle silhouette, not velocity.
(`skybarons.jo:1620–1634`, `skybarons.jo:1821–1833`.)

`settings.level` constructs a horizon-level up vector from forward and a retained right-vector
fallback, so the plane can bank while the horizon stays stable. It is a camera preference,
not a control/flight change. (`skybarons.jo:146`, `skybarons.jo:1834–1841`; `0687e1c`.)

Under mouse steering, a rate-5 blend shifts the camera behind the world aim direction and
levels the camera; aim itself eases at rate 25. Target tracking blends at rate 8 to a camera
behind the craft relative to the target and looks at the target. This is the main flying
presentation feel to preserve while retuning seaplane framing.
(`skybarons.jo:1822–1823`, `skybarons.jo:1842–1849`, `skybarons.jo:1859–1863`.)

FOV is 65° in landscape, with portrait adjustment
`2*atan(tan(32.5°)/sqrt(aspect))`; ornithopter scope is 14°. There is no speed-based FOV
increase in this function. (`skybarons.jo:1613–1617`.)

`finish_camera` clamps the camera above terrain/sea+1 m and handles nearly parallel view/up
vectors by projecting a craft-forward or world-axis hint. This prevents blank views while
looking almost straight up/down. Camera near/far are .5/7,000 m.
(`skybarons.jo:1884–1908`; `903b89a`.)

It does not perform general building-wall camera collision. For towns, add a sphere cast/pull-in
or equivalent; the public `FollowCamera` and physics queries support that pattern.
(`skybarons.jo:1886–1908`, `docs/API.md:3789–3825`, `docs/API.md:5255–5258`.)

Foot camera: shoulder offset .7 m right, 4.5 m back and 1.9 m up; falling/chute uses 9 m back,
chute 2 m up. Rate-14 position easing. On a moving deck it eases a craft-relative offset,
avoiding lagging behind the entire moving craft. (`skybarons.jo:1768–1789`.)

Gunner eyes are moved toward/past the muzzle to clear hulls; selected own-body/rotor/prop parts
are faded or hidden per seat. Those are useful cockpit visibility ideas, not a ready seaplane
cockpit. (`skybarons.jo:1801–1810`, `skybarons.jo:1867–1877`,
`skybarons.jo:2236–2256`; `49c5da8`, `903b89a`.)

Kill camera runs up to 3.5 s inside recovery time, can be disabled/skipped, and now selects
an orbit or flyby shot with a hard initial cut. Good cinematic reference; omit from the first
sandbox milestone. (`skybarons.jo:1636–1748`; `5d0f662`, `78afd91`, `17537db`.)

### HUD and sensory feedback

The pilot's instruments show speed as `length(vel)*3.6` km/h, **height above terrain** (not
barometric sea-level altitude), stall-sensitive airspeed color, and throttle/power lever.
Their “airspeed” is world velocity, because winged flight has no wind-relative airspeed.
(`skybarons.jo:3901–3930`, `sim.jo:3338–3381`.)

Other reusable HUD concepts: nose gunsight at 300 m; separate mouse aim ring at 400 m; lead ring
for target motion/drop; bomb fall estimate; hull/heat/ammo plate; seat list; context prompts;
on-foot crosshair; off-screen target arrows. (`skybarons.jo:3680–3694`,
`skybarons.jo:3752–3791`, `skybarons.jo:3834–3837`, `skybarons.jo:3934–4038`,
`skybarons.jo:4389–4418`, `skybarons.jo:5005–5015`.)

Context prompts fade after 5 s over 1.5 s, but stay for urgent falling/downed situations.
Labels prioritize selected target, then nearest, and reject overlaps. Keep these policies for
harbor labels and interaction prompts. (`skybarons.jo:3620–3683`,
`skybarons.jo:3895–3899`, `skybarons.jo:4389–4405`; `0116747`, `1f0021f`.)

Shake perturbs look-at, with amplitude `shake²*.035*view_distance`; shake decays 2.2/s.
Near hostile bullet segments within 8 m trigger .2/.35 shake and a crack at most every .08 s.
Own long gun sets shake=1; nearby flak/large impacts contribute distance-based kicks.
(`skybarons.jo:1902–1907`, `skybarons.jo:2766–2772`, `skybarons.jo:2931–2939`,
`skybarons.jo:3214–3218`, `skybarons.jo:3281–3299`.)

Particles/audio are presentation events, separate from damage. Thunderdome's extra flak curtain
is explicitly cosmetic; damage comes from sim shots. This separation lets a future storm/spray
effect be rich without making visual particle density affect simulation.
(`skybarons.jo:2752–2756`, `skybarons.jo:3237–3279`.)

### Sound synthesis and mixing

There are no loaded engine/weapon sound assets in this subsystem: tones/noise are mixed into
`Sound` values. Engine = saw 55 Hz + square 110 Hz + quiet high-rate noise; wind uses
`HISS=MIX_RATE/16`. Gun, hits, explosions, flak, pistol, chute, cannon, machinery and pedals
have separate synthesized cues. (`skybarons.jo:3328–3392`.)

`sounds()` keeps eight looping engine voices, selecting nearest aircraft and prioritizing
the player's. Local engine is centered at reduced volume; others use spatial `move_sound`.
Pitch combines craft-specific base, `.45*throttle`, and `speed/200`; wind rises above 30 m/s
and is capped by 80 m/s, plus a falling cue. (`skybarons.jo:3393–3440`,
`skybarons.jo:3535–3540`.)

Shot sounds are inferred from monotonically counted shots/cooldown increases between frames;
booms trigger other one-shots. This avoids playing each gun event again after rollback but
is not a general reliable audio event bus. (`skybarons.jo:2870–2879`,
`skybarons.jo:3479–3534`.)

Reuse the mix/voice-selection pattern and positional API. Retune the seaplane motor, water
wash, wind, footsteps and settlement ambience as new content. The historical wind fix changed
noise generation when pitched noise became a loud low whoosh; loud crashes were also reduced.
(`skybarons.jo:3328–3331`, `skybarons.jo:3406–3440`; `fd4f2c0`, `f57f616`.)

## 4. Combat and NPC pilots

### Ordinary guns and projectiles

Base bullet: 380 m/s relative to firer, 75 ticks life (1.25 s), 7 damage; gravity 9.8 m/s².
The nominal relative range is 475 m (calculated), plus inherited craft motion and drop.
Pilot muzzle alternates guns; deterministic scatter is ±.004 in right/up components before
normalization. (`sim.jo:11–14`, `sim.jo:3204–3235`, `sim.jo:4923–4930`.)

| Ordinary kind | Cadence / heat behavior | Source |
|---|---|---|
| Scout | every 4 ticks, +5 heat/shot | `sim.jo:669` |
| Fighter in Classic | every 4 ticks, +9 heat/shot | `sim.jo:670`, `sim.jo:3211–3234` |
| Fighter outside Classic | three alternating mounts, gaps 3,3,2 ticks; heat +6 each | `sim.jo:3209–3234` |
| Ornithopter unscoped | every 6 ticks, +9 heat | `sim.jo:685`, `sim.jo:3232–3234` |
| Ordinary crew machine gun | every 6 ticks, +6 heat; aims within seat cone | `sim.jo:4052–4062`, `sim.jo:4105–4108` |

Pilot heat cools one/tick; at 300 it jams until heat<120. Gunners use a simpler `heat<300`
fire gate with cooling, not the pilot's `jammed` hysteresis flag. No ammunition depletion for
ordinary pilot machine guns; finite ordnance is separate. (`sim.jo:3193–3196`,
`sim.jo:3232–3235`, `sim.jo:4060–4062`, `sim.jo:4105–4108`.)

Lead helper `lead_from(at,v,e,ev,speed)` starts `t=distance/speed`, refines twice with relative
velocity, and returns `relative_position+(ev−v)*t+(0,4.9*t²,0)`. It is an iterative intercept
estimate with drop compensation, not an exact quadratic ballistic solve.
(`sim.jo:4655–4662`.)

Rocket launch inherits velocity +60 m/s forward; then accelerates 120 m/s² up to 240 m/s,
with 2 m/s² downward drift. Life 240 ticks; proximity radius normally 3 m; blast radius 14 m,
max damage 55. (`sim.jo:3246–3258`, `sim.jo:5075–5078`,
`sim.jo:5094–5095`, `sim.jo:5138–5141`.)

Bombs inherit .95*craft velocity, fall under gravity, receive .02/s velocity damping, and
burst with 30 m radius / 170 max damage. Initial life is 40 seconds, but bomb expiration alone
does not trigger the generic timed burst branch. (`sim.jo:3260–3267`,
`sim.jo:5079–5082`, `sim.jo:5138–5141`.)

Keep pirate/bounty combat initially to ordinary bullets, maybe bombs. Fantasy weapons add
extensive per-kind fields and exceptions: ballista, near-hits from the long gun, homing healing
packs, drone launch/ram, boulders, Greek fire, broadside batteries and bombard shockwaves.
Their definitions are mapped at `sim.jo:51–227`, firing at `sim.jo:3967–4260`,
and flight/damage at `sim.jo:5041–5170`.

### Hit detection and damage limits

`seg_near(a,b,r)` computes closest segment point to origin. `hits_craft` broad-phases a sphere,
then transforms bullet endpoints into craft space, allowing translation from previous to current
craft position, divides by ellipsoid half-extents, and segment-tests the unit sphere.
It uses current orientation for both endpoints, so rotational sweep is approximate.
(`sim.jo:4680–4702`.)

Aircraft are not hit against rendered triangles. Castle uses layered oval solids, carrier uses
boxes/gasbag spheres, everything else generally one ellipsoid. Reuse the ordinary branch;
choose consistent float/wing extents for new seaplanes. (`sim.jo:4693–4780`.)

`shoot` precomputes team/open/radius/occupied projections, then integrates each bullet, checks
craft, people/chutes, balls, buildings, and terrain. It consumes the bullet on the first craft
by array iteration that tests true, not a globally nearest intersection parameter.
(`sim.jo:4904–4987`.)

Terrain impact is an endpoint height check below the code's 700 m shortcut; building checks
are also height-gated. Those bounds fit these maps and must be revisited for taller islands or
very fast shots. `building_hit` returns the first intersecting oriented box by list order.
(`sim.jo:4974–4985`, `sim.jo:5001–5028`.)

Buildings use oriented boxes; blasts use distance to craft approximate surface / building box
and linearly decrease damage to zero at blast radius. Blasts do not ray-test occlusion, so
walls do not shield from blast in this implementation. (`sim.jo:5001–5037`,
`sim.jo:5145–5170`.)

Friendly fire gates damage through `harms`. Crewed friendly craft can be passed through by
bullets; empty friendly craft do not get that same early pass-through test, though damage still
checks friendliness. Paint and actual crew are distinct. (`sim.jo:1435`,
`sim.jo:4913–4919`, `sim.jo:4941–4952`, `sim.jo:4810–4814`.)

`hurt_person` has no health meter: damage>=20 kills, otherwise a deterministic one-in-three
hash condition kills. Sniper crew hit checks can directly kill seated people; ordinary guns
generally harm craft instead. Replace this if inhabitants need injuries/survival states.
(`sim.jo:4871–4874`, `sim.jo:4990–4998`.)

Aircraft collision: X-sorted broad phase, sphere reject, five sample points from each body
against the other's approximate surface. Air damage is
`relative_speed*6*clamp(other_mass/own_mass,.15,6)` (castle raises max ratio to 40).
Knock cooldown 30 ticks; ground aircraft stop/ease apart without this damage.
(`sim.jo:3813–3896`, `sim.jo:3940–3944`.)

This is forgiving crowded-airfield behavior, not harbor collision physics. Also, airborne
`fly_air` only queries terrain contact, and `collide` only craft: there is no general plane
versus town-building/trees collision stage. `bumped` checks buildings only while rolling.
(`sim.jo:3394–3397`, `sim.jo:3529–3536`, `sim.jo:3813–3826`.)

### Bot decision flow and steering mathematics

Bots are layered priority decisions returning `Pad`, not a named combat-state enum. Persistent
pieces are craft target/wait/rest and person physical state. `bot_pad` selects walking,
falling, gunning or flying; it also bails from downed winged craft above 60 m after a skill
dependent delay. (`sim.jo:812–818`, `sim.jo:5831–5856`.)

`choose_targets` refreshes valid targets every 90 ticks, staggered by craft ID, or immediately
when invalid. Score = distance*(2−forward_alignment), previous target ×.7; fighters prefer
large craft ×.6, drones ×2.5, screws ×2; modes add other weights. It scans `g.air`, not a
general sensory memory. (`sim.jo:5731–5777`.)

`steer(c,want)` is the most useful general NPC/mouse helper (`sim.jo:5663–5699`):

```text
l = inverse_rotation * normalize(want)       # desired direction in aircraft frame
ahead = -l.z; a=max(ahead,.1); rate=6
near_pitch = clamp(l.y/a*rate/max(pitch_rate,.1), -1,1)
near_yaw   = clamp(l.x/a*rate/max(yaw_rate,.1)*.4, -1,1)
near_roll  = clamp((right.y*1.6+l.x/a*4)*2.6/max(roll_rate,.1), -1,1)
err = atan2(l.x,l.y); off=acos(clamp(ahead,-1,1))
far_roll = clamp(err*2*min(1,3.6/roll_rate), -1,1)
far_pitch = (clamp(off*3,0,1) if abs(err)<1.2 else .2)*min(1,2.4/pitch_rate)
blend = smoothstep(.94,.995,ahead)
```

Here the rate denominators in far controls also use the guarded `rr/pr` values. If aim is a
little below and mostly not sideways, blend is raised using smoothstep(.7,.85,ahead), avoiding
an unnecessary inverted roll. It blends far roll-and-pull with near corrections, then adds
bank-compensating rudder. (`sim.jo:5675–5698`.)

`bot_fly` priorities: downed → crew-call wait → carrier recovery → mode jobs → helicopter →
ground takeoff → kind-specific airborne bot. Ground AI waits for nearby players up to 15 s,
taxies from parking, steers around static craft, yields to moving craft, uses three takeoff
lanes and pulls up only aligned/fast enough. (`sim.jo:5951–6028`.)

`bot_fighter` prioritizes low terrain avoidance (130 m current clearance or four-second
prediction within 100 m), mission-specific low runs, close-and-closing breakaway, led enemy
aim, flag/prey/ground attack, otherwise returns toward center at 500 m. Skill scales pitch
and adds deterministic aim error. (`sim.jo:6808–6939`.)

If slow (<1.3*stall), positive pitch is capped at 15; default full throttle, reducing it when
close behind a slower target. Fire requires range<480 m and alignment near .9995 (looser at
low skill), and heat<270. Rockets target large craft closer in. These are explicit gameplay
choices rather than flight expertise. (`sim.jo:6940–6972`.)

`avoid` scans airborne craft within 400 m, computes closing speed and reach
`own_radius+other_radius+25+1.3*max(closing,0)`, predicts relative position up to 1.5 s,
then adds weighted away and vertical separation vectors. It is local avoidance, not pathfinding
through islands or towns. (`sim.jo:6974–6994`.)

`bot_bomber` demonstrates civilian cruise-like direction/altitude control: goal vector with
vertical correction clamped ±.25, desired altitude at least terrain+220, pitch scale .7.
But its destination is enemy target/field and it has no ordinary field-landing procedure.
(`sim.jo:7030–7068`.)

`bot_recover` is a useful approach-pattern reference: align behind a moving carrier window,
approach from ~650 m behind, control closing speed, floor target speed at 1.15*stall.
Actual recovery is an instantaneous carrier catch/hoist, **not** water touchdown or runway flare.
(`sim.jo:6454–6479`, `sim.jo:4397–4429`, `sim.jo:4454–4495`.)

Crew gunners acquire within their cone, refine lead with skill wobble, ease aim, and only fire
when aligned. Generic target refresh every four ticks. Gun limits are enforced in both input
and simulation. Only selected ground gun behavior uses terrain line-of-sight; do not assume all
airborne AI respects islands/clouds. (`sim.jo:3967–4062`, `sim.jo:5174–5180`,
`sim.jo:5210–5222`, `skybarons.jo:1041–1059`.)

Reusable for civilian pilots: `steer`, `avoid`, reduced cruise altitude logic and speed feedback,
taxi/yield ideas, and approach alignment. New code must supply job/route state, waypoint passage,
arrival/departure scheduling, safe terrain lookahead, wind-aware water approach, flare, floating,
taxi-to-dock and retry/go-around. This is an extraction recommendation, not an existing AI mode.
(`sim.jo:5668–5708`, `sim.jo:5951–6028`, `sim.jo:6454–6479`, `sim.jo:6975–6994`,
`sim.jo:7030–7068`.)

### Bailouts and parachutes

`bail_out` frees seat, places person at seat+1.5 m up, gives craft velocity plus 4 m/s craft-up,
sets `FALL`, remembers departed craft, and emits `BAILED`. Chute opens automatically after
75 ticks, or T after >10 ticks, unless torn. (`sim.jo:3025–3041`, `sim.jo:2425–2442`.)

Freefall applies gravity and .15/s damping. Chute eases vertical speed to −9 m/s at rate 6,
up to −18 m/s with forward/dive input, damps horizontal speed at 1.2/s, and permits limited
forward steering. Unchuted landing speed>14 m/s kills. Chute sphere hit at person+(0,6.5,0),
radius 3.5, switches back to torn freefall. (`sim.jo:2148`, `sim.jo:2443–2491`,
`sim.jo:4955–4966`.)

Falling people can automatically enter nearby free aircraft seats or land on supported decks;
their recently departed craft is excluded temporarily. Useful later for rescue/adventure, but
automatic boarding should be reconsidered for civilian interaction expectations.
(`sim.jo:2458–2481`, `sim.jo:2921–2981`, `sim.jo:2130–2142`.)

## 5. On-foot movement and entering/leaving vehicles

Person states are `WALK`, `SEATED`, `FALL`, `CHUTE`, `DEAD`, `POST`. Swimming is a wet branch
inside `WALK`, not another state; deck walking is `WALK` with `craft>=0`.
(`sim.jo:866–903`, `sim.jo:2508–2532`.)

Ground walking builds forward/right vectors from world aim yaw; normalized input prevents faster
diagonals. Speeds: walk 5.5 m/s, run 10, swim 1.8; bot speeds vary deterministically ×.75…1.20.
Horizontal velocity eases at rate 12. (`sim.jo:2145–2147`, `sim.jo:2511–2525`.)

Movement rejects uphill steps where terrain normal-y<=.55; downhill is allowed. This samples a
heightfield, not a capsule sweep. `out_of_buildings` pushes out of building XZ boxes with .5 m
radius, excluding AA/masts/targets; it does not use village mesh triangles.
(`sim.jo:2526–2529`, `sim.jo:3115–3127`, `world.jo:512–546`.)

Jump speed 4.6 m/s, gravity 9.8, only when on dry ground and vertical speed<=0. Current grounded
test allows a held jump to trigger again once grounded; it prevents jumping again in mid-air.
Wet movement sets y=−1.1 and vertical speed zero. There is no drowning/oxygen, shore animation,
or water-current force in this branch. (`sim.jo:1893`, `sim.jo:2521–2545`,
`tests/t/skybarons_foot.jo:19–29`.)

F boarding scans whole landed craft moving <=3 m/s, with a free seat within 8 m. Larger craft
have ladder/gate shortcuts. `get_in` prioritizes pilot seat, then nearest gunner, then hooks;
it updates both person and craft occupant slots and emits `BOARDED`.
(`sim.jo:2149`, `sim.jo:2823–2864`.)

T from grounded craft below 4 m/s calls `get_out`; otherwise it bails. `get_out` places the
person to the aircraft's left, samples terrain for the exit Y, frees the seat, sets WALK and
clears craft/seat. It has no dock/shore selection or safe-exit obstacle search.
(`sim.jo:2407–2413`, `sim.jo:3006–3022`.)

For seaplanes, changing `landed` to include floating is not enough: define a safe disembark point
on a nearby dock/shore, and boarding reach from dock to aircraft rather than clamped sea floor.
Otherwise existing exit code puts people into the water. This is a recommendation from those
exit/terrain assumptions. (`sim.jo:3011–3019`, `world.jo:123–139`.)

Numbered seat changes can move friendly bots aside or eject them; G can expel friendly crew;
F held in the application can trigger that same kick behavior. Those multiplayer convenience
policies should not silently govern persistent NPC passengers. (`skybarons.jo:1182–1185`,
`sim.jo:2376–2387`, `sim.jo:2868–2905`, `sim.jo:2983–2989`.)

U deck walking transforms desired world movement into craft-local XZ, maintains `deck` and
`step`, integrates gravity locally, resolves each X/Z movement separately against deck solids,
steps up .6 m, and falls if floor is >4 m below. World pos is recomputed after craft movement.
(`sim.jo:1892–1895`, `sim.jo:2596–2645`, `sim.jo:1492–1495`.)

`deck_floor` chooses highest eligible surface no more than a step above feet; `deck_blocked`
tests obstacles against person height 1.7 m. Deck surfaces are manually modeled boxes, slopes,
ellipses, and special hull/terrace curves. They are separate from visual mesh geometry.
(`sim.jo:1997–2079`.)

This is a good template for walking on boats or large docks, but **not** a complete enterable
town. The visual houses are solid shapes and doors are painted geometry; general interiors,
doors, room navigation and NPC pathfinding are new work. Public `physics3d.character` offers
capsule steps/slopes/walls and moving-platform support if that is preferable to extending the
handwritten controller. (`models.jo:2731–2752`, `models.jo:5730–5740`,
`world.jo:541–546`, `docs/API.md:5260–5280`.)

On-foot animation draws body plus four rigid limbs with speed-based phase/stride and stronger
run swing; deck-relative speed is used aboard moving craft. No skeleton or inverse kinematics
is needed for this cheap baseline. (`skybarons.jo:2217–2232`, `models.jo:988–1027`.)

`bot_walk` heads directly to a scored aircraft seat, with local side-stepping and a special
building-avoidance lookahead for castle/carrier gates. It is not a navigation mesh or village
pedestrian planner. People stranded far away can use match “leave” to teleport/respawn; remove
that shortcut for persistent inhabitants. (`sim.jo:5872–5944`, `sim.jo:2578–2588`.)

## 6. World, procedural models and rendering

### Terrain, water, clouds and lighting

World is a fixed 6,400 m square with 128×128 cells, 50 m spacing, and 129² cached f64 corner
heights. Farmland is summed sines, river depression and raised mountain rim; Gorge is a winding
river floor and steep blended plateaus. No imported heightmap, streaming or editable island
database exists. (`world.jo:9–11`, `world.jo:75–118`.)

Airfields flatten the procedural heights with smooth margins. `ground` uses piecewise planar
interpolation on the **same diagonal** as `make_ground`'s triangles, then clamps to zero.
Keep this collision/render agreement; do not substitute bilinear interpolation over the same
vertices. `flatness` finite-differences height over ±2 m; wet is considered flat.
(`world.jo:97–149`, `world.jo:477–498`.)

`make_ground` emits 32,768 flat-shaded terrain triangles (calculated: 128²×2), plus airfield
boards. Colors depend on strip, height, slope, woods and hashed agricultural patches. This is
cheap aerial scenery; a 50 m grid cannot express a walkable quay, narrow beach or town steps.
(`world.jo:463–508`.)

Water is one `plane_mesh(MAP)`, translated to y=.3, opaque blue-gray, specular .8, no shadow
casting. It has no wave displacement, animated normal, shoreline foam, reflection/refraction,
depth color or wakes. Simulation sea surface is zero, not .3. (`skybarons.jo:1946`,
`skybarons.jo:2412`, `world.jo:123–139`.)

Clouds: 55 clusters ×6 ellipsoidal puffs, deterministically placed within ±2,500 m, base
520…819 m (+250 in Gorge); each puff radius 25…49 m with anisotropic scaling. Persistent GPU
instances of a 10×6 sphere, white/emissive .35, opaque and non-shadow-casting. They never move;
their ellipsoids also hide HUD target locks in plain mode. (`world.jo:566–581`,
`skybarons.jo:1948`, `skybarons.jo:2415`, `skybarons.jo:1331–1352`.)

Trees are three hashed candidates per wooded 50 m cell, rejected near airfields, water, steep
ground and high farmland. One six-sided cone mesh is scaled per tree and instanced. No tree
trunk/canopy species, foliage animation or tree collision is supplied here.
(`world.jo:441–452`, `world.jo:549–564`, `skybarons.jo:1947`, `skybarons.jo:2414`.)

Every frame fixes sun direction (−.4,.8,.45), warm sun color, blue top/gray horizon/green-gray
ground sky, fog (.74,.8,.88) with density .00025 / height falloff .0015, shadows strength .6
/ area40, bloom .4 / threshold .8 / vignette .3 / saturation1.05. No time-of-day/weather update
changes these values. (`skybarons.jo:2405–2415`.)

Stock shadow implementation is a **single** orthographic map around camera target, bounds
±area, 2048² GPU /512² software, not cascaded world shadows. With area40, that projection spans
80 m across. Increasing area trades texel detail for reach; do not assume island-wide detail.
(`lib/game/draw3d.jo:717–737`.)

### Model construction and useful builders

Models are baked vertex-color triangles, mostly duplicated per face for flat normals, not
loaded assets. `quad`/`tri` orient normals away from an interior hint; `plate` extrudes polygon
pieces; `loft` connects rectangular fuselage sections; `lathe` connects radial profiles; `beam`
and `tube` make rods/rigging. (`models.jo:102–148`, `models.jo:535–598`.)

`Wing` stores root height, span stations `(x,leading_z,chord,thickness)`, a section polygon and
dihedral. `add_wing` lofts both halves and closes tips; `wing_surface` locates decals on actual
wing faces. Insignia are extra triangles clipped/subdivided across surface bends, not textures.
(`models.jo:150–435`, `models.jo:632–707`.)

| Builder / range | Reuse value and limitation |
|---|---|
| `loft`, `quad`, `ring_at`, `plate` — `models.jo:105–148` | Small self-contained geometry foundation; good starting point for fuselage/float profiles. |
| `v3`, `shade`, `tri`, `beam`, `tube`, `wheel`, `lathe`, `disc` — `models.jo:535–598` | General primitive toolkit for hulls, rigging, piers, tanks, props; guard degenerate zero-length rods when adapting. |
| `Wing`, `wing_section`, `add_wing`, `station_at`, `wing_surface` — `models.jo:632–687` | Most valuable aircraft geometry abstraction; decouple from military markings. |
| `cockpit`, `undercarriage` — `models.jo:758–769` | Pilot/windscreen placeholder; wheels explicitly need replacing with floats or a boat hull. |
| `make_biplane` / `make_triplane` — `models.jo:454–531` | Compact fighter geometry; includes gun mounts, wheels and military paint. |
| `make_parasol` / `make_sesquiplane` — `models.jo:836–934` | More shaped scout wings, bracing and airfoils; suitable visual scaffolds for a new floatplane. |
| `make_fighter` — `models.jo:944–951` | Wraps those older fighter builders plus rocket tubes; omit rocket additions for civilian craft. |
| `make_prop`, `make_turret` — `models.jo:954–987` | Separate rotating propeller and gun geometry; public `prop_mesh` caches them (`models.jo:7229–7230`). |
| `make_person`, `person_part` — `models.jo:988–1027` | Cheap rigid-part people; change clothing/palette for civilians. |
| `make_muromets`, `make_gotha` — `models.jo:1071–1127`, `models.jo:1164–1212` | Larger aircraft examples: engines, braced wings, crew pits; not seaplane models. |
| `make_zeppelin` — `models.jo:1282–1343` | Large airship hull, seams and mounted detail; optional late-world content. |
| Ultra aircraft builders — `models.jo:1357–1753` | Extensive fantasy-scale multipart bomber detail; little first-milestone value. |
| `make_parachute`, rocket/bomb — `models.jo:2657–2710` | Cheap adventure/combat effects geometry. |
| `house`, `window_at` — `models.jo:2731–2752` | Parameterized roof/wall/window shell; windows/doors are surface decoration, not openings. |
| `make_hangar`, `make_tank`, `make_hq` — `models.jo:2756–2832` | Harbor workshop/fuel/storehouse starting assets after reskinning; no business/interior logic. |
| `make_mast`, `crates`, `make_depot`, `make_factory` — `models.jo:3008–3100` | Cargo, warehouse and industrial-detail kit; depot includes military shells/sandbags to remove. |
| `make_wreck` — `models.jo:3111–3151` | Burnt aircraft debris; independent presentation asset. |
| `dv_half/top/keel/hull_at` — `models.jo:3179–3218` | Actual ship-shaped section/hull math; promising boat-builder source, but tuned to a huge flying galley. |
| Hull/deck part of `make_davinci` — `models.jo:3521–3577` | Planked hull/bulwark/deck; extract before towers, engines, weapons and rowers. Not an operational watercraft. |
| `ca_rock` — `models.jo:5559–5564` | Faceted hanging rock geometry example, depends on `ca_under_y` (`models.jo:5546–5558`); not terrain collision or an island generator. |
| `ca_tower`, `ca_square`, `ca_hall`, `ca_house`, `ca_houses` — `models.jo:5651–5813` | More detailed stone town/roof kit and terrace placement. Walls are not enterable; castle-specific helpers/palettes need pruning. |
| `fk_arch`, `fk_lantern`, `fk_lamp_post`, `fk_festoon`, `fk_balustrade` — `models.jo:6665–6708` | Attractive architectural/harbor detail helpers; lantern geometry does not itself create a point light. |
| `craft_vertices`, `craft_mesh`, `_once` — `models.jo:7168–7227` | Dispatch and lazy GPU mesh caching patterns; rebuild cache keys around new vehicle identities/variants. |

No float-equipped aircraft builder or ordinary boat entity appears in the audited kind dispatch.
The galleass is ship-shaped **flying** content, not a ready watercraft. A seaplane needs new
float/boat-hull geometry and physical contact data. (`models.jo:7168–7183`,
`sim.jo:691–693`, `sim.jo:3564–3642`.)

### Draw calls, instancing, LOD and size limits

Scenery generation is lazy/cached; terrain and villages each become a merged mesh; trees/clouds
are uploaded once via `instance_buffer`. Animated props/guns/person limbs are separate draws;
tracer/fire/grape groups and some mechanical crews are dynamically instanced.
(`skybarons.jo:1942–1977`, `skybarons.jo:2217–2232`, `skybarons.jo:2634–2654`,
`skybarons.jo:2691–2737`, `models.jo:4023–4044`.)

There is no game-level terrain LOD, aircraft mesh LOD or streamed chunk system in these paths.
The stock renderer does sphere/frustum culling of ordinary mesh submissions, but explicitly
accepts **all instanced draws** without that test. Whole-world tree/cloud buffers are therefore
not a scalable visibility strategy for an expanded archipelago. (`skybarons.jo:2400–2415`,
`skybarons.jo:2468–2508`, `lib/game/draw3d.jo:748–764`, `lib/game/draw3d.jo:831–838`.)

Arena flight turns back outside radius2,200 m in Farmland or ±1,500/±2,700 m in Gorge.
Height lookup clamps corner indices outside ±3,200 m, extending edge values rather than
generating more world. Camera far is 7,000 m. Remove arena steering and replace terrain queries
before extending map size. (`world.jo:120–160`, `sim.jo:3176–3183`, `skybarons.jo:1908`.)

Positions/velocity/quaternions/matrices are f32 vectors despite f64 scalar equations; no origin
rebasing or double world-position type exists here. Recommendation: keep the first archipelago
near origin, and separate persistent world coordinates from local render/physics coordinates
before making a much larger ocean. Precision loss at scale is a risk, not a measured failure
of this bounded map. (`sim.jo:782–784`, `docs/LANGUAGE.md:165–178`.)

### Renderer API already available, but unused by Sky Barons

| Capability | Use for Aegean Skies / qualifications |
|---|---|
| Sloppy vertex/fragment shaders: `shader`, `make_shader`, `draw` | Animated ocean normals/displacement, sun glitter, foam, shoreline color, cloud shading. No custom shaders are authored in Sky Barons' draw path. Shader code cannot allocate strings/growable arrays/maps/closures. (`docs/GRAPHICS.md:37–78`, `docs/API.md:4160–4202`, `skybarons.jo:2400–2750`.) |
| `draw_custom`, scene camera/sun/fog/shadow accessors | Insert custom ocean/atmosphere in depth-tested 3D; transparency runs after sky with depth writes off; additive option for glow. Must implement material/shadow integration, not just call stock `draw_mesh` with a new shader argument. (`docs/API.md:3694`, `docs/API.md:3729–3739`.) |
| Persistent/custom instance buffers, `set_instances`, ranged custom draws | Chunk trees/houses by island/town and update only changed batches; ordinary array overload uploads every draw. Sky uses persistent buffers, but not per-chunk/ranged custom shaders. (`docs/API.md:3688–3689`, `docs/API.md:4266–4275`.) |
| `wind` parameter of instanced stock drawing | Cheap vegetation motion; Sky leaves it at default zero. (`docs/API.md:3688–3689`, `skybarons.jo:2414–2415`.) |
| GPU buffers, `compute`/`dispatch`, `gpu_mesh`, indirect/count draws | Later GPU vegetation culling, ocean grids or visual particle fields; CPU fallback on OpenGL/WebGL/software, true GPU compute via Vulkan. Avoid individual GPU-buffer reads on CPU. (`docs/GRAPHICS.md:113–148`, `docs/API.md:4430–4438`, `docs/API.md:4510–4527`.) |
| `point_light`, `night_stars`, variable sun/sky/fog/post tint | Harbor lamps, dawn/dusk, weather grading; max eight selected point lights, no point-light shadows. Sky uses static sun/sky and emissive geometry, not these point lights/stars. (`docs/API.md:3676–3685`, `skybarons.jo:2406–2415`.) |
| `render_target`, `draw_to`, target texture | Offscreen/reflection/minimap building blocks; Sky already uses targets for 160×100 picker thumbnails, not a sea reflection system. Target lifetime/state must be managed. (`docs/API.md:2709–2714`, `docs/API.md:2781–2791`, `skybarons.jo:4620–4644`.) |
| glTF meshes, skins and blended animation | Authored aircraft/town details or better NPC animation. Materials support base color/textures/emissive, not metal/roughness/normal-map import; no morph/compressed meshes. (`docs/API.md:3841–3859`.) |
| Terrain mesh helper; physics terrain triangles and character queries | Alternative collision/visual pipeline for detailed settlements; not an automatic streaming/LOD system. (`docs/API.md:3751`, `docs/API.md:5191`, `docs/API.md:5255–5280`.) |

The surveyed API does not promise a ready ocean, PBR environment reflections, volumetric cloud
renderer, cascaded shadows or automatic world streaming. Treat those as custom work or bounded
approximations. The supported rendering backends are Vulkan1.3, OpenGL ES3, WebGL2 and software;
GPU f64/int64 shader arithmetic is effectively 32-bit. (`docs/GRAPHICS.md:7–35`,
`docs/GRAPHICS.md:75–78`, `docs/API.md:3576–3755`, `docs/API.md:3859`.)

## 7. Curated lessons from Sky Barons and Aces history

These are actionable interpretations of commit messages, not promises that historical tuning
numbers remain current. Each bullet gives the history hash and a present source anchor.

- `0f4d68e`: Keep flight sim testable without graphics; Aces established identical native/wasm/arm64 ticks.
  Preserve deterministic replay tests even without multiplayer. (`tests/t/skybarons_sim.jo:1–16`.)
- `76830a4`: Scale aim-controller gain to the aircraft's actual turn rates; one fixed gain does not fit scouts and bombers.
  Keep the rate-normalized near steering. (`sim.jo:5663–5698`.)
- `2a9a026`: Banked wings must lose vertical support; a free sideways roll otherwise has little flying consequence.
  Preserve explicit bank sag when retuning floatplane lift. (`sim.jo:3387–3393`.)
- `82e703c`: Bank should also pull the nose down, with skyward rudder able to hold it; update bots to compensate too.
  Copy the coupled physics and steering corrections. (`sim.jo:3359–3364`, `sim.jo:5694–5698`.)
- `3b79f0b`: Add yaw toward the low wing so banking actually turns the aircraft, not merely drops it.
  Check this separately from direct rudder control. (`sim.jo:3365–3372`.)
- `903b89a`: Make keyboard/mouse handoff explicit: held keys fly, release preserves the new aim and levels wings.
  Do not leave a latent bank fighting the user's mouse aim. (`skybarons.jo:1069–1073`, `skybarons.jo:1539–1541`.)
- `49c5da8`: Cap far roll-and-pull for extremely agile craft; naive gain made the cat loop upside down repeatedly.
  Retain the separate near/far response and blend. (`sim.jo:5683–5689`.)
- `0687e1c`: Offer camera roll lock as a preference; stable horizon and visible aircraft bank can coexist.
  Keep this independent of flight assists. (`skybarons.jo:1834–1841`.)
- `d50d53f`: Let observation and movement be independent where the vehicle permits it; helicopter keys stopped snapping look forward.
  Useful for taxiing, sightseeing and docking-camera design. (`skybarons.jo:1250–1267`.)
- `427c45d`: Decouple requested horizontal speed, climb rate and power; changing one should not unexpectedly drive another.
  Reuse that control principle for low-speed water handling. (`sim.jo:6187–6229`.)
- `f8bb5da`: Yield to moving traffic, steer around static traffic, and bound waits; waiting for parked planes caused permanent queues.
  Apply the same policy to harbor traffic. (`sim.jo:5986–6011`.)
- `bc95bf1`: Spread departures across lanes and formations; vary pedestrians deterministically; leave unusual craft available to players.
  Avoid a synchronized line of identical NPCs. (`sim.jo:2520`, `sim.jo:5910–5911`, `sim.jo:6012–6016`, `sim.jo:6887–6894`.)
- `ef2645a`: Forgive slow ground contacts: stopping and separating crowded vehicles is better than constant accidental destruction.
  Reconsider the threshold for docks, rather than copying airfield damage wholesale. (`sim.jo:3867–3881`.)
- `fc297fc`: Build compact query lists once per tick and sweep collision candidates; historical 64-a-side tick time fell 1.7→.55 ms.
  Treat those figures as historical, but preserve the algorithmic lesson. (`sim.jo:1443–1452`, `sim.jo:3827–3845`.)
- `455efaf`: Keep static instance data on GPU and instance particles; historical 6,000-particle CPU time fell 1.8→.5 ms/frame.
  Do not upload unchanged forest transforms each frame. (`skybarons.jo:1975`, `docs/API.md:3688–3689`.)
- `c413696`: Log practice as well as online sessions, with frame zones, GPU, counts and memory; otherwise local failures lack evidence.
  Preserve a lightweight diagnostics path. (`skybarons.jo:683–700`.)
- `fd4f2c0`: Revisit synthesized-noise frequency when audio semantics change; the old wind became a loud low whoosh over the motor.
  Listen to engine/wind together, not as isolated effects. (`skybarons.jo:3328–3331`.)
- `f57f616`: Cap crash loudness and audible reach so an explosion does not drown the rest of the scene.
  Carry this mix discipline into sea/harbor ambience. (`skybarons.jo:2896–2906`.)
- `54afe2a`: Tracers need thin tapered hot-head/red-tail shapes, not thick nearby slabs; report a death only once by its cause.
  Separate visual readability from damage volume. (`skybarons.jo:2727–2735`, `skybarons.jo:3301–3321`.)
- `f530192`: Accurate defenses should be escapable by jinking or terrain; visual flak density can exceed actual damaging shells.
  Keep cover queries and cosmetic spectacle separate. (`sim.jo:5174–5180`, `skybarons.jo:3244–3279`.)
- `0116747`: Place target labels first, nearest next, suppress overlapping names but retain marks.
  Reuse for island, port and traffic annotations. (`skybarons.jo:3620–3683`.)
- `1f0021f`: Use one coherent HUD scale and fading contextual help; marker-free lock-on should require an object visible on screen.
  Avoid omniscient navigation/combat labels in exploration. (`skybarons.jo:1333–1353`, `skybarons.jo:4389–4405`.)
- `2c3cb77`: A small predicted aiming pip can communicate enough; showing an entire rocket path cluttered the view.
  Reserve full trajectories for actions that need them. (`skybarons.jo:4440–4466`.)
- `a0368d0`: Cargo changes framing requirements; the carried ball needed a farther/higher camera to preserve visibility.
  Test seaplanes with passengers/cargo, not empty silhouettes alone. (`skybarons.jo:1828–1829`.)
- `3177f8c`: Show throw trajectories from a useful side/quarter view when the craft itself occludes them.
  Frame an interaction around what the player must judge. (`skybarons.jo:1850–1858`.)
- `6e6e783`: Recovery speed must remain above aircraft stall; use an approach window with clear “near/aligned/too fast” feedback.
  Adapt the legibility, not the instantaneous carrier catch. (`sim.jo:326–329`, `sim.jo:6475–6478`, `skybarons.jo:3792–3798`.)
- `e992fd9`: Put approach aids in-world and preserve propeller clearance; the carrier's catcher evolved into open jaws and a semaphore.
  Docks need understandable physical affordances too. (`models.jo:7112–7163`, `skybarons.jo:2288–2362`.)
- `a58d7e8`: Match camera scale to the object currently occupied, not a much larger parent vehicle.
  A caught fighter should still be seen at fighter distance. (`skybarons.jo:1792–1800`.)
- `1b5d53b`: Walkers aboard moving vehicles need local coordinates, real edges and falling transitions.
  Do not approximate a deck as stationary world ground. (`sim.jo:2596–2645`, `sim.jo:2114–2126`.)
- `4db70eb`: Seats, boarding and occupant identity must be independently modeled; landing by parachute can naturally become boarding.
  Keep vehicle existence independent of its pilot. (`sim.jo:2921–2981`.)
- `2d86d6b`: A multicrew vehicle needs an explicit gathering/wait policy before departure, not an implicit assumption crew appear.
  Use the principle for ferries/courier passengers. (`sim.jo:2158–2164`, `sim.jo:2259–2328`.)
- `ee49695`: Distribute NPCs among concurrent crew requests; taking all from an already flying vehicle defeats the system.
  Expose prioritized requests rather than a single global summon. (`sim.jo:2217–2238`, `skybarons.jo:4098–4136`.)
- `a64e313`: Give failed assignments a fallback; lone big-craft pilots now abandon an unfilled crew call for a small available craft.
  Civilian jobs also need explicit failure/replanning paths. (`sim.jo:5853–5869`.)
- `8ecda22`: Recheck parking capacity/spacing and terrain flattening for restricted vehicle mixes, not only the default mix.
  Test harbor fleets with worst-size cargo/passenger combinations. (`world.jo:181–273`, `world.jo:97–107`.)
- `199ede8`: Normalize configuration at the simulation boundary and exercise all offered choices; invalid attacking sides crashed hosts.
  Treat UI choices as data requiring validation. (`sim.jo:1184–1203`, `tests/t/skybarons_lobby.jo:1–10`.)
- `0299e3b`: Healing must never lower current health and must use the actual scaled maximum, not only the type's base hull.
  Apply to repairs/upgrades in a persistent world. (`sim.jo:5066–5069`, `sim.jo:617–619`.)
- `be220b1`: Health bars and smoke thresholds must use that same real maximum, otherwise damage can appear to do nothing.
  Keep presentation denominators tied to vehicle configuration. (`skybarons.jo:2786–2787`, `skybarons.jo:3994–3995`.)
- `dbb317a`: Include every variant dimension in mesh cache identity; a new third team made a golden cat reuse a drone mesh.
  Use structured keys or explicit dimension ranges. (`models.jo:7185–7195`.)
- `9457af4`: Visual scale and hit scale must agree; the golden cat had been drawn much larger than its collision body.
  Update physical/seat/visual extents together for floats and cargo. (`sim.jo:4688–4702`, `skybarons.jo:2506–2507`.)
- `8a88ae9`: Keep event IDs unique and avoid browser-reserved control keys; a shared event number produced false carrier messages.
  Prefer named event types and test each payload contract. (`sim.jo:1016–1019`, `skybarons.jo:119–121`.)
- `5d0f662`: Cinematic death feedback should fit inside existing recovery time and be immediately skippable.
  Do not lengthen a failure loop to show the camera. (`skybarons.jo:1636–1644`, `skybarons.jo:1735–1748`.)
- `17537db`: Cinematic observation feels different from another chase camera; use deliberate orbit/flyby shots and an initial cut.
  Useful for later vista/replay cameras. (`skybarons.jo:1663–1722`.)
- `0b00df8`: Reacquire pointer lock only after Escape is released; otherwise browser unlock immediately reopens pause.
  Preserve delayed relock logic when changing menus. (`skybarons.jo:999–1006`, `skybarons.jo:1475–1483`.)
- `e6a547c`: Fullscreen Escape has browser meaning; provide an alternative menu key and trigger it on release from gameplay.
  Track the key's context so menu input cannot become an accidental action. (`skybarons.jo:1455–1469`.)
- `33f2591`: Separate enter, bail, chute-open and return-to-action inputs and timing; overloaded transitions confused players.
  Do not carry the match teleport action onto a sandbox disembark key. (`sim.jo:2425–2442`, `sim.jo:2578–2588`.)
- `306cc82`: UI availability and actual selection must use one acceptance predicate; an offered craft should really be obtainable.
  Reuse for shops, jobs and dock interactions. (`sim.jo:3088–3106`, `skybarons.jo:4648–4694`.)
- `ead2252`: Measure effective incoming DPS before scaling boss durability; the useful curve came from measured bot damage, not a guessed square law.
  Apply measured bounds to pirate encounter/economy scaling. (`sim.jo:1709–1711`.)
- `c15a74f`: Against swarms, raw health alone cannot preserve maneuvering time; use explicit pressure/time budgets if that is the intended experience.
  This is an encounter-design lesson, not a recommended default NPC invulnerability rule. (`sim.jo:538–573`, `sim.jo:4828–4835`.)
- `d358ba2`: Fast-object trails need spatial sampling along movement, not one clump per frame; scale machinery audio to its physical identity.
  Use the same idea for spray/wakes and distant moving aircraft. (`skybarons.jo:2846–2854`, `skybarons.jo:3441–3469`.)
- `2a3127d`: Keep cosmetic aircraft/insignia changes out of simulation so appearance can evolve without changing combat results.
  Maintain the sim/model separation as art improves. (`models.jo:7168–7195`, `sim.jo:668–698`.)
- `e5be4f1`: Exercise event-to-name/audio mappings for every entity kind; destroying a gun nest panicked because its display name was missing.
  Enum/payload coverage matters as new town objects are added. (`skybarons.jo:70–71`, `skybarons.jo:2916–2924`.)

## 8. Sloppy language/API gotchas and verification conventions

- **Values, not references.** `c=g.crafts[i]` is a value snapshot; editing `c` does not edit the
  array until written back. Arrays/maps share storage until mutation. Use `mut` parameters or
  `loop mut` for intentional in-place changes. (`docs/LANGUAGE.md:299–345`.)
- **COW cost grows with state.** `tick`'s `let g=g`, previous-frame arrays and `view()` are cheap
  initially, but subsequent shared mutations copy storage. Do not put an entire archipelago's
  inhabitants/markets inside a 60 Hz copied render snapshot. (`sim.jo:1439–1445`,
  `skybarons.jo:972–987`, `skybarons.jo:1565–1566`, `docs/LANGUAGE.md:2177–2189`.)
- **Borrowing vs old optimization comments.** Current docs say ordinary function parameters are
  borrowed, not unconditionally copied. `sim.jo:1415–1416` describes copying/counting costs of
  accessing/passing craft in this design; do not generalize it over the language's current
  contract. Local snapshots, return values, nested arrays and mutation still matter.
  (`docs/LANGUAGE.md:314–332`, `docs/LANGUAGE.md:2210–2215`.)
- **Watch stale write-back.** Helpers may mutate the same craft/people in `g`; writing an old
  local `c` afterward can erase those changes. Existing code deliberately writes state before
  callbacks and reloads it afterward. Preserve that sequencing. (`sim.jo:3292–3295`,
  `sim.jo:3470–3474`, `docs/LANGUAGE.md:341–345`.)
- **Aliasing restrictions.** Passing `g.crafts[i]` as `mut` while also passing its containing
  array/state can be illegal. Pass state+index or split ownership, rather than forcing a
  reference-style port. (`docs/LANGUAGE.md:322–332`, `sim.jo:3138–3139`.)
- **Imports are not interchangeable.** `use` merges names; `import` namespaces them; imports
  are not transitive; module top-level code runs before importer code. Sky explicitly uses both
  world and sim, while models is namespaced because constants/helpers overlap.
  (`docs/LANGUAGE.md:1233–1267`, `skybarons.jo:32–34`, `sim.jo:5`, `models.jo:84–98`.)
- **Globals and shadowing.** `x=v` in a function declares a local unless `global x`; `let`
  always shadows. Field writes/compound assignments have different global lookup behavior.
  Do not remove global lists from input/camera functions mechanically.
  (`docs/LANGUAGE.md:112–158`, `skybarons.jo:1432–1433`.)
- **Loop/range endpoints.** Bare `0..n` excludes n; `[0..n]` includes it; `[0..n)` excludes it.
  The grid intentionally loops `0..CELLS+1` for corners, `0..CELLS` for cells. Historical range
  semantics changed (`0f3efa7`), so follow current docs, not older source snippets.
  (`docs/LANGUAGE.md:499–507`, `world.jo:116–117`, `world.jo:486–498`.)
- **Numeric types.** `int` is signed64 and wraps; vectors/matrices are f32; integer division
  truncates; `%` is remainder; float-to-int truncates/saturates. Explicit f32/f64 conversions
  document precision boundaries; they cannot make a vec3 position double precision.
  (`docs/LANGUAGE.md:165–221`, `sim.jo:3379–3394`.)
- **Degrees/radians and axes.** Camera FOV/gun helper cone arguments use degrees; physical rates
  and quaternion angles use radians; stored seat arc is cosine. `facing` points −Z, unlike
  unturned glTF's +Z convention. (`sim.jo:642–644`, `sim.jo:667`, `docs/API.md:3580`,
  `docs/API.md:3673`, `lib/game/vmath.jo:325–334`.)
- **Exponential smoothing.** `approach`'s rate is not units/second; use `exp(−rate*dt)` thinking.
  Retain fixed-DT control smoothing versus frame-DT camera easing deliberately.
  (`lib/game/gameutil.jo:117–119`, `skybarons.jo:1302`, `skybarons.jo:1842–1843`.)
- **Do not call all counters seconds.** Bullet life, heat cooldowns, respawn and most sim
  timers are integer ticks; camera/effect lifetimes use frame seconds/elapsed time.
  (`sim.jo:7–14`, `sim.jo:883–895`, `skybarons.jo:3211–3224`.)
- **Long-world clocks need an explicit policy.** Frame dt is capped at .1 and local accumulated
  flight time at .1; a stalled game does not simulate all elapsed wall time. Schedule economic
  ticks deliberately; use saved time/offline catch-up only if designed for it.
  (`docs/LANGUAGE.md:1601–1611`, `docs/LANGUAGE.md:1629–1652`, `skybarons.jo:1561`.)
- **Rendering is queued.** HUD/2D after 3D flushes/draws on top; custom draw must enter the 3D
  pass explicitly. The thumbnail path even uses a tiny 2D mark to force 3D completion before
  switching targets. Do not interleave render targets casually.
  (`docs/API.md:3578`, `docs/API.md:3694`, `skybarons.jo:4623–4636`.)
- **Performance tools exist.** Release compilation, frame zones/stats, memory counts and COW
  diagnostics (`SLOPPY_COPIES`, threshold configurable) are available. Measure before adopting
  GPU compute or SoA everywhere. (`docs/LANGUAGE.md:2170–2225`, `docs/API.md:2520–2526`.)
- **Shader portability limits.** GPU shader int64/f64 are effectively 32-bit; allocations are
  forbidden; individual GPU-buffer CPU reads are slow. Keep economic/NPC authoritative state
  on CPU and use GPU paths for visuals unless a measured reason says otherwise.
  (`docs/GRAPHICS.md:64–78`, `docs/API.md:4432–4438`.)

### Existing tests and safe headless practice

`SKY_TEST="seconds mode people-per-side"` runs sim-only before `window`, ticks at 60 Hz,
prints event totals/hash, stops at winner, and exits. It omits later event kinds from its
human-readable names, so not every event is summarized. `SKY_SEAT="kind seat"` only takes
effect when starting local practice; it does not itself bypass the menu.
(`skybarons.jo:43–68`, `skybarons.jo:553–605`.)

The repo's simulation tests are top-level programs with expected `.out` files, not all `test`
blocks: e.g. `skybarons_sim.jo` runs five 40-second fights and hashes state; foot/flyer tests
exercise jump/fire and auto-level/steering. Compare their output using the repository runner
or port assertions deliberately. (`tools/runtests.py:1–3`, `tools/runtests.py:68–76`,
`tests/t/skybarons_sim.jo:1–37`, `tests/t/skybarons_sim.out:1–11`,
`tests/t/skybarons_foot.jo:1–49`, `tests/t/skybarons_flyers.jo:1–54`.)

Suggested future commands, **not run in this audit**; all source copies/builds/output live in
the permitted scratch tree. `--release` and `-o` are documented build options.
(`docs/START.md:108–125`, `tools/rendertest.py:42–53`.)

```bash
source_repo="$HOME/dev/slop-lang"
audit_root="$HOME/dev/tmp/aegean-skies"
mkdir -p "$audit_root/scratch"
cp -a "$source_repo/examples/skybarons" "$audit_root/scratch/source"
export DISPLAY= WAYLAND_DISPLAY= SLOPPY_NO_AUDIO=1 SLOPPY_THREADS=2
export SLOPPY_SAVE_DIR="$audit_root/scratch/saves"
sloppy build --release "$audit_root/scratch/source/skybarons.jo" -o "$audit_root/scratch/skybarons"
SKY_TEST="120 0 3" "$audit_root/scratch/skybarons"
SLOPPY_SOFTWARE=1 SLOPPY_SCREENSHOT="$audit_root/scratch/menu.png" SLOPPY_FRAMES=60 "$audit_root/scratch/skybarons"
```

Use a fresh scratch/source destination if repeating the copy. Screenshots fix clock at 1/60 s;
`SLOPPY_FRAMES` alone uses real time. Set a seed for cosmetic randomness, isolate saved settings,
and inject input with `SLOPPY_INPUT` if testing gameplay, not just the menu. `SLOPPY_NO_AUDIO=1`
disables sound. (`docs/LANGUAGE.md:1933–1965`, `docs/API.md:1391`.)

Do not use `tools/rendertest.py --update` in this read-only audit: it rewrites references, and
its default scratch uses the system temp directory. Historical/desktop `SKY_TEST` wall timings
are not a quiet-laptop benchmark; use hashes/event counts here and follow machine benchmark
rules for actual speed comparisons. (`tools/rendertest.py:9–18`, `tools/rendertest.py:62–74`,
`skybarons.jo:67`.)

## 9. Recommended reuse plan and risks

### Concrete extraction list

These are **selective extraction ranges**, not a claim that each range compiles by itself.
Prune kind/mode branches and replace `Game` callbacks with the new game's interfaces.

| Decision | Source slice | Adaptation / dependencies |
|---|---|---|
| Copy concept, reduce structs | `sim.jo:623–664`, `sim.jo:756–818`, `sim.jo:874–903` | Keep aircraft/person separation, local seats, physical state and independent controls. Remove match/fantasy fields; add stable IDs, ownership/cargo/fuel as required. |
| Copy largely | `sim.jo:1390–1400` | Orientation/attachment/lifecycle helpers; clarify what “alive/whole” means in the new game. |
| Copy/adapt first | `sim.jo:3335–3397` | Ordinary flight; eliminate Turncoats multipliers/special creatures and replace contact query/callback. Needs DT, kind, vehicle, Pad and terrain/water adapter. |
| Copy coupled to flight | `sim.jo:5668–5699` | Mouse/NPC steering, including rate scaling and bank hold; keep it tested against flight coefficients. |
| Adapt contact | `sim.jo:3401–3461`, `sim.jo:3487–3536` | Keep dry landing/takeoff baseline only; replace wet destruction with floating/planing mode; separate obstacle solver. |
| Adapt walking/boarding | `sim.jo:2511–2545`, `sim.jo:2823–2864`, `sim.jo:3006–3041` | Remove team/respawn policy; add dock-aware safe exits and vehicle interaction checks. |
| Optional moving-platform template | `sim.jo:1886–1898`, `sim.jo:2042–2079`, `sim.jo:2596–2685` | Reuse local-frame idea for boats/docks; supply new deck shapes and occupancy/edge behavior. |
| Adapt input shell | `skybarons.jo:113–135`, `skybarons.jo:1009–1075`, `skybarons.jo:1170–1306`, `skybarons.jo:1512–1554` | Preserve mouse/key handoff and smoothing; remove special craft/crew/map/match actions; keep optional device abstraction. |
| Copy/adapt view | `skybarons.jo:967–988`, `skybarons.jo:1559–1574`, `skybarons.jo:1613–1634`, `skybarons.jo:1768–1789`, `skybarons.jo:1819–1908` | Fixed tick + interpolation + ordinary chase/foot camera. New render snapshot; add town collision, viewpoint transitions and seaplane framing. |
| Adapt compact NPC controllers | `sim.jo:5978–6023`, `sim.jo:6454–6479`, `sim.jo:6975–6994`, `sim.jo:7051–7061` | Taxi yielding, approach alignment, avoidance and cruise altitude feedback; replace match destinations and add real route/job state. |
| Copy combat kernel later | `sim.jo:910–923`, `sim.jo:4655–4662`, `sim.jo:4680–4702`, `sim.jo:4782–4806`, ordinary portions of `sim.jo:4904–4987` | Bullet integration, motion-relative ellipsoid tests and intercept lead; remove giant-craft cases and use nearest-hit ordering if required. |
| Copy geometry toolkit | `models.jo:105–148`, `models.jo:535–598`, `models.jo:632–707`, `models.jo:758–769` | General primitives/wing/body kit; create new floatplane and boat shapes, no military insignia dependency unless wanted. |
| Adapt settlement props | `models.jo:2731–2832`, `models.jo:3008–3100`, `models.jo:5730–5740`, `models.jo:6665–6708` | Harbor shells/cargo/lamps; new interiors/collision/semantic buildings. Do not import the entire castle/carrier. |
| Copy patterns, rebuild content | `world.jo:110–149`, `world.jo:477–498`, `skybarons.jo:1912–1977` | Shared visual/contact height data and persistent GPU buffers. New island terrain, finer shoreline/town geometry, per-chunk caches. |
| Adapt feedback | `skybarons.jo:2691–2737`, `skybarons.jo:2753–2772`, `skybarons.jo:3284–3299`, `skybarons.jo:3328–3340`, `skybarons.jo:3393–3440` | Instanced tracers, bounded shake, synthesized sounds and nearest engine voices; replace event protocol and add sea/settlement ambience. |
| Leave behind | `sim.jo:387–619`, `sim.jo:1094–1345`, `sim.jo:1511–1869`, `sim.jo:5329–5660`; `skybarons.jo:342–966` | Match modes/score/flags/balls/respawn allocation/Boss/Turncoats/network shell. Preserve only tiny generic helpers when needed. |
| Leave behind initially | `sim.jo:3564–3808`, `sim.jo:4137–4640`, giant craft/creature model builders | Helicopters, airships, fantasy ordnance, carriers/tethers/hoists and special creatures multiply dependencies without advancing the first seaplane loop. |

### First living-archipelago milestone: proposed order

1. Build a new small world state with stable person/vehicle/settlement IDs and versioned save
   data. Use `save_value`/`load_value` or explicit serialization; Sky only saves settings/logs,
   not its inhabitants. (`docs/API.md:1382–1395`, `docs/API.md:1423–1427`, `skybarons.jo:171–218`.)
2. Extract one winged aircraft and `steer`; verify level cruise, turns, climbs, stalls and
   key/mouse handoff before adding economy. Preserve the coupled flight/steer behavior.
   (`sim.jo:3335–3397`, `sim.jo:5668–5699`.)
3. Add explicit water contact and a dock: float stability, directional water drag, taxi thrust,
   planing/takeoff, landing damage, safe embark/disembark. Existing wet paths destroy craft or
   put people at sea level; replace them before calling the vehicle a seaplane. (`sim.jo:3446–3459`, `sim.jo:3513–3516`, `sim.jo:3006–3022`.)
4. Make a few islands with shared terrain/collision and walkable harbor geometry. Add one
   functional town path and interior before scattering decorative settlements. (`world.jo:123–147`, `world.jo:477–546`, `docs/API.md:5260–5280`.)
5. Give a small population persistent identities, homes/workplaces, cash/inventory and simple
   jobs/needs; run those at a slower explicit simulation cadence, keeping nearby motion at 60 Hz.
   This is new work: present Person/Game contain no economic or social state. (`sim.jo:874–908`, `sim.jo:1065–1090`.)
6. Connect settlement stock/production/consumption to a visible courier/trade route; use one
   civilian aircraft route with arrival, water approach, docking, transfer and departure.
   Existing cruise/avoidance are helpers, not this job lifecycle. (`sim.jo:6454–6479`, `sim.jo:6975–6994`, `sim.jo:7030–7068`.)
7. Improve sea/sky/light within a measured frame budget, then add pirates/bounty combat.
   The public shader/instance APIs enable richer materials without tying jobs/needs to rendering.
   (`docs/API.md:3694`, `docs/API.md:4262–4275`, `docs/GRAPHICS.md:113–148`.)

### Top risks / acceptance gates

- **Water handling is the critical new physics feature.** Gate: cold start floating, taxi to
  dock, safe exit/reentry, takeoff, gentle and hard water landings; no hidden ditch/removal path.
  Existing blockers: `sim.jo:3401–3461`, `sim.jo:3487–3526`, `sim.jo:3006–3022`.
- **“Living” is new simulation, not a bot retheme.** Gate: same inhabitants/jobs/money survive
  save/reload and continue coherent work; no match respawn replaces them silently.
  Existing limits: `sim.jo:874–908`, `sim.jo:2709–2800`, `skybarons.jo:171–218`.
- **Terrain detail and collision must grow together.** Gate: boats/feet/camera agree with quay,
  beach and terrain surfaces; aircraft hit intended town obstacles. Current visual villages,
  center contact and 50 m grid are insufficient. (`world.jo:9–11`, `world.jo:512–546`, `sim.jo:3395–3397`, `sim.jo:3529–3536`.)
- **COW and global work can dominate at population scale.** Gate: profile with representative
  people/craft/markets, render only compact nearby state, avoid O(N²) social scans each flight
  tick; inspect COW traces before redesign. (`sim.jo:1439–1509`, `docs/LANGUAGE.md:2177–2208`.)
- **Civilian autonomy needs recovery paths.** Gate: NPCs complete routes repeatedly and recover
  from blocked docks, failed approaches and missing craft without teleporting out of the world.
  Existing recovery is carrier-specific; foot fallback is match respawn. (`sim.jo:5875–5916`, `sim.jo:6454–6479`.)
- **Visual ambition can exceed the stock renderer's coverage.** Gate: sea/sky look coherent on
  Vulkan plus intended fallback hardware, with bounded overdraw/batches and shadow reach.
  Instancing bypasses stock frustum culling; custom ocean/reflections are new work.
  (`lib/game/draw3d.jo:717–737`, `lib/game/draw3d.jo:831–838`, `docs/GRAPHICS.md:7–35`.)
- **Index references and duplicated geometry constants are fragile.** Gate: stable handles
  survive deletion/save/load, and model seats/collision/float points come from shared data.
  Existing integer links and duplicate attachment constants need deliberate replacement.
  (`sim.jo:800–850`, `sim.jo:881–903`, `models.jo:3247–3249`, `docs/API.md:1429–1499`.)

Audit limit: this report establishes source behavior and reusable seams, not that the current
flight feels wonderful for leisurely seaplane travel. That judgment needs a bounded hands-on
flight prototype after extraction. No source repo files or Aegean Skies repo files were changed;
the report is the only artifact produced by this audit.
