"""Colour-key oracle shared by native and WebGL2 cloud-transparency fixtures."""
import json, sys
from PIL import Image
names=['prop','splash','vapour','smoke','additive','battle_trail','rain','wake','exhaust','vessel_smoke','tracer','water','glass_path','world_marker_path']
im=Image.open(sys.argv[1]).convert('RGB'); w,h=im.size
mode=sys.argv[2]; rows={}
for row,name in enumerate(names):
    counts=[]
    for col in range(3):
        cx=(.5+(col-1)*.29)*w;cy=(row+.5)*h/14
        box=(int(cx-w*.045),int(cy-h*.03),int(cx+w*.045),int(cy+h*.03))
        count=sum(r>g+25 and b>g+20 for r,g,b in im.crop(box).getdata())
        expected=mode!='behind' or name=='rain'
        assert count>4 if expected else count==0,(mode,name,col,count)
        counts.append(count)
    rows[name]=counts
# Clouds themselves must actually render; otherwise foreground-only is a false pass.
if mode!='clear':
    r,g,b=im.getpixel((int(w*.36),int(h*.5)))
    assert g>90 and b>90,('cloud absent',r,g,b)
print(json.dumps(rows))
