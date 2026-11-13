"""Offline interpretation and scalar bank invariants; no reference material needed."""
import unittest,sys,json,math,zlib,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from music_performance import BeatMap,interpret,apply_performance_map,performance_signature
from music_timbres import pack_models,ROOT
class Performance(unittest.TestCase):
 def score(self):
  return [[i*.5,.48,p,k,.6,.6,tr] for i in range(40) for p,k,tr in [(60+i%8,1,0),(48,6,2),(55,6,2)]]
 def test_deterministic_preserves_notes_and_section_chords(self):
  source=self.score();a,report=interpret(source,'gladiators',BeatMap([(0,0,.5)]));b,_=interpret(source,'gladiators',BeatMap([(0,0,.5)]))
  self.assertEqual(a,b);self.assertEqual(len(a),len(source))
  self.assertEqual(sorted((n[2],n[3],n[6]) for n in a),sorted((n[2],n[3],n[6]) for n in source))
  for n in a:self.assertTrue(n[0]>=0 and n[1]>0 and all(math.isfinite(x) for x in n))
  # Same-section chord tones have one common clock, not independent random delays.
  low=[n[0] for n in a if n[2]==48];high=[n[0] for n in a if n[2]==55]
  self.assertEqual(low,high);self.assertTrue(all(y>x for x,y in zip(low,low[1:])))
  self.assertGreater(report['accented_notes'],0);self.assertGreater(a[-1][0],source[-1][0])
 def test_tempo_map_round_trip(self):
  clock=BeatMap([(0,0,.5),(4,8,.75),(10,16,.4)])
  for t in [0,1,3.99,4,7,10,11,20]:self.assertAlmostEqual(clock.time(clock.beat(t)),t)
 def test_dynamic_phrase_arch_and_final_broadening(self):
  notes=[[i*.5,.45,60,0,.6,.6,2] for i in range(32)]
  a,_=interpret(notes,'adagietto',BeatMap([(0,0,.5)]))
  self.assertGreater(max(n[4] for n in a),min(n[4] for n in a)*1.2)
  self.assertGreater(a[-1][0]-a[-2][0],a[8][0]-a[7][0])
 def test_solo_call_extended_events_round_trip(self):
  from music_pack import opening,pack
  notes=opening();blob,end,events=pack(notes);raw=zlib.decompress(blob,wbits=-15)
  self.assertEqual(raw[:4],b'MUS2');self.assertEqual(len(raw),16+24*14)
  self.assertEqual(struct.unpack_from('<I',raw,4)[0],24)
  for i,n in enumerate(events):self.assertEqual(struct.unpack_from('<IIBBBBBB',raw,16+i*14),n)
  self.assertEqual(events[15][2],64);self.assertEqual(events[-1][2],73)
  self.assertLess(end/16000,20)
 def test_annotated_clock_keeps_effort_separate_from_mix(self):
  from music_pack import pack
  notes=[[0,1,60,7,.5,.6,0],[1,1,64,0,.6,.5,2]]
  a=dict(version=1,input_note_count=2,input_sha256=performance_signature(notes),time_map=[[0,0],[2,3]],section_tracks={'harp':[0]},section_levels={'harp':[[0,.5],[2,2]]})
  out=apply_performance_map(notes,a)
  self.assertEqual(out[0][:7],[0,1.5,60,7,.5,.6,0]);self.assertEqual(out[0][7:],[.5,1.25])
  self.assertEqual(out[1][7:],[1,1])
  blob,_,events=pack(out,mix_levels=True);raw=zlib.decompress(blob,-15)
  self.assertEqual(raw[:4],b'MUS3');self.assertEqual(len(raw),48)
  self.assertEqual(struct.unpack_from('<IIBBBBHH',raw,16),events[0])
  with self.assertRaises(ValueError):apply_performance_map(notes[:-1],a)
  a['time_map']=[[0,0],[2,0]]
  with self.assertRaises(ValueError):apply_performance_map(notes,a)
 def test_section_tags_and_harp_presence_preserve_effort(self):
  from music_pack import pack
  notes=[[0,1,60,7,.5,.6,0],[0,1,48,7,.5,.6,0]]
  a=dict(version=1,input_note_count=2,input_sha256=performance_signature(notes),time_map=[[0,0],[2,3]],section_tracks={'harp':[0]},section_levels={},harp_presence=dict(start_pitch=48,full_pitch=60,upper_db=3,opening_db=2,opening_hold_seconds=24,opening_end_seconds=48))
  out=apply_performance_map(notes,a);upper=next(n for n in out if n[2]==60);low=next(n for n in out if n[2]==48)
  self.assertAlmostEqual(upper[7],10**(.25));self.assertEqual(low[7],1)
  self.assertEqual(upper[4:6],[.5,.6])
  blob,_,events=pack(out,mix_levels=True,sections={0:0});raw=zlib.decompress(blob,-15)
  self.assertEqual(raw[:4],b'MUS4');self.assertEqual(events[0][3]&15,7);self.assertEqual((events[0][3]>>4)-1,0)
 def test_model_bank_rebuild_preserves_every_scalar(self):
  data=json.loads((ROOT/'data/music/instruments.json').read_text())
  actual=(ROOT/'data/music/instruments.z').read_bytes()
  # zlib and zlib-ng can select different deflate blocks for the same scalar bytes.
  raw=zlib.decompress(actual,wbits=-15)
  self.assertEqual(zlib.decompress(pack_models(data),wbits=-15),raw)
  self.assertEqual(raw[:8],b'TIM1\x10\x07\x03\x20')
  header=11+raw[4]*7
  values=struct.unpack('<'+str((len(raw)-header)//4)+'f',raw[header:])
  self.assertTrue(all(math.isfinite(x) and x>=0 for x in values))
if __name__=='__main__':unittest.main()
