# Painted clouds

Cumulus, towers and anvils are world-oriented solids ray-marched against a baked
distance atlas, on every quality tier. Their light follows the real sun. Their
silhouettes stay fixed as the camera moves around them. Decks, rain curtains and
sea fog are analytic weather layers drawn by the same pass (`src/cloud_volume.jo`).
Everything is procedural: no reference pixels, generated images or traced shapes
enter the baker or the game.

## Forms (`src/cloud_density.jo`)

28 forms of eight kinds, each built from round lobes in metres, with the form's
x half-width as 1:

- **humilis:** flat-based caps, wider than tall, with a few large lumps on top;
- **fractus:** torn pieces with broken edges and a ragged base;
- **cluster:** a clump or short street of cells of power-law sizes on one base;
- **mediocris:** a heaped cell, sometimes with a smaller neighbour;
- **congestus:** a broad base cell and two to four rising turrets. A turret is
  a column of similar lobes, so a taller tower stacks more lobes rather than
  bigger ones. Side turrets lean on the main column; standing apart, their heads
  would arch over a window. Twin towers stand shoulder to shoulder at different
  heights.
- **anvil:** a massive body under a flat plate that spreads downwind at the
  tropopause, thick over the body and thinning to a ragged rim (a plate
  primitive smoothly joined to the lobes);
- **mass:** a large complex of cells.

`cloud_heap` fills an elliptical footprint layer by layer. Its profile narrows
with height: a low dome for humilis; for a turret, lobes piled on the flat base and
narrowing all the way to a domed head (a profile power of 1.4 to 2.2), each layer
stepped a little aside from the last, rather than a straight-sided column.
Exposed lobes carry the cauliflower: smaller heads, then smaller heads again,
never below one voxel. A shared cut gives every form the same flat condensation
base, at `p.y = -CLOUD_BASE` in the box. Fractus bases are torn rather than cut.

Forms come in four size classes. Each class's voxel grid has the aspect of its
box (flat 64x26x48, heaped 64x44x56, tower 48x64x48, anvil/mass 64x56x56), so
voxels are cubes in metres. Instances scale **uniformly**. Nothing is stretched;
only the depth varies by ±10%. Four forms of a class share each RGBA8 texel, one
per channel. A texel stores the encoded distance (0.5 at the surface, larger
inside, in units of the half-width).

The 2048x734 atlas takes 6.0 MB decoded. Below the slices, each form's top-down
footprint for cloud shadows holds four height slabs, the densest value of each
slab per column.

Normals are the distance's gradient from four tetrahedral taps about three
voxels apart. That wide reach gives the lobes' broad shoulders rather than every
crevice.

Rebake with `env -u DISPLAY -u WAYLAND_DISPLAY SLOPPY_THREADS=1 sloppy --release
tools/bake_clouds.jo`; it takes about 6 s and is included in `tools/bake.jo`.
`assets/clouds.png` is ignored and embedded at build time, so rebake after
merging. `CLOUD_ATLAS_OUT=/absolute/path.png` redirects a standalone bake.

## Field (`src/cloud_field.jo`)

There are three size octaves of persistent world cells: 1.6 km to 16 km, 6.5 km
to 70 km and 26 km to 150 km. Identities depend on seed and cell only. Occupancy
follows a coarse clumping cascade and wind-aligned streets, so clouds gather in
clusters and rows with clear lanes between, as a cumulus field seen from above.

A cell places a small group:

- **small octave:** two to five small clouds;
- **middle octave:** a main cloud with satellites;
- **large octave:** a big mass, or a street of heaped cells and clumps along a
  heading.

Sizes follow a power law within each octave. A placed cloud picks one of the
seeds of its kind, a heading, and a mirror (half are mirrored). Every cloud of
an air mass sits on its condensation level (`air.ceiling`).

Each frame needs only some clouds: those that can be in view (a cone around
the camera's forward, conservative for the cloud's size and the curved horizon)
or that can shadow the shadow map (`cloud_needed`). Only these are evolved. On
low and medium the list is rebuilt every third frame. Clouds less than about
two pixels wide fade out (`smoothstep(0.0025, 0.005)` on half-width over
distance). The small octave reaches 13 km.

Life: a cloud swells (0.72 to 1.06 of its size) and wears away (erosion of its
distance) at its own proportions.

