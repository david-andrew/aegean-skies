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
  root.AegeanWeb = { specializeUniforms, chooseTier, cappedSize, livingStoreEncode, livingStoreDecode, installLivingStorage };
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
      const [w,h] = cappedSize(canvas.width,canvas.height,canvas.clientWidth,canvas.clientHeight,maxPixels);
      if (canvas.width !== w) canvas.width = w;
      if (canvas.height !== h) canvas.height = h;
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
    return shaderSource.call(this, shader, specializeUniforms(source));
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
