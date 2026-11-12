#!/usr/bin/env python3
"""Build evidence, never scores. All child processes are serial, silent and bounded.

Usage: tools/judge_pack.sh round1 [--stage build|images|sequences|world|audio|tests|web|bench|index]
A completed capture is reused only if its binary, environment and recipe hash agree.
Use --force to replace captures; --previous ROUND supplies the previous pack's commit.
Dependencies: Sloppy, Python 3 + Pillow + Matplotlib, Node, ssh/rsync; Chromium on redfox.
"""
import argparse, csv, datetime, gzip, hashlib, json, math, os
from pathlib import Path
import re, shutil, statistics, subprocess, sys, time
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
BASE=Path.home()/'dev/tmp/aegean-skies/judging'
os.environ.setdefault('MPLCONFIGDIR',str(BASE/'tool-cache/matplotlib'))
ENV={k:v for k,v in os.environ.items() if not k.startswith(('AEGEAN_','COMBAT_','LIFE_','LIVING_','AIRCRAFT_SOUND_','VESSEL_','RADIO_','STALL_','FLIGHT_','SLOPPY_')) and k not in ('DISPLAY','WAYLAND_DISPLAY')}
ENV.update(SLOPPY_THREADS='1',SLOPPY_NO_AUDIO='1',SLOPPY_SEED='12345')
KINDS=['capital','port','market','fishing','hill','monastery','hamlet','farm','lighthouse','chapel']
CRAFT=['Gull','Heron','Corsair','Falco','Tern','Petrel','Osprey','Swift','Pelican','Kite','Ibis','Kestrel','Minnow','Albatross','Cormorant','Kingfisher']
STAGES=['build','images','sequences','world','audio','tests','web','bench','index']
P=None; A=None; SLOPPY=None; TOOLCHAIN=None

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n' if not isinstance(value,str) else value)
def run(cmd,log,extra=None,timeout=1800,cwd=ROOT):
    log.parent.mkdir(parents=True,exist_ok=True)
    print('RUN',log.relative_to(P),flush=True)
    before=time.monotonic()
    with log.open('w') as f:
        f.write('COMMAND '+json.dumps(list(map(str,cmd)))+'\nENV '+json.dumps(extra or {})+'\n');f.flush()
        try:
            r=subprocess.run(list(map(str,cmd)),cwd=cwd,env=ENV|dict(extra or {}),stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
        except subprocess.TimeoutExpired:
            f.write(f'\nTIMEOUT after {timeout} seconds\n')
            r=subprocess.CompletedProcess(cmd,124)
    with (P/'commands.jsonl').open('a') as f:f.write(json.dumps(dict(command=list(map(str,cmd)),log=str(log.relative_to(P)),seconds=round(time.monotonic()-before,3),returncode=r.returncode))+'\n')
    return r.returncode

def build():
    if not all((ROOT/'assets'/n).exists() for n in ['terrain.bin','world.bin','clouds.png']):
        assert run([SLOPPY,'--release','tools/bake.jo'],P/'logs/bake.log',timeout=3600)==0
    inputs=git('ls-files','*.jo','*.js','*.mjs')+'\n'+git('diff','HEAD')
    names=['terrain.bin','world.bin','clouds.png','fonts/JosefinSans-SemiBold.ttf','fonts/Limelight-Regular.ttf','fonts/JosefinSans-OFL.txt','fonts/Limelight-OFL.txt']
    for name in names:
        source=ROOT/'assets'/name;frozen=P/'assets'/name
        if frozen.exists():
            assert digest(source)==digest(frozen),f'Round asset changed: {source}. Restore the frozen round/assets copy or start a new round.'
        else:
            frozen.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,frozen)
    compiler=subprocess.check_output([SLOPPY,'--version'],text=True).strip()
    assets={n:dict(bytes=(ROOT/'assets'/n).stat().st_size,sha256=digest(ROOT/'assets'/n)) for n in names}
    stamp=hashlib.sha256((git('rev-parse','HEAD')+inputs+Path(__file__).read_text()+compiler+TOOLCHAIN+json.dumps(assets,sort_keys=True)).encode()).hexdigest()
    prior=json.loads((P/'provenance.json').read_text()) if (P/'provenance.json').exists() else {}
    baseline=prior.get('game_baseline',git('rev-parse','HEAD'))
    write(P/'source.patch',git('diff','HEAD')+'\n')
    write(P/'provenance.json',dict(commit=git('rev-parse','HEAD'),game_baseline=baseline,branch=git('branch','--show-current'),dirty=bool(git('status','--porcelain')),source_signature=stamp,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),host=os.uname().nodename,cpu=[l.split(':',1)[1].strip() for l in Path('/proc/cpuinfo').read_text().splitlines() if l.startswith('model name')][0],memory=Path('/proc/meminfo').read_text().splitlines()[0],python=sys.version,pillow=Image.__version__,compiler=compiler,toolchain_sha256=TOOLCHAIN,assets=assets))
    for source,name in [('aegean.jo','aegean'),('tools/combatlab.jo','combatlab'),('tools/lifelab.jo','lifelab'),('tools/lifelog.jo','lifelog'),('tools/judge_audio.jo','audio'),('tools/vessellab.jo','vessellab')]:
        output=P/'build'/name;done=output.with_name(output.name+'.stamp')
        if not A.force and output.exists() and done.exists() and done.read_text()==stamp:continue
        assert run([SLOPPY,'build','--release',source,'-o',output],P/'logs'/f'build-{name}.log')==0
        write(done,stamp)
    output=P/'build/aegean.html';done=output.with_name(output.name+'.stamp')
    if A.force or not output.exists() or not done.exists() or done.read_text()!=stamp:
        assert run([SLOPPY,'build','--release','--target','wasm','aegean.jo','-o',output],P/'logs/build-web.log')==0
        write(done,stamp)
    # Keep the embedded build for file:// probing and the production split for byte counts.
    web=P/'web';web.mkdir(exist_ok=True)
    for old in web.glob('aegean.*.wasm'):old.unlink()
    shutil.copy2(output,web/'index.html')
    assert run(['python3','tools/package_web.py',web/'index.html'],P/'logs/package-web.log')==0
    assert all(digest(ROOT/'assets'/n)==digest(P/'assets'/n) for n in names),'An asset changed during the build; restore frozen assets and rerun build'
    write(P/'numbers/web-size.json',{str(f.relative_to(P)):dict(bytes=f.stat().st_size,gzip_bytes=len(gzip.compress(f.read_bytes(),mtime=0))) for f in [output,*web.glob('*.html'),*web.glob('*.wasm')]})

