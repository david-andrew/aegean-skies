// Run a web build of the game on the test phone (USB, adb) in its Chrome, and report how it ran.
// Serves the page's folder from this process, makes it reachable on the phone with `adb reverse`,
// opens it in a Chrome tab over DevTools (adb forward of chrome_devtools_remote), and records:
// the boot stages (page load, the loading card gone = the title's first frame), shader failures,
// errors, the requestAnimationFrame cadence (fps, median/p95/max gaps), the game's FRAME_STATS lines
// (AEGEAN_FRAME_STATS=1 is added to the query), the JS heap, the battery temperature and the
// thermal status. The server and the port mappings end with the tool.
//
// usage: node tools/phone_run.mjs <page.html | URL> [--secs 60] [--warm 20] [--query "AEGEAN_X=1&..."]
//          [--out result.json] [--browser chrome|beta|chromium] [--keep] [--inject script.js] [--cold]
//   a URL (the Pages site) is opened as it is; a page file is served (index.html + index.wasm)
//   --warm: seconds after the loading card goes before the measured window of --secs starts
//   --keep: leave the tab open on the game afterwards (default: navigate it to about:blank)
// Hold the phone lock around it: flock -w 900 ~/dev/tmp/phone.lock node tools/phone_run.mjs ...
// One device is expected (adb devices); ADB_SERIAL / ANDROID_SERIAL pick another.
import {execFileSync} from 'node:child_process';
import {writeFileSync, readFileSync} from 'node:fs';
import {openPage} from './web_page.mjs';

const args = process.argv.slice(2);
const opt = (name, def) => { const i = args.indexOf('--' + name); return i >= 0 ? args[i + 1] : def; };
const flag = (name) => args.includes('--' + name);
const page = args[0];
if (!page || page.startsWith('--')) { console.error('usage: node tools/phone_run.mjs <page.html|URL> [--secs 60] [--warm 20] [--query ...] [--out f.json]'); process.exit(2); }
const secs = Number(opt('secs', 60)), warm = Number(opt('warm', 20)), out = opt('out', null);
const sockets = {chrome: 'chrome_devtools_remote', beta: 'chrome_devtools_remote', chromium: 'chrome_devtools_remote'};
const browser = opt('browser', 'chrome');
const packages = {chrome: 'com.android.chrome', beta: 'com.chrome.beta', chromium: 'org.chromium.chrome'};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const adb = (...a) => execFileSync('adb', a, {encoding: 'utf8'}).trim();
const devport = 9222 + ['chrome', 'beta', 'chromium'].indexOf(browser);

// the phone's state: battery temperature (C), the hottest CPU and GPU sensors and the skin/board
// ones (C, from /sys/class/thermal), the thermal status (0 none .. 6 shutdown) and the cooling
// devices' throttling steps (thermal-cpufreq-N: CPU cluster caps, thermal-devfreq-0: the GPU's)
const phoneState = () => {
  const bat = adb('shell', 'dumpsys', 'battery');
  const thermal = adb('shell', 'dumpsys', 'thermalservice');
  const zones = adb('shell', 'for z in /sys/class/thermal/thermal_zone*; do echo "$(cat $z/type) $(cat $z/temp)"; done 2>/dev/null');
  let cpu = -1e9, gpu = -1e9;
  const other = {};
  for (const line of zones.split('\n')) {
    const [name, v] = line.trim().split(/\s+/); const c = Number(v) / 1000;
    if (!name || !isFinite(c) || c < -40 || c > 150) continue;
    if (/^cpu-/.test(name)) cpu = Math.max(cpu, c);
    else if (/^gpuss/.test(name)) gpu = Math.max(gpu, c);
    else if (/skin|xo-therm|quiet|pa-therm/.test(name)) other[name] = c;
  }
  const caps = {};
  for (const m of thermal.matchAll(/CoolingDevice\{mValue=(\d+), mType=\d+, mName=(thermal-(?:cpufreq|devfreq)-\d+)\}/g)) caps[m[2]] = Number(m[1]);
  // (Battery Saver: LG then holds the panel at 30 Hz and limits the CPU; the panel's rate now)
  const saver = adb('shell', 'settings', 'get', 'global', 'low_power') === '1';
  const hz = Number(adb('shell', 'dumpsys', 'SurfaceFlinger').match(/refresh-rate\s*:\s*([\d.]+)/)?.[1]);
  return {battery_saver: saver, refresh_hz: hz, battery_c: Number(bat.match(/temperature: (\d+)/)?.[1]) / 10, level: Number(bat.match(/level: (\d+)/)?.[1]),
    cpu_c: cpu, gpu_c: gpu, sensors: other, thermal_status: Number(thermal.match(/Thermal Status: (\d+)/)?.[1] ?? -1), caps};
};

