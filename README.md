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
sloppy --release tools/bake.jo                     # once, and after changing the islands: bakes the eroded land
sloppy aegean.jo                                   # play
sloppy build aegean.jo --target wasm -o index.html # the web page
```

## Layout

| file | what it holds |
| --- | --- |
| `aegean.jo` | the game: the loop, input, camera, what is drawn |
| `src/world.jo` | the archipelago: islands and the height of the ground anywhere |
| `src/look.jo` | the light at each hour, and the shading every shader shares |
| `src/sky.jo`, `src/sea.jo`, `src/terrain.jo`, `src/clouds.jo` | the shaders and meshes of the world |

`src/erosion.jo` is a port of Rune Skovbo Johansen's Advanced Terrain Erosion Filter and Phacelle
noise, under the Mozilla Public License 2.0 (as stated in that file); the rest is the project's own.

See [docs/ART.md](docs/ART.md) for the art direction.
