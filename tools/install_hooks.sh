#!/bin/sh
# Point this clone (every worktree of it) at the repository's hooks: tools/githooks.
#   sh tools/install_hooks.sh
# pre-commit and pre-push run tools/check_tracked_files.py, which refuses scratch and reference
# material, recordings, soundfonts and big binaries. `git config --unset core.hooksPath` removes it.
set -e
cd "$(git rev-parse --show-toplevel)"
chmod +x tools/githooks/* tools/check_tracked_files.py
git config core.hooksPath tools/githooks
echo "hooks installed: core.hooksPath = $(git config core.hooksPath)"