// keep the phone's screen on and Chrome in front, then reach its DevTools
adb('shell', 'cmd', 'media_session', 'volume', '--stream', '3', '--set', '0');   // (the phone stays silent)
adb('shell', 'svc', 'power', 'stayon', 'usb');
adb('shell', 'input', 'keyevent', 'KEYCODE_WAKEUP');
adb('shell', 'wm', 'dismiss-keyguard');
adb('shell', 'am', 'start', '-a', 'android.intent.action.VIEW', '-d', 'about:blank', '-p', packages[browser]);
adb('forward', `tcp:${devport}`, `localabstract:${sockets[browser]}`);
await sleep(1500);

let served = null, url = page;
if (!/^https?:/.test(page)) {
  served = await openPage(page);
  url = served.url;
  const port = new URL(url).port;
  adb('reverse', `tcp:${port}`, `tcp:${port}`);
  url = url.replace('127.0.0.1', 'localhost');
}
const given = opt('query', '');
// (a fresh page each run: the server lets the browser keep index.html for ten minutes)
url += (url.includes('?') ? '&' : '?') + (given ? given + '&' : '') + 'AEGEAN_FRAME_STATS=1&run=' + Date.now().toString(36);

const dev = `http://localhost:${devport}`;
let targets = await (await fetch(`${dev}/json`)).json();
let target = targets.find((t) => t.type === 'page');
if (!target) target = await (await fetch(`${dev}/json/new?about:blank`, {method: 'PUT'})).json();
const ws = new WebSocket(`ws://localhost:${devport}/devtools/page/${target.id}`);
await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
let n = 0;
const pend = new Map(), logs = [];
const t0 = Date.now();
const stamp = () => (Date.now() - t0) / 1000;
ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pend.has(m.id)) { pend.get(m.id)(m.result ?? m.error); pend.delete(m.id); return; }
  if (m.method === 'Runtime.consoleAPICalled') logs.push([stamp(), m.params.type, m.params.args.map((a) => a.value ?? a.description ?? a.type).join(' ')]);
  else if (m.method === 'Runtime.exceptionThrown') logs.push([stamp(), 'exception', m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text]);
  else if (m.method === 'Log.entryAdded') logs.push([stamp(), 'log.' + m.params.entry.level, m.params.entry.text]);
};
const send = (method, params = {}) => new Promise((r) => { const i = ++n; pend.set(i, r); ws.send(JSON.stringify({id: i, method, params})); });
const evaluate = async (expr) => (await send('Runtime.evaluate', {expression: expr, returnByValue: true, awaitPromise: true}))?.result?.value;

// the probe: animation frames' times, the boot's stages, failed shader programs, errors
const probe = `(() => {
  const P = window.__phone = {t0: performance.now(), stages: {}, frames: [], fails: [], errors: []};
  const mark = (k) => { if (!(k in P.stages)) P.stages[k] = Math.round(performance.now() - P.t0); };
  window.__phoneMark = mark;
  const raf = window.requestAnimationFrame.bind(window);
  window.requestAnimationFrame = (cb) => raf((t) => { if (P.frames.length < 200000) P.frames.push(t); mark('first_frame'); cb(t); });
  const proto = WebGL2RenderingContext.prototype, link = proto.linkProgram, loc = proto.getUniformLocation;
  P.uniforms = {asked: 0, missing: []};
  proto.getUniformLocation = function (p, name) {
    const l = loc.call(this, p, name);
    P.uniforms.asked++;
    if (!l && P.uniforms.missing.length < 400) P.uniforms.missing.push(name);
    return l;
  };
  proto.linkProgram = function (p) {
    mark('first_program');
    link.call(this, p);
    if (!this.getProgramParameter(p, this.LINK_STATUS))
      P.fails.push({log: this.getProgramInfoLog(p), shaders: this.getAttachedShaders(p).map((s) => this.getShaderInfoLog(s))});
  };
  const ctx = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function (...a) { mark('context'); return ctx.apply(this, a); };
  const inst = WebAssembly.instantiate;
  WebAssembly.instantiate = function (...a) { mark('instantiate'); return inst.apply(this, a).then((r) => { mark('instantiated'); return r; }); };
  addEventListener('error', (e) => P.errors.push(String(e.error || e.message)));
  addEventListener('unhandledrejection', (e) => P.errors.push('unhandled rejection: ' + String(e.reason && (e.reason.stack || e.reason))));
  addEventListener('load', () => mark('load'));
  addEventListener('DOMContentLoaded', () => {
    mark('dom');
    new MutationObserver(() => {
      if (document.getElementById('aegean-loading')) mark('card');
      else if ('card' in P.stages) mark('card_gone');
      const log = document.getElementById('log');
      if (log && /error/.test(log.textContent)) mark('error');
    }).observe(document.body, {childList: true, subtree: true, characterData: true});
  });
})();`;
const before = phoneState();
await send('Runtime.enable');
await send('Log.enable');
await send('Page.enable');
await send('Page.addScriptToEvaluateOnNewDocument', {source: probe});
// (--inject f.js: a script of one's own run before the page's, for experiments)
if (opt('inject', null)) await send('Page.addScriptToEvaluateOnNewDocument', {source: readFileSync(opt('inject'), 'utf8')});
// (--cold: the browser's cache emptied first, compiled wasm with it: a first visit)
if (flag('cold')) { await send('Network.enable'); await send('Network.clearBrowserCache'); }
await send('Page.navigate', {url});
console.log(`phone_run: ${url} (${browser}), battery ${before.battery_c} C, thermal ${before.thermal_status}, display ${before.refresh_hz} Hz`);
if (before.battery_saver) console.log('phone_run: WARNING Battery Saver is on (30 Hz panel, CPU limited): `adb shell cmd power set-mode 0` turns it off');

