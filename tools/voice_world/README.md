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

`phone_align.py` labels a speaker's takes phone by phone: an acoustic phone classifier (the
Charsiu wav2vec2 frame classifier, charsiu/en_w2v2_fc_10ms, loaded from a scratch copy; its code
is MIT-licensed, the checkpoint's card states no licence, so it is an analysis tool only and never
ships) scores 39 phones and silence every 10 ms, and our own Viterbi walks the line's
pronunciation with accent variants (neighbouring vowels, reductions, common consonant swaps,
optional drops), so a phone is labelled as spoken. It replaced the earlier DTW-to-synthesis
alignment, which cut units in the wrong places across large rate and pitch differences.
`voicefile.py` reads a packed voice back. `evaluate.py` can score word accuracy with a local
speech recognizer (faster-whisper; scratch only). Its
pronunciations follow the game's: weak forms, the name list, CMUdict, plural and possessive endings
on a known stem (-'s, -s, -es, as `voice_text.jo` does), then the letter-to-sound rules.

`tune_round.py` runs one tuning round on whatever the speaker has recorded. It caches the
alignment and analysis of each take and, for nested random subsets of the pool, builds three
voices: the prior voice adapted toward the speaker (per-phone spectral offsets, the speaker's
prosody), a blend (the speaker's own units where there are at least two tokens, adapted prior
units elsewhere), and the speaker's units only. Each is scored on the held-out lines as they stand
at the time of the run (with the starting voice and earlier rounds' voices scored again on the same
lines), including word accuracy, and the round is published with a learning curve per kind. A failed run says at which stage and why, and `--round rN` retries it,
reusing every finished scoring.

More of the speaker's data must never make the voice worse, so the fitter:

- fits prosody (durations, pitch, intonation, pauses) to the plain reads only: the game adds
  each genre's delivery itself, and fitting the performed reads would count it twice;
- moves each prosody number from the prior toward the speaker's by how much data it rests on
  (n / (n + k)) rather than switching over at a threshold;
- removes the level its fitted intonation shapes would add (they are fitted to mean-removed
  contours, but the synthesizer adds them to the phrase level as they are; a speaker's fit came
  out 3 semitones high);
- guards the prosody: about ten training lines are kept out of the prosody fit, and at each pool
  size the new prosody, the new prosody with the previous intonation, and the previous choice
  are scored on them by word accuracy. The one with the most of the speaker's data within five
  points of the best is kept (two until round 4: how close the voice sounds to the speaker is
  their call, so the guard only stops a real loss of intelligibility). The round's note reports
  each candidate's word accuracy and pitch match side by side.

Pronunciation and delivery follow the speaker (round 4):

- a voice carries the dictionary entry of every word in the script, not only the game's own text
  (held-out words used to fall to the letter-to-sound rules: "measured" came out /miːzjʊrd/);
- the aligner chooses among the dictionary's alternative pronunciations of each word ("nobody"
  reduced, "twenty" without its T, "wind" the noun), and the speaker's most frequent
  realisation of each word they have said goes into their voice's lexicon; a dictionary phone
  they systematically say as another (in half or more of at least 15 tokens) is changed in the
  words they have not said;
- the speaker's room noise (the room-tone take) is subtracted from every analysed frame: a stop's
  closure in a home recording is room noise, which had entered the units and the adapted voice's
  per-phone offsets about 20 dB too loud and was heard as a scratch at stops; consonant level
  offsets also stay within 3 dB of the vowels';
- delivery is fitted by synthesis: sample training lines of each genre are rendered and compared
  with the speaker's takes (articulation rate, pitch median and spread, pauses, voicing), and each
  genre's tempo, register, range and pause scale (`style_<genre>` in the data file, used through
  `VoiceStyle.genre`), the plain reading's register, reference rate and pauses, and the shape
  gain, pitch limit and voicing threshold (`shape`) are set so the synthesis matches; a genre with
  few lines stays nearer the plain reading (n / (n + 1)), a genre with none keeps the station's
  hand-set style.

Sentence intonation, the energy envelope and vocal effort are learned from the speaker (round 5,
`intonation.py`):

- each syllable's pitch level (re the line), its slope through the vowel and its energy (re the
  line, after the vowel's own intrinsic loudness) are linear functions of 43 features: accent
  (first, nuclear, before and after), place in the phrase, what ends the phrase (full stop,
  question, exclamation, comma, ellipsis or dash, breath), resets at later phrases and sentences,
  and genre; ridge-fitted on the takes, the weights travel in the data file (`tune_*`) and the
  game computes the same features (`voice_syllable_features`) and joins the targets into a
  contour (centred on the line, so register and range are calibrated separately) and an energy
  envelope;
- an ellipsis or a dash is now a pause in the game, and every pause knows what ended its phrase;
- each genre's vocal effort is the speaker's own spectral change against their plain reads
  (`tilt_<genre>`), and calibration fits brightness (the plain reading's too), the contour's size
  per genre and a sustain floor for voiced frames by synthesis, like tempo and register;
- on held-out lines with the speaker's own timing, the learned contour correlates 0.47 with their
  takes (round 4's model 0.44) at 3.5 st RMS (4.3); two takes of the same line by the speaker
  correlate 0.55 at the syllable level, so that is about the ceiling.

The voice studio's "Tune" button starts a round. The recordings, voices and rounds all stay in
scratch.

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
