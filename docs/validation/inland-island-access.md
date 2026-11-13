# Quota-stop checkpoint: Olythandra corrected survey

Quota reached **100% used / 0% left**. No further runs were started. Runtime remains the tested `26739b6`; **44 gaps remain**. No new island is claimed connected in this resume.

The original Olythandra candidate was installed provisionally and gained a hull-validated 3.682 km sea route to Olythenos (309890). Physical acceptance then **failed**: the ramp crossed a low rise, burying its deck; the approach clipped an olive-press wall that the old footprint survey omitted. The provisional landing, sea link and manifest were reverted before checkpointing.

The corrected offline survey checks the full ramp centre profile and the player's complete walking query (including working buildings), not only settlement footprints. It finds **6 candidates**, selecting an **8-point** route to root **(-17422.355, 2.183593, 81806.64)** and tip **(-17333.969, 1.2, 81718.25)**. Exact data is in JSON `latest_survey.landing_source` and scratch `shore-301041-v2.txt`. The updated probe checks/executes successfully. It is still **not installed**: full quay/loading/mooring contact and sea-service validation remain.

New offline tools: `install_island_landing.jo` preserves existing landings; `bake_island_sea_access.jo` appends a hull-verified route without renumbering old services. Both checked and executed on the rejected provisional candidate; their mutations were reverted. Keep them in the validation workflow, never treat installation alone as acceptance.

A runtime migration issue also surfaced: the layout key omits catalogue links, so saves with unchanged town coordinates can miss a new ship service. The unfinished fix and regression checks are preserved in `~/dev/tmp/aegean-skies/towns/inland/olythandra-pending-runtime.patch`, **not in the tested runtime**. On resume, apply/review it, install the corrected landing, rebake its sea connection and manifest, then run access/contact and real-save migration before committing the island. Prior failing logs remain `test-301041.log`; successful stronger survey is `shore-301041-v2.log`. No Redfox or live jobs.

# Follow-up survey checkpoint (runtime 26739b6)

**44 gaps remain.** Two roads are committed separately: Myrevilaki in `ab604e7`, Velyinanti in `26739b6`. Native low-tier air/street captures are `inland/island-{301551,303831}-{air,street}.png`; native release build succeeds. These are functional captures, not timings or a visual gate. The thin tracks can be seen from the air. The street cameras also expose the existing steep village paving, so do not treat them as a sign-off on village presentation.

The bounded precise 4 m search (300 m margin, 180,000 closed-node limit) finds no road for **Istrinatha 300321** or **Melavilerio 300381**. Both ends have dry clear exits; the bounded failure does not prove no route exists. Their old state is unchanged.

A new **read-only** `tools/probe_island_shore.jo ID SCRATCH_FILE` preserves all shipped landings. It varies shore-root inset (8/12/18/25/35/50 m) and tip reach (60/90/110/140 m), retains the actual 5 m quay and mooring clearances, and surveys at most six ranked candidates with close-contact-aware pathfinding. It deduplicates tip choices for each root before spending a route search. It does not silently narrow the quay while leaving loading/contact positions wide.

**Olythandra 301041:** old fixed survey found zero candidates; variable distances yield **7**, and the best has a verified **7-point** approach. Root **(-17378.625, 2.0101917, 81935.19)**; tip **(-17287.162, 1.2, 81874.07)**. The exact generated candidate is retained in the JSON inventory's `latest_survey.landing_source`. **Not installed, not counted served**: precise full walk, quay/loading contact, actual ship route, catalogue/manifest update and migration remain. This is the first next task. No Redfox was used.

# Second island road checkpoint

Velyinanti **303831** → Thalvathavos **303830**: **1,893.861 m / 120 points**, using its existing harbour. Both new island roads pass the full precise-contact walk and dry wagon-width checks. Fresh audit: **750/794 served, 44 unresolved**, **1,240 links**. Real migration preserves all 1,238 c767023 links and economic/identity state. Save access version 3 upgrades version-2 checkpoints too. Evidence uses suffix `-303831.log` in the same scratch directory. Render review/main integration remain pending. No Redfox.

# Island access repair checkpoint

Myrevilaki **301551** now has a **1,456.409 m / 91-point** wagon-width road to Ardevalanti **301550**, using its existing harbour and two moorings. Fine-grid routing checks the actual walking capsule/frontages as well as the older terrain/footprint validator. The first candidate failed precise contact 6 m outside the square; it was discarded. The replacement passes a continuous 25 cm walking sweep.

