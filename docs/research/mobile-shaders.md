# WebGL2 startup portability

The build on `9656387`, compiled with Sloppy 0.29.2, makes built-in lighting
programs during `init_curved_world()` → `__3d_init()`, including shaders the game
does not draw with. The generated `LitParams` contains 192 vec4 bone rows plus
matrices, point lights and material parameters. Chromium/ANGLE exposes the entire
struct (240 conservative vector rows) as active even in the ordinary unskinned
program. The guaranteed WebGL2 fragment budget is only 224. Removing function
parameter passing alone still leaves all those fields active on the tested ANGLE
backend; they must be separately declared uniforms.

This is an identified portable-limit violation and a strong explanation for the
reported phone startup link failure, not a confirmation on that particular phone.
Its empty driver log did not identify a program, and the phone was unavailable.
The sea's shadow quads are within budget.

## Shipping compatibility pass

`src/web_compat.js` is loaded by the game's build block. It specializes generated
read-only uniform-struct parameters to globals, then declares the referenced fields
as independent uniforms. Uniform location lookups translate the names; all native
byte layouts, texture binding, arrays, bone capacity and materials stay intact.
Only the generated `S_*` / `f_*` GLSL grammar is supported; unsupported uniform
copies/mutations/arguments fail instead of silently changing behavior. This is a
project-local bridge, not a general GLSL optimizer. Native Vulkan is unaffected.

Linked ordinary lighting drops to 46 conservative rows (44 for instancing).
The skeletal program retains all 64 joints: 207 maximum vertex rows, 33 fragment
rows; its *combined* active count can exceed 224 without violating a per-stage
limit. Across all 58 embedded shader stages the largest fragment program is the
far sea, 60 rows; at most 5 varying vectors, 9 attribute locations, and 3 fragment
samplers (2 vertex samplers). The count charges each scalar its own row and includes
array lengths, matrix columns and nested structs. Floats and integers are explicitly
highp in both stages; existing sampler defaults match. No new precision downgrade.

`node tools/check_web_shaders.cjs site/index.html` audits the actual embedded or
packaged Wasm's GLSL, after the same transformation used at runtime. `--raw`
demonstrates the baseline budget failures. The Pages workflow runs this audit and
`tools/web_compat_test.cjs`; unknown resource types are errors. Browser probes also
link real programs and record their sources. The static gate deliberately does
not pretend that overriding `getParameter()` clamps a GPU's physical limits.

The runtime now includes vertex/fragment entrypoints, capability limits and stage
logs in a link failure; an empty driver log is explicitly labeled. This ensures a
subsequent phone report is actionable even if that driver has a second issue.

## For the Sloppy maintainers

Please specialize read-only uniform struct arguments in `compiler/glsl.jo`, expose
fields independently, and update `gl_udesc()` names accordingly (or implement an
equivalent shader-stage uniform-liveness solution). Reproduce using a uniform
struct with a used color and an unused `vec4[240]` field; merely removing the unused
field's expressions/function arguments was insufficient on tested Chromium/ANGLE.
Do not shrink the 64-joint palette or silently truncate arrays.

Also enhance `lib/web/gfx.js:glCreateProgramFrom`: it currently reports only
`getProgramInfoLog(p)`, which some mobile drivers return empty. Include both shader
logs, shader entrypoint/source identity and relevant GPU limits. No changes were
made to the shared slop-lang checkout. Remove this game's compatibility pass once
a released compiler provides the fix and the same budget/link tests pass.

Specifications: [WebGL2](https://registry.khronos.org/webgl/specs/2.0.0/),
[Khronos WebGL2 reference](https://www.khronos.org/files/webgl20-reference-guide.pdf).