def capture(name,label,extra=None,frames=90,binary='aegean',size='1280x720',group='images'):
    image=P/group/(name+'.png');log=P/'logs'/group/(name+'.log')
    e=dict(AEGEAN_CAPTURE_READY='1',SLOPPY_WINDOW=size,SLOPPY_FRAMES=str(frames),SLOPPY_SCREENSHOT=str(image),SLOPPY_SAVE_DIR=str(P/'saves'/group/name))
    e.update(extra or {})
    if e.get('AEGEAN_CAPTURE_READY')=='':e.pop('AEGEAN_CAPTURE_READY')
    identity=dict(binary=digest(P/'build'/binary),environment=e)
    receipt=image.with_suffix('.json');image.parent.mkdir(parents=True,exist_ok=True)
    old=json.loads(receipt.read_text()) if receipt.exists() else {}
    old_identity={k:v for k,v in old.get('identity',{}).items() if k!='label'}
    if A.force or not image.exists() or old_identity!=identity:
        shutil.rmtree(Path(e['SLOPPY_SAVE_DIR']),ignore_errors=True)
        assert run([P/'build'/binary],log,e,timeout=600)==0,log
        with Image.open(image) as im:assert im.size==tuple(map(int,size.split('x'))),(image,im.size)
        pose=[l for l in log.read_text().splitlines() if l.startswith('CAPTURE ')]
        write(receipt,dict(identity=identity,label=label,pose=pose,sha256=digest(image)))
    else:
        assert digest(image)==old['sha256'],f'Changed capture: {image}; use --force'
        write(receipt,old|dict(identity=identity,label=label))
    return image

def sheet(paths,out,labels=None,cols=4,width=320):
    rows=math.ceil(len(paths)/cols);height=round(width*720/1280)
    canvas=Image.new('RGB',(cols*width,rows*(height+26)),(25,29,33));draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf',13) if Path('/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf').exists() else ImageFont.load_default()
    for i,p in enumerate(paths):
        with Image.open(p) as im:
            im=im.convert('RGB');im.thumbnail((width,height));x=i%cols*width;y=i//cols*(height+26)
            canvas.paste(im,(x,y));draw.text((x+5,y+height+4),(labels or [q.stem for q in paths])[i],fill='white',font=font)
    out.parent.mkdir(parents=True,exist_ok=True);canvas.save(out)

def images():
    for name,hour in [('dawn',6),('noon',12),('dusk',18.5),('night',22)]:
        capture('home-'+name,f'Home harbor, {hour:04.1f} h; world clock advanced to match lighting; fixed aerial view',dict(AEGEAN_CAPTURE='home',AEGEAN_HOUR=str(hour),AEGEAN_CAPTURE_MINUTES=str(round((hour-9.5)%24*60))))
    for k,kind in enumerate(KINDS):
        for view in ['air','ground']:
            capture(f'{kind}-{view}',f'{kind.title()} from {view}, 09:30; lowest stable generated settlement ID of this kind',dict(AEGEAN_CAPTURE=f'place:{k}:{view}'))
    capture('capital-old-quarter','Capital old-quarter hill and streets, elevated view, 09:30',dict(AEGEAN_CAPTURE='place:0:old'))
    capture('mainland-4000','Kalyra mainland, camera at 4000 m, 09:30',dict(AEGEAN_CAPTURE='mainland'))
    capture('cliff-coast','Thera Minor limestone cliff coast, 09:30',dict(AEGEAN_CAPTURE='cliff'))
    capture('low-crossing','Low sea crossing off the home harbor; 8 m / 190 m/s initial drawn speed, 09:30',dict(AEGEAN_FLYING='8 190'))
    capture('evening-square','Home town square with people following real evening routines; day 2, approximately 18:20; daily-life scene fixture',dict(LIFE_CAPTURE='evening'),frames=31,binary='lifelab')
    for i,name in enumerate(CRAFT):
        capture(f'aircraft-{i:02}-dock',f'{name} at the home dock, 09:30',dict(AEGEAN_CAPTURE='dock',AEGEAN_CRAFT=str(i)))
        capture(f'aircraft-{i:02}-flight',f'{name} flying off home harbor, 09:30; initial altitude 300 m and drawn speed 190 m/s',dict(AEGEAN_FLYING='300 190',AEGEAN_CRAFT=str(i),AEGEAN_CAPTURE='flight'))
    for mode in ['dock','flight']:
        sheet([P/'images'/f'aircraft-{i:02}-{mode}.png' for i in range(16)],P/'sheets'/f'aircraft-{mode}.png',CRAFT)
    capture('first-view','Unmodified opening view at the home quay, 1.5 s after start',dict(AEGEAN_CAPTURE_READY=''))
    capture('controls-help','Keyboard help opened with H at the starting quay, 09:30',dict(SLOPPY_INPUT='2:h+ 92:h-'))
    capture('cockpit','Gull cockpit with brass compass and radio dial, off home harbor, 09:30',dict(AEGEAN_FLYING='300 190',SLOPPY_INPUT='2:v+ 3:v-'))
    capture('battle','Thirty-aircraft battle fixture over sea, t=6 s, 14:30 lighting',dict(COMBAT_SEEK='360',COMBAT_FREEZE='1',COMBAT_STATIC_CAMERA='1'),2,'combatlab')
    capture('chart-world','Whole-world chart with pocket compass, at home harbor, 09:30',dict(AEGEAN_CHART='1'))
    capture('chart-local','Local archipelago chart with pocket compass, at home harbor, 09:30',dict(AEGEAN_CHART='1',SLOPPY_INPUT='2:tab+ 3:tab-'))
    capture('pause','Pause menu from the starting quay, 09:30',dict(SLOPPY_INPUT='60:p+ 61:p-'))
    capture('conversation','Conversation with the nearest person at the starting quay, 09:30; real greeting',dict(AEGEAN_TALK='1'))
    capture('notebook','Notebook with available real home-board notices pinned by the capture hook; day 2 at 08:00',dict(AEGEAN_CAPTURE_PANEL='notebook',AEGEAN_HOUR='8',AEGEAN_CAPTURE_MINUTES='1170'))
    for name,e in [('touch-flight',dict(AEGEAN_FLYING='300 190')),('touch-cockpit',dict(AEGEAN_FLYING='300 190',SLOPPY_INPUT='2:v+ 3:v-')),('touch-quay',{})]:
        capture(name,f'Phone-like 844×390 low-tier {name.removeprefix("touch-")}; native layout proxy, 09:30',e|dict(AEGEAN_TOUCH='1',AEGEAN_QUALITY='low'),size='844x390')

    additions()

