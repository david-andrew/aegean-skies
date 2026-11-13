// Headless WebGL2 compatibility proxy, not phone timing. Node22+, Chromium, Pillow.
// node tools/test_web_clouds.mjs <chromium> <cloud_transparency_test.html> <scratch>
import {spawn, execFileSync} from 'node:child_process';
import {mkdirSync, mkdtempSync, readFileSync, writeFileSync, rmSync} from 'node:fs';
import {resolve, join} from 'node:path';
import assert from 'node:assert/strict';

const [chrome, pageArg, outArg] = process.argv.slice(2);
assert(chrome && pageArg && outArg, 'chromium, built page and scratch output directory required');
const page=resolve(pageArg), out=resolve(outArg);
readFileSync(page); mkdirSync(out,{recursive:true});
const profile=mkdtempSync(join(out,'chromium-'));
const gpu=process.env.WEB_CLOUD_GPU==='native'
  ? ['--use-angle=vulkan','--enable-features=Vulkan','--disable-vulkan-surface']
  : ['--enable-unsafe-swiftshader','--use-angle=swiftshader'];
const env={...process.env};delete env.DISPLAY;delete env.WAYLAND_DISPLAY;
const browser=spawn(chrome,['--headless=new','--no-sandbox','--mute-audio','--allow-file-access-from-files',
  '--remote-debugging-port=0',`--user-data-dir=${profile}`,'--window-size=1200,900',...gpu,'about:blank'],
  {env,stdio:['ignore','ignore','pipe']});
