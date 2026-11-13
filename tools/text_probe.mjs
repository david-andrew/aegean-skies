// Silent deterministic WebGL capture / resolution-cost probe. One browser at a time.
// node tools/text_probe.mjs CHROME PAGE.html OUT_PREFIX [frames=180] [query]
// TEXT_GPU=native: ANGLE/Vulkan on redfox; otherwise SwiftShader compatibility only.
// TEXT_MOBILE=1: 844x390 CSS, DPR3. TEXT_WIDTH/HEIGHT/DPR override metrics.
// No actual phone-performance claim.
import {spawn} from 'node:child_process';
import {mkdtempSync,writeFileSync,rmSync} from 'node:fs';
import {dirname,join} from 'node:path';
const [chrome,page,out,frames='180',query='']=process.argv.slice(2);
const profile=mkdtempSync(join(dirname(out),'text-browser-'));
const gpu=process.env.TEXT_GPU==='native' ? ['--use-angle=vulkan','--enable-features=Vulkan','--disable-vulkan-surface'] : ['--use-angle=swiftshader','--enable-unsafe-swiftshader'];
const browser=spawn(chrome,['--headless=new','--no-sandbox','--mute-audio','--allow-file-access-from-files',...gpu,'--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{stdio:['ignore','ignore','pipe']});
let rejectDeadline;
const deadline=new Promise((_,reject)=>rejectDeadline=reject);
const timeout=setTimeout(()=>rejectDeadline(Error('Browser probe exceeded 180 seconds')),180000);
let ws;
try {
 const endpoint=await new Promise((resolve,reject)=>{
  let log='';browser.stderr.on('data',d=>{log+=d;const m=log.match(/DevTools listening on (ws:\S+)/);if(m)resolve(m[1]);});browser.once('exit',c=>reject(Error('Browser exited '+c)));
 });
 const target=(await(await fetch(`http://127.0.0.1:${new URL(endpoint).port}/json`)).json()).find(t=>t.type==='page');
 ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise(r=>ws.addEventListener('open',r));
 let id=0;const pending=new Map(),logs=[];let done;
 const finished=Promise.race([new Promise(r=>done=r),deadline]);
 ws.addEventListener('message',event=>{
  const m=JSON.parse(event.data);
  if(m.id){const p=pending.get(m.id);pending.delete(m.id);if(m.error)p.reject(Error(JSON.stringify(m.error)));else p.resolve(m.result);}
  if(m.method==='Runtime.consoleAPICalled'){
   const line=m.params.args.map(a=>a.value??a.description).join(' ');logs.push(line);
   if(line==='TEXT_PROBE_DONE')done();
  }
  if(m.method==='Runtime.exceptionThrown'){logs.push(JSON.stringify(m.params.exceptionDetails));done();}
 });
 const send=(method,params={})=>new Promise((resolve,reject)=>{const i=++id;pending.set(i,{resolve,reject});ws.send(JSON.stringify({id:i,method,params}));});
 await send('Runtime.enable');await send('Page.enable');
 const mobile=process.env.TEXT_MOBILE==='1';
 await send('Emulation.setDeviceMetricsOverride',{width:Number(process.env.TEXT_WIDTH||(mobile?844:1280)),height:Number(process.env.TEXT_HEIGHT||(mobile?390:720)),deviceScaleFactor:Number(process.env.TEXT_DPR||(mobile?3:1)),mobile});
 if(mobile){await send('Emulation.setTouchEmulationEnabled',{enabled:true,maxTouchPoints:5});await send('Emulation.setUserAgentOverride',{userAgent:'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/124 Mobile Safari/537.36'});}
 await send('Page.addScriptToEvaluateOnNewDocument',{source:`
  globalThis.textProbe={frames:[],allocations:[],errors:[],links:[],liveTextures:new Map(),liveDepth:new Map()};
  const p=WebGL2RenderingContext.prototype;
  for(const method of ['texImage2D','renderbufferStorage','deleteTexture','deleteRenderbuffer','linkProgram']){
   const original=p[method];p[method]=function(...a){
    const result=original.apply(this,a),q=textProbe;
    if(method==='texImage2D'&&typeof a[3]==='number'){
     const item={w:a[3],h:a[4],format:a[2],type:a[7]};q.allocations.push(item);q.liveTextures.set(this.getParameter(this.TEXTURE_BINDING_2D),item);
    }
    if(method==='renderbufferStorage')q.liveDepth.set(this.getParameter(this.RENDERBUFFER_BINDING),{w:a[2],h:a[3],format:a[1]});
    if(method==='deleteTexture')q.liveTextures.delete(a[0]);
    if(method==='deleteRenderbuffer')q.liveDepth.delete(a[0]);
    if(method==='linkProgram')q.links.push({ok:this.getProgramParameter(a[0],this.LINK_STATUS),log:this.getProgramInfoLog(a[0])});
    return result;
   };
  }
  const raf=requestAnimationFrame;let n=0;
  requestAnimationFrame=cb=>raf(()=>{
   if(n>=${Number(frames)})return;
   const gl=document.querySelector('canvas')?.getContext('webgl2');
   if(!gl){cb(n*1000/60);return;}
   const started=performance.now();cb(n*1000/60);const submitted=performance.now();gl.finish();
   textProbe.frames.push({n,cpu:submitted-started,total:performance.now()-started});
   if(++n>=${Number(frames)}){requestAnimationFrame=()=>0;textProbe.done=true;console.log('TEXT_PROBE_DONE');}
  });
  window.addEventListener('error',e=>textProbe.errors.push(String(e.error||e.message)));
 `});
 await send('Page.navigate',{url:'file://'+page+query});await finished;
 const result=await send('Runtime.evaluate',{returnByValue:true,expression:`(()=>{
  const p=textProbe,c=document.querySelector('canvas'),gl=c.getContext('webgl2'),ext=gl.getExtension('WEBGL_debug_renderer_info');
  return {...p,liveTextures:[...p.liveTextures.values()],liveDepth:[...p.liveDepth.values()],quality:AegeanWeb.quality,resolution:AegeanWeb.resolution,canvas:[c.width,c.height],context:gl.getContextAttributes(),renderer:gl.getParameter(ext?ext.UNMASKED_RENDERER_WEBGL:gl.RENDERER),wasmBytes:sloppy.memory().buffer.byteLength};
 })()`});
 if(result.exceptionDetails)throw Error(JSON.stringify(result.exceptionDetails));
 writeFileSync(out+'.json',JSON.stringify({host:process.env.HOSTNAME,...result.result.value,logs},null,2));
 const shot=await send('Page.captureScreenshot',{format:'png'});writeFileSync(out+'.png',Buffer.from(shot.data,'base64'));
 if(process.env.TEXT_RESIZE==='1') {
  const checks=[];
  for(const [width,height,deviceScaleFactor] of [[390,844,3],[844,390,3],[1280,720,1]]) {
   await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor,mobile});
   const r=await send('Runtime.evaluate',{returnByValue:true,expression:`(()=>{
    sloppy.res.fit();for(let i=0;i<3;i++)sloppy.frameNow();
    const c=document.querySelector('canvas'),g=c.getContext('webgl2');
    return {resolution:AegeanWeb.resolution,canvas:[c.width,c.height],error:g.getError(),liveTextures:textProbe.liveTextures.size,liveDepth:textProbe.liveDepth.size};
   })()`});checks.push({width,height,deviceScaleFactor,...r.result.value});
  }
  writeFileSync(out+'-resize.json',JSON.stringify(checks,null,2));
 }
 console.log('Saved '+out);
} finally {clearTimeout(timeout);ws?.close();if(browser.exitCode===null&&browser.signalCode===null){const exited=new Promise(r=>browser.once('exit',r));browser.kill();await exited;}rmSync(profile,{recursive:true,force:true});}