def additions():
    for name,weather,recipe in [('storm','storm','weather-storm'),('overcast-above','overcast','weather-above'),('overcast-below','overcast','weather-below'),('rain','rain','home'),('fog','fog','weather-fog')]:
        e=dict(AEGEAN_CAPTURE=recipe,AEGEAN_WEATHER=weather)
        if name=='storm':e['AEGEAN_WEATHER_CENTER']='0 -26000'
        capture('weather-'+name,f'{name.replace("-"," ").title()}, 09:30; explicit saved-weather fixture, fixed camera recorded below',e)
    for scene,label in [('morning','Three caiques by the harbor mouth, 06:36'),('steamer','Coastal steamer under way, 14:30'),('convoy','Six-ship convoy with escorts, 14:30'),('catalog','All eighteen vessel types, 14:30')]:
        capture('ships-'+scene,label+'; explicit vessel fixture, navigation solved before capture',dict(VESSEL_SCENE=scene),90,'vessellab')
    capture('ships-harbour-morning','Home harbor at 06:36, with the normal vessel population; world clock advanced to match lighting',dict(AEGEAN_CAPTURE='home',AEGEAN_HOUR='6.6',AEGEAN_CAPTURE_MINUTES='1266'))
    capture('options','Options page at the starting quay, 09:30; default settings',dict(AEGEAN_CAPTURE_PANEL='options',SLOPPY_INPUT='60:p+ 61:p-'))
    capture('touch-options','Phone-like 844×390 low-tier Options page; default tilt and inversion settings',dict(AEGEAN_CAPTURE_PANEL='options',SLOPPY_INPUT='60:p+ 61:p-',AEGEAN_TOUCH='1',AEGEAN_QUALITY='low'),size='844x390')
    for name,tick in [('tumble',30),('canopy',150)]:
        capture('bailout-'+name,f'Bail-out {name}, {tick/60:.2f} s after leaving aircraft; explicit combat fixture, 14:30',dict(COMBAT_SCENE='chute',COMBAT_SEEK=str(tick),COMBAT_FREEZE='1'),2,'combatlab')

