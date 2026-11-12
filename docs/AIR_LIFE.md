# Living air traffic and capital meetings

`traffic.jo` still projects the living world's aircraft and trips. The new `air_pilot.jo`
layer supplies flight intentions to the existing autopilot: a wind-aligned water run,
terrain-aware waypoints, predictable right-of-way, loose echelon following, occasional
wing greetings, offshore coast following and one inspection circle around an actual ship.
Occupation/traits select the style: couriers keep a high, economical route; racers fly
lower and faster; pirates stay low. Social manoeuvres are disabled during final approach.
An occupied berth is still resolved by the world's reservation/holding logic.

Pilots operate the controls; they never assign an airborne attitude or position. With the
inertial stall trial enabled, rate feedback and angle-of-attack feedback prevent the old
instant-rate steering from overcorrecting. NPC departure and approach procedures also
establish a safe climb, join the extended approach line before descending, reduce flare
power at accelerated travel speeds, finish a clear-water flare beyond the nominal point,
and brake the water run before turning toward a dock. `FlightPlan.arrival_setup` saves the
approach-entry leg; the shared autopilot and player flight equations remain intact.

## Capital clubs

`air_events.jo` owns the *flight schedule*, not a second population or fleet. It uses the
living world's `register_far_aircraft`, `fill_far_tank` and berth APIs. Each capital can
purchase one Swift and one Falco, promote two real cohort pilots, consume yard parts and
pay for finite fuel. Each new aircraft purchase is limited to 5% of the household purse.
Registration keys are permanent; wrecks, missing stock and insufficient money do not
produce free replacements. A practice sortie is scheduled at 10:00 on ordinary days.

The shared capital feast calendar schedules an over-water six-gate, two-lap race at 17:00,
followed by a display at 19:00, ending at 21:00. Club pilots begin departure at 15:00.
Courses are checked against terrain; an unsafe venue is omitted and unsafe weather
cancels the event. Race heights are separated, arrivals are queued, and a 22-litre reserve
can end a display early. The course speed is limited to 140 m/s before each type's race
pace factor, independently of the debug travel-speed multiplier. Scoring uses swept
forward crossings, height, width, gate order and completed circuits. Discontinuities are
rejected. Finished times survive subsequent accidents; unfinished entrants become DNF.

The quay audience represents a bounded sample of the calendar's existing unnamed
residents (24 on low quality, 48 otherwise). Named people remain with the living scene.
No entry fee, prize, reward, new inventory or race-specific HUD is added.

## UI integration

The application holds one `AirEvents` value named `air_events` and updates it after the
world's clock/traffic update. Public entry points:

- `nearby_air_meets(events, position) -> AirMeet[]`: meetings/results within 15 km.
- `enter_player_air_meet(events, world, meet_id) -> AirEntryResult`: guarded admission,
  with `accepted` and a human-readable `reason`. Requires the player's actual aircraft,
  at least 10 litres, hull/engine health >= 700/1000, proximity and registration still open.
- `withdraw_air_meet(events, meet_id, craft_id) -> bool`: mark an unfinished entry DNF.
- `air_standings(meet) -> AirEntry[]`: finishes, then progress, then DNF; stable ID ties.
- `snapshot_air_events(events, world) -> str`: save-boundary snapshot, including flight
  integrators in each club aircraft's opaque scene extension. Save this returned string
  **alongside** the world. Restore with `from_text[AirEvents]` before resuming updates.
  The game currently has no live world-save command to wire this to. Race state must not
  be reconstructed from aircraft poses alone.

UI needed: a harbor/notebook meeting listing and entry/withdraw buttons; start countdown;
next-gate direction/height and lap counter; finish/DNF standings and cancellation reason.
Use `AirMeet.id` (not its array index). `race_tick`, `display_tick`, `end_tick`,
`AirEntry.started_tick` and `finished_tick` use world simulation ticks: **60 ticks per real
second, 120 ticks per world minute**. Gate zero starts timing and closes each full lap.
`AirEntry.gate` is the next required gate. `missed` means the pilot needs to rejoin behind
that gate. Positions/forward vectors, half-width, floor and ceiling are in `AirGate`.
Player controls are never taken over; entering does not teleport, refuel or repair them.

## Rendering and budgets

`air_view.jo` replaces full ordinary aircraft meshes beyond 1.8 km with one instanced
silhouette batch, visible to 12 km. Distant dots, view-dependent sun glints, forward-facing
dusk approach lights and short exhaust histories provide recognition cues. Exhaust is
bounded at 256/768 ribbon segments; water-run spray at 160/480 particles. Combat-owned
models keep their existing renderer. Club bodies join the existing engine audio, wakes,
shadows and aircraft rendering through a combined *render-only* traffic projection.
They are never inserted into the core harbor/trip-indexed adapter.

`tools/airlab.jo` is an explicit synthetic visual/performance fixture; it is not game data.
Use `AIR_SCENE=traffic|dusk|meet|quay`, `AIR_BASELINE=1` for the old far-model rendering, and
`AIR_CPU=3600` for the eight-aircraft control/physics workload. Run timings only on the
quiet laptop under its bench lock. The implementation report records measured results.
