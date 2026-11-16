// The afterglow's shaders link before dusk, not at it. Opens a built page (high tier) in headless
// Chromium a little before the sky begins to glow, with the day running fast, and records every
// WebGL program link and every frame. Passes when the glow's shaders were queued before the sky
// began to glow and no program links within a few frames of the first glowing one.
// Usage: node tools/test_web_afterglow.mjs CHROMIUM PAGE.html [OUTPUT.json]
// Build: sloppy build aegean.jo --target wasm --release --wasm-file -o DIR/index.html
import {spawn} from 'node:child_process';
import {writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {openPage} from './web_page.mjs';
const [chrome,page,out]=process.argv.slice(2);
if(!chrome||!page)throw new Error('Expected CHROMIUM PAGE.html [OUTPUT.json]');
const served=await openPage(page);
const profile=mkdtempSync(join(process.env.AEGEAN_SCRATCH??tmpdir(),'afterglow-'));
const errors=[];let stderr='',id=0;const pending=new Map();let complete;
const done=new Promise(r=>complete=r);let ready;const listening=new Promise(r=>ready=r);
const browser=spawn(chrome,['--headless=new','--no-sandbox','--mute-audio','--use-angle=vulkan','--enable-features=Vulkan','--disable-vulkan-surface','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{env:{...process.env,DISPLAY:undefined,WAYLAND_DISPLAY:undefined},stdio:['ignore','ignore','pipe']});
browser.on('error',error=>complete({error:String(error)}));
browser.stderr.on('data',d=>{stderr+=d;if(/DevTools listening on (ws:\S+)/.test(stderr))ready()});
const timeout=setTimeout(()=>complete({timeout:true}),300000);
let ws;
try{
  await Promise.race([listening,done.then(r=>{throw new Error(JSON.stringify(r))})]);
  const port=new URL(stderr.match(/DevTools listening on (ws:\S+)/)[1]).port;
  const tab=(await(await fetch(`http://127.0.0.1:${port}/json`)).json()).find(t=>t.type==='page');
  ws=new WebSocket(tab.webSocketDebuggerUrl);await new Promise(r=>ws.addEventListener('open',r,{once:true}));
  ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){const [a,b]=pending.get(m.id);pending.delete(m.id);m.error?b(m.error):a(m.result)}
    if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails?.text??'exception');
    if(m.method==='Runtime.consoleAPICalled'){const s=m.params.args.map(x=>x.value??x.description).join(' ');if(m.params.type==='error')errors.push(s)}});
  const send=(method,params={})=>new Promise((a,b)=>{const n=++id;pending.set(n,[a,b]);ws.send(JSON.stringify({id:n,method,params}))});
  await send('Runtime.enable');await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride',{width:1280,height:720,deviceScaleFactor:1,mobile:false});
  // (every frame's start, every link and the game's AFTERGLOW lines, on one clock)
  await send('Page.addScriptToEvaluateOnNewDocument',{source:`window.glowProbe={frames:[],links:[],marks:[]};const p=glowProbe,raf=requestAnimationFrame,log=console.log;
window.requestAnimationFrame=cb=>raf(t=>{p.frames.push(performance.now());cb(t)});
console.log=(...a)=>{const s=a.join(' ');if(s.startsWith('AFTERGLOW_'))p.marks.push([performance.now(),s]);log.apply(console,a)};
const gl=WebGL2RenderingContext.prototype,link=gl.linkProgram;gl.linkProgram=function(prog){const t=performance.now();link.call(this,prog);p.links.push([t,performance.now()-t])};`});
  // (the free camera off the home harbour, looking west at 15:45; the day runs at an hour in 20 s,
  // so the sky begins to glow, at about 16:26, some 15 s in)
  const q=new URLSearchParams({AEGEAN_TITLE:'0',SLOPPY_NO_AUDIO:'1',SLOPPY_SEED:'12345',AEGEAN_QUALITY:process.env.GLOW_QUALITY??'high',
    AEGEAN_VIEW:'447 111 -6052 1.5708 -0.05 15.75',AEGEAN_HOUR_RATE:'0.05',AEGEAN_GLOW_LOG:'1'});
  await send('Page.navigate',{url:served.url+'?'+q});
  const until=Date.now()+150000;let probe;
  for(;;){
    await new Promise(r=>setTimeout(r,2000));
    probe=(await send('Runtime.evaluate',{expression:'window.glowProbe',returnByValue:true})).result.value;
    const on=probe?.marks.find(m=>m[1].startsWith('AFTERGLOW_ON'));
    if(on&&probe.frames.filter(f=>f>on[0]).length>60)break;
    if(Date.now()>until){complete({timeout:true});break}
  }
  const on=probe.marks.find(m=>m[1].startsWith('AFTERGLOW_ON')),queued=probe.marks.find(m=>m[1].startsWith('AFTERGLOW_QUEUED'));
  // (the frames round the first glowing one: from three before to three after)
  const at=probe.frames.findIndex(f=>f>=on[0]);
  const lo=probe.frames[Math.max(at-3,0)],hi=probe.frames[Math.min(at+4,probe.frames.length-1)];
  const near=probe.links.filter(l=>l[0]>=lo&&l[0]<=hi);
  const between=queued?probe.links.filter(l=>l[0]>=queued[0]&&l[0]<on[0]).length:0;
  const result={queued:queued?.[1]??null,on:on[1],linksBetweenQueueAndGlow:between,linksNearGlow:near.length,
    nearGlowMs:near.map(l=>+l[1].toFixed(1)),linksTotal:probe.links.length,frames:probe.frames.length,errors};
  console.log(JSON.stringify(result,null,1));
  if(out)writeFileSync(out,JSON.stringify({result,probe},null,1));
  const high=(process.env.GLOW_QUALITY??'high')==='high';
  if(errors.length||near.length>0||(high&&(!queued||queued[0]>on[0]||between<4)))process.exitCode=1;
}finally{clearTimeout(timeout);ws?.close();await served.close();const exited=new Promise(r=>browser.once('exit',r));if(browser.exitCode===null){browser.kill();const g=setTimeout(()=>browser.kill('SIGKILL'),5000);await exited;clearTimeout(g)}rmSync(profile,{recursive:true,force:true})}
