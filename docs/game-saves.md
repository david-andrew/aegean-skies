# Game slots and autosave

The shell (`aegean.jo`) now uses the living world's compact codec for complete game checkpoints.
Three user slots, numbered **0–2**, each retain two independently checked generations. A request
is processed at a completed frame boundary, including while paused. Loading validates everything
before replacing the running world. A failed read/write keeps the running game and the previous
committed bank; an incompatible schema/terrain is retained until explicit deletion.

## Pause-menu API

These functions live in `aegean.jo`, beside the `complete game slots` block. The menu owns labels,
confirmation and presentation; the backend adds no keyboard shortcuts or menu layout.

| Function | Result |
| --- | --- |
| `game_save_slots() -> GameSlotView[]` | Three cached metadata rows; no World copy or body decoding |
| `game_save_status() -> GameSaveStatus` | `ready`, `busy`, `operation`, `slot`, `sequence`, `error`, `active_slot` |
| `request_game_save(slot) -> bool` | Queue a complete checkpoint in that slot |
| `request_game_load(slot) -> bool` | Queue validation/restore, falling back to the older intact bank |
| `request_game_delete(slot) -> bool` | Queue deletion of both banks in that slot |

A `true` request means **accepted**, not durable success. Disable other slot actions while `busy`.
Wait for a later `sequence` with `busy == false`, then inspect `error` (empty means success).
Browser completion is acknowledged only after the IndexedDB transaction commits. An early request
returns false while storage is opening/busy, another request is pending, or the slot is invalid.
These requests never change the pause: a load keeps the pause state as it was. The game's own load
handler (`process_game_saves` in `aegean.jo`) does unpause, once a load has succeeded and the game is
in place: Load was chosen to play on, so the pause menu closes and the loaded game carries on at once
(see "The pause menu's Game page" below). A failed load leaves the game paused, with its note.

`GameSlotView` has `slot`, `exists`, `compatible`, `generation`, `summary`, `error`. The summary has
`minute` (world minutes, the usual calendar/clock contract), stable `place`, `place_name`,
`player_name`, and `mode`. Listing inspects headers only; load verifies checksums, world invariants
and the complete session, and can recover an older bank if the newest body is corrupt. A future
schema or different terrain is not overwritten. Full-body verification is intentionally not done
every time a menu draws. Initial listing is unavailable until `status.ready`.

The lower-level `src/game_slots.jo` API is for tools/tests: `GameSlots`, `init_game_slots`,
`poll_game_slots`, `list_game_slots`, `save_game_slot`, `load_game_slot`, `delete_game_slot`,
`take_game_slot`. Its caller supplies a folded `SaveGame`; `capture_game` in `game_session.jo`
constructs that from the running scene. UI callers should use the shell requests instead.

## The pause menu's Game page

The pause menu opens on its **Game** tab (`src/debugmenu.jo game_page`, rows made by
`src/game_menu.jo game_row` from the cached headers). Each slot shows its world time, place and a
summary (aircraft, purse, day: `SaveSummary.craft` and `cents`, added for the menu; older headers
decode with them empty and simply omit them), and marks the active autosave slot. Save here on an
empty slot saves at once; saving over a slot, Load and Delete ask for a yes. Buttons are disabled
while `busy`. A note under the slots says what the last request came to (`Saved in slot 2.`, an
error text, `Slot 1 deleted.`) and where the autosave goes or why it is off. A successful load
unpauses and closes the menu. A finished autosave shows only the quiet Saved card
(`src/hud.jo saved_toast`), never a menu note. `tools/game_menu_probe.jo` drives the
page's requests end to end (autosave and its card, save, change, load, delete; position, purse, a
cat's friendship and a seen battle card restored).

## The title screen

The game starts on a title screen (`src/title_screen.jo`, wired in `aegean.jo` beside the
game-slot block) over the **title reel** (`src/title_shots.jo`): the live world, seen through a
free camera the reel flies, in unordered shots of 18-28 seconds with a short dip to dusk between
them, each with its own hour and fair weather (never rain):

