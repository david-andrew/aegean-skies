# World ambience

The cockpit engine still leads. World sounds come from nearby state and geometry, with no
recordings or downloaded audio. `src/ambience_synth.jo` makes 23 short instruments once at
startup. `src/ambience.jo` schedules and mixes them; `src/ambience_scene.jo` is the read-only
adapter to terrain, settlements, people, vessels and weather. No simulation or save schema
changes are required.

The pause menu's World → Sounds... button reveals controls for Bells, Harbour, Cafes, Music, Shore, Nature, Animals,
Ships and Weather separately, beside the existing Air/Cloth/Airframe switches. The expanded category rows replace
the money controls in that panel; click Sounds... again to return. This keeps the switches
within the existing panel height on short screens. These have the
same session-only lifetime as the existing sound switches. Pausing stops active ambience and
musician tails and drops delayed events; resuming does not replay missed bells or thunder.
A clock rewind, load jump or large listener teleport also discards queued ambience.

| Source | Authority and conditions |
|---|---|
| Hour bells / service peals | Registry church/hill-church landmarks and original towns' visible chapel anchors. Nearest audible church strikes 1–12 on the hour; at 09:00 on Sundays/feasts a short three-pitch service peal replaces the hour count. No startup backlog. |
| Harbour voices / ropes / rigging | Awake, non-travelling, non-carried people physically near the quay. Loudness saturates at six bodies. Wind drives ropes and rigging. Hull hammering also requires an arrived, working mechanic nearby. |
| Cafe voices / clinks | Actual cafe landmarks/core life venues, nearby awake bodies, 17:00–23:00. No settlement population multiplier. |
| Musicians | Existing arrived performers and notes; square performances get four quiet early reflections baked into the note. Occlusion softens the note and its reflections. |
| Beaches / cliffs | A nearby zero crossing of the canonical height field, classified by the same slope criterion as the terrain beach material. Wind increases wash/boom; sources stay at the coast. |
| Wind / insects / owl | Actual resident tree-stand bounds, plane-tree landmarks, olive ecology and the shared `grass_cover` query. Summer afternoon sun/low rain favours cicadas; dry, calm nights favour crickets and occasional owls. |
| Dogs / goats / donkeys | Stable ambient habitat locations: inhabited quays, elevated farm/hill/hamlet sites, and occupied farms during daylight. These are ambient off-screen fauna, not new saved animal actors or livestock counts. Rain suppresses goats; calls are sparse deterministic events. |
| Ships | Actual vessel pose, kind, status and speed. Powered ships thump underway; sailboats luff according to apparent wind/head-to-wind. Steam whistles follow observed departures/arrivals, never first discovery. Sunk/stopped craft have no propulsion sound. |
| Rain / thunder | Saved spatial weather. Roof rain uses actual nearby houses/parcels; sea rain uses an open-water surface tile. Rain is silent above cloud base. Thunder follows the existing storm-ID/23-second lightning phase, once per double flash, delayed by source distance / 343 m/s. |

There is no animal simulation, air-temperature field or seasonal climate in main. Habitat and
fixed-summer solar time are explicit proxies for animal presence and daytime heat. Civil dates
below do not silently change that climate. Crowd murmurs are intentionally indistinct synthesis;
they do not claim to speak generated dialogue.

## Calendar shared with daily life

The checked main has Sunday routines (`day_index(minute) % 7 == 6`) but no feast notion.
`src/calendar.jo` therefore has no sound or world dependencies. Day zero is **Monday, 3 June
1929**, matching the existing weekly clock. `calendar_date(day)` returns year/month/day/weekday;
`calendar_feast(date)` returns a name or none; `calendar_service_day(day)` combines Sunday and
feasts. Gregorian leap years and backwards dates are supported.

The initial common summer list is 24 June (Nativity of Saint John), 29 June (Saints Peter and
Paul), and 15 August (Dormition / Assumption). This is a deliberately small common observance
set, not a complete regional liturgical calendar. **Daily-life routines do not yet read these
feasts.** Their owner can import this module instead of adding a second calendar. The sound
adapter passes the existing saved `day_index`, whose epoch is 09:30 on day zero.

## Bounds and integration

- State selection runs twice a second; geometry is cached until 64 m movement or registry growth.
  Registry lookup uses spatial bins and at most eight nearby districts. Grass/shore probes and
  occlusion samples are fixed small grids. Population positions are gathered once per scan.
- Six loop sources maximum, at most one per instrument; each has direct and 850 Hz softened
  voices. Four one-shots maximum; 24 pending events maximum. Music adds at most three notes.
  Old loops fade before their slots are reused. No per-frame synthesis or convolution.
- All sources use positional `play_at` / `move_sound`. Distance reduces loudness; terrain and
  building footprints reduce gain and favour softened audio. This is inexpensive approximate
  obstruction, not a ray-traced indoor acoustics model.
- Loop amplitudes share a gain budget of 0.055 aboard / 0.65 ashore; hits share 0.035 / 0.42.
  Instruments have a 0.45 peak bound. Musicians use 0.012 per note aboard. A conservative
  file-based comparison of maximum ambient layers against idle engine audio is in the lab.
- The complete direct/soft instrument bank is 33,753,600 PCM bytes (about 32.2 MiB); notes and
  early-reflection copies are additional. Sound arrays are shared between emitter voices.
  No WAV or sample assets add to the download. `SLOPPY_NO_AUDIO=1` skips live sound-bank startup.
- `Ambience(active=true, playback=false)` allows state/queue evaluation without device calls.
  `build_ambience(render_only=true)` builds the bank with playback disabled. The offline lab
  never calls play. Tests that exercise mixer handles require `SLOPPY_NO_AUDIO=1` explicitly.

## Reproduce

Use the repository's pinned Sloppy 0.29.2, a scratch save directory, one process at a time and
`SLOPPY_THREADS=1`. No window or speaker output is needed:

```sh
env -u DISPLAY -u WAYLAND_DISPLAY SLOPPY_NO_AUDIO=1 SLOPPY_THREADS=1 \
  SLOPPY_SAVE_DIR="$HOME/dev/tmp/aegean-skies/sound/save" sloppy test tests/ambience.jo

env -u DISPLAY -u WAYLAND_DISPLAY SLOPPY_NO_AUDIO=1 SLOPPY_THREADS=1 \
  AMBIENCE_SAMPLES="$HOME/dev/tmp/aegean-skies/sound/samples" \
  sloppy --release tools/ambiencelab.jo
```

Create the sample directory first. The lab writes individual instruments, contextual quay/night/
storm mixes, dry/reflected musician phrases, a softened quay and idle-engine comparisons. The
storm fixture has a flash at t=1 and a source 1,029 m away; thunder begins at t=4.
`tools/ambience_cost.jo` is a silent adapter workload through a generated capital. Only enable
`AMBIENCE_TIMING=1` on the quiet laptop under the shared benchmark lock; use instruction counts
on the desktop. See `~/dev/tmp/aegean-skies/sound/report.md` for measured checks and limitations.