Towers: a heaped middle-octave cell carries a tower form, and some small cells
a small one. `cloud_tall` measures how strongly the air builds towers: the
towers weather, or afternoon heating over land, weighted by the cell's tone.
In the growth band the tower rises at its own proportions out of the heaped
cloud, scaled up from 0.4 while the heaped form wears away inside it.
`world_clouds` emits both for that band. An eroding tower would turn into a
skeleton of holes. Below the band only the heaped form shows, above it only
the tower.

## Drawing (`src/cloud_volume.jo`)

Each instance is a screen-space quad over its projected support box. The ray
marches distance steps in metres, refined only near the surface.

- **Close relief.** Within 60 m of a body's surface, two octaves of billowed
  value noise (95 m and 38 m, in the cloud's own metres) break up the
  silhouette into rounded bulges with creases. They fade with the size of a
  low-resolution pixel and are kept off the flat base. They enter the light
  only at 30%: full relief shading reads as crumpled paper.
- **Antialiased edges.** A ray that misses is still partly covered if it passed
  within three hit tolerances of the surface. Upsampled from the third-resolution
  target, the silhouette is soft rather than stepped.
- **Painted light.** Flat bands on a mix of the local and the mass normal:
  shade, cream, and full white on the lumps turned most to the sun, with narrow
  transitions. Two values as the film paints them: cream lit tops (`paint_light`,
  never mint) and a slate blue-grey shade (`paint_shade` 0.33, 0.43, 0.55) 15-25 L*
  darker, the lower body in the shade band whatever the light. Far clouds take the
  air's haze three quarters grey, so a front-lit far tower stays cream and slate
  rather than cyan (a far tower at 600 m: lit L* 67, shade 51). A broad sunward self-shadow, never on sun-facing faces, where it
  reads as a crater. A rim light, and a darker flat base.
- **Brushwork.** Brush strokes in the cloud's own metres curl round each lobe
  along the terminator (`cloud_strokes`): they break every band edge into
  dry-brush cuts and pool pigment along the strokes. Beyond the close relief,
  scalloped brush dabs break the silhouette (`cloud_brush`; not on the low tier,
  where its noise at every march step near a surface cost redfox about 0.3 ms). Both stay a few
  pixels across at any distance, stepping through blended octaves in metres so
  nothing swims, and never reach more than a tenth of a cloud's size. A storm's
  cloud adds broad strokes at its own scale and layers its bands darker toward
  the base and brighter toward the top; it skips the self-shadow probe, whose
  cut drew round holes at that size. A storm's cells and canopy also skip the close relief and the
  brush dabs and step longer to a coarser tolerance: at kilometres across that detail
  showed nothing and cost redfox medium about 2 ms near a storm (the shelf keeps both
  for its ragged lit lip). The strokes and dabs are keyed to the low-resolution pixel
  they land in, never finer, so they don't flicker pixel by pixel on shaded sides. The strokes live in the shader, not the
  atlas: every RGBA8 texel already holds four forms.

The third-resolution colour target, depth reconstruction, edge repair, decks,
rain and fog are as before. The visibility veil for blended effects
(`src/cloud_transparency.jo`) marches the same forms.

## Shadows (`src/cloud_shadow.jo`, `src/cloud_shadow_map.jo`)

The map is redrawn only every few frames (below), so "each frame" means each
redraw: the clouds near the camera are drawn into a coverage map in
sun-projected coordinates: a point P maps to `P.xz - k*P.y`, with `k =
sun.xz/max(sun.y, 0.12)`. That is where the sunlight through P meets sea level.

- **Map size by tier:** 384 px over 28 km on low (73 m texels), 640 over 36 km
  on medium (56 m), 1536 over 48 km on high (31 m). Each redraw draws every
  cloud with four taps a texel: at 1024 px on medium that burst cost redfox about
  0.4 ms a frame. It is centred ahead of the view and snapped to texels.
- **Fill.** The map fades to nothing over its outer eighth, so receivers need
  no edge test. Flat forms take three slab taps instead of four.
- **Drawing it.** One instanced quad per cloud covers its projected box. Four
  footprint taps (one per height slab) project the cloud along the sun.
- **Edges.** The map holds two channels: the outline's coverage as a smooth
  ramp about a texel each side (x), and the shadow's strength (y, the cloud's
  opacity and the edge fade). The full-resolution multiply cuts the ramp sharp
  (`cloud_shadow_edge`): a quick transition with a hint of softness, never
  narrower than the ramp's change across a pixel, which would stair-step. The
  reduced-resolution tint and ramp are smooth, so they enlarge cleanly.
