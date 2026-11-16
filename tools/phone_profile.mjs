// Profile a web build's startup (or a window of play) on the test phone's Chrome, with the wasm
// frames named from the module's sloppy_lines section (file, line, function of each call site).
// Prints self time by function and, for startup, the time under each top-level function call
// (init_<file> > the function it called: where the start goes).
//
// usage: node tools/phone_profile.mjs <page.html> [--query "AEGEAN_TITLE=1"] [--until first_frame|card_gone|<seconds>]
//          [--module local-copy.html (a URL page: its module, for the names)] [--top 40] [--under <function>] [--runs] [--cold] [--out profile.json]
//        node tools/phone_profile.mjs <page.html> --analyze profile.json   (again, from a saved profile)
// Hold the phone lock: flock -w 1200 ~/dev/tmp/phone.lock node tools/phone_profile.mjs ...
// (sampling every 1 ms costs some speed: the stages come out a little slower than tools/phone_run.mjs's)
import {execFileSync} from 'node:child_process';
import {writeFileSync, readFileSync} from 'node:fs';
import {openPage, pageModule} from './web_page.mjs';

const args = process.argv.slice(2);
const opt = (name, def) => { const i = args.indexOf('--' + name); return i >= 0 ? args[i + 1] : def; };
const page = args[0];
const flag2 = (name) => args.includes('--' + name);
const until = opt('until', 'first_frame'), top = Number(opt('top', 40));
const adb = (...a) => execFileSync('adb', a, {encoding: 'utf8'}).trim();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// each function's name: Chrome gives a wasm frame as its function's start (module offset), and the
// module's sloppy_lines section gives the call sites (module offsets) with their file, line and
// function; a function is named by the first call site inside its body (one without calls stays
// wasm-function[N])
const named = (() => {
  const b = pageModule(opt('module', page));
  let i = 8;
  const leb = () => { let r = 0, sh = 0, x; do { x = b[i++]; r += (x & 127) * 2 ** sh; sh += 7; } while (x & 128); return r; };
  const bodies = [];   // [start of the body after its size, end]
  while (i < b.length) {
    const id = b[i++], n = leb(), end = i + n;
    if (id === 10) { const count = leb(); for (let k = 0; k < count; k++) { const size = leb(); bodies.push([i, i + size]); i += size; } }
    i = end;
  }
  const sec = WebAssembly.Module.customSections(new WebAssembly.Module(b), 'sloppy_lines');
  if (!sec.length) throw Error('no sloppy_lines section');
  const s = new Uint8Array(sec[0]), dec = new TextDecoder();
  let j = 0;
  const num = () => { let x = 0, sh = 0, c; do { c = s[j++]; x += (c & 127) * 2 ** sh; sh += 7; } while (c & 128); return x; };
  const strs = () => { const n = num(), a = []; for (let k = 0; k < n; k++) { const l = num(); a.push(dec.decode(s.subarray(j, j + l))); j += l; } return a; };
  const files = strs(), fns = strs();
  const byStart = new Map();
  let o = 0, bi = 0;
  for (let n = num(); n > 0; n--) {
    o += num(); const f = num(), line = num(), fn = num();
    while (bi < bodies.length && bodies[bi][1] <= o) bi++;
    if (bi < bodies.length && o >= bodies[bi][0] && !byStart.has(bodies[bi][0])) byStart.set(bodies[bi][0], {file: files[f], line, fn: fns[fn]});
  }
  return byStart;
})();

