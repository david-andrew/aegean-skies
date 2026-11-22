"""Rebuild licensed note data: python -m pip install mido; python tools/music_pack.py.
No audio, sampled instruments or network calls. Durations include MIDI tempo changes.
The per-track channel state matters: exported orchestral MIDIs reuse channel numbers.
"""
from pathlib import Path
from bisect import bisect_right
from collections import defaultdict, deque
import json, math, struct, zlib
import mido
from music_performance import score_clock, interpret, apply_performance_map, schubert_points, BeatMap, SCHUBERT_MIDI_QUARTER
from music_grace import regrace
from expressive_timing import ExpressiveTiming, timing_map, warp, MOODS, mood_timing, mood_touch
ROOT = Path(__file__).resolve().parents[1]
RATE = 16000
# Must agree with MusicInstrument in music_synth.jo.
STRINGS, BRASS, FLUTE, OBOE, CLARINET, BASSOON, PIANO, HARP, BOUZOUKI, ACCORDION, BANJO, TIMPANI, DRUMS, BASS, CHOIR, TRUMPET = range(16)
PIECES = [
 ('adagietto', 'Symphony No. 5: Adagietto', 'Gustav Mahler', 'Voice of Kalyra'),
 ('mahler-opening', 'Symphony No. 5: opening call (excerpt)', 'Gustav Mahler', 'Voice of Kalyra'),
 ('magnetic', 'Magnetic Rag (foxtrot arrangement)', 'Scott Joplin', 'Blue Lantern'),
 ('el-choclo', 'El Choclo', 'Angel Villoldo', 'Night Gull / Blue Lantern'),
 ('gladiators', 'Entry of the Gladiators (excerpt)', 'Julius Fucik; arr. Eric Russ', 'Orenthia National'),
 ('ikariotikos', 'Ikariotikos', 'Traditional Greek', 'Archipelago Radio'),
 ('bethena', 'Bethena: a concert waltz', 'Scott Joplin', 'Blue Lantern'),
 # The Hotel Ancora's quiet evening set (piano, violin, guitar, mandolin): not on the radio.
 ('gymnopedie', 'Gymnopedie No. 1', 'Erik Satie', 'Hotel Ancora'),
 ('ave-maria', 'Ave Maria (on the first Prelude of Bach)', 'Charles Gounod', 'Hotel Ancora'),
 ('clair-de-lune', 'Clair de lune', 'Claude Debussy', 'Hotel Ancora'),
 ('adelita', 'Adelita', 'Francisco Tarrega', 'Hotel Ancora'),
 ('berceuse', 'Berceuse (Dolly)', 'Gabriel Faure', 'Hotel Ancora'),
 # The radio's Gymnopedie: the same score as the bar's, in the manner of Debussy's orchestration
 # (1897): harp and low strings under it, the tune on the oboe and then the flute, muted strings.
 ('gymnopedie-orchestra', 'Gymnopedie No. 1 (orchestrated)', 'Erik Satie; orch. after Claude Debussy', 'Voice of Kalyra'),
 # The wider repertoire (data/music/SOURCES.md): the concert hall's symphonies, concertos, piano
 # pieces and choruses; the light programme's waltzes, marches and overtures; the cafe stations'
 # songs; the chapel's choir. Each played by our own synthesizer from a public-domain or CC0 score.
 ('new-world-largo', 'Symphony No. 9 "From the New World": Largo', 'Antonin Dvorak', 'Kalyra Concert Hall'),
 ('seventh-allegretto', 'Symphony No. 7: Allegretto', 'Ludwig van Beethoven', 'Kalyra Concert Hall'),
 ('kleine-nachtmusik', 'Eine kleine Nachtmusik: Allegro', 'Wolfgang Amadeus Mozart', 'Kalyra Concert Hall'),
 ('clarinet-adagio', 'Clarinet Concerto K. 622: Adagio', 'Wolfgang Amadeus Mozart', 'Kalyra Concert Hall'),
 ('pathetique-adagio', 'Sonata "Pathetique": Adagio cantabile', 'Ludwig van Beethoven', 'Kalyra Concert Hall'),
 ('mozart-forty', 'Symphony No. 40', 'Wolfgang Amadeus Mozart', 'Kalyra Concert Hall'),
 ('bach-air', 'Air (Orchestral Suite No. 3)', 'Johann Sebastian Bach', 'Kalyra Concert Hall'),
 ('moldau', 'Ma vlast: The Moldau', 'Bedrich Smetana', 'Kalyra Concert Hall'),
 ('liebestraum', 'Liebestraum No. 3', 'Franz Liszt', 'Kalyra Concert Hall'),
 ('standchen', 'Standchen (Schubert, arr. Liszt)', 'Franz Schubert; arr. Franz Liszt', 'Kalyra Concert Hall'),
 ('fifth-valse', 'Symphony No. 5: Valse', 'Pyotr Ilyich Tchaikovsky', 'Kalyra Concert Hall'),
 ('lohengrin-chorus', 'Lohengrin: Bridal Chorus', 'Richard Wagner', 'Kalyra Concert Hall'),
 ('hungarian-one', 'Hungarian Dance No. 1', 'Johannes Brahms', 'Kalyra Concert Hall'),
 ('daphnis-introduction', 'Daphnis et Chloe: Introduction', 'Maurice Ravel', 'Kalyra Concert Hall'),
 ('bolero', 'Bolero', 'Maurice Ravel', 'Kalyra Concert Hall'),
 ('barber-overture', 'The Barber of Seville: Overture', 'Gioachino Rossini', 'Orenthia Light Programme'),
 ('carmen-overture', 'Carmen: Prelude', 'Georges Bizet', 'Orenthia Light Programme'),
 ('blue-danube', 'On the Beautiful Blue Danube', 'Johann Strauss II', 'Orenthia Light Programme'),
 ('thunder-lightning', 'Unter Donner und Blitz', 'Johann Strauss II', 'Orenthia Light Programme'),
 ('radetzky', 'Radetzky March', 'Johann Strauss I', 'Orenthia Light Programme'),
 ('florentiner', 'Florentiner March', 'Julius Fucik', 'Orenthia Light Programme'),
 ('summer-accordion', 'Summer (The Four Seasons): Presto, on the accordion', 'Antonio Vivaldi', 'Radio Mandolinata'),
 ('csardas', 'Csardas', 'Vittorio Monti', 'Radio Mandolinata'),
 ('babbino-caro', 'O mio babbino caro', 'Giacomo Puccini', 'Radio Mandolinata'),
 ('brindisi', 'La traviata: Brindisi', 'Giuseppe Verdi', 'Radio Mandolinata'),
 ('la-paloma', 'La Paloma', 'Sebastian Yradier', 'Cafe Aman'),
 ('santa-lucia', 'Santa Lucia', 'Teodoro Cottrau', 'Radio Mandolinata'),
 ('funiculi', 'Funiculi, funicula', 'Luigi Denza', 'Radio Mandolinata'),
 ('locus-iste', 'Locus iste', 'Anton Bruckner', 'The Chapel Bell'),
 ('va-pensiero', 'Nabucco: Va, pensiero', 'Giuseppe Verdi', 'The Chapel Bell'),
 ('melita', 'Melita (Eternal Father, Strong to Save)', 'John Bacchus Dykes', 'The Chapel Bell'),
 ('pictures-promenade', 'Pictures at an Exhibition: Promenade', 'Modest Mussorgsky; orch. Maurice Ravel', 'Kalyra Concert Hall'),
 ('pictures-old-castle', 'Pictures at an Exhibition: The Old Castle', 'Modest Mussorgsky; orch. Maurice Ravel', 'Kalyra Concert Hall'),
 ('pictures-bydlo', 'Pictures at an Exhibition: Bydlo', 'Modest Mussorgsky; orch. Maurice Ravel', 'Kalyra Concert Hall'),
 ('pictures-chicks', 'Pictures at an Exhibition: Ballet of the Unhatched Chicks', 'Modest Mussorgsky; orch. Maurice Ravel', 'Kalyra Concert Hall'),
 ('pictures-baba-yaga', "Pictures at an Exhibition: The Hut on Hen's Legs", 'Modest Mussorgsky; orch. Maurice Ravel', 'Kalyra Concert Hall'),
 ('pictures-great-gate', 'Pictures at an Exhibition: The Great Gate of Kiev', 'Modest Mussorgsky; orch. Maurice Ravel', 'Kalyra Concert Hall'),
 ('beethoven-fifth', 'Symphony No. 5: Allegro con brio', 'Ludwig van Beethoven', 'Kalyra Concert Hall'),
 ('beethoven-fifth-finale', 'Symphony No. 5: Finale', 'Ludwig van Beethoven', 'Kalyra Concert Hall'),
 ('pathetique-finale', 'Symphony No. 6 "Pathetique": Finale', 'Pyotr Ilyich Tchaikovsky', 'Kalyra Concert Hall'),
 ('swan-lake-waltz', 'Swan Lake: Waltz (piano)', 'Pyotr Ilyich Tchaikovsky', 'Orenthia Light Programme'),
 ('rachmaninoff-third', 'Piano Concerto No. 3: Allegro ma non tanto (two pianos)', 'Sergei Rachmaninoff', 'Kalyra Concert Hall'),
 ('meistersinger-prelude', 'Die Meistersinger: Prelude (piano, after Bulow)', 'Richard Wagner; arr. Hans von Bulow', 'Kalyra Concert Hall'),
 ('liebestod', 'Tristan und Isolde: Liebestod (piano)', 'Richard Wagner', 'Kalyra Concert Hall'),
 ('valkyries', 'Die Walkure: Ride of the Valkyries (piano and voices)', 'Richard Wagner', 'Kalyra Concert Hall'),
 ('aida-march', 'Aida: Triumphal March', 'Giuseppe Verdi', 'Orenthia Light Programme'),
 ('traumerei', 'Traumerei', 'Robert Schumann', 'Kalyra Concert Hall'),
 ('slavonic-dance', 'Slavonic Dance Op. 72 No. 1, for wind band', 'Antonin Dvorak', 'Kalyra Concert Hall'),
 ('brandenburg-two', 'Brandenburg Concerto No. 2', 'Johann Sebastian Bach', 'Kalyra Concert Hall'),
 ('pange-lingua', 'Pange lingua', 'Anton Bruckner', 'The Chapel Bell'),
 ('brahms-first-finale', 'Symphony No. 1: Finale', 'Johannes Brahms', 'Kalyra Concert Hall'),
 ('hebrides', "The Hebrides (Fingal's Cave), for wind band", 'Felix Mendelssohn', 'Kalyra Concert Hall'),
 ('humoresque', 'Humoresque', 'Antonin Dvorak', 'Radio Mandolinata'),
 ('donna-mobile', 'Rigoletto: La donna e mobile', 'Giuseppe Verdi', 'Radio Mandolinata'),
 ('coriolan', 'Coriolan Overture', 'Ludwig van Beethoven', 'Kalyra Concert Hall'),
 ('egmont', 'Egmont Overture', 'Ludwig van Beethoven', 'Kalyra Concert Hall'),
 ('emperor-allegro', 'Piano Concerto No. 5 "Emperor": Allegro', 'Ludwig van Beethoven', 'Kalyra Concert Hall'),
 ('emperor-adagio', 'Piano Concerto No. 5 "Emperor": Adagio un poco mosso', 'Ludwig van Beethoven', 'Kalyra Concert Hall'),
 ('ninth-first', 'Symphony No. 9: Allegro ma non troppo', 'Ludwig van Beethoven', 'Kalyra Concert Hall'),
 ('ninth-finale', 'Symphony No. 9: Finale (Ode to Joy)', 'Ludwig van Beethoven', 'Kalyra Concert Hall'),
 ('water-music', 'Water Music, for wind band', 'George Frideric Handel', 'Kalyra Concert Hall'),
 ('rejouissance', 'Music for the Royal Fireworks: La Rejouissance', 'George Frideric Handel', 'Kalyra Concert Hall'),
 ('handel-oboe', 'Oboe Concerto No. 3', 'George Frideric Handel', 'Kalyra Concert Hall'),
 ('mahler-fifth-storm', 'Symphony No. 5: Sturmisch bewegt', 'Gustav Mahler', 'Kalyra Concert Hall'),
 ('mahler-ninth-rondo', 'Symphony No. 9: Rondo-Burleske (two pianos)', 'Gustav Mahler', 'Kalyra Concert Hall'),
 ('clarinet-allegro', 'Clarinet Concerto K. 622: Allegro', 'Wolfgang Amadeus Mozart', 'Kalyra Concert Hall'),
 ('mozart-forty-finale', 'Symphony No. 40: Allegro assai', 'Wolfgang Amadeus Mozart', 'Kalyra Concert Hall'),
 ('jupiter', 'Symphony No. 41 "Jupiter"', 'Wolfgang Amadeus Mozart', 'Kalyra Concert Hall'),
 ('dance-of-the-hours', 'La Gioconda: Dance of the Hours', 'Amilcare Ponchielli', 'Orenthia Light Programme'),
 ('swan-lake-scene', 'Swan Lake: Scene (Act II), for wind band', 'Pyotr Ilyich Tchaikovsky', 'Kalyra Concert Hall'),
 ('tchaikovsky-fourth-finale', 'Symphony No. 4: Finale', 'Pyotr Ilyich Tchaikovsky', 'Kalyra Concert Hall'),
 ('snowflakes', 'The Nutcracker: Waltz of the Snowflakes', 'Pyotr Ilyich Tchaikovsky', 'Orenthia Light Programme'),
 ('sugar-plum', 'The Nutcracker: Dance of the Sugar Plum Fairy, for wind band', 'Pyotr Ilyich Tchaikovsky', 'Kalyra Concert Hall'),
 ('verdi-sanctus', 'Requiem: Sanctus', 'Giuseppe Verdi', 'The Chapel Bell'),
 ('ballade-two', 'Ballade No. 2', 'Frederic Chopin', 'Kalyra Concert Hall'),
 ('chopin-berceuse', 'Berceuse', 'Frederic Chopin', 'Kalyra Concert Hall'),
 ('fantaisie-impromptu', 'Fantaisie-Impromptu', 'Frederic Chopin', 'Kalyra Concert Hall'),
 ('nocturne-fsharp', 'Nocturne in F sharp major, Op. 15 No. 2', 'Frederic Chopin', 'Kalyra Concert Hall'),
 ('polonaise-csharp', 'Polonaise in C sharp minor, Op. 26 No. 1', 'Frederic Chopin', 'Kalyra Concert Hall'),
 ('bassoon-andante', 'Bassoon Concerto K. 191: Andante ma adagio', 'Wolfgang Amadeus Mozart', 'Kalyra Concert Hall'),
 ('flute-andante', 'Andante for flute and orchestra K. 315', 'Wolfgang Amadeus Mozart', 'Kalyra Concert Hall'),
 ('horn-concerto-two', 'Horn Concerto No. 2 K. 417: Allegro maestoso', 'Wolfgang Amadeus Mozart', 'Kalyra Concert Hall'),
 ('fantasia-d-minor', 'Fantasia in D minor K. 397', 'Wolfgang Amadeus Mozart', 'Kalyra Concert Hall'),
 ('mozart-twentyfive', 'Symphony No. 25: Allegro con brio', 'Wolfgang Amadeus Mozart', 'Kalyra Concert Hall'),
 ('mozart-twentyfive-andante', 'Symphony No. 25: Andante', 'Wolfgang Amadeus Mozart', 'Kalyra Concert Hall'),
 ('nachtmusik-rondo', 'Eine kleine Nachtmusik: Rondo', 'Wolfgang Amadeus Mozart', 'Kalyra Concert Hall'),
 ('clarinet-quintet-larghetto', 'Clarinet Quintet K. 581: Larghetto', 'Wolfgang Amadeus Mozart', 'Kalyra Concert Hall'),
 ('beethoven-fifth-andante', 'Symphony No. 5: Andante con moto', 'Ludwig van Beethoven', 'Kalyra Concert Hall'),
 ('brahms-intermezzo', 'Intermezzo in A major, Op. 118 No. 2', 'Johannes Brahms', 'Kalyra Concert Hall'),
 ('midsummer-intermezzo', "A Midsummer Night's Dream: Intermezzo", 'Felix Mendelssohn', 'Kalyra Concert Hall'),
 # Greek songs from Bourgault-Ducoudray's 1877 collection, in our own transcription (voice and
 # the piano's bass): the dances on the bouzouki, the lyrical songs on the violin, over a guitar.
 ('greek-sta-giannina', 'Sta Giannina (In Yannina), a kalamatianos', 'Traditional Greek; coll. L.-A. Bourgault-Ducoudray', 'Archipelago Radio'),
 ('greek-ta-matakia-sou-ta-mavra', 'Ta matakia sou ta mavra (Your black eyes)', 'Traditional Greek; coll. L.-A. Bourgault-Ducoudray', 'Archipelago Radio'),
 ('greek-san-pethano-sto-karavi', 'San pethano sto karavi (If I die on the ship)', 'Traditional Greek; coll. L.-A. Bourgault-Ducoudray', 'Archipelago Radio'),
 ('greek-karavi-apo-ti-hio', "Karavin en' apo ti Hio (A brigantine from Chios)", 'Traditional Greek; coll. L.-A. Bourgault-Ducoudray', 'Archipelago Radio'),
 ('greek-an-pethano-roum-ba', 'An pethano, rixete me (Roum ba, roum balia)', 'Traditional Greek; coll. L.-A. Bourgault-Ducoudray', 'Archipelago Radio'),
 ('greek-aftos-o-kosmos', 'Aftos o kosmos (Ah! Eleni mou)', 'Traditional Greek; coll. L.-A. Bourgault-Ducoudray', 'Archipelago Radio'),
 ('greek-ta-matakia-aman', 'Ta matakia sou (Aman, aman)', 'Traditional Greek; coll. L.-A. Bourgault-Ducoudray', 'Cafe Aman'),
 ('greek-nystaxan-ta-matakia-mou', 'Nystaxan ta matakia mou (My eyes grew sleepy)', 'Traditional Greek; coll. L.-A. Bourgault-Ducoudray', 'Cafe Aman'),
 ('greek-ena-poulaki', 'Ena poulaki (A little bird)', 'Traditional Greek; coll. L.-A. Bourgault-Ducoudray', 'Hotel Ancora'),
 ('greek-astrapsen-i-anatoli', 'Astrapsen i anatoli (A cradle song)', 'Traditional Greek; coll. L.-A. Bourgault-Ducoudray', 'Hotel Ancora'),
 # The title's music (src/title_music.jo), not on the radio: the opening of Part III, from rehearsal
 # 155 to the bar before 158, in our own transcription of every part (daphnis_lever below).
 ('daphnis-lever-du-jour', 'Daphnis et Chloe: Lever du jour', 'Maurice Ravel', 'Title'),
 # Schubert's Ave Maria (Ellens dritter Gesang, D. 839), voice and piano: the tune on the violin
 # (the singer's line), the piano as written; the whole song, its three strophes as printed. On the
 # classical station's round and, one evening in three, in the hotel's set.
 ('schubert-ave-maria', 'Ave Maria (Ellens dritter Gesang)', 'Franz Schubert', 'Voice of Kalyra'),
]

