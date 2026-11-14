# The radio announcer: WORLD-style analysis and the packed voice

The announcer is a classical vocoder voice, not a recording and not a neural model. These tools
measure a narrator WORLD-style (after M. Morise's WORLD vocoder: F0 from band-filtered interval
agreement refined by instantaneous frequency, a pitch-adaptive harmonic-free spectral envelope,
band aperiodicity) and pack the **averaged numbers** the game synthesizes from. The game's side is
`src/voice_text.jo` (text → phones → durations, pitch → 5 ms frames) and `src/voice_synth.jo`
(the streaming source/filter synthesizer); `docs/radio.md` describes the result.

No WORLD code is used (WORLD is BSD-3; its equations were read, the code here is our own numpy),
nothing from verr-voice (no licence; its approach was studied for ideas only), and no audio or
audio snippet enters the repository.

## What is shipped and where it came from

`data/voice/announcer.z` (raw deflate, format `AVX1`, written by `pack.py`):

- the phone set (CMU ARPAbet, 39 phones + pause);
- 783 **diphone trajectories** (centre of one phone to the centre of the next): each 12 points of
  25 mel-cepstral coefficients (all-pass warping α = 0.42 at 16 kHz), 5 band aperiodicities and a
  voicing fraction, int8/uint8. Each is the mean of up to 12 tokens nearest the medoid of all
  tokens of that diphone, so it is a statistical description of the spectral envelope, without
  phase, pitch or waveform. Gain is relative to the speaker's own vowel level in the same phrase;
- a 2,921-word pronunciation lexicon: CMUdict (Carnegie Mellon University, BSD-style licence;
  first pronunciation of each word) for the words the game's own text uses, plus hand-written
  entries for the world's place names (`pack.py MANUAL`);
- 145 letter-to-sound rules (`lts.py`, written for this project) for words not in the lexicon,
  mostly the living world's invented names.

`src/voice_model.jo` holds the prosody numbers as constants with their provenance: per-phone
median durations, phrase pitch level and spread, accent rise and its peak position, final fall,
continuation rise, pauses and speaking rate.

Sources of the measurements (analysed in scratch, never committed, listed in the scratch
report): a modern recap narrator who deliberately imitates the period newsreel delivery (17
minutes; spectral envelopes and prosody), chosen by the user as the delivery target, and a 1942
newsreel narrator (pauses, declination and final falls only, since its band-limited transfer
cannot give reliable spectra). Phone boundaries came from an automatic aligner; the voice was
separated from music with a source-separation model. Those models were measuring instruments
only and are not part of the game.

## Rebuilding

Python 3 with numpy, scipy, soundfile and (for the lexicon) the `cmudict` package. Inputs are a
separated mono narration track and its phone alignment JSON (`phones`: `p`, `start`, `end`,
`stress`, `confidence`, `segment`, `wi`, `pronunciation_fallback`) plus the word JSON
(`words` with punctuation), all kept outside the repository.

```sh
python analyse_corpus.py VOICE.wav PHONES.json OUT.npz --speakers SPEAKERS.json   # ~6 min / 17 min audio
python prosody.py PHONES.json WORDS.json OUT.npz > prosody.json
python pack.py --corpus OUT.npz PHONES.json --prosody prosody.json --castle period-prosody.json \
               --repo ../.. --report report.json
python -m unittest test_voice_world.py
```

`vocoder.py` is the numpy reference of the game's synthesizer, used for copy-synthesis checks.

## Checks

- `tests/voice_test.jo`: tables load and cover every phone at a phrase edge; numbers and clock
  times; dictionary, plural/possessive and rule pronunciations; deterministic plans with voiced
  pitch in range; the vocoder is identical however the stream is cut; a spoken bulletin repeats
  on the world clock through the receiver.
- `tools/voicelab.jo` renders `name|text` lines to WAV (dry, strong, medium, weak reception) in a
  scratch directory; `tools/voice_budget.jo` times the voice against a music piece in one harness
  (run on redfox, native and `--target wasm`).
- Intelligibility was measured with a local speech recognizer as an instrument (never in the game)
  on held-out sentences; see the scratch report. It is a proxy for listening, not a verdict.