# 12 successive 60 Hz states, nine frames apart = 0.15 s. Full traces accompany the excerpts.
SEQUENCES={
 'takeoff':(dict(AEGEAN_ABOARD='1',SLOPPY_INPUT='1:shift+ 120:shift- 720:s+ 1800:s-'),720),
 'loop':(dict(AEGEAN_FLYING='600 210',SLOPPY_INPUT='1:s+ 1000:s-'),150),
 'water-landing':(dict(AEGEAN_FLYING='3 70',AEGEAN_CAPTURE_ATTITUDE='-0.025',SLOPPY_INPUT='1:z+ 90:z-'),9),
 'dive-into-sea':(dict(AEGEAN_FLYING='100 190',AEGEAN_CAPTURE_ATTITUDE='-0.75'),12),
}
def sequences():
    for name,(e,start) in SEQUENCES.items():
        paths=[]
        for j in range(12):
            frame=start+j*9
            paths.append(capture(name+f'-{j:02}',f'{name}: home harbor departure waters, simulation frame {frame}, {frame/60:.2f} s after 09:30 initialization',e|dict(AEGEAN_CAPTURE_TRACE='1'),frame,group='sequences/'+name))
        sheet(paths,P/'sheets'/f'{name}.png',cols=4)
        # Keep one complete 18-second input/flight trace, beyond the selected excerpt.
        capture(name+'-trace-end',f'{name}: home harbor departure waters, trace endpoint at 18 s after 09:30 initialization',e|dict(AEGEAN_CAPTURE_TRACE='1'),1080,group='traces')
        lines=(P/'logs/traces'/f'{name}-trace-end.log').read_text().splitlines()
        write(P/'traces'/f'{name}.csv','frame,time_s,x_m,y_m,z_m,vx_mps,vy_mps,vz_mps,pitch_rad,throttle,on_water,crashed,hull_damage\n'+'\n'.join(l[7:] for l in lines if l.startswith('FLIGHT,'))+'\n')
    # Supplemental full maneuver: the primary loop strip remains at 0.15 s spacing.
    paths=[]
    for j in range(12):
        frame=1+j*33
        paths.append(capture(f'loop-overview-{j:02}',f'Full-loop overview off home harbor: frame {frame}, {frame/60:.2f} s; supplemental 0.55 s spacing',SEQUENCES['loop'][0]|dict(AEGEAN_CAPTURE_TRACE='1'),frame,group='sequences/loop-overview'))
    sheet(paths,P/'sheets/loop-overview.png',cols=4)
    for name,scene,start in [('flyby','flyby',12),('dogfight','battle',360)]:
        paths=[]
        observer='fixed at (18000, 405, 18070)' if scene=='flyby' else 'tracking actor 0, offset (105, 90, 160), looking 130 m ahead'
        for j in range(12):
            tick=start+j*9
            e=dict(COMBAT_SCENE=scene,COMBAT_SEEK=str(tick),COMBAT_FREEZE='1',COMBAT_COUNT='1' if scene=='flyby' else '30')
            paths.append(capture(f'{name}-{j:02}',f'{name} combat fixture, observer {observer}, 14:30 lighting, simulation time {tick/60:.2f} s',e,2,'combatlab',group='sequences/'+name))
        sheet(paths,P/'sheets'/f'{name}.png',cols=4)

def world():
    log=P/'world/month.txt'
    stamp=log.with_suffix('.stamp');signature=digest(P/'build/lifelog')
    if A.force or not log.exists() or not stamp.exists() or stamp.read_text()!=signature or 'MONTH COMPLETE:' not in log.read_text():
        assert run([P/'build/lifelog'],log,dict(JUDGE_TRANSCRIPT='1',SLOPPY_SAVE_DIR=str(P/'saves/month')),timeout=3600)==0
    write(stamp,signature)
    lines=log.read_text().splitlines()
    notebook_log=P/'logs/images/notebook.log'
    if notebook_log.exists():write(P/'world/notebook.txt','\n'.join(l for l in notebook_log.read_text().splitlines() if l.startswith('NOTEBOOK '))+'\n')
    write(P/'world/summary.md','# Thirty-day transcript\n\nSeed 42; 43,200 game minutes; the existing lifelog driver, with optional job-transition and price evidence. No fabricated jobs or forced successes.\n\n'+'\n'.join(l for l in lines if l.startswith(('MONTH COMPLETE:','JUDGING SUMMARY:')))+'\n\nThe player notebook is UI-owned. Its actual pinned notices are in the notebook capture. `NOTEBOOK SOURCE` lines here are real boards available for copying, not claims that the player accepted or completed them.\n')

def audio():
    folder=P/'audio';folder.mkdir(exist_ok=True)
    assert run([P/'build/audio'],folder/'generation.log',dict(JUDGE_AUDIO_DIR=str(folder)))==0
    write(folder/'layers.csv','name,sample_rate,frames\n'+'\n'.join(l for l in (folder/'generation.log').read_text().splitlines() if re.fullmatch(r'[a-z0-9-]+,[0-9]+,[0-9]+',l))+'\n')
    pictures=[]
    for raw in sorted(folder.glob('*.f32')):
        import numpy as np
        v=np.fromfile(raw,dtype='<f4')[::2];n=2048
        starts=np.linspace(0,max(0,len(v)-n),8).astype(int)
        power=np.mean([abs(np.fft.rfft(v[start:start+n]*np.hanning(n)))**2 for start in starts],axis=0)
        db=10*np.log10(np.maximum(power/max(power),1e-8))
        with (folder/(raw.stem+'.csv')).open('w') as f:
            f.write('frequency_hz,relative_db\n');f.writelines(f'{i*48000/n:.3f},{value:.3f}\n' for i,value in enumerate(db))
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,ax=plt.subplots(figsize=(6.4,2.4),layout='constrained')
        ax.semilogx([i*48000/n for i in range(1,len(db))],db[1:],linewidth=1)
        ax.set(xlim=(20,24000),ylim=(-80,0),xlabel='Frequency (Hz)',ylabel='Relative dB',title=raw.stem)
        ax.grid(True,alpha=.25)
        path=folder/(raw.stem+'.png');fig.savefig(path,dpi=100);plt.close(fig)
        pictures.append(path);raw.unlink()
    sheet(pictures,folder/'spectra.png',cols=3,width=400)
    write(folder/'README.md',SOUND_TEXT)

