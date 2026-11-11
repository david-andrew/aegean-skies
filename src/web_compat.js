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
  root.AegeanWeb = { specializeUniforms, chooseTier };
  if (typeof module !== "undefined") module.exports = root.AegeanWeb;
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
      const ratio = Math.min(1, Math.sqrt(maxPixels / Math.max(canvas.width * canvas.height, 1)));
      const w = Math.max(1, Math.floor(canvas.width * ratio)), h = Math.max(1, Math.floor(canvas.height * ratio));
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
