# The announcer's voice data: where every number comes from

`announcer-v4.z` is the announcer's whole voice: raw-deflate tables, format `AVX1`, written by
`tools/voice_world/pack.py` and read by `src/voice_text.jo` (`voice_load_bytes`). The game embeds it,
so the native and web builds both speak; `AEGEAN_VOICE_DATA` (a path) overrides it with another
voice's file for tuning.

**It was fitted to the developer's own studio recordings. No recording is included in the
repository: no audio, no sample, no waveform, no phase and no pitch track, only derived numbers.**
Nothing in it is measured from a third party's recording except as noted below.

| What the file holds | Where it comes from |
| --- | --- |
| 797 diphone trajectories: for each pair of neighbouring phones, 12 points of 25 mel-cepstral coefficients, 5 band aperiodicities and a voicing fraction (int8/uint8), centre of one phone to the centre of the next | The developer's own studio takes (88 training lines), analysed WORLD-style by this repository's own code (`tools/voice_world/world_analysis.py`, `build_units.py`); the room's noise measured in the developer's room and taken off. Each is the mean of up to 12 takes nearest the medoid of all takes of that diphone (253 of the 797 are one take's envelope: a spectral envelope, not a signal) |
| Phone boundaries used to cut the units | The Charsiu phone classifier, an analysis instrument run on the takes; not in the file |
| Pronunciation lexicon (3,803 words) | CMUdict (Carnegie Mellon University, BSD-style licence: `tools/voice_world/CMUDICT-LICENSE.txt`, which accompanies this file); hand-written place names and words; the developer's own pronunciations |
| Letter-to-sound rules | Written for this project (`tools/voice_world/lts.py`) |
| Prosody model: per-phone durations and their factors, pitch arcs, accent shapes, pauses, effort, calibration numbers (named number lists) | The developer's takes, weighted toward a neutral prior: Klatt's durations (MITalk, Allen, Hunnicutt and Klatt 1987) and, for pauses, declination and the final fall, a 1942 newsreel (Public Domain Mark on archive.org). Nothing is measured from any other recording |
| The developer's clean-ups, voice 4 | Dictionary respellings (thick, today, Agios, Nikolaos, gentlemen, attack), phrase-final lengthening 1.4 / 1.2 (Klatt's), pitch-shape widening 2.0, pauses of 130 ms (comma), 220 ms (full stop) and 120 ms (breath), the developer's own medians; formant emphasis (`postfilter`) 0 |

Chosen by the developer, 2026-11-17 ("voice 4 is mostly fine ... we can put it in the game ... only
include the parameters for running the synthesizer"), after listening. SHA-256 of the file:
`9f2cae0978387f6453e82a8130b3b7115c5f2f985ba29ea7860158f3991e4cca`.

How it was made is in `tools/voice_world/README.md`. The held-out word accuracy of a speech
recognizer on the voice as the game plays it is 86.8% (the developer's own recordings: 96%).
