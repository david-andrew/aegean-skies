Products of `sloppy --release tools/bake.jo` that the game would otherwise work out itself as it
starts (the coast microrelief tile, the islands' settlement registry). They are not committed:
CI bakes them before building. A checkout without them still builds and runs (it makes them at
startup, more slowly), and tests/baked_assets_test.jo checks a bake against what the code makes.
