# Exact playback cache

The sound at `063a405` is the reference. No instrument, score, expressive timing or
receiver parameter changes are part of this optimization. `tools/music_identity.py`
compares the complete dry f64 stream against a git snapshot of that revision, including
warm replay and analytic seeks. The short mode also builds a standalone wasm check page.

## Bounded storage and first play

Each synthesizer owns 64 exact modal-body prefixes of 8192 f64 samples (4 MiB), a
64-entry cache of the analytic wind/bow cycles (256 KiB), and roughly 120 KiB of keys
and recurrence states. Total added storage is about 4.4 MiB. Two simultaneous synth
instances can therefore use about 8.8 MiB of cache. No recording, baked PCM download,
velocity bin, sample quantization, worker thread or persistent browser storage is used.

A key includes instrument, pitch, exact effort and the initial analytic seek age.
The model bank is immutable for an instance. A seek initialization is deliberately
distinct from a recurrence advanced from note onset: the former is not bit-identical
to replay. Different note lengths and envelopes can reuse a modal body because gates,
expression and texture stay live. The per-voice RNG and slot-ordered mix are unchanged.

Only a missing suffix of at most 128 samples is built on demand. No whole-note or
whole-piece bake occurs at an onset. Active prefix readers pin entries. At the prefix
boundary, the exact saved oscillator/decay state transfers to the voice and synthesis
continues live; no looping, crossfade or analytic reconstruction alters its tail.
Unpinned entries use LRU eviction. Wave cycles are copied into their existing per-voice
storage, so their cache does not need pinning. Disabled audio never creates these banks.

The streaming callers refill at most 800 samples (50 ms) per update, including first
play and seeks. The 250 ms queue target builds over subsequent frames. This bounds the
initial and catch-up work instead of asking a single game frame to render 250 ms.
The scalar model bank decodes as one contiguous f32 array, then widens exactly to f64.
Both game streams prepare their storage and run a discarded 128-sample procedural
warmup during world loading. This pays allocation and browser compilation costs before
Play; it opens no stream/device. Preparation resets receiver strength, programme clock,
voices and hall state. A regression test compares cold and prepared programme samples.
Headless/no-audio startup skips preparation entirely.

## Same arithmetic, less repeated work

The renderer batches at most 128 samples between note events and cache boundaries.
It copies voice state once per batch and skips inactive slots once, while retaining
sample order within each recurrence and slot order within each mixed sample. Note-end
handling preserves the old slot reuse and oldest-voice stealing behavior exactly.

Modal loops run one partial over a short contiguous output span. Each sample's partial
addition order is unchanged. The span is checked before a local pointer is taken;
neither storage resizes or escapes while the pointer is held. A conservative decay
bound skips the cutoff test only when every sample is safely above it; quiet tails
retain the original cutoff. Envelopes, wind motion and noise keep their original
operation order. Positive phase wrap avoids a general remainder calculation. On x86-64, independent
loud modes run in pairs to hide floating-point multiply latency. Their contributions
still enter the sum one at a time in the original order; wasm and ARM retain the scalar
kernel. The voice mixer also checks contiguous input/output spans once before its loop,
instead of repeating bounds checks per sample.
Noise RNG integers scale by exact power-of-two multiplication. The expired attack
transient is exactly zero without evaluating its old divide. Receiver unit phases use
truncated subtraction rather than dividing by one; receiver settings stay unchanged.
No reassociation, fused arithmetic, precision change or raised cutoff is used.

A larger 16 MiB body cache saved only about 4% of the hardest measured passage's
instructions compared with 4 MiB. The smaller cache remains the default. Proposed
velocity quantization was rejected because it would change the auditioned output.

## Reproduce validation and runtime checks

- `sloppy test tests/music_cache.jo --release`: exact cached/uncached comparisons with
  eviction, many overlapping voices, long releases, arbitrary seeks, different block
  partitions, receiver continuity and score wrap; cutoff-boundary arithmetic tests.
- `python3 tools/music_identity.py --scratch <outside-repo-directory>`: full f64
  comparison against the auditioned revision. Add `--quick --wasm` for a browser page.
  `--chain` compares 2.88 million receiver samples while varying signal, tuning, wear
  and night; it also supports `--wasm`.
- `sloppy build tools/music_budget.jo --release -o <scratch>/budget`: first play,
  60 seconds of cold and warm playback, block percentiles and seek latency for all
  seven pieces. Compile the same harness against the original `583cc00` and the
  auditioned `063a405` for comparison. `--target wasm` builds a browser equivalent.
- `tools/music_prepare_budget.jo` measures loading warmup separately, then actual
  first-Play and seek latency after preparation. The raw constructor measurement in
  `music_budget.jo` deliberately includes work the game now does during loading.
- Run timing only on redfox, one job under `flock ~/dev/tmp/bench.lock`, with audio
  disabled; mute the headless browser as well. Desktop checks use instruction counts.

The scratch listening report's **Cost** section records the final measurements and
whether the original renderer's runtime budget passes. Instruction counts alone do
not establish that gate. Phrase caching is not a substitute for cold-play performance:
a rolling phrase buffer moves deadlines and helps replay, but cannot eliminate the
work of rendering a phrase for the first time. It must also preserve exact note phases,
expression, noise, stealing and hall state, not merely match a sequence of pitches.
