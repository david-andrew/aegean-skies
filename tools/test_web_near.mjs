// Render the real Porto Vecchio start on foot, in its downward-looking follow camera.
// Regression: nonlinear vertex depth cut away the quay under/in front of the feet.
// Requires Node 22+, Chromium and Python/Pillow (also used by judge_pack.py).
// Build: sloppy build aegean.jo --release --target wasm -o <scratch>/aegean.html
// Run: node tools/test_web_near.mjs <chromium> <aegean.html> <scratch/output-dir>
// WEB_NEAR_GPU=native uses headless ANGLE/Vulkan; default is SwiftShader.
import {spawn, execFileSync} from 'node:child_process';
import {mkdirSync, mkdtempSync, readFileSync, writeFileSync, rmSync} from 'node:fs';
import {resolve, join} from 'node:path';
import assert from 'node:assert/strict';

const [chrome, pageArg, outArg] = process.argv.slice(2);
assert(chrome && pageArg && outArg, 'chromium, built page and scratch output directory required');
const page=resolve(pageArg), out=resolve(outArg);
readFileSync(page); mkdirSync(out,{recursive:true});
const profile=mkdtempSync(join(out,'chromium-'));
const gpu=process.env.WEB_NEAR_GPU==='native'
  ? ['--use-angle=vulkan','--enable-features=Vulkan','--disable-vulkan-surface']
  : ['--enable-unsafe-swiftshader','--use-angle=swiftshader'];
const env={...process.env};delete env.DISPLAY;delete env.WAYLAND_DISPLAY;
const browser=spawn(chrome,['--headless=new','--no-sandbox','--mute-audio','--allow-file-access-from-files',
  '--remote-debugging-port=0',`--user-data-dir=${profile}`,'--window-size=1280,720',...gpu,'about:blank'],
  {env,stdio:['ignore','ignore','pipe']});
let stderr='', ws, seq=0, loaded=false;const pending=new Map(), errors=[];
browser.stderr.on('data',d=>stderr+=d);
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function until(test,limit=120000) {
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
  await send('Emulation.setDeviceMetricsOverride',{width:1280,height:720,deviceScaleFactor:1,mobile:false});
  await send('Page.addScriptToEvaluateOnNewDocument',{source:`
    window.quayFrames=0;window.quayLinks=[];
    const raf=requestAnimationFrame;
    window.requestAnimationFrame=cb=>raf(t=>{if(quayFrames>=180)return;cb(t);quayFrames++;});
    const proto=WebGL2RenderingContext.prototype,link=proto.linkProgram;
    proto.linkProgram=function(p){link.call(this,p);quayLinks.push(this.getProgramParameter(p,this.LINK_STATUS));};
  `});
  const results=[];
  for(const [quality,full] of [['low',false],['medium',false],['medium',true]]) {
    const name=`${quality}-${full?'full-log':'split'}`;
    const query=new URLSearchParams({SLOPPY_NO_AUDIO:'1',SLOPPY_THREADS:'1',SLOPPY_SEED:'12345',
      AEGEAN_CAPTURE_READY:'1',AEGEAN_HOUR:'9.75',AEGEAN_QUALITY:quality,AEGEAN_STRESS_FRAME_DT:String(1/60)});
    if(full)query.set('AEGEAN_FULL_LOG_DEPTH','1');
    errors.length=0;loaded=false;
    await send('Page.navigate',{url:'file://'+page+'?'+query});
    await until(()=>loaded);
    await until(async()=>{
      const r=await send('Runtime.evaluate',{returnByValue:true,expression:'globalThis.quayFrames||0'});
      return r.result?.value>=180;
    });
    const links=(await send('Runtime.evaluate',{returnByValue:true,expression:'quayLinks'})).result.value;
    assert(links.length>20 && links.every(Boolean),`${name}: shaders did not link`);
    assert.equal(errors.length,0,`${name}: JavaScript exception`);
    const shot=await send('Page.captureScreenshot',{format:'png'}), file=join(out,name+'.png');
    writeFileSync(file,Buffer.from(shot.data,'base64'));
    // Fixed daylight/seed/camera. Two boxes avoid the figure, aircraft and HUD.
    // Warm limestone distinguishes the actual quay from the blue-green water below it.
    // A separate sea box rejects blank/solid-color captures and globally missing water.
    const metrics=JSON.parse(execFileSync('python3',['-c',`
import json,sys
from PIL import Image
im=Image.open(sys.argv[1]).convert('RGB');w,h=im.size
result={}
for name,box in [('under_feet',(.47,.77,.54,.82)),('in_front',(.54,.66,.58,.73)),('sea',(.40,.29,.70,.36))]:
 x0,y0,x1,y1=[int(v*d) for v,d in zip(box,[w,h,w,h])]
 pixels=[im.getpixel((x,y)) for y in range(y0,y1) for x in range(x0,x1)]
 result[name]=sum((r>b*1.2 and g>b*1.15) if name!='sea' else (b>r*1.2 and g>r*1.15) for r,g,b in pixels)/len(pixels)
print(json.dumps(result))
`,file],{encoding:'utf8'}));
    const result={name,frames:180,linkedPrograms:links.length,...metrics};results.push(result);
    writeFileSync(join(out,'results.json'),JSON.stringify(results,null,2)+'\n');
    console.log(JSON.stringify(result));
    assert(metrics.under_feet>.95 && metrics.in_front>.95 && metrics.sea>.95,`${name}: quay/sea coverage regression`);
  }
  console.log('PASS: quay under/in front of the walker survives both WebGL depth paths');
} finally {
  ws?.close();
  const exited=new Promise(r=>browser.once('exit',r));
  if(browser.exitCode===null){browser.kill();const guard=setTimeout(()=>browser.kill('SIGKILL'),5000);await exited;clearTimeout(guard);}
  rmSync(profile,{recursive:true,force:true});
}