# An arrangement's own high shelf (dB per instrument number above hz): the orchestral
# Gymnopedie's strings play muted (con sordino), darker and veiled.
ARRANGED_SHELF = {'gymnopedie-orchestra': dict(hz=1500.0, db={'0': -7.0})}

# The piano follows the venue, not the piece (src/music_synth.jo music_set_piano): live at the bar
# (or any period venue) the honky-tonk upright, whatever the number; on the radio the programme's
# (the classical programme the grand, popular and dance the upright). A piece's `piano` in the
# catalogue is the one of the venue where it is usually heard, for the tools and the automatic
# balance: the Hotel Ancora's numbers and the radio's popular stations the upright, the classical
# station (Voice of Kalyra) the grand.
def usual_piano(station):
 return 'grand' if station in ('Voice of Kalyra','Kalyra Concert Hall','The Chapel Bell','Title') else 'upright'

# Each piece's level in the mix (src/music_synth.jo applies it to the whole piece, keeping the
# score's own dynamics): the first thirteen were set by ear; the rest measured to sit at the same
# loudness (tools/music_level.py, BS.1770 over the whole piece). Missing: 1.0.
LEVEL = {'adagietto': .70, 'mahler-opening': .90, 'magnetic': .40, 'el-choclo': .70, 'gladiators': .22,
         'ikariotikos': 1.2, 'bethena': .55, 'gymnopedie': 1.40, 'ave-maria': .60, 'clair-de-lune': .38,
         'adelita': .85, 'berceuse': .30, 'gymnopedie-orchestra': .70}