def tests():
    signature=hashlib.sha256((TOOLCHAIN+''.join(str(p.relative_to(ROOT))+digest(p) for p in sorted([*(ROOT/'src').glob('*.jo'),*(ROOT/'tests').glob('*.jo')]))).encode()).hexdigest()
    stamp=P/'tests/source.stamp'
    changed=not stamp.exists() or stamp.read_text()!=signature
    if changed:
        for old in (P/'tests').glob('*.exit'):old.unlink()
        write(stamp,signature)
    results=[]
    for source in sorted((ROOT/'tests').glob('*.jo')):
        log=P/'tests'/(source.stem+'.log');rcfile=log.with_suffix('.exit')
        if A.force or not rcfile.exists():
            rc=run([SLOPPY,'test','--release',source],log,dict(SLOPPY_SAVE_DIR=str(P/'saves/tests'/source.stem)),timeout=1800);write(rcfile,str(rc))
        rc=int(rcfile.read_text());text=log.read_text()
        results.append(dict(file=str(source.relative_to(ROOT)),exit=rc,passed=sum(map(int,re.findall(r'(?m)^(\d+)(?: tests)? passed',text))),failed=len(re.findall(r'(?m)^test .*FAILED',text)),log=str(log.relative_to(P))))
    write(stamp,signature)
    write(P/'numbers/tests.json',results)
    unexpected=[]
    for r in results:
        known=r['file']=='tests/living_scene_flight.jo' and r['failed']==2 and all(f'living_scene_flight.jo:{n}:' in (P/r['log']).read_text() for n in [129,143])
        if r['exit'] and not known:unexpected.append(r['file'])
    write(P/'numbers/tests-status.json',dict(unexpected_failure_files=unexpected,passed=sum(r['passed'] for r in results),failed=sum(r['failed'] for r in results)))
    # The pack records test failures for judges; a failing game test does not suppress evidence.

SOUND_TEXT='''# Sound evidence (silent collection)

No sound was played. Spectra are generated from the game's actual procedural stereo samples,
downmixed by taking the identical left channel, with eight 2048-sample Hann windows. Each plot
is normalized to its own peak; it does not show mix loudness, Doppler, spatial position or feel.
CSV files preserve the curves. No audible recording is necessary for judging this pack.

- Engines 0–3: rotary, inline, radial and twin timbres; firing pulse and prop harmonics, with
  beating for twins. Pitch follows throttle and true airspeed. Other aircraft use a separate brighter
  prop-harmonic buzz with fainter exhaust, distance attenuation, propagation delay and Doppler
  (`engine_outside_loop`); the shown engine spectra are the cockpit sources.
- Air rush, wires, howl, deep, gale and rumble: filtered noise bands and structural tones;
  speed/load determine their mix. They are separate layers, not six simultaneous full-volume loops.
- Cloth, cloth-hit and heavy-cloth: irregular flutter and individual fabric snaps; flex-up/down
  are brief oil-can sounds tied to changes in load.
- Combat 0–2: representative light, medium and heavy gun reports (the live game selects among eight variants each); 3: impact; 4: canopy opening; 5: fire; 6: falling/canopy wind;
  7: body thump when the player's aircraft is hit; 8: near-pass crack/swish. Spatial attenuation
  and cooldowns apply in play.
- Surf: slowly swelling low-pass noise near shore. Gulls: short procedurally pitched calls.
  Water impacts: noise burst/splash; solid impacts: crunch with a sharper attack. These private
  ambient generators are described here rather than replaced by invented spectral samples.
- Square musician: original plucked phrase, only for an arrived musician nearby. Fundamental
  293.6648 Hz transposed through [0,2,3,5,7,9,10,12] semitones; six harmonics weighted 1/h^1.3
  decay at (5+1.5h)/s. Three notes per second, range 70 m. Analytic harmonic description, not a recording.

- Radio: original foxtrot, tango, waltz, bouzouki, march, wordless choir and Morse programmes.
  A bounded mono 16 kHz synthesizer feeds a 300–3000 Hz AM filter, with signal-dependent static,
  fading and whistle. The radio spectra below use the actual synthesizer, without playback.

Dialogue is text, not recorded voice acting.

Sources: src/sound.jo, src/airsound.jo, src/combat_sound.jo, src/life_audio.jo, src/radio_synth.jo.
'''

def remote(stage):
    host=os.environ.get('JUDGE_REDFOX','dsamson@192.168.1.79')
    remote_dir='dev/tmp/aegean-judge-'+A.round
    assert run(['ssh',host,'mkdir','-p',remote_dir],P/'logs'/f'{stage}-mkdir.log')==0
    for file in [P/'build/aegean',P/'build/aegean.html',ROOT/'tools/measure_web.mjs',ROOT/'tools/judge_redfox.py']:
        assert run(['rsync','-a',file,host+':'+remote_dir+'/'],P/'logs'/f'{stage}-copy-{file.name}.log')==0
    rc=run(['ssh',host,'python3',remote_dir+'/judge_redfox.py',stage]+(['--force'] if A.force else []),P/'logs'/f'redfox-{stage}.log',timeout=1800)
    assert run(['rsync','-a','--exclude=aegean','--exclude=aegean.html',host+':'+remote_dir+'/',P/'redfox'],P/'logs'/f'{stage}-retrieve.log')==0
    assert rc==0,f'redfox {stage}: see log (load gate failure is resumable)'
    if stage=='bench':
        summary={}
        for log in sorted((P/'redfox').glob('bench-*.log')):
            text=log.read_text();rows=[list(map(float,x)) for x in re.findall(r'stats: .*? (\d+\.\d+) ms .*?cpu (\d+\.\d+) ms.*?gpu (\d+\.\d+) ms',text)]
            warm=rows[2:];assert warm,(log,rows)
            summary[log.stem]=dict(median_total_cpu_gpu_ms=[statistics.median(x[i] for x in warm) for i in range(3)],samples=len(warm),load=[l for l in text.splitlines() if l.startswith('LOAD')])
        write(P/'numbers/redfox.json',summary)
    else:
        probe=json.loads((P/'redfox/browser-mobile.png.json').read_text());assert not probe['errors']
        assert all(x['linked'] for x in probe['programs'])
        assert len(probe['frames'])>5,'Browser did not finish startup'
        log=(P/'redfox/browser.log').read_text()
        wasm=re.search(r'"wasm_bytes":(\d+)',log);rss=re.search(r'browser tree RSS KiB (\d+)',log)
        write(P/'numbers/browser.json',dict(host='redfox',html_sha256=digest(P/'build/aegean.html'),audio_synthesis=False,emulation='844x390 DPR3 Android, low tier; hardware Intel Vulkan; no network (file:// embedded build)',canvas=probe['canvas'],frames=len(probe['frames']),first_frame_callback_ms=probe['frames'][0],first_completed_frame_upper_bound_ms=probe['frames'][1],wasm_linear_bytes=int(wasm[1]) if wasm else None,browser_tree_rss_kib=int(rss[1]) if rss else None,shader_programs=len(probe['programs']),errors=probe['errors']))