const record = async () => {
  adb('shell', 'cmd', 'media_session', 'volume', '--stream', '3', '--set', '0');
  adb('shell', 'input', 'keyevent', 'KEYCODE_WAKEUP');
  adb('shell', 'wm', 'dismiss-keyguard');
  adb('shell', 'svc', 'power', 'stayon', 'usb');
  adb('shell', 'am', 'start', '-a', 'android.intent.action.VIEW', '-d', 'about:blank', '-p', 'com.android.chrome');
  adb('forward', 'tcp:9222', 'localabstract:chrome_devtools_remote');
  await sleep(1500);
  const served = /^https?:/.test(page) ? null : await openPage(page);
  const port = served ? new URL(served.url).port : 0;
  if (served) adb('reverse', `tcp:${port}`, `tcp:${port}`);
  const given = opt('query', '');
  const url = (served ? served.url.replace('127.0.0.1', 'localhost') : page) + '?' + (given ? given + '&' : '') + 'AEGEAN_FRAME_STATS=1&run=' + Date.now().toString(36);
  let target = (await (await fetch('http://localhost:9222/json')).json()).find((t) => t.type === 'page');
  if (!target) target = await (await fetch('http://localhost:9222/json/new?about:blank', {method: 'PUT'})).json();
  const ws = new WebSocket(`ws://localhost:9222/devtools/page/${target.id}`);
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
  let n = 0;
  const pend = new Map();
  ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pend.has(m.id)) { pend.get(m.id)(m.result ?? m.error); pend.delete(m.id); } };
  const send = (method, params = {}) => new Promise((r) => { const i = ++n; pend.set(i, r); ws.send(JSON.stringify({id: i, method, params})); });
  const evaluate = async (expr) => (await send('Runtime.evaluate', {expression: expr, returnByValue: true}))?.result?.value;
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Page.navigate', {url: 'about:blank'});
  await sleep(500);
  await send('Page.addScriptToEvaluateOnNewDocument', {source: `(() => {
    const P = window.__phone = {t0: performance.now(), stages: {}};
    const mark = (k) => { if (!(k in P.stages)) P.stages[k] = Math.round(performance.now() - P.t0); };
    const raf = window.requestAnimationFrame.bind(window);
    window.requestAnimationFrame = (cb) => raf((t) => { mark('first_frame'); cb(t); });
    addEventListener('DOMContentLoaded', () => new MutationObserver(() => {
      if (document.getElementById('aegean-loading')) mark('card'); else if ('card' in P.stages) mark('card_gone');
    }).observe(document.body, {childList: true}));
  })();`});
  // (--cold: the browser's cache emptied first, compiled wasm with it: a first visit)
  if (args.includes('--cold')) { await send('Network.enable'); await send('Network.clearBrowserCache'); }
  await send('Profiler.enable');
  await send('Profiler.setSamplingInterval', {interval: 1000});
  await send('Profiler.start');
  await send('Page.navigate', {url});
  const t0 = Date.now();
  let stages = {};
  for (;;) {
    await sleep(500);
    stages = JSON.parse(await evaluate('JSON.stringify(window.__phone ? window.__phone.stages : {})') || '{}');
    if (/^\d+$/.test(until) ? Date.now() - t0 > Number(until) * 1000 : until in stages) break;
    if (Date.now() - t0 > 300000) { console.log('phone_profile: gave up after 5 minutes', stages); break; }
  }
  const {profile} = await send('Profiler.stop');
  await send('Page.navigate', {url: 'about:blank'});
  ws.close();
  if (served) { adb('reverse', '--remove', `tcp:${port}`); await served.close(); }
  adb('shell', 'svc', 'power', 'stayon', 'false');
  if (opt('out', null)) writeFileSync(opt('out'), JSON.stringify(profile));
  return {profile, url, stages};
};
// (--analyze f.cpuprofile: a profile saved with --out, read again without the phone)
const {profile, url, stages} = opt('analyze', null) ? {profile: JSON.parse(readFileSync(opt('analyze'), 'utf8')), url: opt('analyze'), stages: {}} : await record();