LEVEL.update(json.loads((ROOT/'data/music/levels.json').read_text()) if (ROOT/'data/music/levels.json').exists() else {})
# Pieces heard in the concert hall's long reverberation (orchestra, choir, the concert grand).
HALL = {'adagietto', 'mahler-opening', 'gymnopedie-orchestra', 'new-world-largo', 'seventh-allegretto',
        'kleine-nachtmusik', 'clarinet-adagio', 'pathetique-adagio', 'mozart-forty', 'bach-air', 'moldau', 'liebestraum',
        'standchen', 'fifth-valse', 'lohengrin-chorus', 'hungarian-one', 'daphnis-introduction', 'daphnis-lever-du-jour', 'bolero', 'barber-overture',
        'carmen-overture', 'locus-iste', 'va-pensiero', 'melita', 'pictures-promenade', 'pictures-old-castle',
        'pictures-bydlo', 'pictures-chicks', 'pictures-baba-yaga', 'pictures-great-gate', 'beethoven-fifth',
        'beethoven-fifth-finale', 'pathetique-finale', 'rachmaninoff-third', 'meistersinger-prelude', 'liebestod', 'valkyries',
        'traumerei', 'brandenburg-two', 'pange-lingua', 'brahms-first-finale',
        'coriolan', 'egmont', 'emperor-allegro', 'emperor-adagio', 'ninth-first', 'ninth-finale', 'rejouissance', 'handel-oboe', 'mahler-fifth-storm', 'mahler-ninth-rondo', 'clarinet-allegro', 'mozart-forty-finale', 'jupiter', 'tchaikovsky-fourth-finale', 'verdi-sanctus', 'ballade-two', 'chopin-berceuse', 'fantaisie-impromptu', 'nocturne-fsharp', 'polonaise-csharp',
        'bassoon-andante', 'flute-andante', 'horn-concerto-two', 'fantasia-d-minor', 'mozart-twentyfive', 'mozart-twentyfive-andante', 'nachtmusik-rondo', 'clarinet-quintet-larghetto', 'beethoven-fifth-andante', 'brahms-intermezzo', 'midsummer-intermezzo'}

# Pieces that are another arrangement of one source score (data/music/source/<source>.mid).
SOURCE = {'gymnopedie-orchestra': 'gymnopedie', 'daphnis-lever-du-jour': 'daphnis-155-24'}
source_of = lambda name: SOURCE.get(name, name)

# The automatic balance. tools/music_balance.py writes balance.json: a high shelf per instrument
# where a part is harsh (and, for four early pieces, its melody and accompaniment gains: kept).
# tools/music_part_balance.py writes part-balance.json: a gain per part (dB) from each part's
# measured loudness and its role (the tune, a doubling, a counter-melody, the harmony, the bass,
# percussion), so the tune sits forward and what is behind it is heard. The gains are applied
# here, at pack time, as mix gains (a plain level: the touch and its tone are untouched), and what
# was applied is recorded in performance.json. MUSIC_BALANCE=0 packs without them (for measuring).
import os, hashlib
BALANCE = json.loads((ROOT/'data/music/balance.json').read_text()) if (ROOT/'data/music/balance.json').exists() and os.environ.get('MUSIC_BALANCE','1')!='0' else {}
PART_BALANCE = json.loads((ROOT/'data/music/part-balance.json').read_text()) if (ROOT/'data/music/part-balance.json').exists() and os.environ.get('MUSIC_BALANCE','1')!='0' else {}
NAMES = ['strings','brass','flute','oboe','clarinet','bassoon','piano','harp','bouzouki','accordion','banjo','timpani','drums','bass','choir','trumpet']
# Pieces whose balance was set by hand and approved by ear: measured and reported by the part
# balance, never changed by it.
HAND_SET_BALANCE = {
 'adagietto': "the annotated performance's section levels (adagietto-performance.json), approved by ear",
 'mahler-opening': 'the solo call: effort targets per note (opening-performance.json), approved by ear',
 'clair-de-lune': "the annotated performance's voicing (clair-de-lune-performance.json), approved by ear",
 'gymnopedie': 'the gentle touch: a soft mean velocity per voice (GENTLE), set by ear',
 'gymnopedie-orchestra': "the arranger's own levels (gymnopedie_orchestra), the tune set over the rest by ear",
 # The title's music is balanced with the title's own work, not here.
 'daphnis-lever-du-jour': "the title's music: the arranger's own level per part (DAPHNIS_PARTS)",
}

