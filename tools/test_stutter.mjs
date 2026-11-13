// One real-game browser trace. Build tools/stutter_trace.jo --release --target wasm.
// Usage: node tools/test_stutter.mjs CHROMIUM PAGE.html OUTPUT [TOWN] [fly|stay]
// Timings: redfox under bench.lock; STUTTER_PROFILE=1 enables attribution only.
// Default is a 60-second stationary gate, audio running with muted output.
import {spawn} from 'node:child_process';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {join,resolve} from 'node:path';
const [chrome,page,out,town='Olythoria',mode='stay']=process.argv.slice(2);
if(!chrome||!page||!out)throw new Error('Expected CHROMIUM PAGE.html OUTPUT [TOWN] [fly|stay]');
readFileSync(page);const profile=mkdtempSync(join(out,'profile-'));let browser,ws;
const logs=[],errors=[];let stderr='',id=0;const pending=new Map();let complete;
const done=new Promise(r=>complete=r);let ready;
const listening=new Promise(r=>ready=r);
browser=spawn(chrome,['--headless=new','--no-sandbox','--mute-audio','--autoplay-policy=no-user-gesture-required','--allow-file-access-from-files','--use-angle=vulkan','--enable-features=Vulkan','--disable-vulkan-surface','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{env:{...process.env,DISPLAY:undefined,WAYLAND_DISPLAY:undefined},stdio:['ignore','ignore','pipe']});
browser.on('error',error=>complete({error:String(error)}));
browser.stderr.on('data',d=>{stderr+=d;if(/DevTools listening on (ws:\S+)/.test(stderr))ready()});
const timeout=setTimeout(()=>complete({timeout:true}),240000);
try{
 await Promise.race([listening,done.then(r=>{throw new Error(JSON.stringify(r))})]);const port=new URL(stderr.match(/DevTools listening on (ws:\S+)/)[1]).port;
 const tab=(await(await fetch(`http://127.0.0.1:${port}/json`)).json()).find(t=>t.type==='page');
 ws=new WebSocket(tab.webSocketDebuggerUrl);await new Promise(r=>ws.addEventListener('open',r,{once:true}));
 ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){const [a,b]=pending.get(m.id);pending.delete(m.id);m.error?b(m.error):a(m.result)}
 if(m.method==='Runtime.exceptionThrown')errors.push(m.params);
 if(m.method==='Runtime.consoleAPICalled'){const s=m.params.args.map(x=>x.value??x.description).join(' ');logs.push(s);if(m.params.type==='error')errors.push(s);if(s.includes('STUTTER_END'))complete({end:s})}});
 const send=(method,params={})=>new Promise((a,b)=>{const n=++id;pending.set(n,[a,b]);ws.send(JSON.stringify({id:n,method,params}))});
 await send('Runtime.enable');await send('Page.enable');await send('Emulation.setDeviceMetricsOverride',{width:1280,height:720,deviceScaleFactor:1,mobile:false});
 await send('Page.addScriptToEvaluateOnNewDocument',{source:`window.stutterProbe={frames:[],warp:0,finish:0,links:[]};const p=stutterProbe,raf=requestAnimationFrame,log=console.log;window.requestAnimationFrame=cb=>raf(t=>{const start=performance.now();cb(t);p.frames.push([t,start,performance.now()])});console.log=(...args)=>{const s=args.join(' ');if(s.includes('STUTTER_WARP'))p.warp=performance.now();if(s.includes('STUTTER_END'))p.finish=performance.now();log.apply(console,args)};const gl=WebGL2RenderingContext.prototype,link=gl.linkProgram;gl.linkProgram=function(prog){link.call(this,prog);p.links.push(this.getProgramParameter(prog,this.LINK_STATUS))};`});
 if(process.env.STUTTER_PROFILE==='1'){await send('Profiler.enable');await send('Profiler.setSamplingInterval',{interval:1000});await send('Profiler.start')}
 const q=new URLSearchParams({SLOPPY_NO_AUDIO:'1',SLOPPY_THREADS:'1',SLOPPY_SEED:'12345',AEGEAN_QUALITY:'low',AEGEAN_RUNTIME_TRACE:'1',STUTTER_TOWN:town,STUTTER_MODE:mode,STUTTER_WARMUP:process.env.STUTTER_WARMUP??'30',STUTTER_SECONDS:'60'});
 if(process.env.STUTTER_AUDIO!=='0')q.delete('SLOPPY_NO_AUDIO');
 if(process.env.STUTTER_AGL)q.set('STUTTER_AGL',process.env.STUTTER_AGL);
 await send('Page.navigate',{url:'file://'+resolve(page)+'?'+q});
 const result=await done;
 if(process.env.STUTTER_PROFILE==='1')writeFileSync(join(out,'cpu.json'),JSON.stringify(await send('Profiler.stop')));
 const probe=(await send('Runtime.evaluate',{expression:'stutterProbe',returnByValue:true})).result.value;
 writeFileSync(join(out,'frames.json'),JSON.stringify({result,probe,errors},null,2));writeFileSync(join(out,'console.log'),logs.join('\n'));writeFileSync(join(out,'chrome.log'),stderr);
 const shot=await send('Page.captureScreenshot',{format:'png'});writeFileSync(join(out,'end.png'),Buffer.from(shot.data,'base64'));
 console.log(JSON.stringify({result,errors,frames:probe.frames.length,warp:probe.warp,finish:probe.finish,linked:probe.links.filter(Boolean).length,programs:probe.links.length}));
 const over=Number(result.end?.match(/over50=(\d+)/)?.[1]??-1);
 if(result.timeout||errors.length||probe.links.some(x=>!x)||over!==0)process.exitCode=1;
}finally{clearTimeout(timeout);ws?.close();const exited=new Promise(r=>browser.once('exit',r));if(browser.exitCode===null){browser.kill();const guard=setTimeout(()=>browser.kill('SIGKILL'),5000);await exited;clearTimeout(guard)}rmSync(profile,{recursive:true,force:true})}