Fresh audit: **749/794 served, 45 unresolved**, catalogue **1,239 links**. Migration from c767023 preserves all 1,238 previous links, identities, population, money, goods and ledger. Access-upgrade version 2 also adds this road to saves already upgraded to version 1. Three access-connection tests, working-land tests, flight tests and checks of all edited Sloppy files pass.

No new quay or harbour geometry. Scenery consumes the same published cart path. Air/street render review and current-main integration remain pending; no Redfox started. Logs in `~/dev/tmp/aegean-skies/towns/inland/`: `road-301551-precise.log`, `test-301551.log`, `inland_access_audit-301551.log`, `validate_access_migration-301551.log`. The JSON inventory contains only the 45 still unresolved places, with Myrevilaki moved to `resolved`.

## Original hand-off (historical 46-place inventory)

# Unresolved island access: implementation 4331981

**Hand-off, not a claim of completion.** The shipped manifest has 46 unserved small-island communities. All mainland communities are served. The fresh read-only probe `tools/audit_island_access.jo` reproduces the same 46 IDs as the earlier complete catalogue audit; no town, route or landing was changed in this resume. Exact coordinates, populations, categories and evidence hashes are in [the machine-readable inventory](inland-island-access.json).

## Findings and first actions

- **4 existing harbours, missing roads.** `tools/bake_shore_access.jo` skips a town when registry ID `id-1` exists, assuming its coastal sibling supplies access. These four siblings have two moorings each, but the town has no graph route to them. All four direct segments fail `feeder_segment_clear`; they need surveyed contour routes, not a straight painted line or another harbour.
- **32 with no shore candidate under the old survey.** That survey checks 32 radial directions, a root exactly 25 m inland, root height 2–18 m, cross-bank samples at ±2.5 m differing by at most 0.8 m, and an offshore tip fixed 110 m out. This is not proof that no natural landing exists. Survey variable root/tip distances and actual coast normals; retain water/terrain clearance. Narrow landing designs must keep rendering, walking and loading positions consistent: `LandingAccess.width=1.8` currently does not reduce `build_lake_port`'s fixed 5 m quays or its ±1.7 m loading offsets.
- **10 with shore candidates but no verified path among attempted candidates.** The baker tries only the best six. Vathrilyra, Vathravaki, Delyoria and Alevaneli have respectively 1, 4, 2 and 3 further candidates that were never tried. Try those before changing terrain or expanding the search. For the others, inspect grade, route width, intermediate buildings, the shore endpoint and the A* search bound.
- **Town-centre obstruction is not the observed cause.** The fresh probe reports zero building displacement and dry centres at all 46 places. This does not certify a wagon-width exit or the other route endpoint; inspect those separately.

The shore counts below come from the previous survey log, not a newly repeated coast survey. The current manifest and centre/harbour checks are fresh. The relevant registry, geography, shore-data and route-catalogue files are unchanged between the earlier catalogue audit and implementation 4331981.

## Scope and acceptance for the next implementation slice

Keep stable IDs, names, households and trades. Do not move these communities to the mainland or fabricate a lake. Start with the four existing-harbour connections and the ten untried shoreline candidates. Preserve the four already-working surveyed island landings in `src/shore_access_data.jo`.

Owned starting points: `tools/bake_shore_access.jo`, `src/access_path_bake.jo`, `src/living_feeder_bake.jo`, `src/shore_access_data.jo`, and the settlement-side landing adapter `src/lake_ports.jo` if changing quay width. Treat `assets/living-routes.bin`, `src/inland_access_data.jo`, collision and rendering as coupled outputs. Do not edit river data or carving. The current shore baker rewrites its output incrementally; write exploratory surveys to scratch before replacing validated data.

For each proposed connection: check the entire route and width on canonical terrain/water; render the track from the air; walk it through precise contact; verify the quay, loading points and mooring; then rebake living routes and the access manifest from the integrated tree. Preserve paid services and validate migration, cargo and resident travel. Test phone density and contact/depth at new structures; use the normal visual sample gate. Refresh this inventory after rebaking and never label a settlement served merely because it has a nearby harbour.

## Inventory