# Pieces that are songs: a singer (src/singer.jo, the hotel band's voice) sings the melody wherever
# the piece plays, over the piano and the rest, the lead instrument's own notes left out (the data
# keeps them: the violin version is this entry removed, then the part balance and this tool again).
# lead: the instrument whose notes are the tune; floor: the lowest pitch of it that is the tune;
# gain: the voice against the piece (its loudness matched to the violin's, tools/music_stems.jo
# MUSIC_SING=only against MUSIC_KEEP=0).
SUNG = {'schubert-ave-maria': dict(lead=STRINGS, floor=60, gain=0.74)}
SUNG_GAP = 3.0                      # a rest this long ends a sung stretch (the strophes' interludes)

def sung_windows(name, notes):
 """The stretches (seconds) in which the singer sings: where the lead's notes lie, closer than
 SUNG_GAP apart, a little padded."""
 spec=SUNG[name]
 spans=sorted((n[0],n[0]+n[1]) for n in notes if n[3]==spec['lead'] and n[2]>=spec['floor'])
 out=[]
 for a,b in spans:
  if out and a-out[-1][1]<=SUNG_GAP:out[-1][1]=max(out[-1][1],b)
  else:out.append([a,b])
 return [(round(max(0.0,a-.05),2),round(b+.05,2)) for a,b in out]

def kept_balance(name):
 """A balance a piece already had in performance.json before the part balance (balance_db, per
 instrument, from tools/music_balance.py): kept as it is. Its gains, or None."""
 return BALANCE.get(name,{}).get('gains_db') or None

def part_of(note):
 """The part a note belongs to: its instrument on its staff ("strings@3": the strings of track
 3). A keyboard's or a harp's staves are one player's two hands, and the percussion one section:
 one part each, whatever the track."""
 ins=note[3]
 return NAMES[ins] if ins in (PIANO,HARP,TIMPANI,DRUMS) else f'{NAMES[ins]}@{note[6]}'

def score_hash(notes):
 """What a part balance was measured on: the arranged, interpreted notes before any balance."""
 h=hashlib.sha1()
 for n in sorted(notes):h.update(('%.4f %.4f %d %d %.3f %.3f %d|'%tuple(n[:7])).encode())
 return h.hexdigest()[:16]

def balance_notes(name, notes):
 """The piece's part gains as mix gains (notes gain the two mix fields if they had none), and
 what is recorded of it in performance.json."""
 if name in HAND_SET_BALANCE:return notes,False,dict(status='hand-set',reason=HAND_SET_BALANCE[name])
 kept=kept_balance(name)
 if kept:
  out=[]
  for n in notes:
   k=10**(kept.get(str(n[3]),0.0)/20)
   m=list(n) if len(n)>7 else list(n)+[1.0,1.0]
   m[7]*=k;m[8]*=k;out.append(m)
  return out,True,dict(status='kept',reason='the balance it already had (balance_db, per instrument: tools/music_balance.py)')
 entry=PART_BALANCE.get(name)
 if not entry:return notes,False,dict(status='missing')
 if entry['score']!=score_hash(notes):return notes,False,dict(status='stale')
 record=dict(status=entry['status'])
 if entry.get('reason'):record['reason']=entry['reason']
 gains=entry.get('gains_db')
 if not gains:return notes,False,record
 out=[]
 for n in notes:
  k=10**(gains.get(part_of(n),0.0)/20)
  m=list(n) if len(n)>7 else list(n)+[1.0,1.0]
  m[7]*=k;m[8]*=k;out.append(m)
 record['parts']={p:dict(role=v['role'],gain_db=gains.get(p,0.0)) for p,v in entry['parts'].items()}
 return out,True,record