- **Low pass:** low over open water at the top speed (about 450 km/h), the speed flecks streaming
  past as in flight, banking gently (never past 7 degrees); flying free, chasing a Gull ahead,
  overtaken by one, or a **race**: two Falcos in two liveries, flown by the game's own flight
  model (`step` with their real spec), come from behind and overtake close in lanes to the right
  (the NPC controller `air_waypoint_controls` holding lane, height and a jockeying pace), bank hard
  round an air-race pylon (the meets' banded pylon) as the shared steering law (`steer`) turns them,
  and are lined up on the next leg, shrinking ahead as the camera flies straight on past the pylon.
  The race is flown once when its shot is cut, at a fixed 1/60 s step, and kept: repeatable. The eye is at flight's chase-camera height, 13-16 m (lower, the flecks grow
  large and sparse on the screen), the Gull 4-5 m below it. The sea, rivers and lakes are given the
  reel camera's true velocity (`view_velocity`), so the flecks streak and keep their strength as
  at that speed in flight. The Gull is the player's own aircraft, drawn where the reel puts it for
  that frame only.
- **High at sunset:** 2.7-3.4 km up, above the clouds, drifting towards the sun as it goes down.
- **A town and its waterfront:** a low oblique run along the harbour front from just offshore
  (boats, the quay and the seaplanes in frame, the town rising behind); a higher, slow arc at
  golden hour, the roofs a texture; or in Neravessa along its canals. Porto Vecchio, Kalyrassa and
  Neravessa; never a camera looking straight down into the streets.

Behind the title the world runs as in play (traffic, vessels, people, weather), with the game's
own keys muted, nothing autosaved and no slot touched; the world's own sounds are silent. Its rows
are the pause menu's (`game_rows` over the same cached headers) and it uses the same requests:

- **Continue** loads the newest usable slot (`SaveSummary.saved_at`, the unix time of the save,
  added for this; an older header without it falls back to its world time). It is the default:
  Enter, or a tap, starts it with no second question. A successful load begins play.
- **New game** puts back the world as the startup built it: a copy taken when the title opened
  (Sloppy's values: the running world never touches it), installed through the scenario path
  (`load_scenario("start", state)`), keeping the notebook already loaded; about 10 ms. The autosave
  takes the first empty slot as before; when all three hold games it asks first: choose a slot to
  save over (that slot becomes the autosave's), or start without saving (autosave stays off, as the
  policy above says).
- **Saved games** lists the slots to load (at once: nothing is unsaved yet) or delete (asks).
- **Situations**, quieter, are the scenario picker's set pieces (the start one is New game).
- With nothing saved there is only New game (and the quiet Situations). Until the slots have been
  read the screen says "Reading saved games..."; a load says "Loading slot N...".

**Sound.** The Adagietto plays as if from a cockpit radio: through the receiver chain with station
levelling (the pause menu's music player, `MusicAudition`); it leads. Under it on a low pass only a
very faint bed of engine and rushing air, about 20 dB down, faded in and out with the shot; a
race's engines (the engine hearing's own, with Doppler, at an `EngineSource.gain` of 0.04) are
barely there. In a browser
the music begins at the first click, tap or key (browsers allow sound only then); nothing on the
screen says so. When play begins the music fades away over three seconds.

**Loading.** Before the title there are no words: a small two-bladed propeller turns slowly in the
middle of the dusk, a faint ring round it filling as the preparation goes. In a browser it is the
page's own card (`src/web_compat.js`, inline SVG turned by the compositor), so it turns while the
module loads and the world is built, steps the page cannot draw during; natively the game draws
the same (`src/title_screen.jo draw_loading_propeller`). Before the title's first frame the game
finishes the islands' places a few a frame and populates the far economy in one step (about 4 s on
the desktop): the same work play does a few seconds in, in a stall, so the reel and its music
never stall for it and a new game starts populated.