def index():
    if (P/'numbers/browser.json').exists():
        data=json.loads((P/'numbers/browser.json').read_text())
        processes=[json.loads(m) for m in re.findall(r'(?m)^process .*?(\{.*\})$',(P/'redfox/browser.log').read_text())]
        data['browser_tree_pss_kib']=sum(r['Pss'] for r in processes)
        data['browser_tree_private_kib']=sum(r['Private_Clean']+r['Private_Dirty'] for r in processes)
        write(P/'numbers/browser.json',data)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for path in sorted((P/'traces').glob('*.csv')):
        rows=list(csv.DictReader(path.open()))
        if not rows:continue
        times=[float(r['time_s']) for r in rows]
        fig,axs=plt.subplots(2,2,figsize=(10,6),layout='constrained')
        axs[0,0].plot([float(r['x_m'])-float(rows[0]['x_m']) for r in rows],[float(r['z_m'])-float(rows[0]['z_m']) for r in rows]);axs[0,0].set(xlabel='East displacement (m)',ylabel='South displacement (m)',title='Ground track')
        axs[0,1].plot(times,[float(r['y_m']) for r in rows]);axs[0,1].set(xlabel='Time (s)',ylabel='Altitude (m)')
        speeds=[math.sqrt(sum(float(r[v])**2 for v in ['vx_mps','vy_mps','vz_mps']))*3.6 for r in rows]
        axs[1,0].plot(times,speeds,label='Drawn');axs[1,0].plot(times,[v/3.3 for v in speeds],label='True (drawn ÷ 3.3)');axs[1,0].set(xlabel='Time (s)',ylabel='Speed (km/h)');axs[1,0].legend()
        axs[1,1].plot(times,[float(r['pitch_rad'])*180/math.pi for r in rows]);axs[1,1].set(xlabel='Time (s)',ylabel='Nose elevation (degrees)',title='arcsin(forward.y), folds when inverted')
        for ax in axs.flat:ax.grid(True,alpha=.2)
        fig.suptitle(path.stem+' — actual main-game physics, recorded controls')
        fig.savefig(path.with_name(path.stem+'-plot.png'),dpi=120);plt.close(fig)
    if (P/'numbers/redfox.json').exists():
        results=json.loads((P/'numbers/redfox.json').read_text())
        fig,ax=plt.subplots(figsize=(8,4),layout='constrained')
        views=['home','mainland','capital']
        for j,tier in enumerate(['low','medium','high']):
            values=[results[f'bench-{tier}-{view}']['median_total_cpu_gpu_ms'][0] for view in views]
            bars=ax.bar([i+(j-1)*.25 for i in range(3)],values,width=.24,label=tier)
            ax.bar_label(bars,fmt='%.1f',fontsize=8)
        ax.set(xticks=range(3),xticklabels=['Home harbor','Mainland 4000 m','Capital ground'],ylabel='Median interval-average frame time (ms)',title='redfox / Intel UHD 620 / 1280×720')
        ax.legend(title='Quality');ax.grid(axis='y',alpha=.2)
        fig.savefig(P/'numbers/redfox-frame-times.png',dpi=150);plt.close(fig)
    refs=P/'references';refs.mkdir(exist_ok=True)
    source=BASE.parent/'refs';assert source.is_dir()
    shutil.copytree(source,refs/'stills',dirs_exist_ok=True)
    shutil.copy2(BASE.parent/'world/aegean_ref.png',refs/'aegean_ref.png')
    for file in ['DESIGN.md','FEEL.md','JUDGING.md','SIM_SPEC.md']:
        shutil.copy2(ROOT/'docs'/file,refs/file)
    records=[]
    for path in sorted(P.rglob('*.png')):
        if any(part in ('references','build','saves','web','assets','toolchain') for part in path.relative_to(P).parts):continue
        receipt=path.with_suffix('.json')
        if receipt.exists() and 'label' in json.loads(receipt.read_text()):
            data=json.loads(receipt.read_text());label=data['label']
            if data.get('pose'):label+=' — '+data['pose'][0]
        elif path.parent.name=='numbers':label='redfox frame-time comparison: three fixed cameras, each quality tier; see measurement method and raw logs'
        elif 'sheets' in path.parts:label='Contact sheet: '+path.stem.replace('-',' ')+'; see individually timed originals below'
        elif path.name.endswith('-plot.png'):label='Recorded flight trace plot: '+path.stem+'; CSV and controls in adjacent files/receipts'
        elif 'audio' in path.parts:label='Offline spectrum: '+path.stem+'; normalized per layer, not mix loudness'
        elif path.name=='browser-mobile.png':label='Actual Chromium mobile-emulation capture on redfox after a 120 s observation window; 844×390 CSS, low tier, home harbor'
        else:label='Benchmark endpoint: '+path.stem+'; fixed camera named in filename, 20 simulated seconds after 09:30 start; camera coordinates, tier and load in adjacent log'
        records.append(f'- [{path.relative_to(P)}]({path.relative_to(P)}): {label}')
    write(P/'index.md','# Capture index\n\n'+ '\n'.join(records)+'\n')
    modules=[]
    for path in sorted([ROOT/'aegean.jo',*(ROOT/'src').glob('*.jo'),*(ROOT/'tools').glob('*.jo')]):
        data=path.read_text();modules.append(dict(module=str(path.relative_to(ROOT)),lines=len(data.splitlines()),bytes=len(data.encode())))
    write(P/'numbers/code-size.json',modules)
    first=git('rev-list','--max-parents=0','HEAD').splitlines()[0]
    morning=git('rev-list','-1','--before=2026-11-11T08:00:00-05:00','HEAD')
    origins={'first-commit':first,'2026-11-11-morning':morning}
    if A.previous:origins['previous-round']=json.loads((BASE/A.previous/'provenance.json').read_text())['commit']
    for name,commit in origins.items():write(P/'numbers'/f'diff-{name}.txt',f'Baseline {commit}\n'+git('diff','--stat',commit)+'\n')
    numbers=['# Measurements and counts', '', 'Raw logs and JSON are retained; these tables contain observations, not scores.', '']
    if (P/'numbers/redfox.json').exists():
        numbers+=['## Redfox native frame times', '', '| Tier / fixed view | Total ms | CPU ms | GPU ms | Warm samples |', '|---|---:|---:|---:|---:|']
        for name,r in json.loads((P/'numbers/redfox.json').read_text()).items():
            a,b,c=r['median_total_cpu_gpu_ms'];numbers.append(f"| {name} | {a:.2f} | {b:.2f} | {c:.2f} | {r['samples']} |")
        numbers+=['', 'One-minute loads before/after each run are in redfox/*.log and redfox.json.', '']
    if (P/'numbers/browser.json').exists():
        numbers+=['## Chromium mobile emulation on redfox', '', '```json', (P/'numbers/browser.json').read_text().strip(), '```', '']
    if (P/'numbers/web-size.json').exists():
        numbers+=['## Web artifacts', '', '| Artifact | Bytes | Gzip bytes |', '|---|---:|---:|']
        for name,r in json.loads((P/'numbers/web-size.json').read_text()).items():numbers.append(f"| {name} | {r['bytes']} | {r['gzip_bytes']} |")
    if (P/'numbers/tests.json').exists():
        results=json.loads((P/'numbers/tests.json').read_text())
        numbers+=['', '## Per-file release tests', '', f"{sum(r['passed'] for r in results)} passed; {sum(r['failed'] for r in results)} failed; {len(results)} files.", '', '| File | Passed | Failed | Exit |', '|---|---:|---:|---:|']
        for r in results:numbers.append(f"| [{r['file']}](../{r['log']}) | {r['passed']} | {r['failed']} | {r['exit']} |")
    numbers+=['', '## Code size', '', '| Module | Lines | Bytes |', '|---|---:|---:|']
    numbers += [f"| {r['module']} | {r['lines']} | {r['bytes']} |" for r in modules]
    write(P/'numbers/README.md','\n'.join(numbers)+'\n')
    write(P/'README.md',README_TEXT+f'\nGame baseline: `{json.loads((P/"provenance.json").read_text()).get("game_baseline",git("rev-parse","HEAD"))}`. Source commit (including capture tooling): `{git("rev-parse","HEAD")}`. Exact source state and build identity: [provenance.json](provenance.json), [source.patch](source.patch).\n\n'+
          '\n'.join(f'- [{name} change](numbers/diff-{name}.txt), baseline `{commit}`.' for name,commit in origins.items())+'\n')

