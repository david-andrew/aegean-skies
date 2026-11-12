# Living-world validation and game recovery

Validation is **strict by default**, including tests and headless simulation tools.
`living_guard.set_living_strict(false)` is an explicit application choice in `aegean.jo`.
The same failed invariant calls `living_fault` in either mode: strict mode panics with its
site/context; game mode logs its first occurrence and refuses the operation. Repetitions count
in `living_faults()` without flooding the console. These diagnostics are process-local, outside
saved deterministic state. Do not turn strict mode off in simulation acceptance tools.

Cash, cargo, escrow, delivery, refund, portage wages, repair, charter, contraband, raid loot,
services, job creation/cancellation and conversation mutations have transaction boundaries.
An outer game-mode boundary takes one copy-on-write World checkpoint. Nested operations share
it; a failed invariant restores the prior World and returns failure/silence. This also restores
inventory projections, provenance roots, reservations, price residuals and event/receipt counters.
Ordinary expected refusals (no money, occupied dock, stale command) retain their existing API
results. A failed condition formerly asserted by the caller is still loud in strict tests.

Minute rules take a checkpoint after the clock reaches that minute. They stop between dependent
phases after a fault, and restore the entire economic minute on failure. Physical time and
already committed player motion keep advancing. A pre-existing cash/goods imbalance skips
rules and reports actual/expected totals; it does **not** create stock/money or rebase opening
balances to conceal the mismatch. Once a legitimate correction restores the books, later
minutes can run. Existing corrupt state can therefore leave economic decisions paused while
the player keeps moving; retain the console diagnostic for diagnosis.

Physical motion has no per-frame World snapshot. Its revision/pose/fuel checks precede writes.
The scene adapter clamps the metadata throttle (air brake means idle) and projected record speed
at 900 m/s, then logs/refuses a rejected player or NPC write. It does not apply another movement
or debit fuel after refusal. `traffic.commit_player_motion` and `commit_traffic_motion` are the
adapter's public commit boundaries, exercised by the motion regression tests. Simulation
`commit_scene_motion` continues to return -1 for ordinary invalid/stale API requests.

Walking checks refuse invalid targets/routes before navigation indexes them. Missing scene task
IDs are removed from the active index; missing daily intents are rebuilt from the same person's
current place/pose. A bad path blocks that walker until its goal can be replanned. An obstructed
Porto approach returns no route rather than panicking during an in-flight replan. Startup
asset corruption and the initial six-harbor content-construction asserts remain startup errors;
they are not reachable from the audited frame roots. Combat's standalone engagement constructor
asserts are likewise outside the current scene bridge, which registers existing bodies.

`python3 tools/check_living_guards.py` traces a conservative source call graph from traffic,
minute rules, scene/cargo/life adapters, player commands and talk/reply. The current graph reaches
the reachable functions and finds only the strict-mode panic in `living_fault`. This is an approximation,
not a proof about implicit bounds checks, arbitrary callbacks, the renderer or allocation errors.
Re-run it when adding new frame paths; do not introduce unchecked constructors below them.

Acceptance:

- `tests/living_recovery.jo` forces pre-existing conservation failure, a missing physical lot
  partway through a minute, a cash/cargo trade failure and a porter-payment failure after unload
  writes. Recovery restores the relevant prior state and keeps the clock/process running.
- `tests/traffic_recovery.jo` covers negative air-brake throttle, >1000 m/s dives, and refused
  player/NPC revisions without an extra debit or mutation.
- `tools/living_guard_probe.jo`, cases `balance`, `trade`, `motion`: strict builds must exit
  nonzero with a living-invariant diagnostic; `LIVING_RECOVER=1` must reach `RECOVERY CONTINUED`.
