# Cockpit radio

The receiver starts muted. While aboard, with no panel or text field taking input:

* `/` toggles mute.
* `,` and `.` tune down/up by 5 kHz.
* Shift with either tuning key seeks the previous/next station currently on air, wrapping the dial.

This change implements audio and data APIs. The physical cockpit dial, touch controls, station
label and optional bulletin transcript are intentionally left for the coordinator's UI work.
No synthetic speech is shipped: bulletin slots carry **Morse summaries**, with full English copy
available to the UI. Choir is wordless. The research speech sample is not an accepted announcer.

## Stations and programme clock

| Station | kHz | Usual music | Broadcast hours |
| --- | ---: | --- | --- |
| Archipelago Radio | 620 | Modal plucked strings; wordless choir at 06:00 | All day |
| Voice of Kalyra | 780 | Waltz | All day |
| Orenthia National | 940 | Brass march | All day |
| Blue Lantern Dance Band | 1100 | Foxtrot, tango, waltz in rotation | All day |
| Aegean Maritime Service | 1260 | Morse weather and shipping bulletins | All day |
| The Night Gull | 1460 | Tango | 19:00–03:00 |

At each half hour, the first five game minutes carry news, the next five carry a state editorial,
advert or pirate quiz, and the remainder carry music. Maritime alternates weather observations
and shipping notices every fifteen game minutes. The clock is the **saved living-world clock**:
minute zero is 09:30, with two real seconds per game minute. Cosmetic debug sky-hour changes do
not advance the broadcast schedule. Tuning in joins a continuing world-time score.

Transmitters are fictional locations, not declarations of national capitals. The game positions
antennas 65 m above sampled terrain. Reception uses distance, altitude, a fifteen-point terrain
profile with Earth curvature, detuning and increased night reach. Paths refresh at most twice
per second, plus minute/retune changes. Ridges attenuate ground-wave rather than completely
silencing it. This is a bounded gameplay approximation, not a physical propagation simulator;
very narrow obstacles can lie between samples.

## Integration API

Import `src/radio.jo` as `radio` and `src/radio_content.jo` as `broadcast`. These modules do not
re-export each other's symbols. `src/radio_synth.jo` owns synthesis constants and `RadioStyle`.

* `radio.Radio()`: receiver state, initially muted at 1100 kHz. `volume` is clamped to 0–1 at mix
  time; default 0.55. State belongs to the player's current aircraft session. Preferences are
  not yet persisted in the living-world save schema.
* `radio.radio_tune(receiver, khz)`: continuous 540–1600 kHz dial. Stops/discards the old stream.
* `radio.radio_step(receiver, direction)`: one 5 kHz step, direction −1/0/+1.
* `radio.radio_seek(receiver, direction, world.minute)`: adjacent live station, wrapping.
* `radio.radio_mute(receiver, muted)`: immediately stop on mute.
* `broadcast.radio_place_transmitters(receiver, height_function)`: once after loading terrain.
* `radio.radio_receive(receiver, dt, world.minute, aircraft_position, height_function)`: reception
  and programme selection. The height callback takes world x/z metres and returns metres y.
* `broadcast.radio_update_content(receiver, cache, world)`: `RadioBulletinCache()` refreshes copy
  at five-minute bulletin boundaries (fifteen for maritime) and on station/programme changes.
  Read-only World projection.
* `radio.radio_play(receiver, world.tick/60.0, aboard, engine_running, throttle, audio_enabled)`:
  fills one bounded mono stream. `audio_enabled=false` keeps the data path usable without
  generating samples or opening a device. Use false when `SLOPPY_NO_AUDIO` is present.
* `radio.radio_silence(receiver)`: pause/menu teardown; discards the queued stream but preserves
  dial and mute preferences. Resume with the normal receive/content/play calls.
* `radio.radio_snapshot(receiver)`: `khz`, `muted`, `strength`, `station`, `station_name`,
  `programme`, `title`, `transcript`, `morse_text`, `event`, `confidence`, `speech_available`.
  Station identity and copy are withheld when muted, inactive or strength <0.12. Raw frequency
  remains available for drawing the dial. `speech_available` is always false. Distinguish the
  short keyed `morse_text` from the full `transcript`; the radio does not speak the latter.
* `radio.radio_stations()`: catalogue, including ID, callsign, frequency, transmitter, reach,
  country, news home and style. Useful for dial ticks or a station list.

The receiver is silent on foot and on pause. Typing/chart/notebook/dialogue suppress keyboard
radio shortcuts. Audio gain is below the engine and improves as throttle falls; changing the
radio never changes the engine mix. Mixer stop/volume changes take effect at the next mixer
buffer, subject to the audio device's existing latency.

## World information and future war work

National stations use their country's valid seat, falling back to the first place assigned to
that country. A country with no represented place reports no fresh verified news. Other stations
use their configured home queue. Items must be public, heard by the station, no older than a day,
not future-dated, have confidence >=600 and <=4 retellings. Ties resolve by event ID. Reports name
occurrence time and explicitly label uncertainty. No hidden global event, private plan, cargo
contents or uncommunicated NPC knowledge is used. The receiver never teaches NPCs news or
mutates simulation state.

State slogans are explicitly editorial opinion, with no claim that a war has begun or a battle
was won. Existing public event paths can carry future war reports; add accurate event-specific
headlines in `radio_public_news` when new event kinds land. Do not infer national victories from
an arbitrary raid. Weather is a current harbor observation, not invented forecasting. Shipping
notices read actual closure orders; old news of a closure does not masquerade as current status.

## Audio, cost and validation

All music, scores, timbres, noise and Morse are original procedural content. No downloaded
recording, external voice asset, soundfont, network stream or synthesis dependency is bundled.
Five 1024-sample harmonic tables and a note-frequency table are built lazily on first use.
The live stream is 16 kHz mono, expanded to stereo by the engine. Render blocks are capped at
800 source samples (50 ms), with a 4000-sample target queue and at most that much catch-up per
update. Raw tables, state, render block and the engine's stereo queue total roughly 60 KB, plus allocator
and shared mixer overhead; offline audition tools deliberately allocate full clips outside that
runtime budget.

A 300 Hz high-pass and 3000 Hz low-pass, soft saturation, fading, noise, crackle and detuning
whistle give the receiver its AM character. Every generator has local deterministic noise;
none seeds or consumes the game's global random stream. Pause, tuning, programme changes and
clock discontinuities discard old queued audio. Perceptual quality and intelligibility are
listening questions, not established by finite-sample or filter tests.

Run one test process at a time:

```sh
env -u DISPLAY -u WAYLAND_DISPLAY SLOPPY_NO_AUDIO=1 SLOPPY_THREADS=1 sloppy test tests/radio_synth.jo
env -u DISPLAY -u WAYLAND_DISPLAY SLOPPY_NO_AUDIO=1 SLOPPY_THREADS=1 sloppy test tests/radio.jo
```

For WAV auditions, create a scratch directory then set `RADIO_SAMPLE_DIR` to its absolute path
and run `sloppy --release tools/radiolab.jo` with the same headless/silent environment. This tool
only writes files: dry/strong/weak variants of every genre and Morse, plus engine idle/cruise
mixes. `RADIO_COST_SECONDS=120` without a sample directory runs a fixed synthesis workload;
wall-clock measurements belong on redfox under `flock ~/dev/tmp/bench.lock`.

Research, rights checks, candidate speech and archival reference remain in
`~/dev/tmp/aegean-skies/radio/design.md`. The archival comparison is **not for distribution**.
Only the original procedural source goes into the game.
