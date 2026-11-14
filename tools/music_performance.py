"""Deterministic interpretation of a score, before PCM rendering.

Inspired by the KTH/Director Musices rule families, not a port of that program.
A shared, monotone time map keeps all parts together. See docs/music-performance.md.
"""
from bisect import bisect_right
from collections import defaultdict
import math
import mido

# quarter-note metre, nominal beat if there is no MIDI clock, phrase length in bars,
# melody tracks, phrase timing amount, dynamic amount, final ritard, gentle swing.
CONFIG = {
 'adagietto': (4,60/55,4,{2},.13,.22,.35,0),
 'mahler-opening': (4,60/88,4,{0},.07,.12,.18,0),
 'magnetic': (4,60/116,4,{1},.035,.14,.16,.045),
 'el-choclo': (4,.5,4,{0},.045,.17,.20,0),
 'gladiators': (4,60/140,4,{0,5,6},.018,.10,.12,0),
 'ikariotikos': (2,.5,8,{0},.025,.14,.15,0),
 'bethena': (3,.4,8,{1},.065,.20,.24,0),
 'gymnopedie': (3,1.0,4,{1},.05,.14,.28,0),
 'ave-maria': (4,60/66,4,{1},.05,.16,.26,0),
 # Clair de lune's rubato, dynamics, pedal and voicing are its own annotation (clair-de-lune-performance.json)
 'clair-de-lune': (4.5,1.0,4,{1},0,0,0,0),
 'adelita': (3,1.0,4,{1},.06,.15,.24,0),
 # the Berceuse's tempo comes from tools/expressive_timing.py (music_pack.EXPRESSIVE)
 'berceuse': (2,1.0,4,{1},0,.15,0,0),
}

class BeatMap:
 def __init__(self, points, meter=4, pickup=0):
  self.points=points;self.times=[p[0] for p in points];self.beats=[p[1] for p in points]
  self.meter=meter;self.pickup=pickup
 def beat(self,t):
  i=max(0,bisect_right(self.times,t)-1);a,b,seconds=self.points[i]
  return b+(t-a)/seconds
 def time(self,b):
  i=max(0,bisect_right(self.beats,b)-1);t,a,seconds=self.points[i]
  return t+(b-a)*seconds

def score_clock(path,name):
 if name=='mahler-opening':return BeatMap([(0,0,60/88)],4,1)
 m=mido.MidiFile(path);tempo={0:500000};meter=CONFIG[name][0]
 for track in m.tracks:
  tick=0
  for msg in track:
   tick+=msg.time
   if msg.type=='set_tempo':tempo[tick]=msg.tempo
   if msg.type=='time_signature' and tick==0:meter=msg.numerator*4/msg.denominator
 scale=60/116 if name=='magnetic' else 1
 points=[];seconds=0;previous=0;speed=.5
 for tick,val in sorted(tempo.items()):
  seconds+=(tick-previous)/m.ticks_per_beat*speed
  speed=val/1e6;points.append((seconds*scale,tick/m.ticks_per_beat,speed*scale));previous=tick
 return BeatMap(points,meter)

