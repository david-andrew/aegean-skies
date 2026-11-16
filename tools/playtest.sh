#!/bin/sh
# tools/playtest.sh <case> [AEGEAN_X=... ...]: run one playtest case headlessly (tools/playtest_probe.jo)
# in its own save directory; prints its PLAYTEST lines and exits non-zero on a dead end.
case=$1; shift
dir=${PLAYTEST_DIR:-$HOME/dev/tmp/aegean-skies/playtest}/$case
rm -rf "$dir"; mkdir -p "$dir"
cd "$(dirname "$0")/.."
env -u DISPLAY -u WAYLAND_DISPLAY ${PLAYTEST_NO_DRAW:+SLOPPY_NO_DRAW=1} SLOPPY_NO_AUDIO=1 SLOPPY_THREADS=1 SLOPPY_FIXED_STEP=1 SLOPPY_WINDOW=640x360 \
    SLOPPY_FRAMES=$(( ${PLAYTEST_FRAMES:-3000} + 20 )) SLOPPY_SCREENSHOT="$dir/last.png" SLOPPY_SAVE_DIR="$dir/save" PLAYTEST_CASE="$case" "$@" \
    sloppy --release tools/playtest_probe.jo > "$dir/log.txt" 2>&1
code=$?
grep -a "PLAYTEST\|panic\|assert" "$dir/log.txt" | cut -c1-600
exit $code
