# Scene damage and saved aircraft health

AircraftRecord.hull/engine are per-mille physical health projections. CraftState's part health
and attachments are authoritative while the physical body exists. Hull health is the physics
core's mass-weighted aggregate, including its engine share. There is no nonlinear wear-to-health
conversion in the adapter: applying that conversion repeatedly healed bullet damage and made the
world's engine value disagree with its actual part. A separate maintenance model would require
separate fields; it must not reuse these damage fields.

A new unsnapshotted body seeds its parts once from the coarse projections. A world structural
loss changes structure without inventing an engine hit; an explicit world repair can increase
its appropriate projection. Damage per part, detached panels and full integrator state are not
reseeded during save/load.

A valid full scene snapshot at the completed fixed tick owns the saved physical damage. Its
part health wins over a contradictory legacy coarse wear projection; the latter is synchronized
from the actual saved body, not used to heal/re-damage it. Legacy inconsistent aggregate telemetry
is refreshed from its parts. Valid exact telemetry/integrator state remains untouched. Fuel keeps
its saved sub-millilitre fraction within the ledger's one-millilitre rounding tolerance; this is
not a second fuel balance or refill. A later abstract minute invalidates the same-tick snapshot
as before. Any caller replacing an aircraft at the same tick must clear its scene extension.

Tests in living_scene_flight cover exact integrator/controller restoration, full player state,
structural-only harm and repairs, damaged individual parts/detached panels/fractional fuel, and a
contradictory old wear record with an actual damaged snapshot. No original assertion was relaxed.
