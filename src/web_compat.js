// Sloppy 0.29.2 passes the complete uniform struct through every helper. Some
// WebGL linkers consequently activate even unused fields (192 bone vectors in
// the fragment stage). Specialize READ-ONLY uniform parameters to the global
// uniform, then expose its fields separately. Keep the engine's upload layout;
// translate only the uniform names used to look up locations.
// Keep this compatibility pass until the compiler performs this specialization.
(function (root) {
  function specializeUniforms(source) {
    const uniform = source.match(/\buniform (S_\w+) u;/);
    if (!uniform) return source;
    const type = uniform[1], functions = new Map(), aliases = new Set();
    const definition = /\b(\w+) (f_\w+)\(([^()]*)\)\s*\{/g;
    let result = source.replace(definition, (all, ret, name, params) => {
      const args = params ? params.split(",").map(x => x.trim()) : [];
      const indices = [];
      args.forEach((arg, index) => {
        const match = arg.match(new RegExp("^" + type + " (l_\\w+)$"));
        if (match) { indices.push(index); aliases.add(match[1]); }
      });
      if (!indices.length) return all;
      functions.set(name, indices);
      return `${ret} ${name}(${args.filter((_, i) => !indices.includes(i)).join(", ")}) {`;
    });
    if (!functions.size) return source;
    for (const alias of aliases) {
      // Reject mutation, copies and unexpected compiler output, never silently
      // specialize an independently constructed or modified parameter.
      const occurrences = [...result.matchAll(new RegExp("\\b" + alias + "\\b", "g"))];
      for (const m of occurrences) {
        const rest = result.slice(m.index + alias.length);
        if (!/^\s*[.,)]/.test(rest)) throw Error("Unsupported uniform use: " + alias);
        if (/^\s*\.[\w.\[\]]+\s*(?:=(?!=)|[+*/-]=|\+\+|--)/.test(rest))
          throw Error("Mutable shader uniform parameter: " + alias);
      }
      result = result.replace(new RegExp("\\b" + alias + "\\b", "g"), "u");
    }
    // Walk call arguments with balanced parentheses: nested constructors and
    // helper calls are common. Process from the inside out, excluding definitions.
    const names = [...functions.keys()].join("|");
    const pattern = new RegExp("\\b(" + names + ")\\(", "g");
    const edits = [];
    for (const m of result.matchAll(pattern)) {
      let depth = 1, start = m.index + m[0].length, end = start;
      const args = [], ranges = [];
      for (; end < result.length && depth; end++) {
        const ch = result[end];
        if (ch === "(") depth++;
        if (ch === ")") depth--;
        if ((ch === "," && depth === 1) || depth === 0) {
          args.push(result.slice(start, end).trim()); ranges.push([start, end]); start = end + 1;
        }
      }
      if (/^\s*\{/.test(result.slice(end))) continue; // function definition
      const remove = functions.get(m[1]);
      for (const i of remove) if (args[i] !== "u") throw Error("Non-global uniform argument in " + m[1]);
      // Remove just the uniform argument and its separator; other arguments may
      // themselves contain calls with edits, so do not replace the whole call.
      for (const i of remove) {
        const [a, b] = ranges[i];
        edits.push(i > 0 ? [a - 1, b] : [a, b + (args.length > 1 ? 1 : 0)]);
      }
    }
    const merged = [];
    for (const [a, b] of edits.sort((a, b) => a[0] - b[0])) {
      const last = merged[merged.length - 1];
      if (last && a <= last[1]) last[1] = Math.max(last[1], b);
      else merged.push([a, b]);
    }
    for (const [a, b] of merged.reverse()) result = result.slice(0, a) + result.slice(b);
    const body = result.match(new RegExp("struct " + type + "\\s*\\{([^}]+)\\};"))?.[1];
    if (!body) throw Error("Missing uniform struct " + type);
    const fields = [...body.matchAll(/\b(\w+)(?:\[(\d+)\])?\s+(\w+);/g)];
    const declarations = [];
    for (const [_, fieldType, count, name] of fields) {
      const access = new RegExp("\\bu\\." + name + "\\b", "g");
      if (!access.test(result)) continue;
      result = result.replace(access, "aegean_u_" + name);
      declarations.push(`uniform ${fieldType} aegean_u_${name}${count ? `[${count}]` : ""};`);
    }
    result = result.replace(uniform[0], declarations.join("\n"));
    if (/\bu\b/.test(result)) throw Error("Unsupported whole uniform struct use");
    return result;
  }
  // GLSL ES gives sampler2D a default precision of lowp, and a texture lookup returns its
  // sampler's precision, so "precision highp float" alone still reads every texture at fp16
  // on phones (Adreno: lowp and mediump are fp16; desktop GPUs read at 32 bits regardless).
  // The opaque-depth copy multiplies a sampled depth by 16777215: in fp16 it saturates at
  // 65504, the sea then finds "opaque geometry" in front of it everywhere and discards itself
  // (a flat sky-coloured sea on the LG V60). Declare samplers highp in every generated shader
  // that asks for highp floats. Remove once Sloppy declares sampler precision itself.
  function highpSamplers(source) {
    if (!/^precision highp float;$/m.test(source) || /^precision \w+ sampler2D;$/m.test(source)) return source;
    return source.replace(/^precision highp float;$/m, "precision highp float;\nprecision highp sampler2D;");
  }
  function chooseTier(device) {
    if (["low", "medium", "high"].includes(device.override)) return ["low", "medium", "high"].indexOf(device.override);
    if (device.mobile || device.textureLimit <= 4096 || device.fragmentLimit <= 224) return 0;
    if (/Intel|Iris|UHD|SwiftShader|llvmpipe/i.test(device.renderer)) return 1;
    return 2;
  }
  function cappedSize(width,height,cssWidth,cssHeight,maxPixels) {
    if(width*height <= maxPixels) return [width,height];
    // Use the stable CSS aspect, not rounded adaptive-resolution dimensions:
    // one-pixel cap oscillations otherwise recreate every cloud/depth target.
    const aspect = Math.max(cssWidth,1)/Math.max(cssHeight,1);
    return [Math.max(1,Math.floor(Math.sqrt(maxPixels*aspect))),
      Math.max(1,Math.floor(Math.sqrt(maxPixels/aspect)))];
  }
  // The world keeps the old adaptive pixel budget. Only the final 2D pass uses
  // display pixels (1.3 MP on phones, or 2.6 MP for explicit High). A scalar target
  // can round one axis down by a pixel; it must never enlarge the scene.
  function resolutionPlan(width,height,cssWidth,cssHeight,dpr,maxPixels,mobile) {
    const scene = cappedSize(width,height,cssWidth,cssHeight,maxPixels);
    const display = cappedSize(Math.max(1,Math.round(cssWidth*dpr)),
      Math.max(1,Math.round(cssHeight*dpr)),cssWidth,cssHeight,mobile ? Math.max(1300000,maxPixels) : Infinity);
    const lo = Math.max((scene[0]-.5)/display[0],(scene[1]-.5)/display[1]);
    const hi = Math.min(1,(scene[0]+.499)/display[0],(scene[1]+.499)/display[1]);
    const scale = scene[0]>=display[0] && scene[1]>=display[1] ? 1 :
      lo <= hi ? (lo+hi)*.5 : Math.min(1,scene[0]/display[0],scene[1]/display[1]);
    return {display,scale,scene:display.map(v=>Math.max(1,Math.round(v*scale)))};
  }
  // Sloppy presents saves as base64 to localStorage, whose quota counts UTF-16 units.
  // Only binary living-bank bodies use this reversible 15-bit alphabet (no surrogates).
  // Native bytes and the independent world banks stay unchanged; legacy base64 reads too.
  function livingStoreEncode(base64) {
    if (base64.length < 64) return base64;
    const raw = atob(base64), parts = [], codes = [];
    let bits = 0, width = 0;
    for (let i = 0; i < raw.length; ++i) {
      bits |= raw.charCodeAt(i) << width; width += 8;
      if (width >= 15) {
        codes.push(256 + (bits & 32767)); bits >>>= 15; width -= 15;
        if (codes.length === 8192) { parts.push(String.fromCharCode(...codes)); codes.length = 0; }
      }
    }
    if (width) codes.push(256 + bits);
    if (codes.length) parts.push(String.fromCharCode(...codes));
    return `AS15:${raw.length}:` + parts.join("");
  }
  function livingStoreDecode(value) {
    if (value === null || !value.startsWith("AS15:")) return value;
    const colon = value.indexOf(":", 5), digits = value.slice(5, colon);
    if (colon < 0 || !/^\d{1,8}$/.test(digits)) throw Error("Invalid living save byte length");
    const length = Number(digits), start = colon + 1;
    if (length > 64000000 || value.length - start !== Math.ceil(length * 8 / 15)) throw Error("Truncated living save byte store");
    const parts = [], chunk = new Uint8Array(8192);
    let bits = 0, width = 0, count = 0, used = 0;
    for (let i = start; i < value.length; ++i) {
      const code = value.charCodeAt(i) - 256;
      if (code < 0 || code > 32767) throw Error("Invalid living save alphabet");
      bits |= code << width; width += 15;
      while (width >= 8 && count < length) {
        chunk[used++] = bits & 255; bits >>>= 8; width -= 8; ++count;
        if (used === chunk.length) { parts.push(String.fromCharCode(...chunk)); used = 0; }
      }
    }
    if (count !== length || bits !== 0) throw Error("Invalid living save padding");
    if (used) parts.push(String.fromCharCode(...chunk.subarray(0, used)));
    return btoa(parts.join(""));
  }
  function installLivingStorage(proto) {
    if (!proto || proto.__aegeanWideLivingStore) return;
    const get = proto.getItem, set = proto.setItem;
    const bodyKey = key => /^sloppy:.*-(?:a|b)-data$/.test(String(key));
    proto.setItem = function(key, value) { return set.call(this, key, bodyKey(key) ? livingStoreEncode(String(value)) : value); };
    proto.getItem = function(key) { const value = get.call(this, key); return bodyKey(key) ? livingStoreDecode(value) : value; };
    Object.defineProperty(proto, "__aegeanWideLivingStore", {value:true});
  }
  root.AegeanWeb = { specializeUniforms, highpSamplers, chooseTier, cappedSize, resolutionPlan, livingStoreEncode, livingStoreDecode, installLivingStorage };
  if (typeof module !== "undefined") module.exports = root.AegeanWeb;
  if (typeof Storage !== "undefined") installLivingStorage(Storage.prototype);
  if (typeof WebGL2RenderingContext === "undefined") return;
  const mobile = navigator.userAgentData?.mobile || /Android|iPhone|iPad/i.test(navigator.userAgent) ||
    (navigator.maxTouchPoints > 1 && Math.min(screen.width, screen.height) <= 1024);
  const query = new URLSearchParams(location.search);
  const override = [...query].find(([k]) => k.toUpperCase() === "AEGEAN_QUALITY")?.[1];
  // Requesting MSAA is expensive on tiled phone GPUs. This changes the context
  // creation request only; no extra context or render target is allocated.
  const getContext = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function (kind, options) {
    if (kind === "webgl2" && (override === "low" || (mobile && override !== "high")))
      options = {...options, antialias:false};
    return getContext.call(this, kind, options);
  };
  let sceneScale = 1;
  sloppy.env.__aegean_scene_scale = () => sceneScale;
  sloppy.env.__aegean_quality = () => {
    const canvas = document.querySelector("canvas"), gl = canvas.getContext("webgl2");
    const debug = gl.getExtension("WEBGL_debug_renderer_info");
    const device = {override, mobile, textureLimit:gl.getParameter(gl.MAX_TEXTURE_SIZE),
      fragmentLimit:gl.getParameter(gl.MAX_FRAGMENT_UNIFORM_VECTORS),
      renderer:debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER)};
    const tier = chooseTier(device), maxPixels = [230400, 518400, 2600000][tier];
    const originalFit = sloppy.res.fit;
    const fit = () => {
      originalFit();
      const plan = resolutionPlan(canvas.width,canvas.height,canvas.clientWidth,canvas.clientHeight,
        window.devicePixelRatio || 1,maxPixels,mobile);
      sceneScale = plan.scale;
      const [w,h] = plan.display;
      if (canvas.width !== w) canvas.width = w;
      if (canvas.height !== h) canvas.height = h;
      root.AegeanWeb.resolution = plan;
    };
    sloppy.res.fit = fit;
    window.addEventListener("resize", fit);
    window.visualViewport?.addEventListener("resize", fit);
    fit();
    root.AegeanWeb.quality = {tier,maxPixels,...device};
    console.info("Aegean render quality", JSON.stringify(root.AegeanWeb.quality));
    return tier;
  };
  // The phone's gyroscope, for fine aiming by tilting it (as Breath of the Wild's bow did): its
  // turning, from the deviceorientation readings (see below), integrated into degrees about the SCREEN's
  // axes (whichever way up the phone is held), handed over and cleared each frame. iOS asks for
  // permission, and only in answer to a tap: asked at the next touch after the option is turned on.
  {
    let started = false, pendingAsk = false, dx = 0, dy = 0, live = false;
    // (from the phone's orientation, which every browser letters the same way: alpha about z,
    // beta about x, gamma about y, applied Z-X'-Y''. The turn between two readings, in the phone's
    // own axes, comes from the two rotations, so no letters for rates are trusted (browsers
    // disagree on those) and holding the phone upright is no trouble.)
    let prev = null;
    const matrix = (a, b, g) => {
      const d = Math.PI / 180, ca = Math.cos(a*d), sa = Math.sin(a*d), cb = Math.cos(b*d), sb = Math.sin(b*d), cg = Math.cos(g*d), sg = Math.sin(g*d);
      return [ca*cg - sa*sb*sg, -cb*sa, ca*sg + cg*sa*sb,
              cg*sa + ca*sb*sg,  ca*cb, sa*sg - ca*cg*sb,
              -cb*sg,            sb,    cb*cg];
    };
    const onMotion = e => {
      if (e.alpha == null || e.beta == null || e.gamma == null) return;
      const R = matrix(e.alpha, e.beta, e.gamma);
      live = true;
      if (!prev) { prev = R; return; }
      // (dR = prev^T R: the turn since the last reading, in the phone's frame)
      const P = prev;
      const m = (i, j) => P[0*3+i]*R[0*3+j] + P[1*3+i]*R[1*3+j] + P[2*3+i]*R[2*3+j];
      const k = 180 / Math.PI;
      const rx = (m(2,1) - m(1,2)) * 0.5 * k, ry = (m(0,2) - m(2,0)) * 0.5 * k;
      prev = R;
      if (Math.abs(rx) > 20 || Math.abs(ry) > 20) return;   // (a jump: the compass correcting itself)
      const ang = (screen.orientation && screen.orientation.angle) || window.orientation || 0;
      // (right-handed: +x tips the back up, +y turns the back to the left. The aim turns with the
      // phone about the SCREEN's axes as it is held; a twist in the screen's own plane does nothing)
      let up, right;
      switch (((ang % 360) + 360) % 360) {
        case 90: up = -ry; right = -rx; break;      // (the top to the left)
        case 180: up = -rx; right = ry; break;
        case 270: up = ry; right = rx; break;       // (the top to the right)
        default: up = rx; right = -ry;
      }
      dx += right; dy += up;
    };
    const go = () => { if (!started) { window.addEventListener("deviceorientation", onMotion); started = true; } };
    // (listen at once: Android's browsers send the readings without asking. Where the browser has
    // a permission to ask for (Safari, and newer Chrome and Firefox), ask now, and if that needs a
    // tap, ask again at the next one, caught before the game's own touch handling can stop it)
    const ask = () => {
      const D = window.DeviceOrientationEvent;
      if (!D || typeof D.requestPermission !== "function") return;
      D.requestPermission().then(r => { if (r !== "granted") pendingAsk = true; }).catch(() => { pendingAsk = true; });
    };
    const onTouch = () => { if (pendingAsk && !live) { pendingAsk = false; ask(); } };
    window.addEventListener("touchend", onTouch, {capture: true});
    window.addEventListener("click", onTouch, {capture: true});
    sloppy.env.__aegean_motion_start = () => { go(); ask(); };
    sloppy.env.__aegean_motion_live = () => live ? 1 : 0;
    sloppy.env.__aegean_motion_x = () => { const v = dx; dx = 0; return v; };
    sloppy.env.__aegean_motion_y = () => { const v = dy; dy = 0; return v; };
  }
  // In full screen a phone hides its navigation bar, and with it the little rotate button Android
  // offers when auto-rotate is off and the phone is turned. So the page offers its own: when the
  // phone has been held the other way for a moment, a rotate button shows in the corner; tapping it
  // turns the screen that way and keeps it there (till the phone is turned and it's tapped again).
  {
    let held = null, since = 0, button = null, hideAt = 0;
    const physical = g => {
      if (Math.abs(g.x) > Math.abs(g.y) + 2.5) return g.x > 0 ? "landscape-primary" : "landscape-secondary";
      if (Math.abs(g.y) > Math.abs(g.x) + 2.5 && g.y > 0) return "portrait-primary";
      return null;
    };
    const current = () => (screen.orientation && screen.orientation.type) || "";
    const make = () => {
      button = document.createElement("button");
      button.textContent = "\u27F3";
      button.setAttribute("aria-label", "Rotate the screen");
      Object.assign(button.style, {position:"fixed", right:"18px", bottom:"18px", width:"52px", height:"52px",
        borderRadius:"26px", border:"2px solid rgba(255,248,230,0.7)", background:"rgba(16,20,30,0.6)",
        color:"#fff8e6", fontSize:"30px", lineHeight:"46px", padding:"0", zIndex:"10", display:"none"});
      button.addEventListener("click", e => {
        e.stopPropagation();
        if (held && screen.orientation && screen.orientation.lock) screen.orientation.lock(held).catch(() => {});
        button.style.display = "none";
      });
      document.body.appendChild(button);
    };
    window.addEventListener("devicemotion", e => {
      const g = e.accelerationIncludingGravity;
      if (!g || g.x == null || !document.fullscreenElement) { if (button) button.style.display = "none"; return; }
      const p = physical(g), now = performance.now();
      if (p !== held) { held = p; since = now; }
      const differs = held && held.split("-")[0] !== current().split("-")[0];
      if (!button) make();
      if (differs && now - since > 600 && button.style.display === "none") { button.style.display = "block"; hideAt = now + 5000; }
      if ((!differs || now > hideAt) && button.style.display !== "none") button.style.display = "none";
    });
  }
  const proto = WebGL2RenderingContext.prototype;
  const shaderSource = proto.shaderSource, linkProgram = proto.linkProgram, uniformLocation = proto.getUniformLocation;
  proto.shaderSource = function (shader, source) {
    return shaderSource.call(this, shader, highpSamplers(specializeUniforms(source)));
  };
  proto.getUniformLocation = function (program, name) {
    return uniformLocation.call(this, program, name.replace(/^u\./, "aegean_u_"));
  };
  proto.linkProgram = function (program) {
    linkProgram.call(this, program);
    if (this.getProgramParameter(program, this.LINK_STATUS)) return;
    const stages = this.getAttachedShaders(program).map(s => {
      const stage = this.getShaderParameter(s, this.SHADER_TYPE) === this.VERTEX_SHADER ? "vertex" : "fragment";
      const source = this.getShaderSource(s);
      const main = source.slice(source.lastIndexOf("void main"));
      return `${stage}: ${this.getShaderInfoLog(s) || "(empty shader log)"}\n${main}`;
    });
    const limits = ["MAX_VERTEX_UNIFORM_VECTORS", "MAX_FRAGMENT_UNIFORM_VECTORS", "MAX_VARYING_VECTORS", "MAX_TEXTURE_IMAGE_UNITS"]
      .map(n => `${n}=${this.getParameter(this[n])}`).join(", ");
    throw Error(`Shader link failed: ${this.getProgramInfoLog(program) || "(driver returned an empty link log)"}\n${limits}\n${stages.join("\n")}`);
  };
})(globalThis);

