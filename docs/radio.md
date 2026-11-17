# Cockpit radio (the wireless)

On screen the broadcast receiver is the **wireless** (the period British word): the touch
screen's Wireless button, Settings → Sound → Wireless volume, "Wireless off". The R/T (orders
to one's own flight, `src/rt_pad.jo`) is a different set. In code it stays `radio`.

The receiver starts muted. While aboard, with no panel or text field taking input:

* `/` toggles mute.
* `,` and `.` tune down/up by 5 kHz.
* Shift with either tuning key seeks the previous/next station currently on air, wrapping the dial.
* F9 (the touch screen's Wireless button, a tap or click on the radio in the cockpit) steps to the
  next station on the air, and off after the last.
* **Volume**: the knob in the dial's lower left corner. Drag up or down on the radio (the mouse,
  once it is free of the view, or a finger), turn the wheel over it, or press `[` and `]`. A
  gamepad or flight stick has a Wireless button to bind on the Gamepad page (unbound at first:
  every button is taken aboard): a tap steps the stations, and while it is held the look stick
  turns the volume (up and down) and tunes (across). The same level is Settings → Sound → Wireless
  volume, kept with the options. Half way is the level the radio always had; the knob spans
  20 dB either side of it in even steps of loudness (`radio_volume_gain`), and 0 is silent. At
  the top, at cruise, the announcer is about 5 dB under the engine rather than 25; moored, the
  receiver reaches full scale first.

A card names the station, or the volume, for a moment after each change. Bulletins are **read
aloud by a synthesized announcer** (see "The announcer" below); the maritime shipping notices
stay in Morse. The full English copy remains available to the UI. Choir is wordless.

## Stations and programme clock

| Station | kHz | Usual music | Broadcast hours |
| --- | ---: | --- | --- |
| Archipelago Radio | 620 | Modal plucked strings; wordless choir at 06:00 | All day |
| Voice of Kalyra | 780 | Waltz | All day |
| Orenthia National | 940 | Brass march | All day |
| Blue Lantern Dance Band | 1100 | Foxtrot, tango, waltz in rotation | All day |
| Aegean Maritime Service | 1260 | Spoken weather, Morse shipping notices | All day |
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
  remains available for drawing the dial. `speech_available` is true while the programme is
  read aloud (`radio_spoken`): the transcript is then what the announcer says; otherwise the
  short keyed `morse_text` is what is heard. `Radio.speech = false` keeps every bulletin in Morse.
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
headlines in `radio_headline` when new event kinds land. Do not infer national victories from
an arbitrary raid. Weather is a current harbor observation, not invented forecasting. Shipping
notices read actual closure orders; old news of a closure does not masquerade as current status.

