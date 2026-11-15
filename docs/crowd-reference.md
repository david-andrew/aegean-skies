# Crowd reference: what the crowd bed is fitted to

The harbour's and the cafe's crowd bed (`src/ambience_crowd.jo`) is synthesized. Nothing recorded
is shipped, sampled or convolved. Its parameters (`CrowdFit`) were fitted by measuring field
recordings of real crowds and comparing the synthesized bed with them. The recordings are
CC0 or public domain and were used only for analysis; they stay outside the repository.
Fetched and checked 14 November 2026 (Freesound licence fields and Wikimedia Commons metadata).

## Sources

| Recording | Recordist | Licence |
|---|---|---|
| [People Chatting in the Square of Scorrano, Puglia, Italy](https://freesound.org/s/861594/) | bassimat | CC0 1.0 |
| [Italian Square at Sunday Lunch Time, Piazza del Duomo, Padua, Sunday](https://freesound.org/s/832691/) | bassimat | CC0 1.0 |
| [130720_Trogir_17Gradska_4824.wav](https://freesound.org/s/195725/) | blaukreuz | CC0 1.0 |
| [130717_Split_Promenade1_F_4824.wav](https://freesound.org/s/195866/) | blaukreuz | CC0 1.0 |
| [130717_Split_DiocletianPalacePlaza2_4824.wav](https://freesound.org/s/195861/) | blaukreuz | CC0 1.0 |
| [140821_DubrownikPlaza_R.wav](https://freesound.org/s/249761/) | blaukreuz | CC0 1.0 |
| [120803_Brela_AT_Wharf_1_F_4824.wav](https://freesound.org/s/162696/) | blaukreuz | CC0 1.0 |
| [Greek Habitues - (Evosmos - Salonika) 16:18 28.09.11](https://freesound.org/s/130587/) | Ali@k | CC0 1.0 |
| [Crete Village Party 29-Aug-11.wav](https://freesound.org/s/131204/) | subtyrant | CC0 1.0 |
| [120731_Venice_AT_Street_2_F_4824.wav](https://freesound.org/s/162687/) | blaukreuz | CC0 1.0 |
| [VoicesPeopleNaples](https://freesound.org/s/710170/) | davidesforza | CC0 1.0 |
| [Outdoors Walla](https://freesound.org/s/478248/) | brunoboselli | CC0 1.0 |
| [large crowd, medium distance](https://commons.wikimedia.org/wiki/File:360703_eguobyte_large-crowd-medium-distance-stereo.wav) | eguobyte | CC0 1.0 |
| [another crowd](https://commons.wikimedia.org/wiki/File:211146_unfa_another-crowd.flac) | unfa | CC0 1.0 |
| [Karlova Street, Prague](https://commons.wikimedia.org/wiki/File:Karlova_0001.ogg) (checked, not in the fit: its spectrum is dominated by traffic) | Juan de Vojníkov | Public domain |

CC0: <https://creativecommons.org/publicdomain/zero/1.0/>. Freesound recordings were analysed
from their public HQ previews.

## Measures

Each recording (up to 90 s of it) and the bed (its loop played round for 20 s) were measured the
same way, mono for everything but the last measure:

- **Long-term spectrum** in third octaves, and its slope from 500 Hz to 4 kHz and from 4 to 12 kHz.
- **Modulation** of the 300-3000 Hz envelope (5 ms steps), as a modulation index in three bands:
  0.5-2 Hz (phrases and conversations), 2-8 Hz (syllables), 8-32 Hz (consonants, steps, clatter).
- **Level spread**, L10-L90 of the 50 ms level.
- **Voices standing out**: 50 ms frames more than 6 dB over the 2 s running median, per minute.
- **Harmonicity**: median normalized autocorrelation peak (80-400 Hz pitch) of 40 ms frames of
  the 80-1000 Hz band, and the share of frames over 0.6 (how much of it is one clear voice).
- **Sharp transients**: 9 dB rises in 5 ms in the 2-8 kHz band, per second.
- **Stereo coherence**, 250-4000 Hz.

## Results

| Measure | References: 25%, median, 75% | Bed (harbour) | Bed (cafe) | Old murmur |
|---|---|---|---|---|
| Slope 500 Hz-4 kHz, dB/oct | -6.2, -5.0, -3.9 | -5.4 | -5.3 | -8.2 |
| Slope 4-12 kHz, dB/oct | -8.1, -6.0, -5.0 | -6.6 | -6.6 | -7.8 |
| Modulation 0.5-2 Hz | 0.16, 0.22, 0.26 | 0.18 | 0.16 | 0.13 |
| Modulation 2-8 Hz | 0.20, 0.23, 0.33 | 0.22 | 0.21 | 0.23 |
| Modulation 8-32 Hz | 0.17, 0.19, 0.20 | 0.16 | 0.16 | 0.12 |
| Level spread L10-L90, dB | 6.8, 7.9, 10.1 | 9.7 | 9.7 | 6.2 |
| Voices standing out, per minute | 8.6, 16, 22 | 0 (single events instead) | 0 | 0 |
| Harmonicity | 0.35, 0.36, 0.39 | 0.40 | 0.39 | 0.44 |
| Share of clearly voiced frames | 0.04, 0.07, 0.10 | 0.06 | 0.05 | 0.14 |
| Sharp transients, per second | 0.4, 0.6, 1.6 | 2.9 | 2.5 | 5.8 |
| Stereo coherence | 0.53, 0.62, 0.71 | 0.71 | 0.75 | mono |

The long-term spectrum of the references' median, dB re its peak band:

| Hz | 100 | 126 | 159 | 200 | 252 | 317 | 400 | 504 | 635 | 800 | 1008 | 1270 | 1600 | 2016 | 2540 | 3200 | 4032 | 5080 | 6400 | 8063 | 10159 | 12800 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dB | -8.7 | -7.5 | -4.9 | -5.0 | -3.7 | -3.7 | -2.2 | -0.7 | -0.7 | -2.2 | -5.7 | -7.2 | -8.6 | -10.4 | -12.2 | -13.6 | -15.4 | -17.4 | -19.9 | -21.9 | -23.9 | -29.5 |

The bed keeps within 3 dB of it from 100 Hz to 13 kHz except a 3.7 dB dip at 1 kHz.

What the references taught, in the order it mattered: speech is mostly not voice (consonants,
breath and wobble; the old murmur was twice as clearly voiced as any crowd); a crowd is layered
(a few near, more across the square, many beyond); its loudness moves at phrase rate as much
as at syllable rate; it is never mono; and there is always low air under it. Louder single
voices are part of every recording but are left out of the loop, which repeats every 7 s, and
come instead from real people as single events (`ambience_voices`).

## Reproduce

`CROWD_SAMPLES=<scratch dir> sloppy --release tools/crowdlab.jo` renders the beds;
`CROWD_FIT="near=4,rt60=0.9"` tries other settings. The analysis scripts and the recordings are
kept outside the repository (`~/dev/tmp/aegean-skies/sound-hunt/py/crowdfeat.py`,
`~/dev/tmp/aegean-skies/refs/crowd/`).