README_TEXT='''# Aegean Skies — judging capture pack

This is evidence for independent review, not a verdict. Start with [index.md](index.md), then the
[month transcript](world/month.txt), [summary](world/summary.md), [numbers](numbers/), and
[flight traces](traces/). The rubric is copied in [JUDGING.md](references/JUDGING.md). No judge's
scores or recommendations are included. Contact sheets are navigation aids; inspect the originals.

## What the game aims to be

An original painted Aegean/Adriatic seaplane world in the 1920s–30s, with inhabited harbors,
travel, trade, errands, relationships and danger. The design's priorities are: people act from
circumstance and motives; the world keeps running away from the player; consequences persist;
small systems interact; the simulation is deterministic and saveable. The full
[DESIGN.md](references/DESIGN.md) contains both implemented work and aspirations, not a claim
that every item is complete. The original islands are inside a roughly 500×400 km world.

References: [film stills](references/stills/) for atmosphere and [the user's geography reference](references/aegean_ref.png).
These are private review references copied into scratch, not game assets or original work.

## Decisions already made by the user

- The chosen speed feel is the pure speed scale: 3.3× drawn speed, other behavior using true speed,
  with a slower takeoff. Near-field speed tricks were rejected. The no-drag 450+ km/h low-flight
  look is the reference. Do not confuse this ruling with a claim that every default reproduces it;
  capture metadata records the settings actually used.
- Sky Barons' energy is the base; add realism only where it does not make flying harder.
- The title stands alone. No UI taglines or subtitles.
- The original islands' sizes and distances are right; the surrounding world is about 500×400 km.
- Mobile controls follow Sky Barons: drag to aim and a Walk button. The user liked them.
- Tilt for fine aiming was liked; it is available in Options.
- Chaotic stalls were liked and are now the default.
- Clouds are known not to match the film references yet. They are work in progress; judge them anyway.
- Optional trials belong behind the pause menu's Tweaks checkboxes, off by default. The accepted
  chaotic-stall behavior above is now a default, not a rejected trial.
- Read [FEEL.md](references/FEEL.md) and the user feedback in DESIGN.md before proposing to undo
  accepted work. Treat any older world-size wording there as superseded by the ruling above.

## What this pack cannot convey

You cannot feel control latency, resistance, acceleration or the player's decisions through stills.
The six sequences are twelve adjacent states, 0.15 seconds apart: short excerpts, not movies of a
whole maneuver. A supplemental twelve-frame loop overview uses 0.55 s spacing to show one full
turn. Four full 18-second flight traces include position, velocity, pitch, throttle,
water contact, crash and damage; inputs and initial conditions are in each adjacent capture receipt.
Catalog captures skip the transient title/help overlay; `first-view.png` preserves the unmodified
opening view. Native main-game captures use real rendering and physics. The battle and fly-by are explicitly
seeded combat fixtures. Weather shots explicitly replace the saved weather cells; vessel shots
use the existing synthetic acceptance fleet, with real navigation/rendering and no changes to
the living game. The evening square is the existing daily-life fixture, advancing real
routines rather than arranging people. These fixtures are not claims about how often encounters
happen in ordinary play. Notebook notices are copied from the actual board; no player successes
are invented. The month transcript records NPC errands and their real outcomes.

Sound was collected silently: [layer descriptions and spectra](audio/README.md). Normalized
spectra cannot establish whether the mixed sound is pleasant, loud, spatially convincing or timed
well. Phone-sized native shots inspect layout only. Chromium's Android emulation is not a physical
phone and does not impose its RAM/GPU bandwidth limits; the buffer dimensions and memory usage
are reported. Browser startup is file:// without download time, measured on redfox, not a network
load estimate. Startup timestamps are animation-frame times relative to page navigation: the first
callback begins game rendering; the second bounds completion of that first rendered frame.
Audio synthesis is disabled during measurement, matching the native runs.
WASM linear memory is part of browser memory, not an additional amount to sum with it.
Summed process RSS counts shared pages more than once; summed PSS apportions shared pages.
The raw per-process figures and private memory are retained as well.

## Measurement method

All test and capture jobs are serial with SLOPPY_THREADS=1, private saves, no display and no audio.
Native timing is only on redfox (Intel UHD 620), under ~/dev/tmp/bench.lock, at 1280×720.
The one-minute load must be below 1.5 before each run; both initial and final load are logged.
Three fixed cameras (home harbor, mainland at 4000 m, capital ground) run on low/medium/high.
Medians omit the first two statistics intervals. These are medians of the runtime's interval-average
frame/CPU/GPU timings, not per-frame latency percentiles. Raw logs remain alongside the summary.
The full test suite runs per file; the two pre-existing living_scene_flight failures are preserved,
not hidden. Code size is source lines/bytes by module; it is evidence, not a complexity score.

Each round freezes the compiler and standard library under `toolchain/`; builds and tests use
that copy even if the shared installation is upgraded. Embedded assets are frozen under `assets/`;
a build refuses changed inputs so a shared asset rebake cannot silently change a round.
Start a new round to change toolchains or assets.
Collection logs are append-only and retain retries. Final provenance, capture receipts and the
manifest identify the delivered artifacts.
Reproduce with `tools/judge_pack.sh ROUND` from the checkout. See `--help` for resumable stages.
A successful cached image is reused only with matching binary and exact environment. Timing,
browser and tests have explicit logs; source provenance and hashes travel with the pack.
'''