# Each piece's mood (tools/expressive_timing.py MOODS), classified by hand, with the reason.
MOOD = {
 'adagietto': ('tender', "Mahler's wordless love letter: very slow strings and harp, intimate rather than grieving"),
 'mahler-opening': ('stately', "the trumpet's call opening a funeral march: measured, ceremonial, strictly paced"),
 'magnetic': ('jaunty', "a rag in foxtrot dress: syncopation over a steady oom-pah that must not drag"),
 'el-choclo': ('dance-like', "a tango for dancing: clipped, rhythmic, the pulse held"),
 'gladiators': ('triumphant', "a circus march: brass fanfare and drive"),
 'ikariotikos': ('dance-like', "a Greek island dance: quick, even and circling"),
 'bethena': ('dance-like', "Joplin's concert waltz: lilting, the waltz pulse kept under the sentiment"),
 'gymnopedie': ('mournful', "marked 'Lent et douloureux': slow and sorrowful over a rocking accompaniment"),
 'gymnopedie-orchestra': ('mournful', "the same lament, its tune passed from oboe to flute over harp and muted strings"),
 'ave-maria': ('tender', "a devotional song over Bach's prelude: sustained, warm, unhurried"),
 'clair-de-lune': ('dreamy', "moonlight: floating, pedalled, flowing in its middle section"),
 'adelita': ('tender', "a small sentimental mazurka for guitar, wistful rather than danced"),
 'berceuse': ('tender', "a lullaby (Dolly): rocking, gentle, steady"),
 'new-world-largo': ('mournful', "the cor anglais's homesick song over hushed strings: very slow, sustained"),
 'seventh-allegretto': ('stately', 'a processional on a long-short-short tread: measured, the pulse never slackening'),
 'kleine-nachtmusik': ('jaunty', 'a bright serenade: crisp, buoyant, strictly in time'),
 'clarinet-adagio': ('tender', 'the clarinet singing over muted strings: warm, unhurried'),
 'pathetique-adagio': ('tender', 'a cantabile song for the piano: calm, legato'),
 'mozart-forty': ('stately', 'restless G minor: urgent, but the pulse held'),
 'bach-air': ('tender', 'the long line over a walking bass: serene, sustained'),
 'moldau': ('dreamy', 'the river flowing: rippling, rising and falling'),
 'liebestraum': ('dreamy', 'a love dream: flowing arpeggios under a singing tune'),
 'standchen': ('tender', 'a serenade: a quiet song over a plucked accompaniment'),
 'fifth-valse': ('dance-like', 'a symphonic waltz: graceful, the waltz kept'),
 'lohengrin-chorus': ('stately', 'a bridal procession: steady, warm'),
 'hungarian-one': ('dance-like', 'a csardas: slow-fast contrasts, sharp rhythm'),
 'daphnis-introduction': ('dreamy', "the ballet's introduction: a hushed chord built from the depths, distant calls, a slow rising tune"),
 'bolero': ('stately', 'one tune over an unvarying snare rhythm, growing: strictly in time'),
 'barber-overture': ('jaunty', 'a comic overture: sparkling, a long crescendo'),
 'carmen-overture': ('dance-like', "the bullring's march: bright, driving"),
 'blue-danube': ('dance-like', 'the waltz: a lilting one-two-three, its upbeats lingered on'),
 'thunder-lightning': ('jaunty', 'a quick polka: brisk, festive'),
 'radetzky': ('jaunty', 'a quick march: bright, steady'),
 'florentiner': ('jaunty', 'a band march: brisk, festive'),
 'summer-accordion': ('dance-like', 'the storm in summer: fast, fierce, driven'),
 'csardas': ('dance-like', 'a gypsy csardas: a slow lament, then a whirling dance'),
 'babbino-caro': ('tender', "a daughter's plea: sweet, sustained"),
 'brindisi': ('dance-like', 'a drinking song: a lilting waltz'),
 'la-paloma': ('dance-like', 'a habanera: languid, swaying'),
 'santa-lucia': ('tender', "a boatman's barcarolle: gently rocking"),
 'funiculi': ('jaunty', 'a funicular song: brisk and merry'),
 'locus-iste': ('tender', 'a motet: hushed, devout, sustained'),
 'va-pensiero': ('stately', "the exiles' chorus: broad, in unison, yearning"),
 'melita': ('stately', "a sailors' hymn: steady, solemn"),
 'pictures-promenade': ('stately', 'a walk through the gallery: steady, broad'),
 'pictures-old-castle': ('mournful', 'a troubadour by a ruin: slow, lilting, melancholy'),
 'pictures-bydlo': ('stately', 'an ox-cart: heavy, plodding, a long crescendo and away'),
 'pictures-chicks': ('jaunty', 'chicks in their shells: quick, light, chirping'),
 'pictures-baba-yaga': ('dance-like', "the witch's hut: wild, driving"),
 'pictures-great-gate': ('stately', 'the great gate: ceremonial, bells, broad'),
 'beethoven-fifth': ('stately', 'fate knocking: urgent, the pulse held'),
 'beethoven-fifth-finale': ('stately', 'C major triumph: bright, driving'),
 'pathetique-finale': ('mournful', 'the last lament: very slow, grieving'),
 'swan-lake-waltz': ('dance-like', 'a ballroom waltz: lilting'),
 'rachmaninoff-third': ('dreamy', "the concerto's opening: a long plain tune, then storms"),
 'meistersinger-prelude': ('stately', 'a festive prelude: broad, ceremonial'),
 'liebestod': ('dreamy', 'the love-death: rising, swelling, unresolved'),
 'valkyries': ('stately', 'the ride: galloping, heroic'),
 'aida-march': ('stately', 'a triumphal march: trumpets, ceremony'),
 'traumerei': ('tender', 'a dream: slow, intimate'),
 'slavonic-dance': ('dance-like', 'a furiant: fast, cross-rhythms'),
 'brandenburg-two': ('jaunty', 'a concerto grosso: bright, the trumpet on top'),
 'pange-lingua': ('tender', 'a plainchant hymn harmonised: hushed'),
 'brahms-first-finale': ('stately', 'from darkness to the great tune: broad'),
 'hebrides': ('dreamy', 'the sea and the cave: rolling, swelling'),
 'humoresque': ('tender', 'a little lilting piece: wistful'),
 'donna-mobile': ('jaunty', "the duke's song: a swinging tune"),
 'coriolan': ('stately', 'the wider repertoire, batch 3'),
 'egmont': ('stately', 'the wider repertoire, batch 3'),
 'emperor-allegro': ('stately', 'the wider repertoire, batch 3'),
 'emperor-adagio': ('tender', 'the wider repertoire, batch 3'),
 'ninth-first': ('stately', 'the wider repertoire, batch 3'),
 'ninth-finale': ('stately', 'the wider repertoire, batch 3'),
 'water-music': ('jaunty', 'the wider repertoire, batch 3'),
 'rejouissance': ('jaunty', 'the wider repertoire, batch 3'),
 'handel-oboe': ('tender', 'the wider repertoire, batch 3'),
 'mahler-fifth-storm': ('stately', 'the wider repertoire, batch 3'),
 'mahler-ninth-rondo': ('jaunty', 'the wider repertoire, batch 3'),
 'clarinet-allegro': ('jaunty', 'the wider repertoire, batch 3'),
 'mozart-forty-finale': ('stately', 'the wider repertoire, batch 3'),
 'jupiter': ('stately', 'the wider repertoire, batch 3'),
 'dance-of-the-hours': ('dance-like', 'the wider repertoire, batch 3'),
 'swan-lake-scene': ('mournful', 'the wider repertoire, batch 3'),
 'tchaikovsky-fourth-finale': ('stately', 'the wider repertoire, batch 3'),
 'snowflakes': ('dance-like', 'the wider repertoire, batch 3'),
 'sugar-plum': ('jaunty', 'the wider repertoire, batch 3'),
 'verdi-sanctus': ('stately', 'the wider repertoire, batch 3'),
 'ballade-two': ('dreamy', 'the wider repertoire, batch 3'),
 'chopin-berceuse': ('tender', 'the wider repertoire, batch 3'),
 'fantaisie-impromptu': ('dreamy', 'the wider repertoire, batch 3'),
 'nocturne-fsharp': ('dreamy', 'the wider repertoire, batch 3'),
 'polonaise-csharp': ('stately', 'the wider repertoire, batch 3'),
 'bassoon-andante': ('tender', 'the wider repertoire, batch 4'),
 'flute-andante': ('tender', 'the wider repertoire, batch 4'),
 'horn-concerto-two': ('jaunty', 'the wider repertoire, batch 4'),
 'fantasia-d-minor': ('dreamy', 'the wider repertoire, batch 4'),
 'mozart-twentyfive': ('stately', 'the wider repertoire, batch 4'),
 'mozart-twentyfive-andante': ('tender', 'the wider repertoire, batch 4'),
 'nachtmusik-rondo': ('jaunty', 'the wider repertoire, batch 4'),
 'clarinet-quintet-larghetto': ('tender', 'the wider repertoire, batch 4'),
 'beethoven-fifth-andante': ('stately', 'the wider repertoire, batch 4'),
 'brahms-intermezzo': ('tender', 'the wider repertoire, batch 4'),
 'midsummer-intermezzo': ('dreamy', 'the wider repertoire, batch 4'),
 'greek-sta-giannina': ('dance-like', 'a Greek song from the 1877 collection'),
 'greek-ta-matakia-sou-ta-mavra': ('dance-like', 'a Greek song from the 1877 collection'),
 'greek-san-pethano-sto-karavi': ('dance-like', 'a Greek song from the 1877 collection'),
 'greek-karavi-apo-ti-hio': ('dance-like', 'a Greek song from the 1877 collection'),
 'greek-an-pethano-roum-ba': ('dance-like', 'a Greek song from the 1877 collection'),
 'greek-aftos-o-kosmos': ('dance-like', 'a Greek song from the 1877 collection'),
 'greek-ta-matakia-aman': ('tender', 'a Greek song from the 1877 collection'),
 'greek-nystaxan-ta-matakia-mou': ('tender', 'a Greek song from the 1877 collection'),
 'greek-ena-poulaki': ('tender', 'a Greek song from the 1877 collection'),
 'greek-astrapsen-i-anatoli': ('tender', 'a Greek song from the 1877 collection'),
 'schubert-ave-maria': ('tender', "Ellen's prayer to the Virgin: very slow, sustained over rocking arpeggios, hushed"),
 'daphnis-lever-du-jour': ('dreamy', 'daybreak: brooks murmuring in flutes, clarinets and harps, birdsong, the theme rising to full light'),
}

# Pieces played in their mood through the expressive-timing system (generic rubato off in CONFIG);
# the rest keep their current reading until their mood's result is shown to be better.
APPLY_MOOD = {
 'gymnopedie': dict(seed=3, phrase_bars=4, base=0.87),
 'gymnopedie-orchestra': dict(seed=3, phrase_bars=4, base=0.87),
}

# Pieces with an annotated performance (time map, levels; for the piano, dynamics, pedal and
# voicing): data/music/<file>, made by its own tool (tools/clair_performance.py for Clair de lune).
ANNOTATED = {'adagietto': 'adagietto-performance.json', 'clair-de-lune': 'clair-de-lune-performance.json'}

# Pieces whose tempo comes from the expressive-timing system directly (tools/expressive_timing.py:
# intensity measured from the score, shaped into tempo); their generic rubato is off in CONFIG.
# Clair de lune uses the same system through its annotation. The Gymnopedie keeps its steady
# reading (the system pushes on with each entry of the tune, against its "Lent"); the Adagietto
# keeps its measured clock.
EXPRESSIVE = {
 'berceuse': ExpressiveTiming(base=1.0, min_rate=0.88, max_rate=1.2, flow=0.25, build=0.1, peak=0.08, cadence=0.08,
                              final_ritard=0.5, variation=0.02, seed=5, phrase_bars=4),
}

def gm(program, drum=False):
 if drum: return DRUMS
 if program < 8: return PIANO
 if program == 46: return HARP
 if program in (21,22,23): return ACCORDION
 if program in (52,53,54): return CHOIR
 if 24 <= program < 32 or program == 105: return BANJO
 if 32 <= program < 40: return BASS
 if program == 47: return TIMPANI
 if 40 <= program < 52: return STRINGS
 if 56 <= program < 64: return BRASS
 if 64 <= program < 68 or program == 71: return CLARINET
 if program in (68,69): return OBOE
 if program == 70: return BASSOON
 if 72 <= program < 80: return FLUTE
 return STRINGS