def interpret(notes, name, clock):
 if not notes:return [],{}
 meter,nominal,phrase_bars,melody_tracks,timing,dynamic,ritard,swing=CONFIG[name]
 meter=clock.meter; end=max(clock.beat(n[0]+n[1]) for n in notes)
 # One top melody note per simultaneous onset. Do not treat a chord as a rapid run.
 top={}
 for n in notes:
  if n[6] not in melody_tracks or n[3]==12:continue
  b=round(clock.beat(n[0]),5)
  if b not in top or n[2]>top[b][2]:top[b]=n
 melody=sorted((b,n) for b,n in top.items()); starts=[b for b,_ in melody]
 # Phrase punctuation: a real rest or long cadential tone can move a nominal boundary.
 candidates=[]
 for i,(b,n) in enumerate(melody[:-1]):
  finish=clock.beat(n[0]+n[1]);next_b=melody[i+1][0]
  gap=next_b-finish;duration=finish-b
  if gap>.28 or (duration>1.5 and melody[i+1][1][2]<n[2]):
   candidates.append(next_b)
 phrase_length=phrase_bars*meter
 bounds=[0.0];target=clock.pickup+phrase_length
 while target < end-1:
  near=[b for b in candidates if abs(b-target)<meter*.8 and b>bounds[-1]+meter*2]
  boundary=min(near,key=lambda b:abs(b-target)) if near else target
  bounds.append(boundary);target=boundary+phrase_length
 bounds.append(end)
 peaks=[]
 for a,b in zip(bounds,bounds[1:]):
  inside=[(t,n) for t,n in melody if a+(b-a)*.22<t<b-(b-a)*.18]
  peak=max(inside,key=lambda x:x[1][2]+min(2,clock.beat(x[1][0]+x[1][1])-x[0]))[0] if inside else a+(b-a)*.55
  peaks.append(peak)
 def phrase(beat):
  i=min(len(peaks)-1,max(0,bisect_right(bounds,beat)-1));return bounds[i],bounds[i+1],peaks[i]
 def arch(beat):
  a,b,p=phrase(beat)
  phase=(beat-a)/max(.01,p-a) if beat<=p else (b-beat)/max(.01,b-p)
  return max(0,min(1,phase))
 def rate(beat):
  a,b,p=phrase(beat);u=(beat-a)/max(.01,b-a)
  # Starts with poise, moves through the middle, broadens into the cadence.
  v=1+timing*(1.6*(2*u-1)**2-.38)
  at=max(0,bisect_right(starts,beat)-1)
  if at+1<len(melody) and melody[at+1][1][2]>melody[at][1][2]:v-=timing*.18
  # Agogic emphasis at the melodic summit, synchronized in every part.
  v+=timing*.28*math.exp(-((beat-p)/.65)**2)
  remaining=end-beat
  if remaining<min(8,end*.12):v+=ritard*(1-remaining/min(8,end*.12))**2
  return max(.82,min(1.48,v))
 # Integrate tempo on a 1/32-quarter grid; all note and bar times use this same map.
 grid=[i/32 for i in range(math.ceil(end*32)+1)];warped=[0.0]
 for a,b in zip(grid,grid[1:]):warped.append(warped[-1]+(clock.time(b)-clock.time(a))*(rate(a)+rate(b))*.5)
 def warp(t):
  beat=max(0,clock.beat(t));j=min(len(grid)-2,int(beat*32));f=(beat-grid[j])*32
  value=warped[j]+(warped[j+1]-warped[j])*f
  if swing:
   # Light inegales, preserving each quarter; never the heavy 2:1 shuffle of a triplet.
   u=beat-math.floor(beat);value+=swing*nominal*math.sin(math.pi*u)**2
  return value
 parts=defaultdict(list)
 for i,n in enumerate(notes):parts[(n[6],n[3])].append((i,n))
 next_note={}
 for values in parts.values():
  values.sort(key=lambda x:(x[1][0],x[1][2]))
  for j,(i,n) in enumerate(values):
   later=[v for v in values[j+1:j+18] if v[1][0]>n[0]+.001]
   if later:next_note[i]=min(later,key=lambda v:(v[1][0],abs(v[1][2]-n[2])))[1]
 out=[];ratios=[];gaps=0;accents=0
 for i,n in enumerate(notes):
  t,d,p,ins,g0,g1,track=n;b=clock.beat(t);finish=clock.beat(t+d)
  start=warp(t);stop=warp(t+d);length=stop-start
  # Rounded lookup avoids floating point note positions missing the melody accent.
  on_top=round(b,5) in top and top[round(b,5)][2]==p and track in melody_tracks
  voice=1.12 if on_top else .78 if track not in melody_tracks else .88
  if ins in (7,13):voice*=.92
  phrase_gain=1+dynamic*(1.5*arch((b+finish)*.5)-.75)
  metrical=(b-clock.pickup)%meter
  strong=metrical<.04 or meter-metrical<.04
  offbeat=abs(b%1-.5)<.08
  accent=1.0
  if name=='el-choclo':accent=1.15 if strong or abs(metrical-2)<.05 else 1.08 if offbeat else .97
  elif name=='gladiators':accent=1.10 if strong else 1.045 if abs(metrical-2)<.05 else .97
  elif name=='magnetic':accent=1.09 if offbeat and on_top else 1.035 if strong else .98
  elif name=='bethena':accent=1.075 if strong else .97
  elif name=='ikariotikos':accent=1.075 if strong else 1.025 if offbeat else .98
  if accent>1.05:accents+=1
  # Duration contrast affects articulation, not the ensemble's common beat.
  duration_beats=finish-b
  articulation=.98+min(.045,max(-.055,(duration_beats-.5)*.035))
  following=next_note.get(i)
  a,z,peak=phrase(b)
  phrase_end=finish>z-.18
  if following:
   next_start=warp(following[0]);separation=next_start-stop
   connected=abs(separation)<nominal*.20 and abs(following[2]-p)<=7
   if connected and ins in (0,2,3,4,5,9):
    # A repeated pitch needs a tongue/bow change; a stepwise line can overlap gently.
    overlap=-.023 if following[2]==p else .018
    length=max(.035,next_start-start+overlap)
   elif ins in (1,):length*=.94 if name=='gladiators' else .98
  length*=articulation
  if phrase_end and ins in (0,1,2,3,4,5,9):length=max(.035,length-(.025 if ins==0 else .045));gaps+=1
  # Stable, very small section offsets, not random independent timing of each chord tone.
  offset=0 if on_top or ins==12 else .003+.004*math.sin(track*1.7)
  start=max(0,start+offset)
  factor=voice*phrase_gain*accent
  ending=1+dynamic*(1.5*arch(min(end,finish))-.75)
  out.append([start,max(.025,length),p,ins,min(1.25,g0*factor),min(1.25,g1*voice*ending*accent),track])
  ratios.append(length/d)
 out.sort()
 return out,dict(phrases=len(peaks),phrase_beats=[round(b,3) for b in bounds],peaks=[round(p,3) for p in peaks],duration_before=max(n[0]+n[1] for n in notes),duration_after=max(n[0]+n[1] for n in out),articulation_ratio_min=min(ratios),articulation_ratio_max=max(ratios),punctuated_notes=gaps,accented_notes=accents)