Coordinates are world metres `(x, y, z)`. Population is the current registry size converted by the same rule as the inland report. Candidate counts do not imply usable runways or routes.

### Existing landing; road missing (4)

| ID | Name | Kind / residents | Country | Centre (x, y, z) | Evidence / next target |
| --- | --- | --- | --- | --- | --- |
| 300321 | Istrinatha | hill / 64 | Kalyra | 10805.61, 106.84, -34912.16 | Velyyra (300320), 4048 m straight-line; 2 moorings; direct segment rejected |
| 300381 | Melavilerio | hill / 64 | Kalyra | -54902.98, 29.33, 13018.71 | Olytherenia (300380), 3855 m straight-line; 2 moorings; direct segment rejected |
| 301551 | Myrevilaki | hill / 64 | Kalyra | -65239.91, 80.80, 47877.69 | Ardevalanti (301550), 959 m straight-line; 2 moorings; direct segment rejected |
| 303831 | Velyinanti | hill / 64 | Kalyra | -67359.78, 87.53, 59081.91 | Thalvathavos (303830), 1311 m straight-line; 2 moorings; direct segment rejected |

### Shore candidates; verified route missing (10)

| ID | Name | Kind / residents | Country | Centre (x, y, z) | Evidence / next target |
| --- | --- | --- | --- | --- | --- |
| 300341 | Myrevavaki | hill / 64 | Kalyra | 49000.00, 190.43, 8000.00 | 1 candidates; at most 1 tried; 0 untried |
| 300351 | Vathrilyra | hill / 64 | Kalyra | 30235.54, 244.60, 40825.77 | 7 candidates; at most 6 tried; 1 untried |
| 300411 | Vathravaki | hill / 64 | Kalyra | -32000.00, 316.91, 85000.00 | 10 candidates; at most 6 tried; 4 untried |
| 300421 | Delyilenos | monastery / 64 | Orenthia | 130000.00, 115.37, 138000.00 | 1 candidates; at most 1 tried; 0 untried |
| 300451 | Myrevananti | monastery / 64 | Kalyra | 56031.88, 237.74, -157491.50 | 1 candidates; at most 1 tried; 0 untried |
| 300501 | Delyoria | hill / 64 | Kalyra | -43981.72, 251.04, -17454.14 | 8 candidates; at most 6 tried; 2 untried |
| 300561 | Alevaneli | hill / 64 | Kalyra | 48551.51, 155.49, 48915.86 | 9 candidates; at most 6 tried; 3 untried |
| 300601 | Alevinara | monastery / 64 | Kalyra | 79069.12, 256.20, -179954.33 | 1 candidates; at most 1 tried; 0 untried |
| 304391 | Myrevilandra | hill / 64 | Orenthia | 136458.03, 180.69, 49466.31 | 1 candidates; at most 1 tried; 0 untried |
| 308371 | Melaveroria | monastery / 64 | Orenthia | 140563.69, 74.58, 54398.85 | 2 candidates; at most 2 tried; 0 untried |

### No candidate under the previous fixed survey (32)

