# Orchestral room and focused instrument refinements

The classical programme selects a larger procedural room for the two Mahler pieces.
Four prime-length damped combs, two allpass diffusers and three early reflections give
an approximately three-second low-frequency decay. High frequencies decay sooner.
It adds about 57 KiB of delay storage while selected. Other programmes retain the
previous small room. Seeking clears both early and late reflections.

The solo trumpet has an independent deterministic pressure state, refreshed at each
lip cycle and smoothed between cycles. It introduces small correlated pitch and
amplitude irregularity alongside the existing slow vibrato. A faint high-passed air
component and a modest, register-dependent upper-partial boost at high effort give
loud notes more brass edge. No waveform or recorded phase is stored.

A few piano fast-decay modes previously extrapolated to excessively large amplitudes
before their earliest fitted observation. Their initial amplitudes are now constrained
by short-time attack measurements. Slow components, decay rates, hammer noise and
inharmonicity are retained. This removes the main metallic onset without suppressing
the sustained body. The island pluck is unchanged.

All parameters are numbers for procedural synthesis. No recorded samples, impulse
responses or external synthesizer are used at runtime. Reference audio and analysis
remain outside the repository. See `music-playback-budget.md` for the bounded caches.

The Adagietto has an annotated, shared performance clock and independent section-level
contours in `data/music/adagietto-performance.json`. The packer validates the interpreted
score fingerprint before applying the annotation. MUS3 adds two fixed-point mix gains per
note; these do not select a different effort spectrum or enter note-body cache keys.
The clock uses broad chroma alignment; section levels are regularized spectral estimates,
not isolated recordings of the desks. Overlapping string sections remain ambiguous.

## Station levelling

`radio_station.jo` processes programme audio before any record or receiver effects. Its
0.8-second RMS detector steers a gain bounded to 0.35–6, falling over about 1.2 seconds
and rising over four seconds. Only 70% of the logarithmic level difference is corrected,
leaving broad performance contrast. A gentle peak-envelope compressor and 4 ms lookahead
sample-peak limiter catch larger excursions. Silence does not raise the target gain.
The original phrase envelopes and instrument efforts remain in the generated performance;
receiver hiss/crackle never enters the gain detector. Morse uses the same station stage.

The Music page's **Station levelling** checkbox defaults on; unfiltered playback bypasses
both station processing and reception. Toggling or seeking restarts the audition stream,
including the gain detector, with a brief initial gain acquisition. Consequently a seek is
not equivalent to a station which has played continuously from the beginning. The normal
radio uses levelling by default. The small existing receiver AGC remains a separate effect.

The harp has a restrained upper-partial lift (1.5 dB above the third harmonic, with
energy normalization) and 0.35/s additional fast-component decay. Slow body components
are retained. These conservative targets come from transient-minus-background estimates
in mixed orchestral passages, not confidently isolated harp tracks; the hall supplies
its diffuse bloom. String oscillator models remain unchanged.
