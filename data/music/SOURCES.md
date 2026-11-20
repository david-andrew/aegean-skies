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
| Gymnopédie No. 1 | Erik Satie (1866–1925), 1888 | [Mutopia, SatieE/gymnopedie_1](https://www.mutopiaproject.org/ftp/SatieE/gymnopedie_1/), Evin Robertson, Dover edition | Mutopia explicitly marks the transcription **Public Domain** |
| Ave Maria (Méditation sur le premier prélude de Bach) | Charles Gounod (1818–1893), 1853, on J. S. Bach's Prelude in C | [Mutopia, GounodC/AveMaria-PianoViolin](https://www.mutopiaproject.org/ftp/GounodC/AveMaria-PianoViolin/), Yann Leprince, Heugel 1856 | Mutopia explicitly marks the transcription **Public Domain** |
| Suite bergamasque: Clair de lune | Claude Debussy (1862–1918), 1905 | [Mutopia, DebussyC/L75](https://www.mutopiaproject.org/ftp/DebussyC/L75/debussy_Ste_Bergamesq_Clair/), Keith OHara, Fromont 1905 | Mutopia explicitly marks the transcription **Public Domain** |
| Adelita | Francisco Tárrega (1852–1909) | [Mutopia, TarregaF/adelita-duo](https://www.mutopiaproject.org/ftp/TarregaF/adelita-duo/), Jeffrey Olson's two-guitar arrangement, Antich y Tena | Mutopia explicitly marks the arrangement **Public Domain** |
| Berceuse (Dolly, Op. 56) | Gabriel Fauré (1845–1924), 1894 | [Mutopia, FaureG/O56](https://www.mutopiaproject.org/ftp/FaureG/O56/faure_dolly_berceuse/), Mike Blackstock's flute-and-guitar adaptation, Hamelle | Mutopia explicitly marks the adaptation **Public Domain** |
| Symphony No. 9 "From the New World", II: Largo | Antonín Dvořák (1841–1904), 1894 | [julian9284, score 4285886](https://musescore.com/julian9284/scores/4285886) | CC0 1.0 |
| Symphony No. 7, II: Allegretto | Ludwig van Beethoven (1770–1827), 1816 | [alexander, score 949716](https://musescore.com/user/15685/scores/949716) | CC0 1.0 |
| Eine kleine Nachtmusik, I: Allegro | Wolfgang Amadeus Mozart (1756–1791), 1827 | [madmax82, score 2225101](https://musescore.com/user/1817676/scores/2225101) | CC0 1.0 |
| Clarinet Concerto K. 622, II: Adagio | Mozart, 1801 | [NekMib_, score 5486316](https://musescore.com/user/16850931/scores/5486316) | CC0 1.0 |
| Piano Sonata No. 8 "Pathétique", II: Adagio cantabile | Beethoven, 1799 | [Mutopia 295](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=295), Chris Sawer, Berners, 1908 (edited by A. Winterberger); Peters, 1910 | Mutopia explicitly marks the transcription **Public Domain** |
| Symphony No. 40, I: Molto allegro | Mozart, 1798 | [Nicolas, score 106251](https://musescore.com/nicolas/scores/106251) | CC0 1.0 |
| Orchestral Suite No. 3: Air (an arrangement for violin and piano) | Johann Sebastian Bach (1685–1750) | [Aan Aditya Banuwarsa, score 4818780](https://musescore.com/user/5402316/scores/4818780) | CC0 1.0 |
| Má vlast: Vltava (The Moldau), piano | Bedřich Smetana (1824–1884), 1879 | [martinmosch12, score 5911315](https://musescore.com/user/32746368/scores/5911315) | CC0 1.0 |
| Liebestraum No. 3 | Franz Liszt (1811–1886), 1850 | [mooing, score 1578986](https://musescore.com/mooing/scores/1578986) | CC0 1.0 |
| Ständchen (Schwanengesang), piano transcription | Franz Schubert (1797–1828), 1829; Liszt, 1840 | [tonic64, score 4907304](https://musescore.com/user/22249306/scores/4907304) | CC0 1.0 |
| Symphony No. 5, III: Valse (piano) | Pyotr Ilyich Tchaikovsky (1840–1893), 1888 | [hmscomp, score 5623928](https://musescore.com/user/24069/scores/5623928) | CC0 1.0 |
| Lohengrin: Bridal Chorus (choir and piano) | Richard Wagner (1813–1883), 1850 | [Nicolas, score 43724](https://musescore.com/nicolas/scores/43724); the voices sung by our choir | CC0 1.0 |
| Hungarian Dance No. 1 (piano) | Johannes Brahms (1833–1897), 1869 | [ÐÑÐ·ÑÐºÐ°Ð½Ñ, score 1386646](https://musescore.com/user/1580161/scores/1386646) | CC0 1.0 |
| Daphnis et Chloé: Lever du jour | Maurice Ravel (1875–1937), 1912 | [Derek Benton, score 5888526](https://musescore.com/user/6053266/scores/5888526) | CC0 1.0 |
| Boléro | Ravel, 1929 | [darkblue865, score 5173477](https://musescore.com/user/15856401/scores/5173477) | CC0 1.0 |
| The Barber of Seville: Overture | Gioachino Rossini (1792–1868), 1816 | [mike320, score 2540876](https://musescore.com/user/6105546/scores/2540876) | CC0 1.0 |
| Carmen: Prelude (piano four hands) | Georges Bizet (1838–1875), 1875 | [Noah Godard, score 255426](https://musescore.com/user/125838/scores/255426) | CC0 1.0 |
| An der schönen blauen Donau (piano) | Johann Strauss II (1825–1899), 1867 | [hmscomp, score 114435](https://musescore.com/hmscomp/scores/114435) | CC0 1.0 |
| Unter Donner und Blitz (piano) | Strauss II, 1868 | [Mutopia 610](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=610), Stan Sanderson, C. M. Cady, Pub. 1878 | Mutopia explicitly marks the transcription **Public Domain** |
| Radetzky March (small band) | Johann Strauss I (1804–1849), 1848 | [solar, score 153800](https://musescore.com/user/47480/scores/153800) | CC0 1.0 |
| Florentiner March (an arrangement for double reeds) | Julius Fučík (1872–1916), 1907 | [Ian Compton, score 5911596](https://musescore.com/user/9488281/scores/5911596) | CC0 1.0 |
| The Four Seasons, Summer: III Presto | Antonio Vivaldi (1678–1741), 1725 | [bach2practice, score 5573287](https://musescore.com/bach2practice/scores/5573287); the solo violin on our accordion, a bass under the cello | CC0 1.0 |
| Csárdás (orchestra) | Vittorio Monti (1868–1922), 1904 | [TheNightreader, score 1783226](https://musescore.com/thenightreader/scores/1783226) | CC0 1.0 |
| Gianni Schicchi: O mio babbino caro (piano) | Giacomo Puccini (1858–1924), 1918 | [jeronjoseph, score 4416311](https://musescore.com/user/20208436/scores/4416311) | CC0 1.0 |
| La traviata: Brindisi (piano) | Giuseppe Verdi (1813–1901), 1853 | [Mutopia 1215](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1215), Alberto Corella, Calcografía de la 'Nueva Biblioteca Musical Económica', 1857-1869 | Mutopia explicitly marks the transcription **Public Domain** |
| La Paloma (string quartet) | Sebastián Yradier (1809–1865), c. 1863 | [szyhub, score 4816894](https://musescore.com/user/816231/scores/4816894) | CC0 1.0 |
| Santa Lucia (voice and piano) | Teodoro Cottrau (1827–1879), 1849 | [wizarcat, score 5956250](https://musescore.com/user/27649166/scores/5956250); the voice on the mandolin | CC0 1.0 |
| Funiculì, funiculà (two violins) | Luigi Denza (1846–1922), 1880 | [Alexander Evstyugov-Babaev, score 5677874](https://musescore.com/the_alex/scores/5677874); mandolin and guitar | CC0 1.0 |
| Locus iste (SATB) | Anton Bruckner (1824–1896), 1869 | [sangerforum, score 1972546](https://musescore.com/user/3099636/scores/1972546) | CC0 1.0 |
| Nabucco: Va, pensiero (SATB) | Verdi, 1842 | [sangerforum, score 1140631](https://musescore.com/user/3099636/scores/1140631); the voices sung by our choir | CC0 1.0 |
| Melita, "Eternal Father, Strong to Save" (SATB) | John Bacchus Dykes (1823–1876), 1861 | [Mutopia 1260](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1260), Steve Dunlop, www.cyberhymnal.org; sung by our choir | Mutopia explicitly marks the transcription **Public Domain** |

CC0: <https://creativecommons.org/publicdomain/zero/1.0/>.

**The rule** (the user's, from 20 November 2026). A piece ships when both hold:

1. **The composition is in the public domain**, in the United States (published 95 or more years
   ago: in 2026, in 1930 or earlier) and in the European Union (its composer, and anyone whose part
   of it is used: a co-composer, arranger, orchestrator or completer, died 70 or more years ago: in
   2026, in 1955 or earlier).
   Anything not in the public domain needs the user's explicit approval, piece by piece.
2. **The note sequence is free to use**: a MuseScore score in PDMX marked CC0 with
   `license_conflict=False`; a Mutopia edition marked Public Domain; or our own transcription
   from a public-domain score scan, dedicated to CC0.

There is no further margin. Ravel (died 1937) qualifies: *Daphnis et Chloé* (published 1912) and
*Boléro* (composed 1928, published 1929) are public domain in the US, and have been in the EU since
2008 (France's wartime extensions have also run out). 'O sole mio does not: a Turin court recognised Alfredo
Mazzucchi (died 1972) as its co-composer. Traditional music is no licence for a modern
arrangement: the sequence still needs (2), as the Ikariotikos sequence's CC0 does.

The MuseScore sequences were obtained from the MIDI and metadata archives of
[PDMX v9, June 2025](https://zenodo.org/records/15571083), by Phillip Long, Zachary Novack,
Julian McAuley and Taylor Berg-Kirkpatrick. Dataset metadata is
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); the individual scores have the separate permissions above. Each selected
CSV row has `license_conflict=False`; the stored score metadata agrees with its public
CC0 designation and lists no copyright claims. `source/licences.json` preserves the
source URLs, named uploaders, licence URLs and SHA-256 hashes of the exact shipped MIDI.
The original Mutopia RDF permission records (two for the first radio pieces and five for the Hotel
Ancora's evening set, fetched 13 November 2026; four for the wider repertoire, fetched 19 November
2026) are included beside their MIDI files.
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
* The wider repertoire (from *Symphony No. 9: Largo* in the table on) keeps each source's notes
  and instruments, except: Vivaldi's *Summer* gives the solo violin to the accordion and doubles
  the cello's low notes an octave down on the bass; the voices of *Va, pensiero*, *Melita* and the
  *Lohengrin* chorus (exported as piano or clarinet parts) are sung by the choir; *Santa Lucia*'s
  voice is played on the mandolin; *Funiculì, funiculà*'s two violins become mandolin and guitar.
  Each piece is played at one level, measured to sit at the hand-set pieces' loudness
  (`tools/music_level.py`, `levels.json`). On the radio, a station plays its style's pieces one
  after another, each from its start (`src/radio_synth.jo` radio_pool).
* Per-note start/end gain follows velocity and CC7/11. Controller curves within a note
  are approximated by a straight ramp, not reproduced exactly.

* The radio's Gymnopédie No. 1 (`gymnopedie-orchestra`) is the same Mutopia source, scored by
  `tools/music_pack.py` in the manner of Debussy's orchestration (1897, public domain): the tune on
  the oboe and then, from bar 22, the flute; the second-beat chords on the harp with muted strings
  holding them; the bass notes on the harp and the low strings. Only the instrumentation follows
  Debussy; no notes are taken from his score.
* The Hotel Ancora's evening set (not on the radio) is arranged for its small band:
  Gymnopédie No. 1 is Satie's piano texture, the pianist alone; Ave Maria keeps the source violin and piano (the bar's singer
  takes the violin's line, which then plays at half level); Clair de lune is the source piano
  alone, its rubato, dynamics, pedal and voicing from an annotated performance
  (`clair-de-lune-performance.json`, written by `tools/clair_performance.py`; see
  `docs/music-performance.md`); Adelita's two guitars become a mandolin-like plucked voice (the tune) and a guitar;
  the Berceuse's flute becomes the violin over the guitar. All source pitches and rhythms are
  kept; the interpretation pass adds gentle phrase timing and a final ritard. The Mutopia MIDI
  files play each piece once, without the printed repeats.

Rebuild: `python tools/music_pack.py`. Additional repertoire must meet the rule above: the
composition **and** the sequence. Do not substitute an unlicensed MIDI
just because its underlying composition is old.

Dataset publications: Long et al., *PDMX: A Large-Scale Public Domain MusicXML Dataset for Symbolic Music Processing*, ICASSP 2025, [doi:10.1109/ICASSP49660.2025.10890217](https://doi.org/10.1109/ICASSP49660.2025.10890217); Xu et al., *Generating Symbolic Music from Natural Language Prompts using an LLM-Enhanced Dataset*, 2024, [arXiv:2410.02084](https://arxiv.org/abs/2410.02084). Only the source score MIDI is used here, not generated examples or model output.

The interpretation pass changes timing, articulation and dynamics, not these licensed
pitch sequences. Its decisions are recorded in `performance.json`; see
`docs/music-performance.md`. `instruments.json` contains scalar parameters for the game's
procedural oscillators and envelopes, packed by `tools/music_timbres.py`. It contains no
PCM, recorded sample loops, waveform phases or measured impulse responses.
Its 17th family, the 1920s upright piano (`MUSIC_UPRIGHT`, a honky-tonk), was fitted the same
way as the others (per-partial amplitudes, measured over the unison's beat, and two decay rates at
three velocities and seven pitches; inharmonicity, attack, release; loudness kept across the
keyboard), plus a body response fitted from a reference phrase and the unison's spacing (two equal
strings 5 cents apart, `UPRIGHT_DETUNE_CENTS` in src/music_synth.jo), to FluidR3 GM's Honky-tonk
Piano (bank 0, program 3; the same soundfont file, SHA-256 74594e8f...a1bc1cb0, as the measurements
above; copyright Frank Wen, permissive licence). Its notes and phrases were rendered through
FluidSynth offline in scratch for measurement only; no soundfont data or rendered audio is in this
repository, only the fitted numbers.
