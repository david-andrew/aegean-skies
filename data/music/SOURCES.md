# Radio note library

These are **note sequences**, not recordings. Audio is made by `src/music_synth.jo`.
No soundtrack recordings, soundfonts, voice models or generated audio assets ship.
`tools/music_pack.py` converts the checked-in source MIDI to compact events; its only
third-party build dependency is `mido`. It has no network access. Runtime needs neither
Python nor MIDI software. The generated `.z` files and `src/music_data.jo` are checked in.

## Sources and permissions (checked 12 November 2026)

| Piece | Composition | Note transcription / arrangement | Permission for the sequence |
|---|---|---|---|
| Symphony No. 5, IV: Adagietto | Gustav Mahler (1860–1911), 1904 | [mooing, score 4230156](https://musescore.com/user/1397281/scores/4230156); harp, two violins, viola, cello, bass | CC0 1.0 |
| Symphony No. 5, I: opening trumpet call | Mahler, 1904 | Our concert-pitch transcription of the pickup and eight bars on printed p. 3 of [Peters plate 9015, Sibley Music Library](https://hdl.handle.net/1802/15744) | Public-domain 1904 score; new transcription dedicated to CC0 1.0 |
| Magnetic Rag | Scott Joplin (1868–1917), 1914 | [Mutopia 441](https://www.mutopiaproject.org/ftp/JoplinS/magnetic/), Kurt Holtrop, original edition | Mutopia explicitly marks the transcription **Public Domain** |
| El Choclo | Ángel Villoldo (1861–1919), 1903 | [bbuyukkarhan, piano score 5885692](https://musescore.com/user/33429668/scores/5885692) | CC0 1.0 |
| Entry of the Gladiators, marching-band excerpt | Julius Fučík (1872–1916), 1897 | Eric Russ / imwoaheric, [score 5733627](https://musescore.com/user/34335505/scores/5733627), “Stands Tune” | CC0 1.0, including the modern arrangement |
| Ikariotikos | Traditional Greek dance, anonymous | ekwesh62, [score 6124814](https://musescore.com/user/34984664/scores/6124814) | CC0 1.0 |
| Bethena, a concert waltz | Joplin, 1905 | [Mutopia 463](https://www.mutopiaproject.org/ftp/JoplinS/bethena/), Magnus Lewis-Smith, original manuscript | Mutopia explicitly marks the transcription **Public Domain** |

CC0: <https://creativecommons.org/publicdomain/zero/1.0/>.
The named historical composers died more than 100 years ago and these compositions
were published before 1929. This deliberately avoids relying only on a US publication
cutoff or assuming every country uses a 70-year term. Traditional music is not a licence
for a modern arrangement: the selected Ikariotikos sequence separately carries CC0.

The four MuseScore sequences were obtained from the MIDI and metadata archives of
[PDMX v9, June 2025](https://zenodo.org/records/15571083), by Phillip Long, Zachary Novack,
Julian McAuley and Taylor Berg-Kirkpatrick. Dataset metadata is
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); the individual scores have the separate permissions above. Each selected
CSV row has `license_conflict=False`; the stored score metadata agrees with its public
CC0 designation and lists no copyright claims. `source/licences.json` preserves the
source URLs, named uploaders, licence URLs and SHA-256 hashes of the exact shipped MIDI.
The two original Mutopia RDF permission records are included beside their MIDI files.
Dataset MIDI was converted, instrument assignments changed as described below, and only
a small subset of metadata retained. This is not an endorsement by any source author.

## Performance changes and limits

* Adagietto retains the imported timing, expressive note velocities and CC7/CC11 gain
  at note boundaries. Harp and all five string sections remain separate. This is the
  whole imported movement, not a repeated invented phrase. MIDI is a transcription,
  not a critical edition; the converter does not interpret printed expression marks.
* The first-movement sample is **only the opening solo call**, not the whole movement
  or its orchestral entry. Written B-flat trumpet pitches are transposed down a tone.
  The score says “In gemessenem Schritt. Streng. Wie ein Kondukt.” The pickups are
  sixteenth-note triplets. The fourth long note is E4 concert pitch; the final tied
  C-sharp5 is one continuous note. Earlier versions used overly broad pickups and
  incorrectly retriggered that tie. Coarse timing and three-point effort contours in
  `opening-performance.json` now annotate this solo excerpt explicitly.
* Magnetic Rag is explicitly a **foxtrot arrangement of a rag**, not labelled an
  original foxtrot. All source piano pitches/rhythms are retained, at quarter=116;
  upper notes use clarinet, lower piano/bass, with light banjo doubling and a drum beat.
* El Choclo's piano notes become accordion/piano/bass. This is the imported short
  piano arrangement, not a claim to every repeat of the original published score.
* The march retains Eric Russ's short band arrangement. Saxophones use our reed voice;
  percussion is procedural. It is not the entire original march.
* Ikariotikos uses the licensed melody on paired plucked strings, with a quiet octave
  accordion doubling; no new chord progression is substituted for the melody.
* Bethena retains the source piano notes and tempo. MIDI sustain/pitch-bend effects are
  not interpreted; note release and hall decay supply a modest sustain tail.
* Per-note start/end gain follows velocity and CC7/11. Controller curves within a note
  are approximated by a straight ramp, not reproduced exactly.

Rebuild: `python tools/music_pack.py`. Additional repertoire should meet the same
composition **and** sequence permission checks. Do not substitute an unlicensed MIDI
just because its underlying composition is old.

Dataset publications: Long et al., *PDMX: A Large-Scale Public Domain MusicXML Dataset for Symbolic Music Processing*, ICASSP 2025, [doi:10.1109/ICASSP49660.2025.10890217](https://doi.org/10.1109/ICASSP49660.2025.10890217); Xu et al., *Generating Symbolic Music from Natural Language Prompts using an LLM-Enhanced Dataset*, 2024, [arXiv:2410.02084](https://arxiv.org/abs/2410.02084). Only the source score MIDI is used here, not generated examples or model output.

The interpretation pass changes timing, articulation and dynamics, not these licensed
pitch sequences. Its decisions are recorded in `performance.json`; see
`docs/music-performance.md`. `instruments.json` contains scalar parameters for the game's
procedural oscillators and envelopes, packed by `tools/music_timbres.py`. It contains no
PCM, recorded sample loops, waveform phases or measured impulse responses.
