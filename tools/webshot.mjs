// The web build in headless Chromium: load the page, let it run, save a screenshot and print what
// the page logged (errors included).
// usage: node tools/webshot.mjs chrome page.html out.png [seconds] [query]
import { spawn } from "node:child_process";
import { writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [chrome, page, out, secs = "6", query = ""] = process.argv.slice(2);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const dir = mkdtempSync(join(process.env.WEBSHOT_TMP || tmpdir(), "webshot-"));
const b = spawn(chrome, ["--no-sandbox", "--enable-unsafe-swiftshader", "--use-angle=swiftshader", "--remote-debugging-port=0", `--user-data-dir=${dir}`, "--window-size=1280,720", "about:blank"], { stdio: ["ignore", "ignore", "pipe"] });
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
ws.addEventListener("message", (m) => {
  const msg = JSON.parse(m.data);
  if (msg.id && waits[msg.id]) waits[msg.id](msg.result || msg.error);
  if (msg.method === "Runtime.consoleAPICalled") console.log("console:", msg.params.args.map((a) => a.value ?? a.description).join(" "));
  if (msg.method === "Runtime.exceptionThrown") console.log("exception:", JSON.stringify(msg.params.exceptionDetails).slice(0, 600));
});
const send = (method, params = {}) => new Promise((r) => { const i = ++id; waits[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
try {
  await send("Runtime.enable");
  await send("Page.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
  await send("Page.navigate", { url: "file://" + page + query });
  await sleep(parseFloat(secs) * 1000);
  const shot = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(out, Buffer.from(shot.data, "base64"));
  console.log("saved", out);
} finally {
  b.kill();
}
