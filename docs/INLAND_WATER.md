# Stable lake integration seam

Implement `src/lake_field.jo` (pure; no terrain-source/render/unified-water imports):

- `lake_at(x:f64,z:f64)->WaterSample`
- `lake_carve(x:f64,z:f64,h:f64)->f64`
- `lake_key()->u64` (hash authored data and version; currently zero)

`WaterSample` is in `src/water_types.jo`. Set `kind=.lake`, stable `id>=100000`,
`found=true` in the bounded lake corridor, `wet=true` in the actual footprint,
`level` in world metres, `current` in metres/sec, `slope` as dy/dx,dy/dz.
`distance` and `width` also drive bounded terrain refinement around small inland waters.
`segment/lateral/bend/along` are optional river-specific fields. Existing `river_at`
returns the same type (the RiverSample type alias remains).

Gameplay's stable call is **`water_at(x,z)`** in `src/water_field.jo`:
covered lake > covered river > dry lake corridor > dry river corridor > ocean plane.
Ocean fallback has kind=ocean/id=0/level=0/found=false/wet=false: exact exposed
water versus land is still decided by the terrain and sea contact, not a recursive
terrain lookup in this pure field. `water_current` returns zero outside covered inland water.

Already wired: float/water height and slope through swell_at/flight_env, float current,
walking water rejection, spray/lens wetness, wake height/current, boats and depth guards,
grass/tree exclusion, terrain refinement and carving. Geography keys include lake_key.
The ocean appearance and swell path are retained for the ocean fallback.

Rendering: `src/river_render.jo` exports `InlandWaterVertex`,
`inland_water_vertex(p:vec3)` and
`draw_inland_water(surface:Mesh,center:vec3,depth:Texture,L:Light,t:f64,velocity:vec3)`.
Build lake triangle meshes with inland_water_vertex at the source's actual level;
it samples authoritative bed depth, current and world-metric detail coordinates.
Call draw_inland_water in the same transparent phase as draw_rivers, after init_rivers.
The lake renderer owns mesh residency and bounds; this function has no river bounds.
It uses the exact same sea mark function, scales, density and contrast as river/canal
water. A zero-current lake's fine detail stays world-anchored; nonzero current advects it.
No further edits to floats, walking, wakes, spray or water material are required.
