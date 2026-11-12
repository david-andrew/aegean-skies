# Owned paper maps (data contract)

A `PaperMap` is a saved edition. A `MapCopy` is one actual article in a shop, a person's
collection, a loose-paper cache or the destroyed set. Queries derive stock/collection from that
single holder; there is no second unlock inventory. Opening copies have unique immutable source
keys. Sale, gift, discovery and reward move an existing copy. They never print a sheet. All cash
uses the living money ledger. This article class is separate from the nine bulk commodities.

Core construction stocks a Porto tourist street sheet, 1911 channel chart, individual legacy
island maps, a 1924 pilots' mooring sheet and a coarse 1898 Aegean overview. The player owns one
cheap Porto street sheet at startup. Registry publication adds country road/military editions,
island-group coasting sheets and local sheets for inhabited principal islands. Named island
coverage comes from actual geography and settlements. Capital booksellers, local chandlers,
Porto's harbour office, the Kalamos cooperative and Hotel Selene sell particular finite copies.
Publication is idempotent and never replenishes sold sheets. Cohort shops have their own funded
account and a location; an attendant may be attached later without changing title or stock.

The existing chart UI remains unchanged until the coordinator connects these APIs. Do not fall
back to the global edition when the collection or selection is empty. Purchase/collection
requires physical proximity and no active journey; the player carries the paper after handover.

The `living_world.jo` facade exports:

| API | Result / purpose |
| --- | --- |
| `owned_maps(w,person=0)` | Saved `MapCopy[]`, sorted by acquisition and copy ID. |
| `map_description(w,edition_id)` | Optional `PaperMap`: title, publisher, year, kind, bounds, printed scale, detail, layers, accuracy, survey transform, omissions/errors and notes. |
| `map_layers(w,edition_id)` | The edition's actual layer list. Absence means no information. |
| `selected_map(w,person=0)` / `select_map(w,copy_id,person=0)` | Saved selection; only an owned copy can be selected. |
| `map_sellers(w,person=0)` | Actual nearby sellers with stable shop/place ID, account, attendant and position. |
| `map_offers(w,shop_id,person=0)` | Nearby unreserved stock, title/edition/copy ID, price and affordability. |
| `buy_map(w,copy_id,person=0)` | Atomic paid transfer, `MapTradeResult(ok,message,copy,cents)`. |
| `give_map(w,copy_id,giver,receiver)` | Transfer a person's copy within earshot. |
| `nearby_map_finds(w,person=0)` / `find_map(w,copy_id,person=0)` | Loose existing sheets within 3 m; pickup exactly once. |
| `claim_map_reward(w,job_id,person=0)` | Collect a specifically reserved sheet after delivering that job, at its grantor's counter. |
| `map_feature(w,edition,layer,key,actual,label="",town_size=1000000)` | Coverage/layer/detail filtering and that edition's erroneous `MapMark`. |
| `map_extra_marks(w,edition,layer)` | Phantom marks printed on the sheet, separate from actual-world features. |

`MapKind` is nautical/road/tourist/military. `MapLayer` is coast/depth/towns/roads/landmarks/
lighthouses/hazards/airfields/moorings. Bounds are west/north/east/south in world metres, x east,
z south. Printed scale/detail describes the information on the paper; it grants no additional
features by zooming. The old general chart only labels major ports and has no aviation layer.

Renderer rules: apply the edition's smooth `map_position` transform to coastline/polyline
geometry, and `map_feature` to keyed features. Keys include `mooring:<place>:<dock>` and
`road:<canonical road index>`. Omitted features stay omitted. Misnames, displacements, erroneous
soundings and phantom hazards are printed data, not a UI warning revealing the error. Do not
copy current fronts, ships, aircraft, jobs or garrisons onto an old military sheet. Terrain,
settlement and road drawing can use canonical geometry through these filters; news/corrections
need their own explicit acquisition policy rather than silently updating the edition.

Content code uses `living_maps.offer_map_reward(w,job,copy,grantor)` to reserve an actual seller's
copy before agreement. Only a commission from that owner/funder qualifies. It is removed from
sale, mentioned in that person's offer, pinned while collection is pending, and released if the
job is cancelled/failed. Completing an unrelated job confers no right to a map. There is one
opening medicine commission with such a spare-sheet reward and an unclaimed old sheet at the
Porto warehouse. UI needed: a collection/browser, seller stock, physical pickup and reward
collection prompts, and drawing each selected edition's coverage/layers/style/errors.

`tests/living_maps.jo` checks conservation, paid transfers, proximity/funds rejection, gifts,
discovery, an actual on-foot delivery/reward, cancellation, old-map errors and deterministic
saves. `tools/maplog.jo` publishes the complete registry, prints its catalog, validates and
round-trips it, and verifies a second publication changes neither stock nor opening cash.

`map_features(w,edition,layer) -> MapFeature[]` is the preferred renderer input for named
features: already filtered/projected labels, positions and simplified line points, with stable
keys. Each edition stores a fixed feature-key set over shared immutable survey records; moving,
renaming or adding a world feature cannot update it. `map_feature` likewise uses the surveyed
record even when handed a different current position/name. Road lines are at most 33 vertices
and use segment/coverage intersection so a long line crossing a small sheet is retained.
Phantom marks are included once by `map_features` (do not also draw `map_extra_marks` in that
path). Cache these immutable edition projections in the UI rather than rebuilding them each
render frame. Survey storage is bounded to 8192 features and 65536 edition references.