// wait for the title (the card gone) or an error, at most 5 minutes
let stages = {};
for (let i = 0; i < 600; i++) {
  await sleep(500);
  stages = (await evaluate('JSON.stringify(window.__phone && window.__phone.stages)').then((v) => JSON.parse(v || '{}')).catch(() => ({}))) || {};
  if ('card_gone' in stages || 'error' in stages) break;
  if (!('card' in stages) && 'first_frame' in stages && stamp() > 30) break;   // (a page without the card: AEGEAN_TITLE=0 and staged)
}
const shown = 'card_gone' in stages || ('first_frame' in stages && !('error' in stages));
let result = {url, browser, stages_ms: stages, shown};
if (shown) {
  await sleep(warm * 1000);
  const from = await evaluate('performance.now()');
  const mid = phoneState();
  const temps = [];
  for (let s = 0; s < secs; s += 10) {
    await sleep(Math.min(10, secs - s) * 1000);
    // (memory with each sample: the JS heap, the wasm memory and, with --inject of a counter, GL objects)
    const mem = JSON.parse(await evaluate('JSON.stringify({heap_mb: performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1e6) : null, wasm_mb: sloppy.memory ? Math.round(sloppy.memory().buffer.byteLength / 1e6) : null, gl: window.__gl_live || null})') || '{}');
    temps.push({t: s + 10, ...phoneState(), ...mem});
  }
  const frames = JSON.parse(await evaluate(`JSON.stringify(window.__phone.frames.filter((t) => t >= ${from}))`));
  const gaps = frames.slice(1).map((t, i) => t - frames[i]).sort((a, b) => a - b);
  const q = (p) => gaps.length ? gaps[Math.min(gaps.length - 1, Math.floor(p * gaps.length))] : NaN;
  const span = frames.length > 1 ? (frames[frames.length - 1] - frames[0]) / 1000 : 0;
  result = {...result, window_s: secs, warm_s: warm, frames: frames.length, fps: span ? (frames.length - 1) / span : 0,
    gap_ms: {median: q(0.5), p95: q(0.95), p99: q(0.99), max: gaps[gaps.length - 1]},
    heap_mb: await evaluate('performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1e6) : null'),
    wasm_mb: await evaluate('sloppy.memory ? Math.round(sloppy.memory().buffer.byteLength / 1e6) : null').catch(() => null),
    canvas: await evaluate('(() => { const c = document.querySelector("canvas"); return [c.width, c.height, devicePixelRatio]; })()'),
    phone_start: mid, phone_samples: temps};
}
const extra = JSON.parse(await evaluate('JSON.stringify({fails: window.__phone.fails, errors: window.__phone.errors, uniforms: window.__phone.uniforms, log: (document.getElementById("log")||{}).textContent || ""})') || '{}');
result.uniform_lookups = extra.uniforms && {asked: extra.uniforms.asked, missing: extra.uniforms.missing};
result.shader_failures = extra.fails;
result.errors = extra.errors;
result.page_log = (extra.log || '').slice(-4000);
result.frame_stats = logs.filter((l) => /FRAME_STATS/.test(l[2])).map((l) => l[2]);
result.console = logs.filter((l) => !/FRAME_STATS/.test(l[2])).slice(-60);
if (!flag('keep')) await send('Page.navigate', {url: 'about:blank'});
ws.close();
if (served) { try { adb('reverse', '--remove', `tcp:${new URL(served.url).port}`); } catch {} await served.close(); }
adb('shell', 'svc', 'power', 'stayon', 'false');
if (out) writeFileSync(out, JSON.stringify(result, null, 1));
const brief = {...result}; delete brief.console; delete brief.uniform_lookups; delete brief.phone_samples; delete brief.page_log;
console.log(JSON.stringify(brief, null, 1).slice(0, 6000));
if (result.page_log && /error/.test(result.page_log)) console.log('page log:\n' + result.page_log.slice(0, 2000));
process.exit(shown ? 0 : 1);
