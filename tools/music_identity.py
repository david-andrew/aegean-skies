#!/usr/bin/env python3
"""Compare every f64 sample with a frozen git revision; write all fixtures to scratch.

python3 tools/music_identity.py --scratch ~/dev/tmp/aegean-skies/radio/music/cost/identity
Add --quick --wasm to build a short browser verification page (no audio device).
"""
import argparse
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--scratch', type=Path, required=True)
p.add_argument('--revision', default='063a405', help='auditioned sound before caching')
p.add_argument('--quick', action='store_true')
p.add_argument('--chain', action='store_true', help='compare receiver samples instead of score synthesis')
p.add_argument('--wasm', action='store_true', help='build a standalone check page; do not launch it')
a = p.parse_args()
scratch = a.scratch.expanduser().resolve()
if scratch == ROOT or ROOT in scratch.parents:
    p.error('scratch must be outside the repository')
snapshot = scratch / 'previous'
files = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', a.revision,
                                 'src', 'data/music'], cwd=ROOT, text=True).splitlines()
for name in files:
    if name.startswith('src/') and name not in {
        'src/music_synth.jo', 'src/music_models.jo', 'src/music_data.jo', 'src/radio_chain.jo'
    }:
        continue
    dest = snapshot / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(subprocess.check_output(['git', 'show', f'{a.revision}:{name}'], cwd=ROOT))
source = '''
loop piece in 0..7:
    a=previous.make_music_synth();b=current.make_music_synth()
    previous.music_load(a,piece);current.music_load(b,piece)
    loop seek in [0.0,1.125,20.0,40.023,0.0]:
        previous.music_seek(a,seek);current.music_seek(b,seek)
        limit=if seek==0.0 and FULL: a.frames else: min(a.frames,a.cursor+8192)
        checked=0
        loop a.cursor<limit:
            count=min(799,limit-a.cursor)
            fresh=current.music_render(b,count)
            loop i in 0..count:
                v=previous.music_sample(a)
                if f64_bits(v)!=f64_bits(fresh[i]):
                    print("MISMATCH piece={piece} sample={a.cursor-1}")
                    assert(false)
            checked+=count
        assert(a.stolen==b.stolen)
        print("EXACT piece={piece} seek={seek} frames={checked}")
print("DONE")
'''.replace('FULL', 'false' if a.quick else 'true')
module = 'radio_chain.jo' if a.chain else 'music_synth.jo'
if not (snapshot / 'src' / module).exists():
    p.error(f'{module} is not present in revision {a.revision}')
if a.chain:
    source = """
loop seconds in [0.0,19.999,42000.123]:
    a=previous.make_radio_chain(42,seconds);b=current.make_radio_chain(42,seconds)
    loop i in 0..FRAMES:
        strength=[1.0,0.55,0.08][(i/5000)%3]
        detune=f64((i/7000)%41-20)
        record=if (i/16000)%2 == 0:0.0 else:0.8
        night=f64((i/25000)%2)
        source=sin(f64(i)*0.173)*0.4+sin(f64(i)*0.781)*0.1
        av=previous.radio_chain_sample(a,source,strength,detune,record,night)
        bv=current.radio_chain_sample(b,source,strength,detune,record,night)
        assert(f64_bits(av)==f64_bits(bv))
    print("EXACT receiver seconds={seconds} frames=FRAMES")
print("DONE")
""".replace('FRAMES', '8192' if a.quick else '960000')
imports = (f'import {json.dumps(str(snapshot / "src" / module))} as previous\n'
           f'import {json.dumps(str(ROOT / "src" / module))} as current\n')
check = scratch / 'identity.jo'
check.write_text(imports + source)
env = dict(os.environ, DISPLAY='', WAYLAND_DISPLAY='', SLOPPY_NO_AUDIO='1', SLOPPY_THREADS='1')
if a.wasm:
    page = scratch / 'identity.html'
    subprocess.run(['sloppy', 'build', str(check), '--release', '--target', 'wasm', '-o', str(page)],
                   env=env, check=True)
    print(page)
else:
    subprocess.run(['sloppy', '--release', str(check)], env=env, check=True)
