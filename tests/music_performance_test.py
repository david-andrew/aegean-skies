"""Offline interpretation and scalar bank invariants; no reference material needed."""
import unittest,sys,json,math,zlib,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from music_performance import BeatMap,interpret
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
 def test_checked_in_model_bank_rebuilds_exactly(self):
  data=json.loads((ROOT/'data/music/instruments.json').read_text())
  actual=(ROOT/'data/music/instruments.z').read_bytes();self.assertEqual(pack_models(data),actual)
  raw=zlib.decompress(actual,wbits=-15);self.assertEqual(raw[:8],b'TIM1\x0f\x07\x03\x20')
  values=struct.unpack('<'+str((len(raw)-116)//4)+'f',raw[116:])
  self.assertTrue(all(math.isfinite(x) and x>=0 for x in values))
if __name__=='__main__':unittest.main()
