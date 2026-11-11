# Aegean Skies

*A living-world aviation adventure in a sunlit, interwar Aegean.*

An open-world seaplane sandbox written in [Sloppy](https://github.com/david-andrew/sloppy-lang),
growing out of its Sky Barons example. Take off from a harbor, fly between islands, land in a cove,
taxi to a dock, get out and walk into town. The people of the archipelago go about their own lives:
trade, fish, smuggle, race, and fight, and the stories come from what they do.

**Play it in the browser:** https://david-andrew.github.io/aegean-skies/ (built from `main` on
every push).

## Running it

```sh
sloppy --release tools/bake.jo                     # once: bake the original islands and compact world data
sloppy aegean.jo                                   # play
sloppy build aegean.jo --target wasm --release -o site/index.html
python3 tools/package_web.py site/index.html       # HTML loader + separate wasm
```

The world spans 500 × 400 km around the unchanged original archipelago. Open the
chart with **M**; **Tab** switches between the whole world and the original local
chart. New land has no towns or harbors yet. `AEGEAN_WORLD=0` disables the expanded
geography for comparisons.

The game derives the original 14 m render surface from its existing 8 m source at
startup. This saves a second terrain download without changing any source heights
or geometry. New land uses a bounded tile cache; a teleport initially shows coarse
terrain while nearby tiles fill in. `tools/bake_world.jo` rebuilds only the compact
world field after editing its authored regions. See
[the design and measurements](docs/world-renderer-design.md).

Headless checks (no windows or audio):

```sh
env -u DISPLAY -u WAYLAND_DISPLAY SLOPPY_NO_AUDIO=1 SLOPPY_THREADS=1 sloppy test tests/geography_test.jo
env -u DISPLAY -u WAYLAND_DISPLAY SLOPPY_NO_AUDIO=1 SLOPPY_THREADS=1 sloppy --release tools/terrain_check.jo
# Use a path under ~/dev/tmp for SLOPPY_SCREENSHOT; never omit it for render checks.
env -u DISPLAY -u WAYLAND_DISPLAY SLOPPY_NO_AUDIO=1 SLOPPY_THREADS=1 SLOPPY_FRAMES=720 SLOPPY_SCREENSHOT="$HOME/dev/tmp/world-check.png" sloppy --release tools/world_flight.jo
```

## Layout

| file | what it holds |
| --- | --- |
| `aegean.jo` | the game: the loop, input, camera, what is drawn |
| `src/world.jo` | original islands and shared source/contact height queries |
| `src/geography.jo`, `src/world_terrain.jo` | authored mainland/islands, seeded detail, bounded quadtree renderer |
| `src/look.jo` | the light at each hour, and the shading every shader shares |
| `src/sky.jo`, `src/sea.jo`, `src/terrain.jo`, `src/clouds.jo` | the shaders and meshes of the world |

`src/erosion.jo` is a port of Rune Skovbo Johansen's Advanced Terrain Erosion Filter and Phacelle
noise, under the Mozilla Public License 2.0 (as stated in that file); the rest is the project's own.

See [docs/ART.md](docs/ART.md) for the art direction.