def read_midi(path):
 midi = mido.MidiFile(path)
 tempos = {0:500000}
 tracks=[]
 for track in midi.tracks:
  tick=0; events=[]
  for msg in track:
   tick+=msg.time; events.append((tick,msg))
   if msg.type=='set_tempo': tempos[tick]=msg.tempo
  tracks.append(events)
 times=sorted(tempos); seconds=[0.0]
 for a,b in zip(times,times[1:]): seconds.append(seconds[-1]+(b-a)*tempos[a]/midi.ticks_per_beat/1e6)
 def sec(t):
  i=bisect_right(times,t)-1
  return seconds[i]+(t-times[i])*tempos[times[i]]/midi.ticks_per_beat/1e6
 result=[]
 for ti,events in enumerate(tracks):
  program=defaultdict(int); vol=defaultdict(lambda:100); expr=defaultdict(lambda:127); opened=defaultdict(deque)
  initial=next((m.program for _,m in events if m.type=='program_change'),0)
  # A split bass/treble staff has its program on the first track only.
  if not any(m.type=='program_change' for _,m in events) and ti:
   initial=next((m.program for _,m in tracks[ti-1] if m.type=='program_change'),initial)
  cc=defaultdict(list)
  for t,m in events:
   if m.type=='control_change' and m.control in (7,11): cc[(m.channel,m.control)].append((t,m.value))
  def control(ch,control,t,default):
   vals=cc[(ch,control)];i=bisect_right(vals,(t,128))-1
   return vals[i][1] if i>=0 else default
  for t,m in events:
   if m.type=='program_change': program[m.channel]=m.program
   elif m.type=='note_on' and m.velocity:
    opened[(m.channel,m.note)].append((t,m.velocity,program.get(m.channel,initial)))
   elif m.type=='note_off' or (m.type=='note_on' and not m.velocity):
    q=opened[(m.channel,m.note)]
    if not q: continue
    start,vel,pg=q.popleft()
    if t<=start: continue
    gains=[vel/127*control(m.channel,7,x,100)/100*control(m.channel,11,x,127)/127 for x in [start,t-1]]
    result.append([sec(start),sec(t)-sec(start),m.note,gm(pg,m.channel==9),*gains,ti])
  if any(opened.values()): raise ValueError(f'unterminated notes in {path}, track {ti}')
 return result

def opening():
 # The opening solo has six pickups, each a sixteenth-note triplet, not a
 # full-quarter triplet. Tied notes continue through bar lines without retriggering.
 targets=json.loads((ROOT/'data/music/opening-performance.json').read_text())
 return [[n['start'],n['duration'],n['pitch'],15,n['effort'][0],n['effort'][2],0,n['effort'][1],.40] for n in targets]

def gentle_touch(notes, means, spread=.35):
 # A gentler hand on the piano: every key pressed softly. Each voice (the tune, the right hand's
 # chords, the bass, the left hand's chords) is set to its own soft mean velocity, keeping only a
 # third of the phrasing around it, so the tune leads by a little and the bass and the second-beat
 # chords carry more of the sound. (Soft notes are darker in the piano's own model as well.)
 top={}
 for n in notes:
  if n[6]==1:k=round(n[0],2);top[k]=max(top.get(k,0),n[2])
 def role(n):
  if n[6]==1:return 'tune' if n[2]>=67 and n[2]==top[round(n[0],2)] else 'chords'
  return 'bass' if n[2]<48 else 'left'
 groups={}
 for n in notes:groups.setdefault(role(n),[]).append(n[4])
 centre={r:sum(v)/len(v) for r,v in groups.items()}
 out=[]
 for n in notes:
  r=role(n);m=means[r]/127
  g0=max(.2,m+(n[4]-centre[r])*spread);g1=max(.2,m+(n[5]-centre[r])*spread)
  out.append(list(n[:4])+[g0,g1]+list(n[6:]))
 return out

# The Gymnopedie's touch: soft mean velocities per voice (the tune just above the rest).
GENTLE = {'gymnopedie': dict(tune=58, chords=50, bass=57, left=52)}

def gymnopedie_orchestra(notes):
 # The tune: the top of the right hand where it moves on its own (not the second-beat chords),
 # held notes the MIDI re-strikes joined into one; on the oboe until the new phrase at bar 22
 # (beat 63), then the flute. The second-beat chords: harp, with muted strings holding them; the
 # bass notes: harp and the low strings (cellos and basses, soft). Levels set so the tune sits
 # about 3 LU over the rest (measured with tools/music_balance.py's partial loudness: the balancer
 # itself takes one melody instrument, and here the tune passes between two).
 tune=[];chords=[];bass=[]
 by={}
 for n in notes:by.setdefault((n[6],round(n[0],3)),[]).append(n)
 sounding=-1.0
 for (track,start),group in sorted(by.items(),key=lambda kv:(kv[0][1],kv[0][0])):
  if track!=1:
   for n in group:(bass if n[2]<48 else chords).append(n)
   continue
  group=sorted(group,key=lambda n:n[2]);top=group[-1]
  second=round(start)%3==1
  chord_like=second and all(abs(n[1]-group[0][1])<1e-6 for n in group) and len(group)>=3
  if start<sounding-1e-6 or chord_like or (len(group)>1 and top[1]==group[0][1] and second):
   chords+=group;continue
  tune.append(top);chords+=group[:-1];sounding=start+top[1]
 joined=[]
 for n in sorted(tune):
  if joined and joined[-1][2]==n[2] and abs(joined[-1][0]+joined[-1][1]-n[0])<1e-6 and n[0]<62:
   joined[-1]=[joined[-1][0],joined[-1][1]+n[1]]+list(joined[-1][2:]);continue
  joined.append(list(n))
 out=[]
 for start,dur,pitch,ins,g0,g1,track in joined:
  out.append([start,dur,pitch,OBOE if start<62.5 else FLUTE,g0*.85,g1*.85,1])
 for start,dur,pitch,ins,g0,g1,track in chords:
  out.append([start,dur,pitch,HARP,g0*.67,g1*.67,2])
  out.append([start,dur+.25,pitch,STRINGS,g0*.58,g1*.58,3])
 for start,dur,pitch,ins,g0,g1,track in bass:
  out.append([start,dur,pitch,HARP,g0*.85,g1*.85,2])
  out.append([start,dur,pitch,BASS,g0*.61,g1*.61,4])
 return sorted(out)

# Ravel, Daphnis et Chloe, Part III: Lever du jour, from rehearsal 155 to the bar before 158
# (19 bars). The source is our own transcription of every part of the Durand full score at
# concert pitch (data/music/source/daphnis-155-24.mid and .musicxml; data/music/SOURCES.md), its
# MIDI tracks in score order, as named here. The synthesizer has no alto flute, piccolo, cor
# anglais, small or bass clarinet, trombone, tuba or celesta: each plays on the nearest timbre it
# has (below). The bass drum's one held stroke, left from before 155, is not played.
# Each part: (instrument, its level at the opening's pp).
DAPHNIS_PARTS = [
 ('Piccolo', FLUTE, .26), ('Flute 1 (solo calls)', FLUTE, .34), ('Flutes 1-2', FLUTE, .50), ('Alto flute', FLUTE, .44),
 ('Oboes 1-2', OBOE, .36), ('Cor anglais', OBOE, .38), ('Clarinet in E-flat', CLARINET, .36),
 ('Clarinets 1-2 in A', CLARINET, .48), ('Bass clarinet', CLARINET, .50), ('Bassoon 1', BASSOON, .46),
 ('Bassoon 2', BASSOON, .40), ('Bassoon 3, Contrabassoon', BASSOON, .32), ('Horns 1-2', BRASS, .26),
 ('Horn 2', BRASS, .24), ('Horns 3-4', BRASS, .26), ('Trombones 1-2', BRASS, .20), ('Trombone 3', BRASS, .20),
 ('Tuba', BRASS, .22), ('Bass drum', None, 0), ('Celesta', PIANO, .30), ('Harp 1', HARP, .44), ('Harp 2', HARP, .46),
 ('Solo violins 1-3', STRINGS, .26), ('Violins I a', STRINGS, .30), ('Violins I b', STRINGS, .30),
 ('Violins II a', STRINGS, .36), ('Violins II b', STRINGS, .36), ('Violas a', STRINGS, .32), ('Violas b', STRINGS, .32),
 ('Cellos a', STRINGS, .38), ('Cellos b', STRINGS, .44), ('Contrabasses a', STRINGS, .42), ('Contrabasses b', STRINGS, .36)]
DAPHNIS_BARS = [4,4,4,4]+[3]*15      # beats; Lent, a crotchet 1.2 s
# Each bar's level against the opening pp, after the printed dynamics: pp to 156 (bar 8), then
# the long crescendo (p at bar 12, mp 13, mf 14) to the forte at 157 (bar 15), and away.
DAPHNIS_LEVEL = [1,1,1,1,1,1,1,1,1.04,1.1,1.18,1.28,1.42,1.6,2.0,1.95,1.6,1.25,1.0]

