// Exercise the compiled full-game save probe in a fresh, persistent browser profile.
// node tools/run_game_save_web.mjs CHROME PAGE.html SCRATCH [QUERY]
import {spawn} from 'node:child_process';
import {mkdirSync,mkdtempSync,writeFileSync} from 'node:fs';
import {resolve,join} from 'node:path';
const [chrome,page,scratch,query='']=process.argv.slice(2);mkdirSync(scratch,{recursive:true});
const profile=mkdtempSync(join(resolve(scratch),'save-web-'));
const child=spawn(chrome,['--headless','--no-sandbox','--mute-audio','--enable-unsafe-swiftshader','--use-angle=swiftshader','--remote-debugging-port=0',`--user-data-dir=${profile}`,'--window-size=640,360','about:blank']);
const delay=ms=>new Promise(r=>setTimeout(r,ms));let stderr='',ws;child.stderr.on('data',d=>stderr+=d);
let timer;
try{
 const start=Date.now();while(!/DevTools listening on (ws:\S+)/.test(stderr)){if(Date.now()-start>15000)throw Error(stderr);await delay(50);}
 const port=new URL(stderr.match(/DevTools listening on (ws:\S+)/)[1]).port;
 const target=(await(await fetch(`http://127.0.0.1:${port}/json`)).json()).find(t=>t.type==='page');
 ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise(r=>ws.addEventListener('open',r));let id=0;const waiting=new Map();
 const send=(method,params={})=>new Promise(r=>{const n=++id;waiting.set(n,r);ws.send(JSON.stringify({id:n,method,params}));});
 let success,fail;const done=new Promise((r,j)=>{success=r;fail=j;});
 timer=setTimeout(()=>fail(Error('Game-save browser probe timed out')),240000);
 ws.addEventListener('message',event=>{
  const m=JSON.parse(event.data);if(m.id&&waiting.has(m.id)){waiting.get(m.id)(m.result);waiting.delete(m.id);}
  if(m.method==='Runtime.consoleAPICalled'){
   const line=m.params.args.map(x=>x.value??x.description).join(' ');console.log(line);
   if(line.includes('GAME_SAVE_PROBE PASS'))success(line);
   if(/panic:|assertion failed|\[living recovery\]/i.test(line))fail(Error(line));
  }
  if(m.method==='Runtime.exceptionThrown')fail(Error(JSON.stringify(m.params.exceptionDetails)));
 });
 await send('Runtime.enable');await send('Page.enable');
 await send('Emulation.setDeviceMetricsOverride',{width:640,height:360,deviceScaleFactor:1,mobile:false});
 await send('Page.navigate',{url:'file://'+resolve(page)+'?SLOPPY_NO_AUDIO=1&AEGEAN_QUALITY=low&AEGEAN_STRESS_FRAME_DT=0.0166666666667&'+query});
 await done;clearTimeout(timer);
 const storage=await send('Runtime.evaluate',{expression:'navigator.storage.estimate().then(e=>({indexedDB:e.usage,localStorageKeys:localStorage.length,wasmBytes:sloppy.memory().buffer.byteLength}))',awaitPromise:true,returnByValue:true});
 console.log('WEB_SAVE_STORAGE',JSON.stringify(storage?.result?.value));
 const shot=await send('Page.captureScreenshot',{format:'png'});if(shot?.data)writeFileSync(join(resolve(scratch),'save-web.png'),Buffer.from(shot.data,'base64'));
}finally{clearTimeout(timer);ws?.close();child.kill();await new Promise(r=>child.once('exit',r));}
