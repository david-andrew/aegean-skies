# Registry harbours

The original six `Town`, `HarborGeometry`, market and cargo-harbour array slots remain authoritative and unchanged. New-land IDs are semantic settlement IDs, **never indices into those arrays**.

`src/settlement_ports.jo` supplies `settlement_port(WorldSettlement) -> SettlementPort`. The pure builder uses no global RNG. Eight detailed plans are cached; eviction and camera order do not change a plan. The compact settlement catalog, its IDs, centre/out vectors and original generated dock coordinates stay unchanged, so the existing baked living-route catalog stays valid.

A plan exposes Town-shaped geometry (`name`, `center`, `out`, `docks`, `quays`, `buildings`, `boats`), stable `country`/`region`, plus corresponding `loading` points, a `board`, a deep-water `anchorage`, and connected pedestrian `routes`. Quay endpoints are **vec3**, including their deck heights: the landward connection follows a bounded-grade terrain profile. Use `port_quay_height` / `walk_height`, not the original towns' constant `QUAY_TOP`, for contact. `port_harbor_geometry` and `port_cargo_geometry` supply familiar living geometry records with the semantic ID. The cargo adapter uses `-(region+1)` for its land-region grouping, disjoint from original island slots. They are adapters for sparse callers; do not append their results to the six core arrays.

The harbour renderer, collision, mooring bollards and walking contact consume the same plan. Waterfront arms sample the canonical shore, stop at obstructing headlands, and keep their shore approach clear of the main ramp. Service-building footprints are reserved from generated housing. The empty quay boats are harbour scenery; they contain no invented catch, crew or cargo. Working ships still come from the living/vessel owners.

## Living-world integration

`prepare_port_venues(w, observer)` publishes a nearby harbour before far residents choose their routines. It retains other settlement venues and supplies stable keys:

- `port:<id>:board` — square/notice-board meeting point.
- `port:<id>:quay:<dock>` — corresponding accessible loading point.
- `port:<id>:warehouse` — primary market's **door**, not the building centre.
- `port:<id>:building:<ordinal>` — harbour office/workshop or other warehouse doors.

It does not create people, markets or stock. Existing `FarDistrict` residents and accounts own those. Publication is lazy and persisted in `place_contexts`; it does not change the catalog fingerprint/version. This is the adoption boundary for the parallel living-world work.

`arrive_registry_port` records a physical port call only near a dock at low speed. The aircraft retains the pilot's declared core journey during the stopover; the walking player has `place=-1`, `far_place=<registry ID>`, `trip=-1`. The shared `person_place` helper returns that registry ID for visiting core pilots without changing their home or planner. No core delivery/arrival is awarded there. Casting off restores the player's pending trip reference. The aircraft's saved `port_place`, `port_at`, `port_loading` provide the existing portage system with a real loading point. A moving aircraft or stale anchor cannot be loaded remotely.

## Owned goods and presentation hooks

`port_trade(w, person, place, good, milli_packages, buying)` buys/sells through the existing funded district market account and prices. It checks the player's actual vicinity, stock, purse, legal good and physical local sale lots. Sales require owned unpromised goods brought back to the warehouse. It has no direct-to-hold shortcut.

A purchase transfers existing `FarStock` source roots to `CargoLot` pocket custody at the warehouse door. The player uses the ordinary pick-up, carry, put-down and hold-loading actions. Sales return the same roots to district stock. Both directions update exact stock partitions and the aggregate inventory; neither mints goods nor cash. Local taxes go to the district controller's funded treasury. Transactions use the normal rollback guard. Repeated purchases of the same source at the same door coalesce.

Warehouse stock rendering is a bounded view of the actual district inventory; purchased, carried and unloaded lots use the existing cargo meshes with camera-relative projection outside the original islands.

Presentation remains coordinator-owned under `common.md`. Integration points for existing panels:

- `near_port_board(pos)` returns the registry ID or -1. Read that district's real `recent_news`/stock/prices and available funded work; do not pass this ID to the six-port board/job APIs.
- `port_market_spot(w,id)` returns the accessible warehouse door.
- Use the existing goods rows with district prices/stock, `port_sale_quantity` for physically present sale goods, and `port_trade` for commands. `craft` direct-trade options should remain disabled: goods travel through the standard carry/load actions.
- Far people already use persistent person identities and ordinary talk; merchants' UI eligibility should accept their `far_place` and use the sparse market path.

The v1 core job/contract destination schema is still six-port. New-port contracted deliveries, navy bases and a broader sparse Job/Trip migration are separate integration work; no fake job rewards or semantic IDs disguised as array slots are introduced here.