| ID | Name | Kind / residents | Country | Centre (x, y, z) | Evidence / next target |
| --- | --- | --- | --- | --- | --- |
| 300331 | Velyineli | monastery / 64 | Kalyra | 39000.00, 236.36, -29000.00 | 0 candidates under fixed root/width constraints; resurvey |
| 300361 | Teryavavos | monastery / 64 | Kalyra | -5954.48, 201.09, 57043.84 | 0 candidates under fixed root/width constraints; resurvey |
| 300371 | Neravalissa | hill / 64 | Kalyra | -42000.00, 284.06, 47000.00 | 0 candidates under fixed root/width constraints; resurvey |
| 300391 | Thalvissa | monastery / 64 | Kalyra | -44610.49, 306.30, 455.33 | 0 candidates under fixed root/width constraints; resurvey |
| 300401 | Ardevathona | hill / 64 | Kalyra | -60843.42, 250.33, 67724.17 | 0 candidates under fixed root/width constraints; resurvey |
| 300431 | Kalyalissa | hill / 64 | Orenthia | 144812.78, 223.81, 98155.02 | 0 candidates under fixed root/width constraints; resurvey |
| 300481 | Lyravinouna | monastery / 64 | Kalyra | -51489.39, 344.47, -111712.02 | 0 candidates under fixed root/width constraints; resurvey |
| 300511 | Teryanti | monastery / 64 | Kalyra | -55467.77, 510.16, 140292.64 | 0 candidates under fixed root/width constraints; resurvey |
| 300581 | Saryilasia | hill / 64 | Kalyra | -39445.48, 186.43, 128886.58 | 0 candidates under fixed root/width constraints; resurvey |
| 300611 | Teryareia | hill / 64 | Kalyra | 85007.60, 116.27, 20089.33 | 0 candidates under fixed root/width constraints; resurvey |
| 300911 | Myrevilissa | chapel / 4 | Kalyra | 58936.77, 111.94, 34283.62 | 0 candidates under fixed root/width constraints; resurvey |
| 300941 | Velyeressa | hill / 64 | Orenthia | 144944.20, 211.75, 48559.53 | 0 candidates under fixed root/width constraints; resurvey |
| 301041 | Olythandra | hill / 64 | Kalyra | -17897.80, 15.77, 82282.09 | 0 candidates under fixed root/width constraints; resurvey |
| 301181 | Keryavessa | chapel / 4 | Kalyra | -68462.32, 65.44, 143111.48 | 0 candidates under fixed root/width constraints; resurvey |
| 301411 | Teryonaki | chapel / 4 | Kalyra | -100198.37, 69.50, 139238.56 | 0 candidates under fixed root/width constraints; resurvey |
| 301711 | Ardevonandra | chapel / 4 | Kalyra | -104393.35, 72.76, 141817.94 | 0 candidates under fixed root/width constraints; resurvey |
| 301981 | Delyarasia | chapel / 4 | Kalyra | -37843.07, 64.58, -110118.42 | 0 candidates under fixed root/width constraints; resurvey |
| 302381 | Olythilanti | chapel / 4 | Kalyra | -71934.87, 79.39, 140158.06 | 0 candidates under fixed root/width constraints; resurvey |
| 302821 | Kalyavoria | monastery / 64 | Orenthia | 132757.78, 178.10, 119816.34 | 0 candidates under fixed root/width constraints; resurvey |
| 303491 | Ardevaki | hill / 64 | Orenthia | 141254.62, 311.44, 80002.28 | 0 candidates under fixed root/width constraints; resurvey |
| 303911 | Orenthaleia | chapel / 4 | Kalyra | 87495.77, 77.63, 9426.61 | 0 candidates under fixed root/width constraints; resurvey |
| 303931 | Velyavatha | chapel / 4 | Kalyra | -15403.02, 42.96, -110521.18 | 0 candidates under fixed root/width constraints; resurvey |
| 304111 | Kalyavessa | chapel / 4 | Kalyra | -51440.21, 124.16, 131712.72 | 0 candidates under fixed root/width constraints; resurvey |
| 304861 | Kalyalerio | chapel / 4 | Kalyra | -95629.97, 96.23, 139143.62 | 0 candidates under fixed root/width constraints; resurvey |
| 305221 | Pheryinatha | chapel / 4 | Orenthia | 139988.05, 79.57, 117405.22 | 0 candidates under fixed root/width constraints; resurvey |
| 305261 | Lyravona | chapel / 4 | Kalyra | 47182.89, 80.28, 25786.72 | 0 candidates under fixed root/width constraints; resurvey |
| 305971 | Pheryanti | chapel / 4 | Orenthia | 142627.06, 143.99, 33842.72 | 0 candidates under fixed root/width constraints; resurvey |
| 306251 | Saryaveli | chapel / 4 | Kalyra | -29152.71, 45.42, -109541.60 | 0 candidates under fixed root/width constraints; resurvey |
| 306751 | Alevathatha | chapel / 4 | Kalyra | 86716.48, 79.18, -160199.97 | 0 candidates under fixed root/width constraints; resurvey |
| 307811 | Kalyouna | chapel / 4 | Kalyra | 54030.18, 93.93, 35391.54 | 0 candidates under fixed root/width constraints; resurvey |
| 307931 | Olythavissa | chapel / 4 | Kalyra | -45686.31, 101.18, 120708.65 | 0 candidates under fixed root/width constraints; resurvey |
| 311721 | Teryathanti | hill / 64 | Kalyra | 49730.86, 13.10, 67653.21 | 0 candidates under fixed root/width constraints; resurvey |
