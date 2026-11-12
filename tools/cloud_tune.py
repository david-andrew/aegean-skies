#!/usr/bin/env python3
"""Render the actual cloud shader beside a local reference crop (Pillow required).

Build tools/cloud_pilot.jo first. All captures are silent and headless. No server,
film pixels in assets, image grading, or automatic claim of visual equivalence.
Example:
 python3 tools/cloud_tune.py --binary ~/dev/tmp/cloud-pilot \
   --reference ~/dev/tmp/aegean-skies/refs/porco028.jpg \
   --output ~/dev/tmp/aegean-skies/nature/clouds3/tune
"""
import argparse, html, json, os, subprocess
from pathlib import Path
from PIL import Image, ImageDraw

def box(s):
    values=tuple(map(int,s.split(',')))
    if len(values)!=4: raise argparse.ArgumentTypeError('x0,y0,x1,y1')
    return values

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--binary',type=Path,required=True)
p.add_argument('--reference',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--painted-reference',type=Path,help='Optional scratch-only approved cloud crop; never embedded in the game')
p.add_argument('--film-box',type=box,default=(0,500,520,1020))
p.add_argument('--game-box',type=box,default=(350,70,930,650))
p.add_argument('--kind',type=int,default=0)
p.add_argument('--quality',choices=['low','medium','high'],default='high')
p.add_argument('--heading',type=float,default=0)
p.add_argument('--hour',type=float,default=14)
p.add_argument('--distance',type=float,default=1)
p.add_argument('--light',default='0.78 0.90 0.93')
p.add_argument('--shade',default='0.40 0.64 0.70')
p.add_argument('--grain',type=float,default=.06)
a=p.parse_args();a.output=a.output.expanduser().resolve();a.output.mkdir(parents=True,exist_ok=True)
e=os.environ.copy();e.pop('DISPLAY',None);e.pop('WAYLAND_DISPLAY',None)
e.update(SLOPPY_NO_AUDIO='1',SLOPPY_THREADS='1',SLOPPY_FRAMES='3',SLOPPY_SCREENSHOT=str(a.output/'game.png'),SLOPPY_SAVE_DIR=str(a.output/'saves'),CLOUD_VIEW='comparison',CLOUD_KIND=str(a.kind),CLOUD_HEADING=str(a.heading),AEGEAN_HOUR=str(a.hour),AEGEAN_QUALITY=a.quality,CLOUD_DISTANCE=str(a.distance),CLOUD_PAINT_LIGHT=a.light,CLOUD_PAINT_SHADE=a.shade,CLOUD_PAINT_GRAIN=str(a.grain))
# Software Vulkan avoids the shared desktop's GPU. Override explicitly elsewhere.
e.setdefault('VK_ICD_FILENAMES','/usr/share/vulkan/icd.d/lvp_icd.x86_64.json')
with (a.output/'render.log').open('w') as f:subprocess.run([str(a.binary.expanduser().resolve())],env=e,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=180)
for name,path,crop in [('film',a.reference.expanduser(),a.film_box),('cloud',a.output/'game.png',a.game_box)]:
    im=Image.open(path).convert('RGB').crop(crop)
    if im.width!=im.height: raise SystemExit('Use square crops to preserve identical scaling.')
    im.resize((384,384),Image.Resampling.LANCZOS).save(a.output/(name+'.png'))
columns=[('film','Film crop')]
if a.painted_reference:
    Image.open(a.painted_reference.expanduser()).convert('RGB').resize((384,384),Image.Resampling.LANCZOS).save(a.output/'painted.png')
    columns.append(('painted','Approved painted reference'))
columns.append(('cloud','Procedural layers'))
sheet=Image.new('RGB',(384*len(columns),416),(30,32,36));d=ImageDraw.Draw(sheet)
for index,(name,label) in enumerate(columns):
    x=index*384
    sheet.paste(Image.open(a.output/(name+'.png')),(x,32));d.text((x+8,9),label,fill='white')
sheet.save(a.output/'comparison.png')
config={k:str(v) if isinstance(v,Path) else v for k,v in vars(a).items()}
(a.output/'settings.json').write_text(json.dumps(config,indent=2))
page=a.output/'comparison.html'
items=''.join('<div>'+html.escape(label)+'<img src="'+html.escape(str(a.output/(name+'.png')))+'"></div>' for name,label in columns)
page.write_text('<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:transparent;color:var(--foreground,#222);font:14px system-ui}.row{display:grid;grid-template-columns:repeat('+str(len(columns))+',1fr);gap:8px}img{width:100%;display:block}pre{white-space:pre-wrap;font-size:11px}</style><div class="row">'+items+'</div><p>Actual headless renderer. Cropped and resized only; no grading. References stay in scratch.</p><pre>'+html.escape(json.dumps(config,indent=2))+'</pre>')
print(page)
