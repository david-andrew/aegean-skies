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
with height: a low dome for humilis, a column with a rounded head for a turret.
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
low and medium the list is rebuilt every second frame. Clouds less than about
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
- **Painted light.** A terminator ramp on a mix of the local and the mass
  normal. A broad sunward self-shadow, never on sun-facing faces, where it
  reads as a crater. A rim light, and a darker flat base.

The third-resolution colour target, depth reconstruction, edge repair, decks,
rain and fog are as before. The visibility veil for blended effects
(`src/cloud_transparency.jo`) marches the same forms.

## Shadows (`src/cloud_shadow.jo`, `src/cloud_shadow_map.jo`)

Each frame the clouds near the camera are drawn into a coverage map in
sun-projected coordinates: a point P maps to `P.xz - k*P.y`, with `k =
sun.xz/max(sun.y, 0.12)`. That is where the sunlight through P meets sea level.

- **Map size by tier:** 384 px over 28 km on low (73 m texels, redrawn every
  second frame), 1024 over 36 km on medium, 1536 over 48 km on high (about
  35 m texels). It is centred ahead of the view and snapped to texels.
- **Fill.** The map fades to nothing over its outer eighth, so receivers need
  no edge test. Flat forms take three slab taps instead of four.
- **Drawing it.** One instanced quad per cloud covers its projected box. Four
  footprint taps (one per height slab) project the cloud along the sun.
- **Edges.** The penumbra widens with the slab's height above the ground.
- **Combining.** Overlapping clouds combine as coverage: `a + b(1 - a)`.

The shadows are applied in one screen-space pass (`apply_cloud_shadows`), after the
opaque scene and the water and before the clouds. Each pixel's world position comes
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
