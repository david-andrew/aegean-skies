#!/usr/bin/env bash
# Serial, silent capture pack. See tools/judge_pack.py --help and docs/JUDGING.md.
set -euo pipefail
cd "$(dirname "$0")/.."
unset DISPLAY WAYLAND_DISPLAY
export SLOPPY_NO_AUDIO=1 SLOPPY_THREADS=1
judge_python="${JUDGE_PYTHON:-python3}"
if [ -z "${JUDGE_PYTHON:-}" ] && [ -x "$HOME/dev/tmp/aegean-skies/judging/.venv/bin/python" ]; then
  judge_python="$HOME/dev/tmp/aegean-skies/judging/.venv/bin/python"
fi
exec "$judge_python" tools/judge_pack.py "$@"
