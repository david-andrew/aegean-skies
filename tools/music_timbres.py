"""Pack scalar oscillator models. No audio input or third-party synthesis dependencies."""
from pathlib import Path
import json, struct, zlib
ROOT=Path(__file__).resolve().parents[1]
FIELDS=['attack','release','noise','transient','inharmonicity','vibrato_hz','vibrato_cents','loudness','loss0','loss2']
ARRAYS=['early','late','fast','slow','ratios']
def pack_models(data):
 assert data['version']==1 and data['partials']==32
 assert len(data['profiles'])==len(data['pitches'])*7*3
 out=bytearray(b'TIM1')
 out.extend(bytes([len(data['pitches']),7,3,32]))
 out.extend(bytes(data['velocities']))
 for pitches in data['pitches']:out.extend(bytes(pitches))
 for p in data['profiles']:
  values=[p[f] for f in FIELDS]
  for a in ARRAYS:
   assert len(p[a])==32;values+=p[a]
  out.extend(struct.pack('<170f',*values))
 return zlib.compress(bytes(out),9,wbits=-15)
if __name__=='__main__':
 data=json.loads((ROOT/'data/music/instruments.json').read_text())
 blob=pack_models(data);(ROOT/'data/music/instruments.z').write_bytes(blob)
 print(len(blob),'compressed model bytes')
