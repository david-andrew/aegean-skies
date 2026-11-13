const assert = require('node:assert/strict');
const {livingStoreEncode:encode,livingStoreDecode:decode,installLivingStorage:install} = require('../src/web_compat.js');
for (const n of [0,1,2,3,7,15,16,47,48,49,255,8192,65537,2400000]) {
  const bytes=Buffer.alloc(n); for(let i=0;i<n;++i)bytes[i]=(i*73+(i>>>8))&255;
  const source=bytes.toString('base64'), packed=encode(source);
  assert.equal(decode(packed),source);
  if(n>=48)assert.equal(packed.length,Math.ceil(n*8/15)+`AS15:${n}:`.length);
  if(n>=48)assert.throws(()=>decode(packed.slice(0,-1)),/Truncated/);
}
assert.equal(decode(null),null);
assert.equal(decode('ordinary legacy base64'),'ordinary legacy base64');
for(const bad of ['AS15:-1:x','AS15:2:x','AS15:1:\u0100\u0100','AS15:1:\u8000','AS15:1:\u0001'])assert.throws(()=>decode(bad));
class Store { constructor(){this.values=new Map()} setItem(k,v){this.values.set(String(k),String(v))} getItem(k){return this.values.get(String(k))??null} }
install(Store.prototype); const get=Store.prototype.getItem; install(Store.prototype); assert.equal(get,Store.prototype.getItem);
const s=new Store(), b64=Buffer.alloc(400000,217).toString('base64');
s.setItem('sloppy:Aegean Skies/world-a-data',b64);
assert(s.values.get('sloppy:Aegean Skies/world-a-data').startsWith('AS15:'));
assert.equal(s.getItem('sloppy:Aegean Skies/world-a-data'),b64);
for(const key of ['sloppy:world-a','sloppy:options','foreign-world-a-data']){s.setItem(key,b64);assert.equal(s.values.get(key),b64);assert.equal(s.getItem(key),b64)}
s.values.set('sloppy:world-b-data',b64); assert.equal(s.getItem('sloppy:world-b-data'),b64);
// A quota refusal cannot damage the other bank. Backend exceptions still reach Sloppy's
// existing save_data failure/last-valid-bank policy.
class FullStore extends Store {setItem(k,v){if(k.endsWith('-b-data'))throw Error('quota');super.setItem(k,v)}}
install(FullStore.prototype);const full=new FullStore();full.setItem('sloppy:world-a-data',b64);
assert.throws(()=>full.setItem('sloppy:world-b-data',b64),/quota/);
assert.equal(full.getItem('sloppy:world-a-data'),b64);
console.log('Living binary browser storage: exact bytes, legacy reads, narrow keys, corruption and independent-bank failure passed');