def main():
    global A,P,SLOPPY,TOOLCHAIN
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('round');parser.add_argument('--stage',choices=STAGES+['additions'],action='append');parser.add_argument('--force',action='store_true');parser.add_argument('--previous')
    A=parser.parse_args();assert re.fullmatch(r'[a-zA-Z0-9_-]+',A.round)
    P=BASE/A.round;P.mkdir(parents=True,exist_ok=True)
    # Freeze compiler and standard library once per round: shared installations can be upgraded.
    chain=P/'toolchain';SLOPPY=chain/'bin/sloppy'
    if not SLOPPY.exists():
        installed=Path(shutil.which('sloppy')).resolve()
        (chain/'bin').mkdir(parents=True,exist_ok=True)
        shutil.copytree(installed.parent.parent/'lib',chain/'lib',dirs_exist_ok=True)
        shutil.copy2(installed,SLOPPY)
    TOOLCHAIN=hashlib.sha256(''.join(str(p.relative_to(chain))+digest(p) for p in sorted(chain.rglob('*')) if p.is_file()).encode()).hexdigest()
    started=time.monotonic()
    for stage in A.stage or STAGES:
        before=time.monotonic();print('STAGE',stage,flush=True)
        if stage in ['web','bench']:remote(stage)
        else:globals()[stage]()
        with (P/'stages.jsonl').open('a') as f:f.write(json.dumps(dict(stage=stage,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),seconds=round(time.monotonic()-before,3)))+'\n')
    if 'index' in (A.stage or STAGES):
        write(P/'manifest-sha256.json',{str(p.relative_to(P)):digest(p) for p in sorted(P.rglob('*')) if p.is_file() and 'saves' not in p.relative_to(P).parts and p.name!='manifest-sha256.json'})
    print('Pack work completed in',round(time.monotonic()-started,1),'seconds:',P)
if __name__=='__main__':main()