// Game slot storage (independent of graphics).
// Three complete slots need more than localStorage's UTF-16 quota. IndexedDB stores raw
// compressed bytes, with each header/body pair committed by one atomic transaction.
(function(root) {
  class GameSlotStore {
    constructor(idb, name="aegean-skies-game-v1") { this.idb=idb; this.name=name; this.db=null; this.headers=new Map(); }
    async open() {
      if (!this.idb) throw Error("This browser cannot keep game slots (IndexedDB unavailable).");
      this.db=await new Promise((resolve,reject)=>{
        const r=this.idb.open(this.name,1);
        r.onupgradeneeded=()=>{r.result.createObjectStore("headers");r.result.createObjectStore("banks");};
        r.onerror=()=>reject(r.error); r.onblocked=()=>reject(Error("Close the other game tab to open saved games."));
        r.onsuccess=()=>resolve(r.result);
      });
      this.db.onversionchange=()=>{this.db.close();this.db=null;};
      const tx=this.db.transaction("headers","readonly"), store=tx.objectStore("headers");
      const [keys,values]=await Promise.all([this.request(store.getAllKeys()),this.request(store.getAll())]);
      this.headers=new Map(keys.map((k,i)=>[k,values[i]]));
    }
    request(r) { return new Promise((resolve,reject)=>{r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);}); }
    key(slot,bank) { if(!Number.isInteger(slot)||slot<0||slot>2||bank<0||bank>1)throw Error("Invalid game slot.");return `${slot}:${bank}`; }
    header(slot,bank) { return this.headers.get(this.key(slot,bank))?.text || ""; }
    async read(slot) {
      const tx=this.db.transaction("banks","readonly"), store=tx.objectStore("banks");
      const result=await Promise.all([0,1].map(bank=>this.request(store.get(this.key(slot,bank)))));
      for(const bank of result) if(bank && (typeof bank.text!=="string" || bank.text.length>8000000 || !(bank.body instanceof ArrayBuffer) || bank.body.byteLength>16000000))throw Error("Saved game exceeds storage bounds.");
      result.forEach((v,b)=>{const k=this.key(slot,b);if(v)this.headers.set(k,{text:v.text,generation:v.generation});else this.headers.delete(k);});
      return result;
    }
    async write(slot,bank,text,body,generation,expected) {
      const key=this.key(slot,bank);
      if(typeof text!=="string" || text.length>8000000 || !(body instanceof Uint8Array) || !body.length || body.length>16000000)throw Error("Saved game exceeds storage bounds.");
      const value={text,body:body.slice().buffer,generation};
      await new Promise((resolve,reject)=>{
        const tx=this.db.transaction(["headers","banks"],"readwrite"), h=tx.objectStore("headers");
        let count=0, current=0, failure=null;
        for(let b=0;b<2;b++) {
          const r=h.get(this.key(slot,b));
          r.onsuccess=()=>{
            current=Math.max(current,r.result?.generation||0);
            if(++count!==2)return;
            if(current!==expected){failure=Error("Another tab changed this slot; reload it before saving.");tx.abort();return;}
            try {tx.objectStore("banks").put(value,key);h.put({text,generation},key);}
            catch(e){failure=e;try{tx.abort();}catch{}}
          };
        }
        tx.oncomplete=()=>resolve(); tx.onabort=()=>reject(failure||tx.error||Error("Game save was not committed."));tx.onerror=()=>{};
      });
      this.headers.set(key,{text,generation});
    }
    async delete(slot) {
      await new Promise((resolve,reject)=>{
        const tx=this.db.transaction(["headers","banks"],"readwrite");
        for(let b=0;b<2;b++)for(const name of ["headers","banks"])tx.objectStore(name).delete(this.key(slot,b));
        tx.oncomplete=()=>resolve();tx.onabort=()=>reject(tx.error||Error("Game slot was not deleted."));tx.onerror=()=>{};
      });
      for(let b=0;b<2;b++)this.headers.delete(this.key(slot,b));
    }
  }
  root.AegeanSlots={GameSlotStore};
  if(typeof module!=="undefined")module.exports.GameSlotStore=GameSlotStore;
  if(typeof sloppy==="undefined")return;
  const store=new GameSlotStore(root.indexedDB), enc=new TextEncoder();
  let state=0, buffers=[], error="";
  function start(work) {
    if(state===1)return;
    state=1;buffers=[];error="";
    Promise.resolve().then(work).then(()=>{state=2;},e=>{error=String(e?.message||e);state=-1;});
  }
  function copy(value,p,n){const dst=sloppy.bytes(p,n);if(dst.length!==value.length)throw Error("Save bridge length mismatch.");dst.set(value);}
  sloppy.env.aegean_slots_open=()=>start(()=>store.open());
  sloppy.env.aegean_slots_status=()=>BigInt(state);
  sloppy.env.aegean_slots_header_size=(slot,bank)=>BigInt(enc.encode(store.header(Number(slot),Number(bank))).length);
  sloppy.env.aegean_slots_header_copy=(slot,bank,p,n)=>copy(enc.encode(store.header(Number(slot),Number(bank))),p,n);
  sloppy.env.aegean_slots_read=slot=>start(async()=>{
    const banks=await store.read(Number(slot));
    buffers=banks.flatMap(v=>v?[enc.encode(v.text),new Uint8Array(v.body)]:[new Uint8Array(),new Uint8Array()]);
  });
  sloppy.env.aegean_slots_write=(slot,bank,generation,expected,p,n,b,k)=>{
    const text=sloppy.text(p,n), body=sloppy.bytes(b,k).slice();
    start(()=>store.write(Number(slot),Number(bank),text,body,Number(generation),Number(expected)));
  };
  sloppy.env.aegean_slots_delete=slot=>start(()=>store.delete(Number(slot)));
  sloppy.env.aegean_slots_size=index=>BigInt((Number(index)===4?enc.encode(error):buffers[Number(index)]||[]).length);
  sloppy.env.aegean_slots_copy=(index,p,n)=>copy(Number(index)===4?enc.encode(error):buffers[Number(index)]||new Uint8Array(),p,n);
  sloppy.env.aegean_slots_release=()=>{buffers=[];};
})(typeof globalThis!=="undefined"?globalThis:this);
// The loading propeller (docs/glossary: Loading propeller). An engine running up, holding at full,
// easing back to the edge of the disc, and down to idle again, every eight seconds, drawn in the
// in-game propeller's own regimes (src/prop_disc.jo): solid blades turning, a pale disc coming in
// over them, then the pencil arcs in bands that precess by prop_band_speed: slowly at full power,
// fast near the hand-over from the blades. The same timetable, shapes and arcs as the game's own
// loader (src/title_screen.jo draw_loading_propeller): 160 stops a cycle, linear between them.
// In the page each layer is its own composited element animated only by CSS transform and opacity
// keyframes, so it keeps turning while the main thread is blocked (the module compiling, the world
// being built).
(function (root) {
  const CYCLE = 8.0, STOPS = 160, R = 34.0, HUB = 4.5;
  // (rpm in the game's shaft rad/s, at these times, eased between)
  const RUN = [[0, 8], [0.8, 8], [2.6, 78], [4.2, 78], [5.6, 46], [6.6, 46], [8, 8]];
  // (the rim highlight's own turn: a steady fraction of the shaft's, a sheen sliding round the rim)
  const RIM_RATE = 0.06;
  const BLADES_BELOW = 40, DISC_FROM = 16, DISC_FULL = 50, STREAK_FROM = 26, STREAK_FULL = 64, TOP = 78, HOLD = 2.0;
  const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
  const rpmAt = (t) => {
    for (let i = 1; i < RUN.length; i++) if (t <= RUN[i][0]) {
      const [t0, r0] = RUN[i - 1], [t1, r1] = RUN[i];
      return r0 + (r1 - r0) * smooth(t0, t1, t);
    }
    return RUN[RUN.length - 1][1];
  };
  // (src/prop_disc.jo prop_band_speed, line for line)
  const bandSpeed = (rpm) => {
    if (rpm <= BLADES_BELOW) return rpm;
    const x = Math.min(1, Math.max(0, (TOP - rpm) / (TOP - BLADES_BELOW)));
    const k = 0.7, TAU = Math.PI * 2;
    const u = 0.03 + (2.0 + Math.acos(-k) / TAU - 0.03) * x;
    const th = u * TAU;
    let shape = Math.atan2(k * Math.sin(th), 1 + k * Math.cos(th)) / Math.asin(k);
    let e = Math.min(1, Math.max(0, x / 0.2)); e = e * e * (3 - 2 * e);
    const g = 1 + HOLD * e;
    shape = Math.tanh(g * shape) / Math.tanh(g);
    let r = Math.min(1, Math.max(0, x / 0.35)); r = r * r * (3 - 2 * r);
    return (5 + (BLADES_BELOW - 5) * r) * shape;
  };
  // The timetable: for each stop, the blades' and the bands' angles (degrees, clockwise; each
  // cycle closing on itself, a two-bladed prop being the same every half turn) and the layers'
  // opacities.
  const table = () => {
    const out = [], n = 2400, dt = CYCLE / n;
    let blade = 0, band = 0, rim = 0;
    const raw = [];
    for (let i = 0; i <= n; i++) {
      const t = i * dt, rpm = rpmAt(t);
      raw.push([blade, band, rpm, rim]);
      blade += rpm * dt; band += bandSpeed(rpm) * dt; rim += RIM_RATE * rpm * dt;
    }
    const close = (total) => { const half = Math.PI; return Math.round(total / half) * half - total; };
    const fixBlade = close(raw[n][0]), fixBand = close(raw[n][1]), fixRim = close(raw[n][3]);
    for (let s = 0; s <= STOPS; s++) {
      const i = Math.round(s * n / STOPS), [b0, d0, rpm, r0] = raw[i], f = i / n;
      out.push({
        blade: (b0 + fixBlade * f) * 180 / Math.PI,
        band: (d0 + fixBand * f) * 180 / Math.PI,
        rim: (r0 + fixRim * f) * 180 / Math.PI,
        blades: 1 - smooth(BLADES_BELOW - 4, BLADES_BELOW + 4, rpm),
        disc: smooth(DISC_FROM, DISC_FULL, rpm),
        arcs: smooth(STREAK_FROM, STREAK_FULL, rpm),
        rpm
      });
    }
    return out;
  };
  // (src/prop_disc.jo _disc_hash)
  const hash = (x) => { const v = Math.sin(x * 12.9898) * 43758.547; return v - Math.floor(v); };
  // One drawing's pencil arcs, as the game draws them: per blade a band of short arcs about the
  // hub, each of random length and offset, a few left out. [radius, from, to] in radians clockwise
  // from straight up.
  const arcs = (variant) => {
    const list = [], dr = 3.0, r0 = HUB + 2.5;
    for (let k = 0; k < 2; k++) {
      const s = variant * 17.3 + 7.13 * k, axis = k * Math.PI;
      for (let j = 0; r0 + (j + 1) * dr < R; j++) {
        const hs = s + j * 1.37;
        if (hash(hs + 3.3) <= 0.12) continue;
        const rr = r0 + (j + 0.5) * dr + 0.3 * dr * (hash(hs) - 0.5);
        const w = (0.12 + 0.10 * rr / R) * R;
        const centre = (hash(hs + 1.1) - 0.5) * w * 0.9;
        const reach = w * (0.25 + 0.9 * hash(hs + 2.2));
        list.push([rr, axis + (centre - reach) / rr, axis + (centre + reach) / rr]);
      }
    }
    return list;
  };
  // (the disc's rim highlight: two bright arcs, opposite, turning at their own rate, RIM_RATE)
  const RIM = [0, Math.PI].map((k) => [k + Math.PI / 4 - 0.6, k + Math.PI / 4 + 0.6]);
  root.AegeanLoadingProp = { table, arcs, rpmAt, bandSpeed, hash, CYCLE, STOPS, R, HUB, RIM };
  if (typeof module !== "undefined") module.exports.AegeanLoadingProp = root.AegeanLoadingProp;
})(typeof globalThis !== "undefined" ? globalThis : this);

