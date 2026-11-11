// The web build in headless Chromium: load the page, let it run, save a screenshot and print what
// the page logged (errors included).
// Optional WEBSHOT_GPU=native probes headless ANGLE/Vulkan instead of SwiftShader.
// usage: node tools/measure_web.mjs chrome page.html out.png [seconds] [query]
import { spawn } from "node:child_process";
import { writeFileSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [chrome, page, out, secs = "6", query = ""] = process.argv.slice(2);
readFileSync(page); // Fail before opening Chromium when the requested build is missing.
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const dir = mkdtempSync(join(process.env.WEBSHOT_TMP || tmpdir(), "webshot-"));
const gpuFlags = process.env.WEBSHOT_GPU === "native"
  ? ["--use-angle=vulkan", "--enable-features=Vulkan", "--disable-vulkan-surface"]
  : ["--enable-unsafe-swiftshader", "--use-angle=swiftshader"];
const b = spawn(chrome, ["--headless=new", "--allow-file-access-from-files", "--mute-audio", "--renderer-process-limit=1", "--no-sandbox", ...gpuFlags, "--remote-debugging-port=0", `--user-data-dir=${dir}`, "--window-size=1280,720", "about:blank"], { stdio: ["ignore", "ignore", "pipe"] });
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
  console.log("heap", JSON.stringify(await send("Runtime.getHeapUsage")));
  const probe = await send("Runtime.evaluate", {returnByValue: true, expression: `(() => {
    const gl = document.createElement('canvas').getContext('webgl2');
    const names = ['MAX_TEXTURE_SIZE','MAX_ARRAY_TEXTURE_LAYERS','MAX_VERTEX_TEXTURE_IMAGE_UNITS','MAX_TEXTURE_IMAGE_UNITS','MAX_VERTEX_ATTRIBS'];
    const caps = Object.fromEntries(names.map(n => [n, gl.getParameter(gl[n])]));
    caps.extensions = gl.getSupportedExtensions();
    const dbg=gl.getExtension('WEBGL_debug_renderer_info'); caps.renderer=dbg?gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER);
    gl.getExtension('EXT_color_buffer_float');
    caps.formats={};
    for(const [name, internal, format, type] of [['R32F',gl.R32F,gl.RED,gl.FLOAT],['RGBA16F',gl.RGBA16F,gl.RGBA,gl.HALF_FLOAT],['RGBA8',gl.RGBA8,gl.RGBA,gl.UNSIGNED_BYTE]]){
      const t=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,t);gl.texImage2D(gl.TEXTURE_2D,0,internal,4,4,0,format,type,null);
      const f=gl.createFramebuffer();gl.bindFramebuffer(gl.FRAMEBUFFER,f);gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,t,0);
      caps.formats[name]={error:gl.getError(),renderable:gl.checkFramebufferStatus(gl.FRAMEBUFFER)===gl.FRAMEBUFFER_COMPLETE};gl.deleteFramebuffer(f);gl.deleteTexture(t);
    }
    gl.getExtension('WEBGL_lose_context')?.loseContext();
    return {caps,wasm_bytes:typeof sloppy!=='undefined'?sloppy.memory()?.buffer.byteLength:null};
  })()`});
  console.log("probe",JSON.stringify(probe));
  function memory(pid) {
    let total = 0;
    try {
      const status = readFileSync(`/proc/${pid}/status`, "utf8");
      const rss = Number(status.match(/VmRSS:\s+(\d+)/)?.[1] || 0);
      const peak = Number(status.match(/VmHWM:\s+(\d+)/)?.[1] || 0);
      let roll = ''; try {roll=readFileSync(`/proc/${pid}/smaps_rollup`,'utf8')} catch {}
      const fields=Object.fromEntries(['Pss','Private_Clean','Private_Dirty','Swap'].map(n=>[n,Number(roll.match(new RegExp('^'+n+':\\s+(\\d+)','m'))?.[1]||0)]));
      console.log("process", pid, "RSS_KiB", rss, "HWM_KiB", peak, JSON.stringify(fields));
      total += rss;
      for (const child of readFileSync(`/proc/${pid}/task/${pid}/children`, "utf8").trim().split(/\s+/).filter(Boolean)) total += memory(child);
    } catch {}
    return total;
  }
  console.log("browser tree RSS KiB", memory(b.pid));
} finally {
  b.kill();
  await new Promise(r => b.once("exit", r));
  rmSync(dir,{recursive:true,force:true});
}
