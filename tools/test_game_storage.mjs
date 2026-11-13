// Real IndexedDB transaction/reload/budget probe; no game renderer, server or external package.
// node tools/test_game_storage.mjs CHROME SCRATCH
import {spawn} from 'node:child_process';
import {readFileSync,writeFileSync,mkdirSync,mkdtempSync} from 'node:fs';
import {resolve,join} from 'node:path';
const [chrome,scratch]=process.argv.slice(2);if(!chrome||!scratch)throw Error('CHROME SCRATCH required');
mkdirSync(scratch,{recursive:true});const profile=mkdtempSync(join(resolve(scratch),'idb-profile-'));
const source=readFileSync(new URL('../src/web_compat.js',import.meta.url),'utf8').split('// Game slot storage (independent of graphics).')[1];
if(!source)throw Error('Missing storage source');
const file=join(resolve(scratch),'game-storage.html');writeFileSync(file,'<!doctype html><title>Game storage test</title><script>'+source+'</script>');
const child=spawn(chrome,['--headless','--no-sandbox','--disable-gpu','--mute-audio','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank']);
let stderr='';child.stderr.on('data',d=>stderr+=d);const delay=ms=>new Promise(r=>setTimeout(r,ms));let ws;
try {
 const start=Date.now();while(!/DevTools listening on (ws:\S+)/.test(stderr)){if(Date.now()-start>15000)throw Error(stderr);await delay(50);}
 const port=new URL(stderr.match(/DevTools listening on (ws:\S+)/)[1]).port;
 const page=(await(await fetch(`http://127.0.0.1:${port}/json`)).json()).find(t=>t.type==='page');
 ws=new WebSocket(page.webSocketDebuggerUrl);await new Promise(r=>ws.addEventListener('open',r));let id=0;const waiting=new Map();
 ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id&&waiting.has(m.id)){waiting.get(m.id)(m);waiting.delete(m.id);}});
 const send=(method,params={})=>new Promise(r=>{const n=++id;waiting.set(n,r);ws.send(JSON.stringify({id:n,method,params}));});
 await send('Page.enable');await send('Runtime.enable');await send('Page.navigate',{url:'file://'+file});await delay(500);
 const expression=`(async()=>{
  const assert=(ok,why)=>{if(!ok)throw Error(why)};
  const Store=AegeanSlots.GameSlotStore,name='game-slots-acceptance',store=new Store(indexedDB,name);
  await store.open();const before=localStorage.length,size=4558153;
  const body=new Uint8Array(size);for(let i=0;i<size;i+=65536)crypto.getRandomValues(body.subarray(i,Math.min(size,i+65536)));
  const digest=async b=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',b))).join(',');
  const expected=await digest(body);
  for(let slot=0;slot<3;slot++){
   await store.write(slot,0,'header-'+slot+'-1',body,1,0);
   await store.write(slot,1,'header-'+slot+'-2',body,2,1);
  }
  store.db.close();const reopened=new Store(indexedDB,name);await reopened.open();
  assert(reopened.headers.size===6,'all slot headers survive reopen');
  for(let slot=0;slot<3;slot++){
   const banks=await reopened.read(slot);assert(banks.length===2,'two banks');
   for(let bank=0;bank<2;bank++){assert(banks[bank].generation===bank+1,'generation');assert(await digest(banks[bank].body)===expected,'exact month-size bytes');}
  }
  let stale=false;try{await reopened.write(0,0,'stale',body,3,1)}catch{stale=true;}assert(stale,'stale tab refused');
  // Abort after the body request, before the header request. The original pair must survive.
  const original=reopened.db.transaction.bind(reopened.db);
  reopened.db.transaction=(...args)=>{
   const tx=original(...args);if(args[1]!=='readwrite')return tx;
   const objectStore=tx.objectStore.bind(tx);tx.objectStore=name=>{
    const s=objectStore(name);if(name==='banks'){
     const put=s.put.bind(s);s.put=(...values)=>{const request=put(...values);tx.abort();return request;};
    }return s;
   };return tx;
  };
  let refused=false;try{await reopened.write(0,0,'must-not-commit',body,3,2)}catch{refused=true;}
  reopened.db.transaction=original;assert(refused,'aborted write refused');
  const intact=await reopened.read(0);assert(intact[0].text==='header-0-1'&&intact[1].text==='header-0-2','atomic abort retained both headers');
  assert(await digest(intact[0].body)===expected,'atomic abort retained body');
  const estimate=await navigator.storage.estimate();assert(localStorage.length===before,'no localStorage growth');
  await reopened.delete(1);assert((await reopened.read(1)).every(v=>v===undefined),'both generations deleted');
  assert((await reopened.read(0))[1].generation===2&&(await reopened.read(2))[1].generation===2,'other slots preserved');
  let denied=false;try{await new Store(null).open()}catch{denied=true;}assert(denied,'unavailable browser storage is an error');
  reopened.db.close();return {pass:true,slots:3,banks:6,bodyBytes:size,totalBodyBytes:size*6,localStorageGrowth:localStorage.length-before,estimate};
 })()`;
 const result=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});
 if(result.result?.exceptionDetails)throw Error(JSON.stringify(result.result.exceptionDetails));
 const value=result.result?.result?.value;if(!value?.pass)throw Error(JSON.stringify(result));console.log(JSON.stringify(value,null,2));
}finally{ws?.close();child.kill();await new Promise(r=>child.once('exit',r));}
