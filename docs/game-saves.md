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
A load keeps the existing pause state; the UI may unpause after successful completion.

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
(`src/hud.jo saved_toast`), never a menu note. There is no start screen, so no Continue offer:
a fresh start plays on and the player loads from the page. `tools/game_menu_probe.jo` drives the
page's requests end to end (autosave and its card, save, change, load, delete; position, purse, a
cat's friendship and a seen battle card restored).

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
Failures back off for at least 30 safe seconds instead of retrying every frame. Manual saves can
checkpoint flight/combat as well as the quay. No world or serialization work is done per frame
by the eligibility check; it uses bounded registry bins and scene state.

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
Pending operations retain compressed bytes, never a live World projection across frames. A
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
- `tools/game_save_probe.jo`: actual game autosave, a real paid fuel purchase, paused manual
  save/load/delete, exact restoration, then 120 resumed frames and full conservation. `GAME_SAVE_CASE=flight`
  with `AEGEAN_FLYING='300 150'` also checks that flight is not autosaved and manual flight works.
- `tools/run_game_save_web.mjs CHROME PAGE.html SCRATCH`: the compiled probe through the real
  Wasm/IndexedDB bridge. Web probes draw before saving and after restore, with intermediate
  renderer work reduced; this is a compatibility/functional proxy, not a phone FPS measurement.
- `tools/test_game_storage.mjs CHROME SCRATCH`: six actual month-size banks, exact bytes/reopen,
  stale writer refusal, transaction abort between body/header, deletion and unavailable storage.
- Existing save/codec, speech/refuel/collision/cat/flight, world/air-event and ledger replays remain
  the affected gates. Run with headless/silent settings and isolated `SLOPPY_SAVE_DIR`.
