#!/usr/bin/env python3
"""Copied to an isolated scratch folder on redfox; no edits outside that folder."""
import fcntl,glob,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent;os.chdir(root)
assert os.uname().nodename=='redfox','Timings are allowed only on redfox'
assert 'i5-8350U' in Path('/proc/cpuinfo').read_text(),'Expected the quiet redfox laptop, not the similarly named desktop'
env={k:v for k,v in os.environ.items() if k not in ('DISPLAY','WAYLAND_DISPLAY') and not k.startswith(('AEGEAN_','SLOPPY_'))}
env.update(SLOPPY_NO_AUDIO='1',SLOPPY_THREADS='1',SLOPPY_SEED='12345')
def gate():
    load=Path('/proc/loadavg').read_text().strip()
    print('LOAD',load,flush=True)
    if float(load.split()[0])>=1.5:
        print('Load gate closed; rerun this stage when redfox is quiet. No timing started.',flush=True);sys.exit(75)
    return load
with (Path.home()/'dev/tmp/bench.lock').open('w') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    (root/'machine.json').write_text(json.dumps(dict(host=os.uname().nodename,kernel=os.uname().release,cpu=[l.split(':',1)[1].strip() for l in Path('/proc/cpuinfo').read_text().splitlines() if l.startswith('model name')][0],memory=Path('/proc/meminfo').read_text().splitlines()[0],binary_sha256=hashlib.sha256((root/'aegean').read_bytes()).hexdigest()),indent=2)+'\n')
    if sys.argv[1]=='bench':
        for tier in ['low','medium','high']:
            for name,recipe in [('home','home'),('mainland','mainland'),('capital','place:0:ground')]:
                label=f'bench-{tier}-{name}'
                identity=hashlib.sha256((hashlib.sha256((root/'aegean').read_bytes()).hexdigest()+tier+recipe+'1200').encode()).hexdigest()
                receipt=root/(label+'.done')
                if '--force' not in sys.argv and receipt.exists() and receipt.read_text()==identity and (root/(label+'.log')).exists() and (root/(label+'.png')).exists():
                    print('REUSE',label,flush=True);continue
                load=gate();shutil.rmtree(root/('save-'+label),ignore_errors=True)
                e=env|dict(AEGEAN_QUALITY=tier,AEGEAN_CAPTURE=recipe,SLOPPY_FRAMES='1200',SLOPPY_STATS='log',SLOPPY_SCREENSHOT=str(root/(label+'.png')),SLOPPY_SAVE_DIR=str(root/('save-'+label)))
                with open(label+'.log','w') as f:
                    f.write('HOST redfox\nLOAD before '+load+'\nENV '+json.dumps({k:v for k,v in e.items() if k.startswith(('AEGEAN_','SLOPPY_'))})+'\n');f.flush()
                    r=subprocess.run([root/'aegean'],env=e,stdout=f,stderr=subprocess.STDOUT,timeout=600)
                    f.write('LOAD after '+Path('/proc/loadavg').read_text())
                assert r.returncode==0,label
                receipt.write_text(identity)
                print('DONE',label,flush=True)
    else:
        load=gate();chrome=sorted(glob.glob(str(Path.home()/'.cache/ms-playwright/chromium*/chrome-linux*/chrome')))[-1]
        node='/home/linuxbrew/.linuxbrew/bin/node'
        with open('browser.log','w') as f:
            f.write('HOST redfox\nLOAD before '+load+'\n');f.flush()
            r=subprocess.run([node,'measure_web.mjs',chrome,str(root/'aegean.html'),str(root/'browser-mobile.png'),'120','?AEGEAN_QUALITY=low&AEGEAN_CAPTURE=home&SLOPPY_NO_AUDIO=1&SLOPPY_SEED=12345&SLOPPY_THREADS=1'],env=env|dict(WEBSHOT_GPU='native',WEBSHOT_MOBILE='1',WEBSHOT_TMP=str(root)),stdout=f,stderr=subprocess.STDOUT,timeout=600)
            f.write('LOAD after '+Path('/proc/loadavg').read_text())
        assert r.returncode==0
