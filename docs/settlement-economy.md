# Settlement economy

`World.far.populated` enables the funded cohort tier. `far_scene.configure_far_economy` publishes
it once the complete settlement registry and life contexts are ready. This avoids freezing the
mainland-only catalog while streamed island generation is still running. Normal full-world games
use the tier; legacy `AEGEAN_WORLD=0` and isolated core tests retain the six-harbor simulation.

All793 settlements have saved household/market accounts, citizenship cohorts, original country,
current controller, local authority, stock, prices, production, raw reserves, shortages and hunger.
Population includes the original named people/children and actual vehicle crew exactly once.
National treasuries have explicit finite opening endowments; taxes transfer money to the current
controller without changing citizenship. Cohort wages and household purchases use existing funds.
Primary production requires labor and wages; workshops consume fuel and finite ore, arms require
parts, medicine consumes wine/alcohol, and the refinery consumes finite raw crude. No daily reset
or free replenishment. Opening reserves are simulation construction data, not new job cargo.

The six original markets alias their existing owned crates/accounts. Their old abstract household
pseudo-sales are disabled while these funded cohorts buy food. Existing detailed outside import,
export, care/credit and visitor mechanisms remain explicit ledger boundaries; this slice does not
claim the old core is a closed economy. New far accounts/services never receive outside cash.

`living_far_stock` uses the same CargoSource ledger. `far_quantity` partitions a root between
abstract stores and detailed crates. Cached totals join the goods-conservation equation; validation
recomputes stores and partitions. Tier transfers keep the exact source, with no import, production,
consumption or new title created. Only unpromised, physically present market stock may leave a
core gateway. Goods carried by a person are unavailable to abstract shipping.

`tools/bake_living_routes.jo` produces `assets/living-routes.bin`:41KB compressed,516 canonical
roads from606 candidates plus276 water-only sea lanes. Sea approaches/crossings are sampled every
35m against canonical terrain. Rejected chords are not services. Runtime performs no route search;
terrain, geography and sorted settlement layout fingerprints must match. After changing those
inputs, run the baker headlessly and commit the updated catalog. Stale/corrupt data fails loudly
in tools, logs once and leaves the far tier disabled in play.

Up to768 saved reciprocal ship/cart services acquire cargo by paying the origin market from the
receiving market's real purse and paying freight to the carrier. Title then belongs to that buyer;
the vehicle owns custody of the same physical roots. Ships are sailing coasters, not fuel-free
motor vessels. Crew are removed from cohorts and provision actual grain for the full crossing;
daily meals follow them at sea. Paid delivery commits only at the actual route endpoint. Full
warehouses hold an arriving load rather than discard its identity. Journeys carry at most12 local
accounts; only actual arrival copies these to the destination's local news list.

Per-minute work is staggered: approximately14 districts each minute, one hourly work/purchase step
each. Transport advances active journeys once per minute and checks departures every30minutes.
`living_world.far_transport_views(w,observer,radius=6000)` exposes saved service ID, kind, actual
origin/destination/position/velocity, commodity/quantity and a factual reason. This is data for a
scene consumer; this slice does not yet draw ships/carts or supply named far people or aircraft.
The sparse IDs are keys, never indexes into `World.places` or the six original Towns.

Stock fragments are capped at64 per store. Production roots aggregate by producer/good/origin;
spent source audit totals survive. Temporary batches are internal to a guarded operation: do not
save/yield or expose one between taking and placing/consuming it. Full save validation checks
population/crew conservation, route/reference/custody/title/capacity and counters before indexed
helpers. Strict/recovery policy is the same as the rest of the living world.

Tests: root gateways4, funded cohorts/transport5, including seven-day combined-core replay and
malformed reference rejection. `tools/farlog.jo` exercises all793 places for seven days, with hourly
conservation and daily canonical save round-trips. Named local promotion, scene vehicles, far
aviation, political force logistics, combat/capture/refugee/rescue/contracts remain subsequent
work; district data alone is not a running war.
