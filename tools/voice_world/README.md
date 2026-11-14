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

## The data file is not in the repository

Until the final voice is chosen, the packed announcer data is kept out of git entirely (it is
derived from reference recordings, and `/data/voice/` is ignored). `pack.py --out` refuses a path
inside the repository. The game and tools read it from the path in **`AEGEAN_VOICE_DATA`**; without
it the announcer is off and the radio keeps its Morse bulletins (`tests/voice_test.jo` checks
both cases). Development listening is from WAV samples rendered in scratch.

## What the data file holds and where it came from

The announcer data file (raw deflate, format `AVX1`, written by `pack.py`):

- the phone set (CMU ARPAbet, 39 phones + pause);
- 783 **diphone trajectories** (centre of one phone to the centre of the next): each 12 points of
  25 mel-cepstral coefficients (all-pass warping α = 0.42 at 16 kHz), 5 band aperiodicities and a
  voicing fraction, int8/uint8. Each is the mean of up to 12 tokens nearest the medoid of all
  tokens of that diphone, so it is a statistical description of the spectral envelope, without
  phase, pitch or waveform. Gain is relative to the speaker's own vowel level in the same phrase;
- a 2,921-word pronunciation lexicon: CMUdict (Carnegie Mellon University, BSD-style licence,
  reproduced in `CMUDICT-LICENSE.txt` beside this file; first pronunciation of each word) for the words the game's own text uses, plus hand-written
  entries for the world's place names (`pack.py MANUAL`);
- 145 letter-to-sound rules (`lts.py`, written for this project) for words not in the lexicon,
  mostly the living world's invented names;
- the fitted **prosody model** (`prosody_fit.py`), as named number lists that
  `src/voice_model.jo` reads (the repository only has neutral placeholder defaults):
  - durations: per-phone base durations (stressed and reduced vowels separate: schwa AX is not the
    vowel of "strut" AH; IX, AXR, IYX likewise) and multiplicative factors for function words,
    word position, clusters, polysyllables, phrase-final rhymes and stress, with a separate rate
    elasticity per class (how much stressed vowels, unstressed vowels, onsets and codas shrink as
    the narrator speeds up), fitted by least squares on log duration and scored on held-out
    phrases against per-phone medians;
  - intonation: a least-squares superposition of a phrase arc over normalised time, accent shapes
    aligned to each stressed content-word vowel (first, downstepped middle, nuclear with its fall)
    and microprosody (inside voiced obstruents, after obstruents), scored on held-out phrases
    (it fitted better than a Fujisaki command model and the first hat-bump model); phrase level
    by position in the sentence and its spread;
  - vocal effort: the mel-cepstral change per semitone as the narrator raises his voice;
  - fricative caps (90th percentile by position) and pauses (comma, full stop, unpunctuated
    breath).

The measured values themselves are only in the data file and the scratch report.

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
python prosody_fit.py PHONES.json WORDS.json OUT.npz SPEAKERS.json fit.json     # ~3 min
python pack.py --corpus OUT.npz PHONES.json --fit fit.json \
               --repo ../.. --out ~/dev/tmp/aegean-skies/radio/voice2/data/announcer.z --report report.json
python -m unittest test_voice_world.py
```

`vocoder.py` is the numpy reference of the game's synthesizer, used for copy-synthesis checks.

`evaluate.py` scores the voice against held-out recordings of a real speaker (the user's own
recordings, kept in scratch). It synthesizes each line in its genre's delivery and aligns the
recording to the synthesis by dynamic time warping. The synthesis's phone boundaries carry over
to the recording, so the same aligner serves for fitting. It then reports mel-cepstral distortion,
F0 RMSE and correlation, energy correlation, phone-duration error, speaking rate and voicing
errors, and publishes loudness-matched comparisons for listening.

`tune_round.py` runs one tuning round on whatever the speaker has recorded. It caches the
alignment and analysis of each take, fits voices to nested random subsets of the pool (falling
back to a prior voice's prosody where the subset is too small), scores each on the held-out lines,
and publishes the round with a learning curve. The voice studio's "Tune" button starts it. The
recordings, voices and rounds all stay in scratch.

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