def performance_signature(notes):
 import hashlib,json
 return hashlib.sha256(json.dumps([[round(v,6) for v in n] for n in notes],separators=(',',':')).encode()).hexdigest()

def arpeggio_gestures(notes, settings):
 """Arpeggios as single gestures across both hands. A line is followed through the notes that
 are alone in their hand at their moment (a hand playing two at once is a chord or a melody in
 thirds, not an arpeggio): each joins the line that has just sounded close in time and pitch,
 whichever hand plays it. A line is cut into gestures at its low turning points (each sweep up
 and back, at most `max_seconds`), and each gesture gets one smooth contour rising to its highest
 note and falling after it, the same in either hand. Returns {note index: (dB, the gesture's
 common touch)}."""
 if not settings:return {}
 gap=settings.get('gap',0.4);long=settings.get('long_seconds',1.0);least=settings.get('min_notes',4)
 rise=settings.get('rise_db',2.0);base=settings.get('base_db',0.0);most=settings.get('max_seconds',4.5)
 leap=settings.get('max_leap',9)
 order=sorted(range(len(notes)),key=lambda i:notes[i][0])
 moments=[]
 for i in order:
  if moments and notes[i][0]-notes[moments[-1][0]][0]<0.03:moments[-1].append(i)
  else:moments.append([i])
 lines=[];done=[]
 for m in moments:
  alone=[i for i in m if notes[i][1]<long and sum(1 for j in m if notes[j][6]==notes[i][6])==1]
  taken=set()
  for i in sorted(alone,key=lambda i:notes[i][2]):
   best=None;best_d=leap+1
   for k,line in enumerate(lines):
    if k in taken:continue
    last=notes[line[-1]]
    if 0.03<=notes[i][0]-last[0]<=gap:
     d=abs(notes[i][2]-last[2])
     if d<best_d:best,best_d=k,d
   if best is None:lines.append([i]);taken.add(len(lines)-1)
   else:lines[best].append(i);taken.add(best)
  # (lines that have gone quiet are finished)
  now=notes[m[0]][0]
  done.extend(l for l in lines if now-notes[l[-1]][0]>gap)
  lines=[l for l in lines if now-notes[l[-1]][0]<=gap]
 out={}
 for run in done+lines:
  if len(run)<least:continue
  pieces=[];piece=[run[0]]
  for k in range(1,len(run)):
   p0=notes[run[k-1]][2];p1=notes[run[k]][2];nxt=notes[run[k+1]][2] if k+1<len(run) else p1
   turn=p1<p0 and k+1<len(run) and nxt>p1 and len(piece)>=3
   if turn or notes[run[k]][0]-notes[piece[0]][0]>most:pieces.append(piece);piece=[]
   piece.append(run[k])
  pieces.append(piece)
  for g in pieces:
   # (one touch for the whole gesture, whichever hand: the score reading's per-hand levels go)
   touch=sum(notes[i][4] for i in g)/len(g)
   if len(g)<3:
    for i in g:out[i]=(base,touch)
    continue
   top=max(range(len(g)),key=lambda k:notes[g[k]][2])
   for k,i in enumerate(g):
    u=k/max(1,top) if k<=top else 1-(k-top)/max(1,len(g)-1-top)
    out[i]=(base+rise*(math.sin(math.pi*0.5*u)**2-0.5),touch)
 return out