let stderr='', ws, seq=0, loaded=false;const pending=new Map(), errors=[];
browser.stderr.on('data',d=>stderr+=d);
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function until(test,limit=300000) {
  const end=Date.now()+limit;
  while(!(await test())) {assert(Date.now()<end,'browser/frame timeout: '+stderr.slice(-500));await sleep(100);}
}
try {
  await until(()=>/DevTools listening on (ws:\S+)/.test(stderr),15000);
  const port=new URL(stderr.match(/DevTools listening on (ws:\S+)/)[1]).port;
  const target=(await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find(t=>t.type==='page');
  ws=new WebSocket(target.webSocketDebuggerUrl);
  await new Promise(r=>ws.addEventListener('open',r,{once:true}));
  ws.addEventListener('message',e=>{
    const m=JSON.parse(e.data);
    if(m.id && pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(m.error):p.resolve(m.result);}
    if(m.method==='Page.loadEventFired')loaded=true;
    if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails);
  });
  const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
  await send('Runtime.enable');await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride',{width:1200,height:900,deviceScaleFactor:1,mobile:false});
  await send('Page.addScriptToEvaluateOnNewDocument',{source:`
    window.quayFrames=0;window.quayLinks=[];window.nearLimit=4;window.nearPending=null;
    const raf=requestAnimationFrame;
    const schedule=cb=>raf(t=>{if(quayFrames>=nearLimit){nearPending=()=>schedule(cb);return;}cb(t);quayFrames++;});
    window.requestAnimationFrame=schedule;
    window.nearAdvance=n=>{nearLimit=n;const next=nearPending;nearPending=null;if(next)next();};
    const proto=WebGL2RenderingContext.prototype,link=proto.linkProgram;
    proto.linkProgram=function(p){link.call(this,p);quayLinks.push(this.getProgramParameter(p,this.LINK_STATUS));};
  `});
  const results=[];
  for(const full of [false,true]) for(const mode of ['front','behind']) {
    const name=`${full?'log':'split'}-${mode}`;
    const query=new URLSearchParams({SLOPPY_NO_AUDIO:'1',SLOPPY_THREADS:'1',SLOPPY_SEED:'12345',CLOUD_TEST_MODE:mode,AEGEAN_QUALITY:'low'});
    if(full)query.set('AEGEAN_FULL_LOG_DEPTH','1');
    errors.length=0;loaded=false;
    await send('Page.navigate',{url:'file://'+page+'?'+query});
    await until(()=>loaded);
    await until(async()=>{const r=await send('Runtime.evaluate',{returnByValue:true,expression:'globalThis.quayFrames||0'});return r.result?.value>=4;});
    const links=(await send('Runtime.evaluate',{returnByValue:true,expression:'quayLinks'})).result.value;
    assert(links.length>15 && links.every(Boolean),`${name}: shader linking failed`);
    assert.equal(errors.length,0,`${name}: JavaScript exception ${JSON.stringify(errors)}`);
    const shot=await send('Page.captureScreenshot',{format:'png'}),file=join(out,name+'.png');
    writeFileSync(file,Buffer.from(shot.data,'base64'));
    const pixels=JSON.parse(execFileSync('python3',[new URL('./check_cloud_pixels.py',import.meta.url).pathname,file,mode],{encoding:'utf8'}));
    results.push({name,file,linkedPrograms:links.length,pixels});
    console.log(JSON.stringify(results.at(-1)));
  }
  const sky=process.argv[5];
  if(sky) {
    const probes=[];
    for(const full of [false,true]) for(const target of ['moon','venus']) for(const cloud of [false,true]) {
      const name=`sky-${full?'log':'split'}-${target}-${cloud?'cloud':'clear'}`;
      const q=new URLSearchParams({SLOPPY_NO_AUDIO:'1',SKY_TARGET:target,SKY_HOUR:target==='moon'?'0':'5.8',SKY_DAY:target==='moon'?String(29.53059/2-10):'0'});
      if(full)q.set('AEGEAN_FULL_LOG_DEPTH','1');if(cloud)q.set('SKY_CLOUD','1');
      errors.length=0;loaded=false;await send('Page.navigate',{url:'file://'+resolve(sky)+'?'+q});
      await until(()=>loaded);await until(async()=>{const r=await send('Runtime.evaluate',{returnByValue:true,expression:'globalThis.quayFrames||0'});return r.result?.value>=4;});
      const links=(await send('Runtime.evaluate',{returnByValue:true,expression:'quayLinks'})).result.value;
      assert(links.every(Boolean)&&errors.length===0,name+': sky shader/runtime failure');
      const shot=await send('Page.captureScreenshot',{format:'png'}),file=join(out,name+'.png');writeFileSync(file,Buffer.from(shot.data,'base64'));
      const pixels=JSON.parse(execFileSync('python3',['-c',`
import json,sys
from PIL import Image,ImageStat
im=Image.open(sys.argv[1]).convert('RGB');w,h=im.size;x=w//2;y=h//2
center=im.crop((x-3,y-3,x+3,y+3));rim=im.crop((x+35,y-3,x+45,y+3))
print(json.dumps({'peak':max(max(p) for p in center.getdata()),'contrast':max(max(p) for p in center.getdata())-sum(ImageStat.Stat(rim).mean)/3}))
`,file],{encoding:'utf8'}));
      probes.push({name,full,target,cloud,file,...pixels});
    }
    for(const clear of probes.filter(p=>!p.cloud)) {
      const cloud=probes.find(p=>p.cloud&&p.full===clear.full&&p.target===clear.target);
      assert(clear.contrast>40,clear.name+': celestial body not visible');
      assert(cloud.contrast<25,cloud.name+': celestial body leaked over cloud');
    }
    writeFileSync(join(out,'sky.json'),JSON.stringify(probes,null,2)+'\n');
    console.log('PASS: moon and Venus visibility and cloud occlusion on both WebGL2 depth paths');
  }
  writeFileSync(join(out,'results.json'),JSON.stringify(results,null,2)+'\n');
  console.log('PASS: every foreground material visible; background materials cloud-occluded on split and full log WebGL2 depth');
} finally {
  ws?.close();
  const exited=new Promise(r=>browser.once('exit',r));
  if(browser.exitCode===null){browser.kill();const guard=setTimeout(()=>browser.kill('SIGKILL'),5000);await exited;clearTimeout(guard);}
  rmSync(profile,{recursive:true,force:true});
}