def daphnis_lever(notes):
 beat=60/50
 starts=[0]
 for b in DAPHNIS_BARS:starts.append(starts[-1]+b)
 end=starts[-1]
 def bar_of(b):return max(i for i in range(len(DAPHNIS_BARS)) if starts[i]<=b+1e-6)
 def level(b):
  # the bar's level; the crescendo leans into the next bar over each bar's last quarter
  i=bar_of(b);x=(b-starts[i])/DAPHNIS_BARS[i];nxt=DAPHNIS_LEVEL[min(i+1,len(DAPHNIS_LEVEL)-1)]
  return DAPHNIS_LEVEL[i]+(nxt-DAPHNIS_LEVEL[i])*(x-.75)/.25*.5 if x>.75 and i+1<14 else DAPHNIS_LEVEL[i]
 def upper(p):
  # a trill's upper note, in D major
  return next((p+k for k in (1,2) if (p+k)%12 in (2,4,6,7,9,11,1)),p+2)
 out=[]
 def add(b,d,p,ins,g0,g1,track):out.append([b*beat,d*beat,p,ins,min(1.25,g0),min(1.25,g1),track])
 for t,d,p,_,_,_,track in notes:
  name,ins,g=DAPHNIS_PARTS[track-1]
  if ins is None:continue
  b=round(t/beat,6);d=round(d/beat,6);i=bar_of(b);fast=d<.3
  lv=level(b)
  # the rising figure and the theme (crotchets and quavers from bar 9) sing over the murmuring
  if i>=8 and not fast and d<=1.5 and ins!=HARP:lv*=1.25
  # horns, trombones and tuba follow the crescendo a little less
  if ins==BRASS:lv=1+(lv-1)*.8
  g*=lv
  if fast:
   # each bar of the arabesques and glissandi swells and falls under its slur; the divided
   # violins' arabesques at 157 sit under the winds'
   g*=.82+.18*math.sin(math.pi*(b-starts[i])/DAPHNIS_BARS[i])
   if ins==STRINGS:g*=.9
  if d<=.25:g*=.8
  g0=g1=g
  if ins in (STRINGS,BRASS,BASSOON) and d>=2:
   # held notes: a soft start, and on to the level of the bar they end in, tapering
   g0=g*.9;g1=g*level(min(end-.01,b+d))/lv*.8
  if b+d>=end-1e-6 and d>=1.5:
   # the last chord rings on for two beats and dies away
   d+=2;g1=0.0
  if name in ('Piccolo','Solo violins 1-3') and d>=1:
   # their long notes are trills (the MIDI holds the written note)
   k=0;at=b
   while at<b+d-1e-9:
    add(at,min(.125,b+d-at),p if k%2==0 else upper(p),ins,g*.8,g*.8,track)
    at+=.125;k+=1
   continue
  add(b,d,p,ins,g0,g1,track)
 return sorted(out)

# Pieces whose arrangement is already the performance: no further interpretation (phrase rubato,
# voicing, articulation) is laid over it.
AS_ARRANGED = {'daphnis-lever-du-jour'}

# The Greek songs (our transcription: the voice, and the piano's lowest note per beat). The piano's
# introductions and interludes were not transcribed beyond that bass line, so a stretch with no
# voice longer than GREEK_GAP is cut to GREEK_KEEP seconds of the bass, before and after; the
# dances take the tune on the bouzouki with a quiet accordion an octave below (as Ikariotikos), the
# lyrical songs on the violin; the bass on the guitar.
GREEK_LYRICAL = {'greek-ta-matakia-aman', 'greek-nystaxan-ta-matakia-mou', 'greek-ena-poulaki', 'greek-astrapsen-i-anatoli'}
GREEK_GAP, GREEK_KEEP = 4.0, 1.6

def greek_song(name, notes):
 voice = sorted((n[0], n[0] + n[1]) for n in notes if n[6] == 0)
 # (the stretches with the voice, and what is kept around them)
 spans = []
 for a, b in voice:
  if spans and a - spans[-1][1] <= GREEK_GAP: spans[-1][1] = max(spans[-1][1], b)
  else: spans.append([a, b])
 keep = []
 for a, b in spans:
  a = max(0.0, a - GREEK_KEEP); b = b + GREEK_KEEP
  if keep and a <= keep[-1][1]: keep[-1][1] = b
  else: keep.append([a, b])
 out = []
 lyrical = name in GREEK_LYRICAL
 for start, dur, pitch, ins, g0, g1, track in notes:
  shift = None; t = 0.0
  for a, b in keep:
   if a <= start < b: shift = t - a; break
   t += b - a
  if shift is None: continue
  start += shift
  if track == 0:
   if lyrical: out.append([start, dur, pitch, STRINGS, g0, g1, track])
   else:
    out.append([start, dur, pitch, BOUZOUKI, g0, g1, track])
    out.append([start, dur, pitch - 12, ACCORDION, g0 * .28, g1 * .28, track])
  else:
   out.append([start, dur, pitch, HARP, g0 * .8, g1 * .8, track])
 return sorted(out)

SCHUBERT_CLOCK=BeatMap(schubert_points(),4)

def arrange(name,notes):
 if name=='gymnopedie-orchestra':return gymnopedie_orchestra(notes)
 if name.startswith('greek-'):return greek_song(name,notes)
 if name=='daphnis-lever-du-jour':return daphnis_lever(notes)
 out=[]
 top={}
 for start,dur,pitch,ins,g0,g1,track in notes:
  key=(track,round(start,3));top[key]=max(top.get(key,-1),pitch)
 for start,dur,pitch,ins,g0,g1,track in notes:
  if name=='summer-accordion':
   # The solo violin on the accordion; the ripieno strings as they are, a bass under the cello.
   if track==0: ins=ACCORDION
   elif track==4 and pitch<48: out.append([start,dur,pitch-12,BASS,g0*.5,g1*.5,track])
  elif name in ('va-pensiero','melita') or (name=='lohengrin-chorus' and track<4):
   # The voices (exported as piano or clarinet) sung by the choir.
   ins=CHOIR
  elif name=='schubert-ave-maria':
   # The singer's line (the score's voice, exported as a pan flute) on the violin; the piano as
   # written. The score's own tempo (a placeholder 24 to the quarter) is replaced by the played
   # one, with its ritardandi (music_performance.schubert_points): the notes' times go through it.
   clock=SCHUBERT_CLOCK
   end=clock.time((start+dur)/SCHUBERT_MIDI_QUARTER);start=clock.time(start/SCHUBERT_MIDI_QUARTER);dur=end-start
   if track==1:ins=STRINGS
  elif name=='santa-lucia' and track==0:
   # The boatman's song on the mandolin, over the piano.
   ins=BOUZOUKI
  elif name=='funiculi':
   # The two violins become mandolin and guitar.
   ins=BOUZOUKI if track==0 else HARP
  if name=='magnetic':
   start*=60/116;dur*=60/116
   ins=CLARINET if track==1 and pitch>=60 else PIANO if pitch>=48 else BASS
   # Keep every original piano pitch; light banjo doubles the off-beat middle register.
   if track==2 and 48<=pitch<67:out.append([start,dur,pitch,BANJO,g0*.36,g1*.36,track])
  elif name=='el-choclo': ins=ACCORDION if track==0 else PIANO if pitch>=48 else BASS
  elif name=='gymnopedie':
   # Satie's own texture: the piano alone.
   ins=PIANO
  elif name=='adelita':
   # Two guitars: the tune on a mandolin-like plucked voice, the accompaniment on a guitar.
   ins=BOUZOUKI if track==1 else HARP
   if track==1:g0*=.85;g1*=.85
  elif name=='berceuse':
   # Flute and guitar become violin and guitar.
   ins=STRINGS if track==1 else HARP
  elif name=='ikariotikos':
   ins=BOUZOUKI
   # Unison octave accompaniment follows the traditional melody, no invented harmony.
   out.append([start,dur,pitch-12,ACCORDION,g0*.28,g1*.28,track])
  out.append([start,dur,pitch,ins,g0,g1,track])
 if name=='magnetic':
  end=max(n[0]+n[1] for n in out);beat=60/116
  for i in range(int(end/beat)):
   out.append([i*beat,.12,36 if i%2==0 else 38,DRUMS,.25,.25,99])
 return sorted(out)

# Pieces whose grace notes the generic reading must not touch: the opening solo and the title's
# music are annotated or transcribed note for note as played.
GRACE_SKIP = {'mahler-opening', 'daphnis-lever-du-jour'}
# Mutopia's LilyPond 2.6 exports leave a grace note sounding through its main note.
GRACE_OVERLAPPED = {'thunder-lightning'}