- **Combining.** Overlapping clouds combine as coverage: `a + b(1 - a)`.
- **From height.** As the film shows them, shadows grow lighter and softer as one
  climbs (`cloud_shadow_apply.jo`, from 150 to 1500 m: on the sea from about 10 L*
  darker to about 2 at 1300 m), and a small cloud's shadow fades with the viewer's
  height (`cloud_shadow.jo`, by its size against the eye's height). Close to the
  ground they keep their defined edge.

The shadows are applied in screen space (`apply_cloud_shadows`), after the
opaque scene and the water and before the clouds: a tint factor computed at a
quarter (low), a third (medium) or half (high) resolution (the shadows are soft, and its two dependent
fetches a pixel cost 0.87 ms at full resolution on redfox), then multiplied
into the scene at full resolution. Each pixel's world position comes
from the scene depth (on water that writes none, from the curved sea), so the shadow
falls offset by the sun's angle and lands at the right place on hills and roofs. The
map darkens it by a cool tint: navy over deep water, deeper teal over the shallows,
land keeping its colour. A multiply keeps the sea's small marks at their contrast.
The sea itself takes only a per-vertex value (`sun_lost`) to drop the sun's glints
and sheen in shadow.

Why not in the receivers: main's ground, painted-object and blended-effect pixel
shaders sit at the edge of what Intel GPUs (the UHD 620 on redfox) can compile at
SIMD16. Any added live value, even one varying, made them fall back to SIMD8 and
cost about 0.2 ms with shadows off. The screen pass leaves them untouched;
`INTEL_DEBUG=fs` on redfox lists SIMD16 compiles to check this. For the same
reason the transparency veil derives each form's atlas layout from one packed
index (`cloud_stamp_value_of`) rather than carrying it.

The fade:
- Things well above the cloud bases are not shaded: 400 to 1800 m over the
  condensation level near the camera. That covers an aircraft over the field
  and high peaks. The map holds coverage only, no heights.
- Shadows fade out with a low sun, and at the map's edge.

The map is redrawn every 8 frames on low and medium (2 on high), sooner when
the camera has moved 600 m or the sun has turned. It is anchored in the world,
so between redraws only the clouds' own centimetres of drift wait; no stepping
shows and no second map is blended.

All shaders stay within WebGL2's guaranteed limits (`tools/check_web_shaders.cjs`).

## Storms (`src/lightning.jo`, `src/storm_render.jo`, `src/weather_scene.jo`)

- **A system, drawn as few large pieces** (`storm_system_clouds`): a saved storm is about 26 km
  across. Its layout (`storm_cells`) places four cells at fixed places in its frame turned
  downwind; the cells, the rain shafts and where lightning strikes all share it.
  - The deck (weather kind 10): a dark layer from a ragged 1150 m base, lumps of it hanging
    lower, to 3.4-3.9 km, above the flight ceiling, without gaps. Its wall is sharp at its rim;
    its samples are spaced as squares from where the ray enters it, so its colour comes from
    just inside the wall rather than kilometres in (evenly spaced samples drew the wall as tiles).
  - The shelf cloud (kind 9): an analytic distance of three tiered, tapered, waved rolls along
    the leading edge, marched and painted as a body; lighter on its lit upper edges, dark beneath.
  - The cells: anvil, tower and mass forms at their stages, 3.5-7 km half-widths.
  - The anvil canopy (kind 11): an analytic plate, thick over the middle and thinning to a ragged
    rim, painted as a body.
  - The rain shafts (kind 8) under the cells, hazed less than the air so they show from 40 km.
  - The rain veil (kind 6, `weather.y` 2): a slate curtain filling the space under the system
    from its base to the sea, hazed less than the air like the shafts, so from 10-40 km the
    storm reads as reaching the water rather than a slab floating over it.
  - The palette: near-black slate bellies and deck, a slate blue-grey shade, cream-grey lit
    tops (`cloud_paint` by `weather.y`).
  - Distance LOD comes from the march's own step budget; the far view is cheap.
- **Sound** (`src/storm_sound.jo`): rain on the airframe, gusting wind with the roughness, and
  thunder from the same strikes as the bolts, after their distance.

- **Lightning.** One deterministic schedule per saved storm (`lightning_slot_strike`):
  time is cut into 5.5 s slots, four in five hold a strike, 45% of them cloud to
  ground. A strike has three or four return strokes over 0.55 s. Its channel
  (`lightning_bolt`) is a jagged walk with forked branches: from 400 m inside the
  cloud to the sea, or crawling just under the base. The bolts are camera-facing
  ribbons at least about two and a half pixels across, with a bloom, dimmed but
  never hidden by cloud and rain. The same strike lights its cloud from inside
  (`cloud_flash`, falling off over about 3 km), flashes the sky near it, and is
  heard after its distance: on the ground at 343 m/s (`ambience_thunder`); from the
  aircraft (`src/storm_sound.jo`) at that speed times the speed scale, so a strike 10 km
  off is heard some 9 s after its flash, out to 25 km, its roll made loud enough to stand
  8 dB or so over the cockpit's engine, wind and rain.
- **Rain shafts** (weather kind 8): a few dark columns and curtains under the
  storm's core, clear air between, the lower rain carried downwind (the layer's
  box turns with the storm's wind), streaked, and ragged scud hanging under the
  base. The march holds to their cylinder, six samples. The squall's veil is
  thinner under a storm.
- **Rain inside and under a storm.** A second, denser set of streaks; streaks
  follow the airflow and lengthen with speed. Beads on the windscreen in the
  cockpit. Near a storm's core the view closes in, darker and greyer.
- **Inside a cloud.** The mist carries darker and lighter masses at a few tens of
  metres, sampled along the view in world metres, so they rush past with speed and
  turbulence. `CLOUD_INSIDE_SIZE`, `_CONTRAST` and `_BRIGHTNESS` tune it;
  `AEGEAN_CLOUD_INSIDE="size contrast brightness"` overrides them without a rebuild.
- **Turbulence** (`weather_turbulence`): the bodies of the clouds near the camera
  (`cloud_weather_bodies`) make the air rough inside them, 0.12 in fair cumulus up
  to 1 in a thunderstorm, plus the gust front under a storm. It reaches the flight
  model twice: eddies and drafts in the wind (`weather_turbulent_gust`), and roll,
  pitch and yaw kicks, each the change of a bounded displacement
  (`_turbulence_kick`), so the aircraft is knocked about its path and comes back;
  and the storm's push (`_storm_push`): irregular roll, yaw and pitch, each part a
  share of the type's own control rates and part common, so a fast, stiff racer and a
  heavy boat are thrown about too. Under a storm the gust front and downbursts make the
  air rough 0.7 wherever its rain falls. The push on the heading and climb turns the
  mouse's aim with the nose (`gust_turn`, `aim_gust`): the mouse's steering holds the
  aircraft steady but not on course, so one flies a storm by the compass and the
  attitude indicator, bringing the aim back. `tests/storm_test.jo` flies the game's own
  storm air (the cell, the deck and the cloud bodies, through `flight_env`, on the
  player's speed scale) with every type: hands off on the keys it is banked and off its
  heading within 20 s and in trouble no sooner than 7 s; hands off with the mouse it is
  turned off its course and carried up or down; a correcting pilot gets each through.

## Developer controls

These are not game UI.

- `AEGEAN_CLOUD_SHADOWS=0` turns shadows off.
- `AEGEAN_CLOUD_SHADOW_SKIP=sea` leaves the sea's glints in shadow (cost
  measurements).
- `AEGEAN_CLOUD_TIMELAPSE=k` runs the clouds' drift and lives k times faster.
- `AEGEAN_CLOUD_FRAMES=dir` saves every second frame from frame 60. With `ffmpeg
  -framerate 30 -i dir/%05d.png -crf 18` it makes clips of moving shadows.
- `tools/cloud_pilot.jo` takes `CLOUD_STAMP=n` and `CLOUD_WIDTH=m` to show one
  form at its own proportions. `CLOUD_VIEW`, `CLOUD_EYE`, `CLOUD_TARGET`,
  `CLOUD_HEADING` and `AEGEAN_HOUR` place the camera and sun.

For a reproducible comparison against a local reference, build the pilot and run:

```
python3 tools/cloud_tune.py --binary /absolute/path/to/cloud-pilot \
  --reference /absolute/path/to/local/reference.jpg \
  --film-box 0,500,520,1020 --output /absolute/scratch/comparison
```

Reference material stays outside the repository and the build. A crop
comparison is a diagnostic, not evidence of indistinguishability.