**Capture switches.** `AEGEAN_TITLE_SHOT=low|low-free|low-chase|low-pass|high|city|city-<Town>`
(with `:run` or `:arc`) repeats a kind; `AEGEAN_TITLE_SEED=n` fixes the order; `AEGEAN_TITLE_FRAMES=dir`
saves every 10th frame (`AEGEAN_TITLE_FRAME_STEP=n`: every nth). `AEGEAN_FRAME_STATS=1` prints the
frame statistics every 120 frames, in the title and in play alike, for timing runs.
`AEGEAN_TITLE_BARE=1` draws the reel without the menu; `low-free@14` flies a low pass at that
height; `low-race` the race.

**Guard.** `python3 tests/title_reel_detail_test.py` (needs a GPU; too slow for the software
renderer) renders the reel's low pass and real flight at 125 m/s at fixed frames and requires the
reel's fine water detail to reach 0.7 of flight's (measured 0.79; a parked sea, 0.2).

Test and capture runs start straight in the game: a program that imports `aegean.jo` (its
`PROGRAM_NAME` is not "Aegean Skies"), a run with `SLOPPY_FRAMES` or `SLOPPY_SCREENSHOT`, and a run
or page with any `AEGEAN_` option other than `AEGEAN_QUALITY`, `AEGEAN_TOUCH` and `AEGEAN_TITLE`.
`AEGEAN_TITLE=0` (in a page, `?AEGEAN_TITLE=0`) skips it and `AEGEAN_TITLE=1` forces it.
`tools/webshot.mjs`, `measure_web.mjs` and `text_probe.mjs` add `AEGEAN_TITLE=0` unless their
query names it.

## What persists

- The canonical living World: original cargo roots/ownership, money and fuel ledgers, people,
  positions/trips, jobs/contracts, standing, markets, fields, stories, speech/knowledge, politics,
  war/rescue state and maps.
- `PresentationState`: cat friendship, shown battle cards/history, bark/hail suppression and
  declined contracts. Existing bounded presentation pruning still applies.
- Versioned `GameSession`: player mode, precise walking point, yaw/phase, the full Flyer (exact
  physics/damage/fuel fractions/controls/camera), scene clock and fractional fixed-tick accumulator,
  weather drift and calibration, AirEvents/race progress, notebook, mooring/rope and leisure state.
  Paid table orders, strong-drink times and the current sitting/log remain; an unfinished
  rest/tinkering time skip must finish before a manual save.
- The full physical VesselFleet and Battle, through the existing same-tick war checkpoint.

Capture folds a **copy** of traffic, daily life, portage, far transport and player ownership; it
never releases a live scene lease to save. Club aircraft are checkpointed under their separate
owner. Restore rebuilds bindings and transient effects, retaining existing GPU/audio resources.
It does not serialize pool handles, meshes, voices or external device objects. Menus/unfinished
animations are closed or rebuilt; saved sitting resumes at the table. User options remain the
existing application settings. A new situation resets its leisure state and detaches its save
context; an old asynchronous write cannot attach the new story to the old slot.

## Autosave policy

The first empty slot becomes the active autosave slot for a new story. **If all three already
exist, automatic saving stays disabled until the player explicitly saves or loads a slot.**
Manual save/load selects that slot for subsequent autosaves. Deleting the active slot detaches it;
it is not recreated immediately. Situations/scenarios are separate from saved games.

Autosave waits for three stable safe seconds after reaching a mooring or a town on foot, with a
30-second minimum between attempts. It then saves every 180 unpaused simulation seconds while
safe. Idle sitting is safe; trading/dialogue/menu transactions, cat interaction, refuelling,
rest/tinkering skips, flight/descent/free-camera and nearby fighting/raids defer it.
Failures back off for at least 30 safe seconds instead of retrying every frame. Storage being
busy (as during the save itself) is not leaving the safe place: only an actual departure re-arms
the arrival save, so a successful autosave is followed by the 180-second one, not another after
30 seconds. Manual saves can
checkpoint flight/combat as well as the quay. No world or serialization work is done per frame
by the eligibility check; it uses bounded registry bins and scene state.

## Saving without a stall