def pack(notes, mix_levels=False, sections=None):
 events=[]
 extended=len(notes[0])>7 and not mix_levels
 for n in notes:
  t,d,p,ins,g0,g1,track=n[:7]
  if sections is not None:
   assert mix_levels and 0<=ins<16
   section=sections.get(track,-1)
   assert -1<=section<15
   ins|=(section+1)<<4
  event=(round(t*RATE),max(1,round(d*RATE)),p,ins,min(127,round(g0*100)),min(127,round(g1*100)))
  if mix_levels:event+=(min(65535,max(0,round(n[7]*4096))),min(65535,max(0,round(n[8]*4096))))
  if extended:event+=(min(127,round(n[7]*100)),round(n[8]*100))
  events.append(event)
 events.sort()
 end=max(t+d for t,d,*_ in events)+RATE*2
 longest=max(d for _,d,*_ in events)+RATE*2
 raw=(b'MUS4' if sections is not None else b'MUS3' if mix_levels else b'MUS2' if extended else b'MUS1')+struct.pack('<III',len(events),end,longest)+b''.join(struct.pack('<IIBBBBHH' if mix_levels else '<IIBBBBBB' if extended else '<IIBBBB',*n) for n in events)
 return zlib.compress(raw,9,wbits=-15),end,events

def build(name):
 """A piece's notes as arranged and interpreted, before the part balance: (notes, what is
 recorded of the performance, the score desks of a sectioned piece or None)."""
 notes=opening() if name=='mahler-opening' else read_midi(ROOT/'data/music/source'/f'{source_of(name)}.mid')
 if name=='mahler-opening':
  performance=dict(phrases=6,source='solo-call timing and effort targets',duration_after=max(n[0]+n[1] for n in notes),pickup='sixteenth-note triplets',tied_notes='single continuous event')
 elif name in AS_ARRANGED:
  written=max(n[0]+n[1] for n in notes)
  notes=arrange(name,notes)
  performance=dict(source='arranged from our transcription, played as arranged',duration_before=written,duration_after=written)
 else:
  clock=score_clock(ROOT/'data/music/source'/f'{source_of(name)}.mid',name)
  notes,performance=interpret(arrange(name,notes),name,clock)
  if name in APPLY_MOOD:
   mood=MOOD[name][0];touch=MOODS[mood][1]
   notes=mood_touch(notes,clock,touch)
   if name in GENTLE:notes=gentle_touch(notes,GENTLE[name])
   time_map,curves=timing_map(notes,clock,mood_timing(mood,**APPLY_MOOD[name]))
   notes=warp(notes,time_map)
   performance.update(mood=mood,expressive_timing=True,rate_range=[round(min(curves['rate']),3),round(max(curves['rate']),3)],duration_after=max(n[0]+n[1] for n in notes))
  if name in EXPRESSIVE:
   time_map,curves=timing_map(notes,clock,EXPRESSIVE[name])
   notes=warp(notes,time_map)
   performance.update(expressive_timing=True,rate_range=[round(min(curves['rate']),3),round(max(curves['rate']),3)],duration_after=max(n[0]+n[1] for n in notes))
 if name in ANNOTATED:
  annotation=json.loads((ROOT/'data/music'/ANNOTATED[name]).read_text())
  notes=apply_performance_map(notes,annotation)
  performance.update(annotated_clock=True,time_points=len(annotation['time_map']),duration_after=max(n[0]+n[1] for n in notes),section_mix='independent start/end gains')
  if 'pedal' in annotation:performance.update(pedal_spans=len(annotation['pedal']),voicing=annotation['voicing'],spread_seconds=annotation['spread_seconds'],dynamic_range_db=[min(v for _,v in annotation['dynamics']),max(v for _,v in annotation['dynamics'])])
 sections={track:i for i,key in enumerate(['harp','violin_1','violin_2','viola','cello','bass']) for track in annotation['section_tracks'][key]} if name=='adagietto' else None
 return notes,performance,sections

def main():
 meta=[]; performances={}; unbalanced=[]
 for name,title,composer,station in PIECES:
  notes,performance,sections=build(name)
  performances[name]=performance
  notes,balanced,record=balance_notes(name,notes)
  # Grace notes played as grace notes (tools/music_grace.py). After the balance, which is keyed on the
  # notes before it: a grace note keeps its part's balance.
  if name not in GRACE_SKIP:
   notes,grace=regrace(notes,overlapped=name in GRACE_OVERLAPPED,clock=score_clock(ROOT/'data/music/source'/f'{source_of(name)}.mid',name))
   performance.update(grace_notes=grace)
  if name in SUNG:SUNG[name]['windows']=sung_windows(name,notes)
  if record['status']=='kept':performance.update(balance_db=BALANCE[name]['gains_db'])
  performance.update(part_balance=record)
  if record['status'] in ('missing','stale'):unbalanced.append(f"{name} ({record['status']})")
  blob,end,events=pack(notes,mix_levels=name in ANNOTATED or balanced,sections=sections)
  (ROOT/'data/music'/f'{name}.z').write_bytes(blob)
  meta.append(dict(id=name,title=title,composer=composer,station=station,piano=usual_piano(station),frames=end,notes=len(events),bytes=len(blob),mood=MOOD[name][0],mood_reason=MOOD[name][1],mood_applied=name in APPLY_MOOD,balance=record['status']))
  print(name,len(events),f'{end/RATE:.2f}s',len(blob),'bytes')
 if unbalanced and PART_BALANCE:print('NO PART BALANCE (run tools/music_part_balance.py, then pack again): '+', '.join(unbalanced))
 (ROOT/'data/music/performance.json').write_text(json.dumps(performances,indent=2)+'\n')
 (ROOT/'data/music/catalogue.json').write_text(json.dumps(meta,indent=2)+'\n')
 lines=['# Generated by tools/music_pack.py; edit source MIDI or converter, then rebuild.', 'struct MusicPiece:', '    title: str', '    composer: str', '    station: str', '    frames: int', '    shelf_hz = 0.0                  # the automatic balance\'s high shelf (tools/music_balance.py)', '    shelf_db: f64[] = []            # (dB per instrument above shelf_hz)', '    piano = 0                       # the piano it is played on: 0 the concert grand, 1 the 1920s upright', '    level = 1.0                     # its level in the mix (tools/music_pack.py LEVEL)', '    hall = false                    # heard in the concert hall\'s reverberation',
 '    sung: vec2[] = []               # a song: the stretches (seconds) a singer sings its melody (src/singer.jo)',
 '    sung_lead = 0                   # the instrument whose notes are the tune (MusicInstrument)',
 '    sung_floor = 0                  # the lowest pitch of it that is the tune',
 '    sung_gain = 0.5                 # the voice against the piece', '', 'MUSIC_PIECES: MusicPiece[] = [']
 for r in meta:
  shelf=BALANCE.get(r['id'],{}).get('shelf')
  if r['id'] in ARRANGED_SHELF:
   own=ARRANGED_SHELF[r['id']];merged=dict(own['db'])
   for k,v in (shelf or {}).get('db',{}).items():merged[k]=min(v,merged.get(k,0.0))
   shelf=dict(hz=own['hz'],db=merged)
  extra=f",{float(shelf['hz'])},["+','.join(f"{float(shelf['db'].get(str(k),0.0))}" for k in range(16))+"]" if shelf else ''
  piano=', piano = 1' if usual_piano(r['station'])=='upright' else ''
  level=LEVEL.get(r['id'],1.0);piano+=f', level = {level}' if level!=1.0 else ''
  piano+=', hall = true' if r['id'] in HALL else ''
  if r['id'] in SUNG:
   sg=SUNG[r['id']];piano+=', sung = ['+', '.join(f'vec2({a}, {b})' for a,b in sg['windows'])+f"], sung_lead = {sg['lead']}, sung_floor = {sg['floor']}, sung_gain = {sg['gain']}"
  lines.append('    MusicPiece('+','.join(json.dumps(r[k]) for k in ['title','composer','station'])+f",{r['frames']}{extra}{piano}),")
 lines+= [']','','music_bytes = (piece: int) -> u8[]:', '    match piece:']
 for i,r in enumerate(meta):lines.append(f'        {i}: embed(\'../data/music/{r["id"]}.z\')')
 lines+= ['        else: []','']
 (ROOT/'src/music_data.jo').write_text('\n'.join(lines))
if __name__=='__main__':main()