// each node's frame named; the samples' stacks walked from leaf to root
const nodes = new Map(profile.nodes.map((nd) => [nd.id, nd]));
const parent = new Map();
for (const nd of profile.nodes) for (const c of nd.children || []) parent.set(c, nd.id);
const nameOf = (nd) => {
  const cf = nd.callFrame;
  if (/\.wasm/.test(cf.url) && /^wasm-function/.test(cf.functionName)) {
    // (Chrome's column is the body's start, after or at its size: try both)
    const f = named.get(cf.columnNumber) || named.get(cf.columnNumber - 1) || named.get(cf.columnNumber - 2) || named.get(cf.columnNumber + 1);
    return f ? f.fn : cf.functionName;
  }
  return (cf.functionName || '(anonymous)') + (cf.url && !/\.wasm/.test(cf.url) ? ' [js]' : '');
};
const names = new Map([...nodes.values()].map((nd) => [nd.id, nameOf(nd)]));
const dt = profile.timeDeltas;
const self = new Map();
let total = 0;
for (let k = 0; k < profile.samples.length; k++) {
  const id = profile.samples[k], ms = (dt[k] || 0) / 1000;
  total += ms;
  const nm = names.get(id);
  self.set(nm, (self.get(nm) || 0) + ms);
}
// top-level attribution: walk each sample's stack for the frame running the main file's top level,
// and the call site in it on the way down (the child frame's position in its parent is not kept by
// the profile, so this uses the parent node's own hottest position: approximate for wide frames)
const initNode = (id) => { let found = null; for (let at = id; at !== undefined; at = parent.get(at)) { if (/^init_/.test(names.get(at))) found = at; } return found; };
const childOf = (id, anc) => { let c = id; for (let at = id; at !== undefined && at !== anc; at = parent.get(at)) c = at; return c; };
const byChild = new Map();
for (let k = 0; k < profile.samples.length; k++) {
  const id = profile.samples[k], ms = (dt[k] || 0) / 1000;
  const init = initNode(id);
  if (init === null) continue;
  const c = init === id ? init : childOf(id, init);
  const key = names.get(init) + ' > ' + (c === init ? '(itself)' : names.get(c));
  byChild.set(key, (byChild.get(key) || 0) + ms);
}
// (--under <function>: the time under it, by the function it called, and its own)
const under = opt('under', null), byUnder = new Map();
if (under) for (let k = 0; k < profile.samples.length; k++) {
  const id = profile.samples[k], ms = (dt[k] || 0) / 1000;
  let u = null;
  for (let at = id; at !== undefined; at = parent.get(at)) if (names.get(at) === under) u = at;
  if (u === null) continue;
  const key = u === id ? '(itself)' : names.get(childOf(id, u));
  byUnder.set(key, (byUnder.get(key) || 0) + ms);
}
const show = (m, n) => [...m].sort((a, b) => b[1] - a[1]).slice(0, n).map(([k, v]) => `${v.toFixed(0).padStart(7)} ms  ${(100 * v / total).toFixed(1).padStart(5)}%  ${k}`).join('\n');
console.log(`phone_profile: ${url}\nstages ${JSON.stringify(stages)}\nsampled ${total.toFixed(0)} ms\n\n== self time by function\n${show(self, top)}\n\n== under the top level (init_* > the function it called)\n${show(byChild, top)}`);
if (under) console.log(`\n== under ${under}\n${show(byUnder, top)}`);
// (--runs: each function's longest unbroken stretch on the stack, ms, and when it began: a frame's
// hitch shows as one function's long run)
if (flag2('runs')) {
  const cur = new Map(), best = new Map();
  let at = 0;
  for (let k = 0; k < profile.samples.length; k++) {
    const ms = (dt[k] || 0) / 1000; at += ms;
    const on = new Set();
    for (let id = profile.samples[k]; id !== undefined; id = parent.get(id)) on.add(names.get(id));
    for (const [nm, run] of cur) if (!on.has(nm)) { const b = best.get(nm); if (!b || run.ms > b.ms) best.set(nm, run); cur.delete(nm); }
    for (const nm of on) { const r = cur.get(nm) || {ms: 0, from: at - ms}; r.ms += ms; cur.set(nm, r); }
  }
  for (const [nm, run] of cur) { const b = best.get(nm); if (!b || run.ms > b.ms) best.set(nm, run); }
  const rows = [...best].filter(([nm]) => !/^\(|^init_|wasm-to-js|^__wasm|^onAnim|^frame$|^run$|\[js\]$/.test(nm)).sort((a, b) => b[1].ms - a[1].ms).slice(0, top);
  console.log('\n== longest unbroken runs\n' + rows.map(([nm, r]) => `${r.ms.toFixed(0).padStart(7)} ms  at ${(r.from / 1000).toFixed(1).padStart(6)} s  ${nm}`).join('\n'));
}
process.exit(0);
