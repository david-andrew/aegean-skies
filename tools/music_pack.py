"""Rebuild licensed note data: python -m pip install mido; python tools/music_pack.py.
No audio, sampled instruments or network calls. Durations include MIDI tempo changes.
The per-track channel state matters: exported orchestral MIDIs reuse channel numbers.
"""
from pathlib import Path
from bisect import bisect_right
from collections import defaultdict, deque
import json, math, struct, zlib
import mido
from music_performance import score_clock, interpret, apply_performance_map
from expressive_timing import ExpressiveTiming, timing_map, warp, MOODS, mood_timing, mood_touch
ROOT = Path(__file__).resolve().parents[1]
RATE = 16000
# Must agree with MusicInstrument in music_synth.jo.
STRINGS, BRASS, FLUTE, OBOE, CLARINET, BASSOON, PIANO, HARP, BOUZOUKI, ACCORDION, BANJO, TIMPANI, DRUMS, BASS = range(14)
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
 return 'grand' if station=='Voice of Kalyra' else 'upright'

# Pieces that are another arrangement of one source score (data/music/source/<source>.mid).
SOURCE = {'gymnopedie-orchestra': 'gymnopedie'}
source_of = lambda name: SOURCE.get(name, name)

# The automatic balance (tools/music_balance.py writes it): per piece, a gain per instrument (dB)
# so the melody sits a few loudness units over the accompaniment, and a high shelf where a part is
# harsh. MUSIC_BALANCE=0 packs without it (for measuring).
import os
BALANCE = json.loads((ROOT/'data/music/balance.json').read_text()) if (ROOT/'data/music/balance.json').exists() and os.environ.get('MUSIC_BALANCE','1')!='0' else {}

def balance_notes(name, notes):
 """The piece's part gains as mix gains (notes gain the two mix fields if they had none)."""
 gains=BALANCE.get(name,{}).get('gains_db')
 if not gains:return notes,False
 out=[]
 for n in notes:
  k=10**(gains.get(str(n[3]),0.0)/20)
  m=list(n) if len(n)>7 else list(n)+[1.0,1.0]
  m[7]*=k;m[8]*=k;out.append(m)
 return out,True

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

def arrange(name,notes):
 if name=='gymnopedie-orchestra':return gymnopedie_orchestra(notes)
 out=[]
 top={}
 for start,dur,pitch,ins,g0,g1,track in notes:
  key=(track,round(start,3));top[key]=max(top.get(key,-1),pitch)
 for start,dur,pitch,ins,g0,g1,track in notes:
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

def main():
 meta=[]; performances={}
 for name,title,composer,station in PIECES:
  notes=opening() if name=='mahler-opening' else read_midi(ROOT/'data/music/source'/f'{source_of(name)}.mid')
  if name=='mahler-opening':
   performance=dict(phrases=6,source='solo-call timing and effort targets',duration_after=max(n[0]+n[1] for n in notes),pickup='sixteenth-note triplets',tied_notes='single continuous event')
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
  performances[name]=performance
  sections={track:i for i,key in enumerate(['harp','violin_1','violin_2','viola','cello','bass']) for track in annotation['section_tracks'][key]} if name=='adagietto' else None
  notes,balanced=balance_notes(name,notes)
  if balanced:performance.update(balance_db=BALANCE[name]['gains_db'])
  blob,end,events=pack(notes,mix_levels=name in ANNOTATED or balanced,sections=sections)
  (ROOT/'data/music'/f'{name}.z').write_bytes(blob)
  meta.append(dict(id=name,title=title,composer=composer,station=station,piano=usual_piano(station),frames=end,notes=len(events),bytes=len(blob),mood=MOOD[name][0],mood_reason=MOOD[name][1],mood_applied=name in APPLY_MOOD,balance=BALANCE.get(name,{}).get('summary')))
  print(name,len(events),f'{end/RATE:.2f}s',len(blob),'bytes')
 (ROOT/'data/music/performance.json').write_text(json.dumps(performances,indent=2)+'\n')
 (ROOT/'data/music/catalogue.json').write_text(json.dumps(meta,indent=2)+'\n')
 lines=['# Generated by tools/music_pack.py; edit source MIDI or converter, then rebuild.', 'struct MusicPiece:', '    title: str', '    composer: str', '    station: str', '    frames: int', '    shelf_hz = 0.0                  # the automatic balance\'s high shelf (tools/music_balance.py)', '    shelf_db: f64[] = []            # (dB per instrument above shelf_hz)', '    piano = 0                       # the piano it is played on: 0 the concert grand, 1 the 1920s upright', '', 'MUSIC_PIECES: MusicPiece[] = [']
 for r in meta:
  shelf=BALANCE.get(r['id'],{}).get('shelf')
  if r['id'] in ARRANGED_SHELF:
   own=ARRANGED_SHELF[r['id']];merged=dict(own['db'])
   for k,v in (shelf or {}).get('db',{}).items():merged[k]=min(v,merged.get(k,0.0))
   shelf=dict(hz=own['hz'],db=merged)
  extra=f",{float(shelf['hz'])},["+','.join(f"{float(shelf['db'].get(str(k),0.0))}" for k in range(16))+"]" if shelf else ''
  piano=', piano = 1' if usual_piano(r['station'])=='upright' else ''
  lines.append('    MusicPiece('+','.join(json.dumps(r[k]) for k in ['title','composer','station'])+f",{r['frames']}{extra}{piano}),")
 lines+= [']','','music_bytes = (piece: int) -> u8[]:', '    match piece:']
 for i,r in enumerate(meta):lines.append(f'        {i}: embed(\'../data/music/{r["id"]}.z\')')
 lines+= ['        else: []','']
 (ROOT/'src/music_data.jo').write_text('\n'.join(lines))
if __name__=='__main__':main()
