# Painted clouds

Cumulus and storm towers are three camera-facing painted sheets, on every tier.
`src/cloud_paint.jo` paints eight deterministic cloud formations into RGB pigment /
A coverage sheets. It consumes no image assets. Seeded rising plumes carry
power-law child discs; shared parent shadow shapes, ragged light cuts and broad
pigment washes establish the values. Tangential soft stamps vary brush width,
opacity and bristle gaps. Fine noise models dry brush, pigment pooling and paper
tooth. A common cool underside fades near the condensation level.

The baker paints at 512×512, then downsamples with premultiplied coverage into
256×256 sheets. The 1536×1024 runtime atlas uses 6 MiB of decoded RGBA8 storage.
No learned weights, traced silhouettes or reference pixels enter the baker or
game. Reference images, including earlier rejected generated art, stay in scratch.

Rebake with `SLOPPY_THREADS=1 sloppy --release tools/bake_clouds.jo` (also included
in `tools/bake.jo`). `assets/clouds.png` is ignored and embedded at build time, so
rebake before building after merging. The old density atlas is incompatible.
`CLOUD_ATLAS_OUT=/absolute/path.png` redirects a standalone bake for measurement.

The far sheet contains the whole silhouette; two nearer sheets carry overlapping
plumes. Their depths and lateral offsets provide modest parallax. The foreground sheets
are pigment-selected fragments of the procedural painting with feathered boundaries. Coverage and
ray/plane intersections are shared with vapor trails. Scene depth clips every
sheet. Interior fog bridges entry through the sheets; it is an approximation,
not a simulation of volumetric density. Clouds face the eye and therefore do not
have a fixed three-dimensional silhouette. Overhead views lighten the paintings.

Clouds use a third-resolution color target on all tiers (quarter for overlapping
rain/deck layers) with full-resolution screen-pixel paper grain,
scene-depth reconstruction and edge repair. The four-band luminance ramp,
softened with an 80% within-band wash, is fused into the cloud draw. A native-resolution pilot exceeded the laptop budget and was
rejected. Low-sun shafts retain the existing composite path. Dense weather
disables the extra screen grain for cost; brush texture remains in the paintings.
Weather layers use four analytic samples; both color and trails share that count.
Dense weather writes the depth-repair decision into the scene target’s existing
spare depth renderbuffer. Hardware depth rejection then skips resolved pixels
for every layer. It uses the exact existing reconstruction threshold and adds
no texture allocation; the actual scene depth is detached and sampled read-only.
Ordinary fair clouds use the direct nearest-guide bound.
World identities, cloud lifecycle, wind and saved weather records are unchanged.
Midday sky uses a teal pigment locally; shared terrain lighting is unchanged.

For a reproducible comparison, build `tools/cloud_pilot.jo` and run:

```
python3 tools/cloud_tune.py --binary /absolute/path/to/cloud-pilot \
  --reference /absolute/path/to/local/reference.jpg \
  --film-box 0,500,520,1020 --output /absolute/scratch/comparison
```

Pass `--painted-reference /absolute/scratch/approved-crop.png` for a three-way
film / approved reference / procedural comparison. This optional file is read by
the comparison script only; it is never used by the baker or renderer.

The tool requires Pillow. It launches one silent headless render, crops/resizes
without grading, and writes a comparison PNG, HTML and settings JSON. `--kind`,
`--heading`, `--hour`, `--distance`, `--quality`, `--light`, `--shade`, and `--grain` control the
actual shader, without recompilation. The last three map to developer environment
variables `CLOUD_PAINT_LIGHT`, `CLOUD_PAINT_SHADE`, `CLOUD_PAINT_GRAIN`. Structural
changes to the masks require rebaking and rebuilding. These controls are not game
UI. Reference material stays outside the repository and game build.

A crop comparison is a diagnostic, not evidence of indistinguishability. Check
whole formations, different sun angles, motion, overhead/inside views and depth
occlusion as well as shuffled label-hidden crops. Record guesses before opening
the key; self-review is not an independent reviewer.