def apply_performance_map(notes, annotation):
 """Apply an explicitly annotated clock and section gains after the generic reading.

 Gains are separate from effort: changing the section mix must not select a different
 instrument spectrum or defeat exact note-body reuse. The fingerprint prevents an old
 annotation silently attaching to changed score/rule output.
 """
 if annotation['version']!=1 or len(notes)!=annotation['input_note_count'] or performance_signature(notes)!=annotation['input_sha256']:
  raise ValueError('performance annotation does not match the interpreted score')
 points=annotation['time_map']
 if len(points)<2 or any(b[0]<=a[0] or b[1]<=a[1] for a,b in zip(points,points[1:])):
  raise ValueError('performance time map must increase strictly')
 def interpolate(points,t):
  i=max(0,min(len(points)-2,bisect_right([p[0] for p in points],t)-1))
  a,x=points[i];b,y=points[i+1]
  return x+(y-x)*max(0,min(1,(t-a)/(b-a)))
 sections={track:name for name,tracks in annotation.get('section_tracks',{}).items() for track in tracks}
 # Optional pianist's layer (absent for the Adagietto): a dynamic curve in dB, part of it as
 # touch (effort, which colours the tone) and the rest as level; the melody voiced over its
 # accompaniment; the sustain pedal's spans; chords spread a little from the bass up.
 dynamics=annotation.get('dynamics');voicing=annotation.get('voicing');pedal=annotation.get('pedal')
 spread=annotation.get('spread_seconds',0);touch=annotation.get('effort_share',0)
 groups=defaultdict(list)
 for i,n in enumerate(notes):groups[(n[6],round(n[0],3))].append(i)
 rank={}
 for idx in groups.values():
  idx.sort(key=lambda i:notes[i][2])
  for r,i in enumerate(idx):rank[i]=(r,len(idx))
 pedal_starts=[a for a,_ in pedal] if pedal else []
 gesture=arpeggio_gestures(notes,annotation.get('arpeggios')) if voicing else {}
 out=[]
 for i,n in enumerate(notes):
  t,d,p,ins,g0,g1,track=n
  level=annotation.get('section_levels',{}).get(sections.get(track,''),[[0,1],[points[-1][0],1]])
  start=interpolate(points,t);stop=interpolate(points,t+d)
  if pedal:
   j=bisect_right(pedal_starts,t+1e-6)-1
   if j>=0 and pedal[j][0]<=t<pedal[j][1] and t+d<pedal[j][1]:
    stop=max(stop,interpolate(points,min(pedal[j][1],t+annotation.get('pedal_max_hold',6.0))))
  touch_db=0.0;level_db=0.0
  if dynamics:
   db=interpolate(dynamics,t);touch_db+=db*touch;level_db+=db*(1-touch)
  if voicing:
   r,count=rank[i]
   if i in gesture:
    touch_db+=gesture[i][0]
    g0=g1=gesture[i][1]
   elif track in voicing['melody_tracks']:touch_db+=voicing['melody_db'] if r==count-1 or d>=voicing.get('held_seconds',1e9) else voicing['inner_db']
   elif track in voicing.get('lower_tracks',[]):touch_db+=voicing['lower_db']
  if spread and rank[i][1]>1:
   r,count=rank[i];start+=spread*r/(count-1);stop+=spread*r/(count-1)
  if touch_db:
   k=10**(touch_db/20);g0=min(1.25,g0*k);g1=min(1.25,g1*k)
  gain=10**(level_db/20) if level_db else 1.0
  presence=annotation.get('harp_presence')
  if ins==7 and presence:
   upper=max(0,min(1,(p-presence['start_pitch'])/(presence['full_pitch']-presence['start_pitch'])))
   opening=max(0,min(1,(presence['opening_end_seconds']-start)/(presence['opening_end_seconds']-presence['opening_hold_seconds'])))
   gain=10**(upper*(presence['upper_db']+presence['opening_db']*opening)/20)
  out.append([start,max(.001,stop-start),p,ins,g0,g1,track,interpolate(level,t)*gain,interpolate(level,t+d)*gain])
 out.sort()
 return out