// The title screen (src/title_screen.jo, aegean.jo title_wanted). A page whose URL stages a
// capture (any AEGEAN_ option but quality, touch and title) starts straight in the game, as the
// native runs with those environment variables do. While the module loads and the world is built
// (long steps the page cannot draw during), the page shows a small propeller turning on the
// title's dusk colour, no words, turned by the compositor. The game then reports its own
// preparation as a ring filling round it, and takes the card away when the title has drawn its
// first frame; without the title, at the game's first frame.
(function (root) {
  if (typeof sloppy === "undefined" || typeof location === "undefined") return;
  // (Sloppy 0.34.1's own "loading..." words: nothing before the title has words)
  if (typeof document !== "undefined") document.getElementById("sloppy-loading")?.remove();
  const keys = [...new URLSearchParams(location.search)].map(([k, v]) => [k.toUpperCase(), v]);
  const title = keys.find(([k]) => k === "AEGEAN_TITLE")?.[1];
  const staged = keys.some(([k]) => k.startsWith("AEGEAN_") && !["AEGEAN_QUALITY", "AEGEAN_TOUCH", "AEGEAN_TITLE"].includes(k));
  sloppy.env.__aegean_staged = () => staged ? 1 : 0;
  let card = null;
  sloppy.env.__aegean_shown = () => { if (card) { card.remove(); card = null; } };
  // (while the game prepares the world before its title: which step, and how far, 0..1: the ring fills)
  sloppy.env.__aegean_progress = (stage, fraction) => {
    if (!card) return;
    const f = Math.max(0, Math.min(1, Number(fraction)));
    card.querySelector(".fill").setAttribute("stroke-dashoffset", String(251.3 * (1 - f)));
  };
  const wanted = title !== undefined ? title !== "0" : !staged;
  if (!wanted || typeof document === "undefined" || document.title !== "Aegean Skies" || !document.body) return;
  // The loading propeller (above), small and centred on the dusk, no words; a faint ring round it
  // fills as the game reports its preparation. Every layer its own element, so the compositor
  // turns and fades it alone. All drawn here, no image file.
  const P = root.AegeanLoadingProp, rows = P.table();
  const pct = (s) => (100 * s / P.STOPS).toFixed(3) + "%";
  const frames = (name, f) => "@keyframes " + name + "{" + rows.map((r, s) => pct(s) + "{" + f(r) + "}").join("") + "}";
  const blade = "M0,-3 C5,-6 7,-22 2,-33 C1,-35 -1,-35 -2,-33 C-7,-22 -5,-6 0,-3 Z";
  const at = (r, a) => (r * Math.sin(a)).toFixed(2) + "," + (-r * Math.cos(a)).toFixed(2);
  const arcPaths = (v) => P.arcs(v).map(([r, a0, a1]) => '<path d="M' + at(r, a0) + 'A' + r.toFixed(2) + ',' + r.toFixed(2) + ' 0 0 1 ' + at(r, a1) + '"/>').join("");
  const layer = (cls, inner) => '<div class="' + cls + '"><svg viewBox="-44 -44 88 88">' + inner + '</svg></div>';
  card = document.createElement("div");
  card.id = "aegean-loading";
  card.setAttribute("role", "progressbar");
  card.setAttribute("aria-label", "Loading");
  const ease = " " + P.CYCLE + "s linear infinite";
  card.innerHTML = '<style>#aegean-loading{position:fixed;inset:0;z-index:5;background:#131a26;display:flex;align-items:center;' +
    'justify-content:center}#aegean-loading .stage{position:relative;width:88px;height:88px}' +
    '#aegean-loading .stage>div,#aegean-loading .stage>svg,#aegean-loading .band>div{position:absolute;inset:0;width:88px;height:88px;will-change:transform,opacity}' +
    '#aegean-loading svg{width:88px;height:88px;overflow:visible;display:block}#aegean-loading .fill{transition:stroke-dashoffset .3s linear}' +
    '#aegean-loading .blades{animation:aegean-blade-turn' + ease + ',aegean-blade-show' + ease + '}' +
    '#aegean-loading .disc{animation:aegean-disc' + ease + '}' +
    '#aegean-loading .rim{animation:aegean-rim' + ease + '}' +
    '#aegean-loading .band{animation:aegean-band-turn' + ease + '}' +
    '#aegean-loading .v{animation:aegean-flip .25s step-end infinite}' +
    '#aegean-loading .v1{animation-delay:-.1667s}#aegean-loading .v2{animation-delay:-.0833s}' +
    '@keyframes aegean-flip{0%{opacity:1}33.333%{opacity:0}100%{opacity:0}}' +
    frames("aegean-blade-turn", r => "transform:rotate(" + r.blade.toFixed(2) + "deg)") +
    frames("aegean-blade-show", r => "opacity:" + r.blades.toFixed(3)) +
    frames("aegean-disc", r => "opacity:" + r.disc.toFixed(3)) +
    frames("aegean-band-turn", r => "transform:rotate(" + r.band.toFixed(2) + "deg);opacity:" + r.arcs.toFixed(3)) +
    frames("aegean-rim", r => "transform:rotate(" + r.rim.toFixed(2) + "deg);opacity:" + r.disc.toFixed(3)) +
    '</style><div class="stage">' +
    '<svg viewBox="-44 -44 88 88"><circle r="40" fill="none" stroke="rgba(217,212,196,.10)" stroke-width="1.5"/>' +
    '<circle class="fill" r="40" fill="none" stroke="rgba(199,158,82,.55)" stroke-width="1.5" stroke-dasharray="251.3" ' +
    'stroke-dashoffset="251.3" transform="rotate(-90)"/></svg>' +
    layer("disc", '<circle r="' + P.R + '" fill="rgba(217,212,196,.16)"/><circle r="' + (P.R - 0.8) + '" fill="none" stroke="rgba(217,212,196,.32)" stroke-width="1.1"/>') +
    layer("rim", '<g fill="none" stroke="rgba(250,244,228,.9)" stroke-width="1.8" stroke-linecap="round">' + P.RIM.map(([a0, a1]) => '<path d="M' + at(P.R - 0.8, a0) + 'A' + (P.R - 0.8) + ',' + (P.R - 0.8) + ' 0 0 1 ' + at(P.R - 0.8, a1) + '"/>').join("") + '</g>') +
    '<div class="band">' + [0, 1, 2].map(v => layer("v v" + v, '<g fill="none" stroke="rgba(240,232,210,.92)" stroke-width="1.4" stroke-linecap="round">' + arcPaths(v) + '</g>')).join("") + '</div>' +
    layer("blades", '<g fill="#c79e52" opacity=".85"><path d="' + blade + '"/><path d="' + blade + '" transform="rotate(180)"/></g>') +
    '<svg viewBox="-44 -44 88 88"><circle r="' + P.HUB + '" fill="#8a6a35"/></svg></div>';
  document.body.appendChild(card);
  // A program that fails to start, or panics, says so with a `sloppy:error` event (Sloppy 0.36.1;
  // the text in its detail) and shows the page's log (#log): take the card away then, which would
  // otherwise cover the error for good, leaving the propeller turning on nothing. (An exit() with
  // a failing code only shows the log, with no event: watched for too.)
  const drop = () => { if (card) { card.remove(); card = null; } };
  window.addEventListener("sloppy:error", drop);
  const log = document.getElementById("log");
  if (log && typeof MutationObserver !== "undefined") {
    const watch = new MutationObserver(() => {
      if (!card) { watch.disconnect(); return; }
      if (log.style.display === "block") { drop(); watch.disconnect(); }
    });
    watch.observe(log, {attributes: true, attributeFilter: ["style"]});
  }
})(typeof globalThis !== "undefined" ? globalThis : this);
