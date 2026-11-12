# Settlement economy implementation status

The stock-partition primitives are implemented; the population/transport/war simulation is
not wired yet. `World.far.version` starts at zero in normal games. The registry still supplies
place/venue data and the map catalog; it does not yet create a populated far tier.

`living_far_stock` uses the existing CargoSource ledger. A root's `far_quantity` partitions its
actual live quantity between abstract stores and detailed crates. Far cached totals join the
existing goods-conservation equation. Validation recomputes the cache from stores, checks each
root partition, and rejects double far aircraft tanks/holds. Production owns the issued batch
immediately; transferring through a core warehouse moves the same roots, without a new import,
production, money, or consumed-goods entry. Unpromised stock must be physically present and
owned by that market; goods in a person's hands are not available to abstract shipping.

Container helpers are pure and refuse bad arguments before mutating. World operations use the
same strict/recovery diagnostics as other living transactions. A temporary batch between stores
is an internal transaction value: do not save/yield or expose it to UI between taking and
placing/consuming it. Call these primitives inside a guarded economic operation.

Stock fragments are capped at64 per store. Production roots aggregate by real producer, good
and origin, so elapsed weeks do not create new roots for the same producer. Persistent far
person records reference World.people identities/accounts/poses; aircraft vehicles reference
World.aircraft bodies/tanks/holds. The dormant schema deliberately does not duplicate either.
Further validators and funded cohort/transport/force construction belong to the next slice.

`tests/living_far_stock.jo` verifies production/use conservation, both gateway directions,
unchanged provenance/no import, ownership of converted detailed crates and canonical saves.
