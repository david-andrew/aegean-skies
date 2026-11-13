// Render real close-camera scenes: quay, moving streets, far port, cockpit, orbit and cloud.
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
  await send('Emulation.setDeviceMetricsOverride',{width:1280,height:720,deviceScaleFactor:1,mobile:false});
  await send('Page.addScriptToEvaluateOnNewDocument',{source:`
    window.quayFrames=0;window.quayLinks=[];window.nearLimit=30;window.nearPending=null;
    const raf=requestAnimationFrame;
    const schedule=cb=>raf(t=>{if(quayFrames>=nearLimit){nearPending=()=>schedule(cb);return;}cb(t);quayFrames++;});
    window.requestAnimationFrame=schedule;
    window.nearAdvance=n=>{nearLimit=n;const next=nearPending;nearPending=null;if(next)next();};
    const proto=WebGL2RenderingContext.prototype,link=proto.linkProgram;
    proto.linkProgram=function(p){link.call(this,p);quayLinks.push(this.getProgramParameter(p,this.LINK_STATUS));};
  `});
  const extraScenes=[
    {id:'street',env:{AEGEAN_AT:'516.177 -6334.7266 2.0527',SLOPPY_INPUT:'60:w+ 239:w-'}},
    {id:'pheryalara',env:{AEGEAN_AT:'14263.08 -170005.45 -1.176',SLOPPY_INPUT:'60:w+ 239:w-'}},
    {id:'cockpit',env:{AEGEAN_ABOARD:'1',SLOPPY_INPUT:'60:v+ 61:v-'}},
    {id:'orbit',env:{AEGEAN_CAPTURE_ORBIT:'9 0.8 0.35'}},
    {id:'cloud',env:{AEGEAN_FLYING:'950 190',AEGEAN_WEATHER:'overcast',SLOPPY_INPUT:'60:v+ 61:v-'}}
  ];
  const cases=[...['low','medium'].map(quality=>({quality,full:false,id:'quay',env:{}})),{quality:'medium',full:true,id:'quay',env:{}},
    ...extraScenes.flatMap(scene=>[false,true].map(full=>({...scene,quality:'medium',full})))];
  const selected=process.env.WEB_NEAR_CASES?.split(',');
  const results=[];
  for(const {quality,full,id,env:sceneEnv} of cases.filter(c=>(!selected||selected.includes(c.id))&&(!process.env.WEB_NEAR_LINEAR||!c.full))) {
    const name=`${id}-${quality}-${process.env.WEB_NEAR_LINEAR?'linear':full?'full-log':'split'}`;
    const query=new URLSearchParams({SLOPPY_NO_AUDIO:'1',SLOPPY_THREADS:'1',SLOPPY_SEED:'12345',
      AEGEAN_CAPTURE_READY:'1',AEGEAN_HOUR:'9.75',AEGEAN_QUALITY:quality,AEGEAN_STRESS_FRAME_DT:String(1/60),SLOPPY_FRAMES:'241',...sceneEnv});
    if(process.env.WEB_NEAR_LINEAR)query.set('AEGEAN_LINEAR_DEPTH','1');
    if(full)query.set('AEGEAN_FULL_LOG_DEPTH','1');
    errors.length=0;loaded=false;
    await send('Page.navigate',{url:'file://'+page+'?'+query});
    await until(()=>loaded);
    await until(async()=>{
      const r=await send('Runtime.evaluate',{returnByValue:true,expression:'globalThis.quayFrames||0'});
      return r.result?.value>=30;
    });
    for(const frame of [180,240]) {
      await send('Runtime.evaluate',{expression:`nearAdvance(${frame})`});
      await until(async()=>{const r=await send('Runtime.evaluate',{returnByValue:true,expression:'quayFrames'});return r.result?.value>=frame;});
      const links=(await send('Runtime.evaluate',{returnByValue:true,expression:'quayLinks'})).result.value;
      assert(links.length>20 && links.every(Boolean),`${name}: shaders did not link`);
      assert.equal(errors.length,0,`${name}: JavaScript exception`);
      const shot=await send('Page.captureScreenshot',{format:'png'}), file=join(out,name+'-'+frame+'.png');
      writeFileSync(file,Buffer.from(shot.data,'base64'));
      // Semantic regions prevent two equally broken paths from passing the comparison.
      // Warm ground differs from water; cockpit roof/panel and cloudy windshield are separate.
      const metrics=JSON.parse(execFileSync('python3',['-c',`
import json,sys
from PIL import Image
im=Image.open(sys.argv[1]).convert('RGB');w,h=im.size
result={}
boxes={'under_feet':(.47,.77,.54,.82),'in_front':(.54,.66,.58,.73),
 'sea':(.40,.29,.70,.36),'roof':(.42,.05,.58,.20),
 'airframe':(.46,.44,.49,.62),'panel':(.45,.64,.55,.70),'mist':(.43,.47,.55,.53)}
for name,box in boxes.items():
 x0,y0,x1,y1=[int(v*d) for v,d in zip(box,[w,h,w,h])]
 pixels=[im.getpixel((x,y)) for y in range(y0,y1) for x in range(x0,x1)]
 result[name]=sum((r>b*1.2 and g>b*1.15) if name!='sea' else (b>r*1.2 and g>r*1.15) for r,g,b in pixels)/len(pixels)
print(json.dumps(result))
`,file],{encoding:'utf8'}));
      const result={name,id,quality,full,frame,file,linkedPrograms:links.length,...metrics};results.push(result);
      writeFileSync(join(out,'results.json'),JSON.stringify(results,null,2)+'\n');
      console.log(JSON.stringify(result));
      if(['quay','street','pheryalara'].includes(id))
        assert(metrics.under_feet>.95 && metrics.in_front>.95,`${name}: ground coverage regression`);
      if(id==='quay')assert(metrics.sea>.95,`${name}: sea control regression`);
      if(['cockpit','cloud'].includes(id))assert(metrics.roof>.95 && metrics.panel>.65,`${name}: cockpit foreground missing`);
      if(id==='orbit')assert(metrics.airframe>.9,`${name}: nearby airframe missing`);
      if(id==='cloud')assert(metrics.mist>.9,`${name}: cloud volume missing`);
    }
  }
  // Optimized bounded-near + far-log rendering must agree with all-fragment log depth.
  const comparisons=[];
  for(const full of results.filter(r=>r.full)) {
    const split=results.find(r=>r.id===full.id && r.quality===full.quality && r.frame===full.frame && !r.full);
    assert(split,`missing split reference for ${full.name}`);
    const diff=JSON.parse(execFileSync('python3',['-c',`
import json,sys
from PIL import Image,ImageChops,ImageStat
im=ImageChops.difference(Image.open(sys.argv[1]).convert('RGB'),Image.open(sys.argv[2]).convert('RGB'))
pixels=list(im.getdata())
print(json.dumps({'mean_rgb_error':sum(ImageStat.Stat(im).mean)/3,'changed_over_16':sum(max(p)>16 for p in pixels)/len(pixels)}))
`,split.file,full.file],{encoding:'utf8'}));
    comparisons.push({id:full.id,frame:full.frame,...diff});
    assert(diff.mean_rgb_error<1.0 && diff.changed_over_16<0.01,`${full.name}: split/full depth disagreement ${JSON.stringify(diff)}`);
  }
  writeFileSync(join(out,'comparisons.json'),JSON.stringify(comparisons,null,2)+'\n');
  console.log('PASS: close-camera coverage and split/full WebGL depth comparisons');
} finally {
  ws?.close();
  const exited=new Promise(r=>browser.once('exit',r));
  if(browser.exitCode===null){browser.kill();const guard=setTimeout(()=>browser.kill('SIGKILL'),5000);await exited;clearTimeout(guard);}
  rmSync(profile,{recursive:true,force:true});
}
