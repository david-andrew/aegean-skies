#!/bin/bash
# The link-card picture the web page shows when its address is shared (Open Graph / Twitter card):
# 1200 x 630, one frame of the game itself, rendered by the game's own renderer with a fixed view
# and hour and none of the screen's text over it (AEGEAN_CAPTURE_CLEAN). Nothing drawn or generated
# elsewhere.
#
#   tools/site_preview.sh site/web/preview.png
#
# The committed site/web/preview.png is what the Pages build publishes (via aegean.jo's build block
# `page_files = "site/web"`): it was drawn on the GPU
# (headless Vulkan; the bakes are needed, as for any run of the game), because CI's software
# renderer draws this view's low sun and its clouds wrongly (white and coloured blocks over the
# sun). SITE_PREVIEW_SOFTWARE=1 uses the software renderer to compare. Redraw it with this script
# when the look of the sea, sky or aircraft changes enough to want a new card.
#
# The view: the home harbour's seaplane in flight at 250 m, seen from 34 m off its right side and
# a little ahead, against the sea with the low sun's glitter, a headland and its harbour town on
# the right, half an hour before sunset. The frames count only settles the terrain (the camera is
# set once, the aircraft flies on from it). Change PREVIEW_* to try another view.
set -euo pipefail
cd "$(dirname "$0")/.."
out=$(realpath -m "${1:?usage: site_preview.sh OUT.png}")
work=$(mktemp -d "${TMPDIR:-/tmp}/site-preview.XXXXXX")
trap 'rm -rf "$work"' EXIT
export SLOPPY_NO_AUDIO=1 SLOPPY_THREADS=1 SLOPPY_SEED=12345 SLOPPY_WINDOW=1200x630
if [ -n "${SITE_PREVIEW_SOFTWARE:-}" ]; then export SLOPPY_SOFTWARE=1; fi
env -u DISPLAY -u WAYLAND_DISPLAY \
  AEGEAN_TITLE=0 AEGEAN_CAPTURE_CLEAN=1 AEGEAN_SETTLE=1 \
  AEGEAN_FLYING="${PREVIEW_FLYING:-250 60}" AEGEAN_HOUR="${PREVIEW_HOUR:-17.5}" \
  AEGEAN_CRAFT_VIEW="${PREVIEW_CRAFT_VIEW:--0.8 0.05 34}" \
  AEGEAN_SKY_AIR="${PREVIEW_SKY_AIR:-clear}" \
  AEGEAN_SUNSET="${PREVIEW_SUNSET:-amber}" \
  AEGEAN_SUNSET_VIVID="${PREVIEW_SUNSET_VIVID:-medium}" \
  AEGEAN_AUREOLE="${PREVIEW_AUREOLE:-normal}" \
  AEGEAN_FLASH="${PREVIEW_FLASH:-none}" \
  AEGEAN_BISHOPS_RING="${PREVIEW_BISHOPS_RING:-off}" \
  AEGEAN_CORONA="${PREVIEW_CORONA:-off}" \
  SLOPPY_FRAMES="${PREVIEW_FRAMES:-30}" SLOPPY_SCREENSHOT="$work/raw.png" \
  sloppy --release aegean.jo
python3 - "$work/raw.png" "$out" <<'PY'
import sys
from PIL import Image
im = Image.open(sys.argv[1]).convert("RGB")
assert im.size == (1200, 630), im.size
im.save(sys.argv[2], optimize=True)
import os
size = os.path.getsize(sys.argv[2])
if size > 900_000:
    # (the sky's fine dither does not compress: 256 colours, dithered, keeps the card light)
    im.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG).save(sys.argv[2], optimize=True)
    size = os.path.getsize(sys.argv[2])
print(f"site preview: {sys.argv[2]} {im.size[0]}x{im.size[1]} {size} bytes")
assert size < 1_000_000, size
PY
