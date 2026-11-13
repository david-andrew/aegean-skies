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
]

# Pieces with an annotated performance (time map, levels; for the piano, dynamics, pedal and
# voicing): data/music/<file>, made by its own tool (tools/clair_performance.py for Clair de lune).
ANNOTATED = {'adagietto': 'adagietto-performance.json', 'clair-de-lune': 'clair-de-lune-performance.json'}

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

def arrange(name,notes):
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
  elif name=='gymnopedie' and track==1:
   # The right hand's top voice is the tune: the violin sings it; the chords stay on the piano.
   ins=STRINGS if pitch>=67 and pitch==top.get((track,round(start,3)),-1) else PIANO
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
  notes=opening() if name=='mahler-opening' else read_midi(ROOT/'data/music/source'/f'{name}.mid')
  if name=='mahler-opening':
   performance=dict(phrases=6,source='solo-call timing and effort targets',duration_after=max(n[0]+n[1] for n in notes),pickup='sixteenth-note triplets',tied_notes='single continuous event')
  else:
   notes,performance=interpret(arrange(name,notes),name,score_clock(ROOT/'data/music/source'/f'{name}.mid',name))
  if name in ANNOTATED:
   annotation=json.loads((ROOT/'data/music'/ANNOTATED[name]).read_text())
   notes=apply_performance_map(notes,annotation)
   performance.update(annotated_clock=True,time_points=len(annotation['time_map']),duration_after=max(n[0]+n[1] for n in notes),section_mix='independent start/end gains')
   if 'pedal' in annotation:performance.update(pedal_spans=len(annotation['pedal']),voicing=annotation['voicing'],spread_seconds=annotation['spread_seconds'],dynamic_range_db=[min(v for _,v in annotation['dynamics']),max(v for _,v in annotation['dynamics'])])
  performances[name]=performance
  sections={track:i for i,key in enumerate(['harp','violin_1','violin_2','viola','cello','bass']) for track in annotation['section_tracks'][key]} if name=='adagietto' else None
  blob,end,events=pack(notes,mix_levels=name in ANNOTATED,sections=sections)
  (ROOT/'data/music'/f'{name}.z').write_bytes(blob)
  meta.append(dict(id=name,title=title,composer=composer,station=station,frames=end,notes=len(events),bytes=len(blob)))
  print(name,len(events),f'{end/RATE:.2f}s',len(blob),'bytes')
 (ROOT/'data/music/performance.json').write_text(json.dumps(performances,indent=2)+'\n')
 (ROOT/'data/music/catalogue.json').write_text(json.dumps(meta,indent=2)+'\n')
 lines=['# Generated by tools/music_pack.py; edit source MIDI or converter, then rebuild.', 'struct MusicPiece:', '    title: str', '    composer: str', '    station: str', '    frames: int', '', 'MUSIC_PIECES: MusicPiece[] = [']
 for r in meta:lines.append('    MusicPiece('+','.join(json.dumps(r[k]) for k in ['title','composer','station'])+f",{r['frames']}),")
 lines+= [']','','music_bytes = (piece: int) -> u8[]:', '    match piece:']
 for i,r in enumerate(meta):lines.append(f'        {i}: embed(\'../data/music/{r["id"]}.z\')')
 lines+= ['        else: []','']
 (ROOT/'src/music_data.jo').write_text('\n'.join(lines))
if __name__=='__main__':main()