Copy reads as a period announcer would say it, on air and in the transcript: the time of an
event in clock words with its part of the day ("From the harbour office: at a quarter to one this
afternoon, ..."; "yesterday evening", "last night"), wind as a Beaufort force ("Wind west, force
four"; "Wind calm"), lists with "and", and no game-minute counts, digits or raw units
(`tests/radio.jo` checks it).

## The announcer

One synthesized voice reads every spoken programme, each station with its own delivery
(`radio_voice_style`: tempo, pitch register and range, vocal effort, tilt, pauses, broadcast
colour). The newsreel default is 1.35 times the measured narrator's syllable rate; the national
stations read their news (the war) at 1.45, three semitones higher, with a wider range and a
raised-voice spectrum. It is a classical vocoder voice built WORLD-style, not a recording and not
a neural model:

* **Text** (`src/voice_text.jo`): words, numbers and clock times ("nine thirty", "nineteen hundred
  hours") become ARPAbet phones from a 2,921-word lexicon (CMUdict for the game's own vocabulary
  plus the world's place names), with letter-to-sound rules and a stress guess for invented
  names; function words take their weak forms and unstressed vowels their reduced symbols.
  Long phrases take a short breath before a conjunction.
* **Rhythm**: a fitted duration model (per-phone base, factors for stress, function words, word
  position, clusters, syllable count and phrase-final lengthening). Tempo is solved so that the
  speech runs at the target syllable rate while each class compresses by its own measured
  elasticity: unstressed vowels shrink most, consonants least. Fricatives are capped at the
  narrator's long-but-normal length; a pause keeps only its measured 45 ms next to speech.
* **Pitch**: a superposition fitted to the narrator: each phrase has its level and an arc over its
  length; every stressed content-word vowel gets an accent shape (a dip, then a peak early in
  the vowel; the first accent highest, later ones downstepped, the nuclear accent followed by
  a fall); microprosody dips inside voiced obstruents. Shapes are widened 1.6 times to restore the
  variance a mean model loses, with a soft limit of 7 semitones around the register.
* **Spectra**: each pair of neighbouring phones takes its measured *diphone trajectory* (spectral
  envelope, band aperiodicity and voicing from the centre of one phone to the centre of the next,
  averaged over the narrator's tokens), so formant transitions, closures, bursts and frication are
  measured, not invented. A diphone the narrator never said borrows each half from the nearest
  observed one; joins are smoothed over 20 ms.
* **Synthesis** (`src/voice_synth.jo`): WORLD's source/filter model in time-domain form. A
  fractionally placed impulse train with slight cycle jitter and shimmer, and white noise, are
  mixed per band by the aperiodicity (calibrated so that the synthetic voice re-analyses to the
  narrator's own), then shaped by a 24th-order lattice all-pole filter fitted to each 5 ms
  envelope frame (mel-cepstrum → power → autocorrelation → Levinson), interpolated each
  millisecond. Vocal effort moves each frame's envelope along the narrator's own raised-voice
  direction, more on higher pitch.
* **Broadcast colour** (`src/radio_studio.jo`): a small studio (early reflections, a short tail,
  room tone, 50 Hz hum), a carbon microphone (resonant 300–3400 Hz band, granule distortion and
  its signal-dependent hiss) and transmitter compression with a soft limiter; then station
  levelling, and the receiver with some transcription-disc wear. It hides vocoder artefacts at
  some cost in intelligibility; `VoiceStyle.colour` and `record` set how much.

A bulletin repeats on the world clock: its period is the programme span (10 s, or 30 s for
maritime) rounded up to fit the words plus a pause, so tuning in mid-bulletin joins it where it is.
The voice data file (340 KB: spectra, lexicon, rules and the fitted prosody model) is **not in
the repository**: the approved voice is fitted to a reference narrator, and nothing derived from
that recording goes into git until its rights are settled. The game reads it from the path in
`AEGEAN_VOICE_DATA`, during world loading with the music. Without it, speech is off and spoken
programmes stay in Morse; `src/voice_model.jo` holds only neutral placeholder numbers. How it is
made: `tools/voice_world/README.md`. Its cost, measured on redfox with the approved voice
(`tools/voice_budget.jo` with the file embedded): loading takes 45 ms native and 80 ms in
Chromium, once; a bulletin's first programme 2–2.4 ms native (20 ms for the first in Chromium,
3–4 ms after), and rendering 1.1 ms native, 1.35 ms in Chromium per 50 ms block. Embedded in a
web build it would add 454 KB to the page (343 KB gzipped: the file is compressed already).

## Backlog: finding the stations (a design note, not built)

From the user, on hearing the first voice: the dial is easy to sweep today, and every station is
there from the first flight. Later, the stations could be **found**:

* **Early on, the pilot knows few stations or none.** The receiver still picks up whatever is in
  range, but a sweep across the band is a search, not a list: a station found by ear is one the
  pilot can come back to.
* **Asking around.** People mention stations: a mechanic who leaves the dance band on in the
  workshop, a fisherman who swears by the maritime forecast, a bar where the Night Gull plays
  after dark, a newspaper's listings. Hearing of one gives its name and roughly where it sits on
  the dial ("the Blue Lantern, up past eleven hundred"), not an exact frequency.
* **Marks on the dial's card.** Once found, the pilot pencils the station on the panel: a small
  hand-written mark and abbreviation on a card above or below the radio's display, at the
  station's place on the scale. The marks build up through a career, in the pilot's hand (or set
  down by the pilot on their own the first time a station is heard clearly). A station heard of
  but not yet found might get a faint question mark at its rough place.
* **Tuning with the marks.** Shift-seek (and the Wireless button) would step between marked stations
  rather than every station on the air; free tuning stays for searching.
* **What it touches:** a found-stations set in the saved game; mentions in talk, the
  newspaper and the bar (`living_*`, `radio_content.jo` for listings); the card drawn in
  `cockpit.jo` beside the dial (procedural strokes, no font images); `radio_seek` restricted to
  marked stations. Nothing here changes reception or the programme clock.

## Audio, cost and validation

All music, scores, timbres, noise, Morse and the announcer are original procedural content. No
downloaded recording, recorded or generated voice, soundfont, network stream or synthesis
dependency is bundled; the announcer ships only averaged spectral and prosodic numbers.
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
env -u DISPLAY -u WAYLAND_DISPLAY SLOPPY_NO_AUDIO=1 SLOPPY_THREADS=1 sloppy test tests/voice_test.jo
```

Announcer auditions: `VOICE_TEXTS=lines.txt VOICE_DIR=/abs/scratch sloppy --release
tools/voicelab.jo` (lines are `name|text`; `VOICE_STATION=n` uses that station's delivery) writes
dry, strong, medium and weak WAVs. `tools/voice_budget.jo` times spoken programmes against a music
piece through the same receiver; build it native and `--target wasm` and run it on redfox.

For WAV auditions, create a scratch directory then set `RADIO_SAMPLE_DIR` to its absolute path
and run `sloppy --release tools/radiolab.jo` with the same headless/silent environment. This tool
only writes files: dry/strong/weak variants of every genre and Morse, plus engine idle/cruise
mixes. `RADIO_COST_SECONDS=120` without a sample directory runs a fixed synthesis workload;
wall-clock measurements belong on redfox under `flock ~/dev/tmp/bench.lock`.

Research, rights checks, candidate speech and archival reference remain in
`~/dev/tmp/aegean-skies/radio/design.md`. The archival comparison is **not for distribution**.
Only the original procedural source goes into the game.