Saving a game is spread over frames (`save_game_slot(..., spread=true)`, stepped by
`step_game_slots` after each frame's update, about 3 ms a frame, 12 ms while paused, standing
aside on a frame that ran a world minute). The request frame only takes the checkpoint: the scene
folded into a copy-on-write copy (`capture_game_snapshot`, with the structural check folding needs).
The following frames run the save check in short steps (`save_check_step`: the same rules as
`validate_save_world`, the far check in 32 slices), write the canonical World text a container
element at a time from a small template (`src/living_save_stream.jo`, byte for byte
`canonical_text`), hash it as it goes, compress it with a resumable deflate (`src/save_stream.jo`,
4096-symbol blocks: a raw deflate stream as before), then store it. The format is unchanged.
Choosing the bank to overwrite reads only the headers and body sizes; the full check of a stored
game (inflate, parse, every World rule, the session) happens when it is loaded. A failing check
refuses the save and keeps both banks. Tests and tools call `save_game_slot` without `spread`
and get the same work done at once.

## Storage and failure handling

Native slots use `game-slot-N-a`/`-b` headers and `-data` bodies in Sloppy's application save
folder. The compact deflate body is written first and the checked header last; the other bank
remains recoverable. Extended sessions are compressed/checksummed separately in that header.
World-only legacy saves still decode through the living-world API, but the game slot API refuses
to pretend they contain a player checkpoint. Existing `world-*` banks are not silently imported or deleted; application options remain
unchanged. A new story retains the notebook the application already loaded. Loading a slot
replaces it with that checkpoint's notes and uses a slot-specific notebook key; the complete
slot body remains authoritative for game restore.

Three complete worlds plus recovery banks cannot fit localStorage's small UTF-16 quota. Browser
slots therefore use IndexedDB (`aegean-skies-game-v1`), with raw compressed ArrayBuffers and atomic
header/body transactions. Only small slot headers are read at startup. A selected slot's bodies
are read on demand; candidates are decoded newest first, keeping one parsed World at a time.
A save in progress holds its checkpoint (a copy-on-write World) until its text is written,
then only compressed bytes. A
stale-tab writer is refused. Browser denial/quota/transaction failures surface through `error`;
there is no false success or silent fallback into an overfull localStorage store.

The decoder supports at most 64 MB of raw World text, 16 MB compressed body and 8 MB raw session.
Writing checks those limits **before** publishing a bank; an oversized checkpoint leaves both
previous banks intact. These are defensive format limits, not a claim that every browser grants
that much disk space. The existing legacy localStorage compact codec remains unchanged.

## Validation

- `tests/game_session.jo`, `tests/game_slots.jo`: full snapshots, live-lease isolation, exact
  physics/fuel/presentation/clock, version/malformed refusal, three-slot isolation, corruption
  fallback, size/write preservation, deletion and bounded autosave retries.
- `tests/save_stream.jo`, `tests/living_save_stream.jo`: streamed deflate and hash equal the
  library's, streamed text equals `canonical_text` on living worlds, stepped checks match
  `validate_save_world`, a save spread over many steps loads back identically, a failing world is
  refused with both banks kept.
- `tools/stutter_trace.jo` with `STUTTER_AUTOSAVE_AT` (`tools/test_stutter.py --autosave-at`): a
  measured stay that spans a real autosave.
- `tools/game_save_probe.jo`: actual game autosave, a real paid fuel purchase, paused manual
  save/load/delete, exact restoration, then 120 resumed frames and full conservation. `GAME_SAVE_CASE=flight`
  with `AEGEAN_FLYING='300 45.5'` also checks that flight is not autosaved and manual flight works.
- `tools/run_game_save_web.mjs CHROME PAGE.html SCRATCH`: the compiled probe through the real
  Wasm/IndexedDB bridge. Web probes draw before saving and after restore, with intermediate
  renderer work reduced; this is a compatibility/functional proxy, not a phone FPS measurement.
- `tools/test_game_storage.mjs CHROME SCRATCH`: six actual month-size banks, exact bytes/reopen,
  stale writer refusal, transaction abort between body/header, deletion and unavailable storage.
- Existing save/codec, speech/refuel/collision/cat/flight, world/air-event and ledger replays remain
  the affected gates. Run with headless/silent settings and isolated `SLOPPY_SAVE_DIR`.
