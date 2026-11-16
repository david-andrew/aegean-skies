// The web build in headless Chromium with a synthetic gamepad: the page's navigator.getGamepads
// answers with a standard-mapping pad this tool moves (no hardware, no Playwright). It works the
// pause menu (Start, the bumpers to the Controls page, the d-pad, A on "Invert Y", B to carry on),
// then flies a take-off from AEGEAN_CAPTURE_TAKEOFF=pad, steering by the game's trace lines
// (AEGEAN_TRACE: speed, height, water), and saves a screenshot at each step.
// usage: node tools/web_gamepad.mjs chrome page.html outdir [WxH]
import { spawn } from "node:child_process";
import { writeFileSync, mkdtempSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { openPage } from "./web_page.mjs";

const [chrome, page, outdir, size = "960x540"] = process.argv.slice(2);
mkdirSync(outdir, { recursive: true });
const [width, height] = size.split("x").map(Number);
const served = await openPage(page);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const dir = mkdtempSync(join(process.env.WEBSHOT_TMP || tmpdir(), "webpad-"));
// (WEBPAD_GPU=1: the machine's GPU through ANGLE's Vulkan; else SwiftShader, slow but anywhere)
const gl = process.env.WEBPAD_GPU === "1" ? ["--use-angle=vulkan", "--enable-features=Vulkan", "--ignore-gpu-blocklist"] : ["--enable-unsafe-swiftshader", "--use-angle=swiftshader"];
const b = spawn(chrome, ["--no-sandbox", ...gl, "--remote-debugging-port=0", `--user-data-dir=${dir}`, `--window-size=${width},${height}`, "about:blank"], { stdio: ["ignore", "ignore", "pipe"] });
let err = "";
b.stderr.on("data", (d) => { err += d; });
const t0 = Date.now();
while (!/DevTools listening on (ws:\S+)/.test(err)) { if (Date.now() - t0 > 15000) throw new Error("no browser"); await sleep(50); }
const port = new URL(err.match(/DevTools listening on (ws:\S+)/)[1]).port;
const target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((x) => x.type === "page");
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r));
let id = 0;
const waits = {};
const lines = [];
let errors = 0;
ws.addEventListener("message", (m) => {
  const msg = JSON.parse(m.data);
  if (msg.id && waits[msg.id]) waits[msg.id](msg.result || msg.error);
  if (msg.method === "Runtime.consoleAPICalled") {
    const s = msg.params.args.map((a) => a.value ?? a.description).join(" ");
    lines.push(s);
    if (/^t \d|^PAD|error|Error/.test(s)) console.log("console:", s.slice(0, 160));
  }
  if (msg.method === "Runtime.exceptionThrown") { errors++; console.log("exception:", JSON.stringify(msg.params.exceptionDetails).slice(0, 600)); }
});
const send = (method, params = {}) => new Promise((r) => { const i = ++id; waits[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
const evaluate = async (expr) => (await send("Runtime.evaluate", { expression: expr, returnByValue: true })).result?.value;

// the pad: standard mapping (0 A, 1 B, 2 X, 3 Y, 4 LB, 5 RB, 6 LT, 7 RT, 8 Back, 9 Start, 10 L3,
// 11 R3, 12-15 the d-pad up down left right, 16 Home); the axes lx ly rx ry
const FAKE = `(() => {
  const pad = { id: "Synthetic Xbox Wireless Controller (STANDARD GAMEPAD)", index: 0, connected: true, mapping: "standard",
    axes: [0, 0, 0, 0], buttons: Array.from({ length: 17 }, () => ({ pressed: false, touched: false, value: 0 })), timestamp: 0 };
  Object.defineProperty(Navigator.prototype, "getGamepads", { value: () => [pad, null, null, null], configurable: true });
  window.__pad = pad;
  // (frames counted, so a press is held until the game has read it)
  window.__frames = 0;
  const raf = window.requestAnimationFrame.bind(window);
  window.requestAnimationFrame = (f) => raf((t) => { window.__frames++; f(t); });
  window.__padSet = (axes, buttons) => {
    if (axes) pad.axes = axes.slice();
    if (buttons) for (const [i, v] of Object.entries(buttons)) pad.buttons[i] = { pressed: v > 0.5, touched: v > 0, value: v };
    pad.timestamp = performance.now();
  };
})();`;
const set = (axes, buttons) => evaluate(`window.__padSet(${JSON.stringify(axes)}, ${JSON.stringify(buttons || null)})`);
// frames go by (the game reads the pad once a frame: a press is held for two, then let go for two)
const frames = async (n) => { const f0 = await evaluate("window.__frames"); while ((await evaluate("window.__frames")) < f0 + n) await sleep(30); };
const press = async (i) => { await set(null, { [i]: 1 }); await frames(2); await set(null, { [i]: 0 }); await frames(2); };
const shot = async (name) => {
  const s = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(join(outdir, name), Buffer.from(s.data, "base64"));
  console.log("saved", name);
};
const last = (re) => { for (let k = lines.length - 1; k >= 0; k--) if (re.test(lines[k])) return lines[k]; return ""; };

let ok = true;
try {
  await send("Runtime.enable");
  await send("Page.enable");
  await send("Page.addScriptToEvaluateOnNewDocument", { source: FAKE });
  await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
  await send("Page.navigate", { url: served.url + "?AEGEAN_TITLE=0&AEGEAN_CAPTURE_TAKEOFF=pad&AEGEAN_TRACE=1" });
  // (until the game runs: its first trace line)
  const t1 = Date.now();
  while (!last(/^t \d/)) { if (Date.now() - t1 > 240000) throw new Error("the game did not start"); await sleep(500); }
  await evaluate(`window.dispatchEvent(new Event("gamepadconnected"))`);
  const fa = await evaluate("window.__frames"); await sleep(5000);
  console.log(`frames a second: ${((await evaluate("window.__frames")) - fa) / 5}`);
  // the menus: Start pauses, RB along the pages to Controls, the d-pad down, A ticks Invert Y
  await press(9);
  await sleep(1000);
  await shot("1-paused.png");
  for (let k = 0; k < 8; k++) await press(5);
  await sleep(800);
  await shot("2-controls.png");
  // (a page turned by the bumpers starts its focus on the page: the Gamepad tab; down to Invert Y)
  await press(13);
  await press(0);
  await sleep(800);
  await shot("3-invert.png");
  await press(0);                  // (untick it again: the flight wants it as it was)
  await press(1);                  // B: carry on
  await sleep(1000);
  // the take-off: RT open; the stick neutral to about 105 m/s, back to lift her, then a climb
  await set([0, 0, 0, 0], { 7: 1 });
  await frames(140);
  await set([0, 0, 0, 0], { 7: 0 });
  const t2 = Date.now();
  let phase = 0, top = 0;
  while (Date.now() - t2 < 300000) {
    const tl = last(/^t \d/);
    const m = tl.match(/spd ([\d.]+) alt ([\d.-]+) .* water (\w+)/);
    if (m) {
      const spd = +m[1], alt = +m[2], water = m[3] === "true";
      top = Math.max(top, alt);
      if (phase === 0 && spd > 105) { phase = 1; await set([0, 0.8, 0, 0]); }
      if (phase === 1 && !water && alt > 8) { phase = 2; await set([0, 0.35, 0, 0]); await shot("4-liftoff.png"); }
      if (phase === 2 && alt > 60) { phase = 3; await set([0, 0.12, 0, 0]); }
      if (phase === 3 && alt > 120) { await shot("5-climb.png"); break; }
    }
    await sleep(200);
  }
  console.log(`take-off: phase ${phase}, highest ${top.toFixed(1)} m; last: ${last(/^t \d/)}`);
  console.log(`pad as the game read it: ${last(/^PAD/)}`);
  ok = phase === 3 && top > 120 && errors === 0;
} finally {
  await served.close();
  b.kill();
}
console.log(ok ? "WEB GAMEPAD OK" : "WEB GAMEPAD FAILED");
process.exit(ok ? 0 : 1);
