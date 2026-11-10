# Speed research: Aegean Skies

Research by code inspection, 2026-11-10. No repository files changed; `src/living_*.jo` excluded. I did not play or record either game, so statements about the resulting image are hypotheses grounded in the code and the designer's reported experience. Constants below are starting points for trials, not validated tuning.

## Recommendation

First make ordinary sea detail readable and continuous at every speed, then replace the camera's speed-driven noise with bounded inertial movement, then strengthen water contact and real near passes. Disable HUD streaks during this work. Do not increase flight speed. The most important question is whether a clean, silent, constant-speed low pass already looks fast before any camera or audio effects are enabled.

## 1. Diagnosis specific to this implementation

### The scene contains motion, but loses its best measuring marks

`src/sea.jo` already has the right foundation: `_fleck` uses world coordinates, and `_swell`, `_ripples`, `_strokes` are world-space fields. Camera-centered mesh rings do NOT mean the texture is camera-locked: `sea_vs` adds `u.cam.xz` before evaluating the field. Keep that property.

However, the meter-scale, light/dark `_fleck` field is visible only through `_rush`, gated by `rush_of` (15–60 m/s and camera height 30–260 m). Its visibility changes with speed. This teaches the eye that a special texture effect has switched on, rather than letting recognizable marks accelerate continuously from rest. `_ripples` mainly alters normals, not body contrast; its shortest 0.8 m component fades over 11.2–48 m and the 3.1 m component over 43.4–186 m. `_strokes` has roughly 9 m rows, broken and moving 2.4 m/s; these help but are thin and anisotropic. Sun glints explicitly re-randomize tilt several times per second, making them a poor sole tracking reference.

`_rush` uses a **0.1 second** world-space exposure: 8.5 m at 85 m/s, six 60 Hz frames of travel. It samples 13 times and divides by **5**, not 13, so blur also increases energy/contrast. At this speed the taps are ~0.71 m apart, comparable to a fleck's dimensions: distinct repeated marks can replace a continuous smear. This is not a full camera shutter model: it ignores camera rotation, vertical motion, projection and visibility. `aegean.jo:365` even passes aircraft velocity, although the uniform is described as camera velocity. The effect can disagree with the spring/lagged viewpoint during a turn or transient.

### The camera already lags, but its lag is mostly towing distance

`src/pilot.jo:130–163`, `chase`: forward is exponentially smoothed at 5/s and position at 9/s. A first-order follower of a constantly translating target has a persistent tracking offset. At 60 Hz, the discrete position lag at 85 m/s is about 8.8 m, in addition to the desired ~12.5–16 m back. Simply making that filter slower will mostly make the aircraft smaller and farther away; it will not create an acceleration-specific spring.

Surge is only the derivative of scalar speed, clamped -8..12 m/s², filtered at 3/s and added to distance at 0.45 seconds². It cannot distinguish a lateral turn from straight motion. Low/fast flight shortens and lowers the desired mount, potentially counteracting the acceleration pullback. The view target is the current aircraft plus 30 m of smoothed forward, so target and eye have different movement histories. This can swing the horizon as a side effect of position error.

`feel` and `place_chase_camera`, lines 167–188, add unrelated noise: on water shake rises from 4 m/s to its maximum by 40 m/s, irrespective of contact load or sea phase. Target jitter is ten times eye jitter. Above the water, speed/altitude and an unsigned turn estimate drive more shake. The load estimate `1 + turn*speed/g` counts downward/sideways trajectory changes as extra positive load; it is useful as an activity estimate, not a physical g reading. These are plausible causes of the reported unearned takeoff shake.

FOV expands 58°–82° over 25–110 m/s, with 0.5 s smoothing. At 85 m/s it is roughly 77°. Wider FOV includes peripheral water but shrinks central landmarks; expansion can look like zooming out and cancel looming. It cannot compensate for absent nearby detail.

### Existing cues need better causal agreement

`_fly_air` in `src/flight.jo:218–296` DOES already perturb orientation and vertical velocity with low-altitude, speed- and wind-scaled noise. Avoid adding another generic turbulence layer. This roughness is driven by time and ground clearance, not actual spatial cliff eddies. The arcade model also steers velocity toward forward with `arc_grip` and auto-trims the path; calm, assisted cruise is intentionally stable. Preserve that accessibility; create urgency through safe proximity and acceleration feedback before weakening controls.

Physical water in `flight.jo:97–106` uses two waves and local `state.time`; rendered water uses six different wind-oriented wavelengths and global `t`. `flight_env` supplies wave amplitude but `wave_time=0`. Spray is emitted at y=0.1, and wake geometry is y=0.06, regardless of rendered swell. Thus visible crests, float contact, foam, and camera disturbance need not coincide. Earned impacts require aligning at least the large contact waves first.

Spray emission in `pilot.jo:206–219` is per update, not time/distance accumulated, so density depends on frame rate. Existing `src/wake.jo` is a real persistent world trail (good), but points at 0.2 s spacing are ~9.4 m apart at a 47 m/s departure. Its strength saturates at 25 m/s. No distinct water-contact audio exists in `src/sound.jo`: surf follows a rough shore proxy, engine throttle, wind speed. Also `aegean.jo:305` supplies ground-speed magnitude as the parameter called airspeed. These systems cannot yet communicate the change from displacement taxi to planing to release cleanly.

Clouds are mostly 150–2300 m wide, based around 640–860 m or higher (`clouds.jo:build_puffs`). They give scale but seldom nearby motion during sea-level flight. Bird flocks really are near-world content, but mostly along coasts and harbors (`birds.jo:build_flocks`), leaving open sea without discrete near passes. Do not fill the entire sea with gulls to solve this.

## 2. What μZero2 actually does

Primary sources fetched with `gh api` from `archive/udewy`, resolved HEAD `9a12cfbc7bcae33d47bb4ca4526168a8d55fccfd`. Links below are pinned to that revision. Local fetched excerpts are in the sibling `uzero2-source` folder.

- [constants.udewy, lines 87–147](https://github.com/david-andrew/dewy-lang/blob/9a12cfbc7bcae33d47bb4ca4526168a8d55fccfd/udewy/tests/uzero2/constants.udewy#L87): hover height 1.5 m, camera back 15 m/lift 4 m, position alpha 0.12, orientation alpha 0.10. This is a surface racer with a consistently nearby textured plane. Its `TOP_SPEED=500000` Q16 is **7.63 m per simulation frame**, not 7.63 m/s. At an assumed 60 simulation frames/s that is 458 m/s; boost bonus would add 366 m/s. These are conditional conversions, not a verified runtime rate. Aegean should not try to match its literal world displacement.
- [render_world.udewy](https://github.com/david-andrew/dewy-lang/blob/9a12cfbc7bcae33d47bb4ca4526168a8d55fccfd/udewy/tests/uzero2/render_world.udewy#L323) draws a checkered apron, textured track, and textured rail strips (`draw_segment_rails`, line 461). Track edges, rails and repeating surface material provide persistent size/spacing references. Translate this to multiscale water marks and coastal routes, not painted road grids over the Aegean.
- [parallax_world.udewy](https://github.com/david-andrew/dewy-lang/blob/9a12cfbc7bcae33d47bb4ca4526168a8d55fccfd/udewy/tests/uzero2/parallax_world.udewy) makes seams and fasteners in `parallax_prepare`, actual rings/trusses in `parallax_machinery`, and geometry-following dashed/edge guides in `parallax_guides`. Near architecture moves against a camera-relative distant sky. Its richness is layered **depth and passage**, not polygon count. Water can supply the floor, cliffs the side wall, and occasional rocks, boats and small cloud fringes the near silhouettes.
- [camera.udewy, update_chase](https://github.com/david-andrew/dewy-lang/blob/9a12cfbc7bcae33d47bb4ca4526168a8d55fccfd/udewy/tests/uzero2/camera.udewy#L14) smooths both orientation and position, re-orthogonalizes the basis, and permits a locally oriented up vector. `bank_target` affects the craft visual basis; do not misread it as directly banking the camera. Camera following of track up gives coherent changing orientation on inverted surfaces. Aegean can retain a mostly level horizon while letting the airplane visibly move against it.
- Its FOV punch multiplies frustum top by 1+0.4*speedNorm; [render_world.udewy:263](https://github.com/david-andrew/dewy-lang/blob/9a12cfbc7bcae33d47bb4ca4526168a8d55fccfd/udewy/tests/uzero2/render_world.udewy#L263) uses base top=near=2 m: 90° vertical at rest, about 109° at top speed. Copying that would strongly miniaturize this game's islands.
- [physics.udewy:505](https://github.com/david-andrew/dewy-lang/blob/9a12cfbc7bcae33d47bb4ca4526168a8d55fccfd/udewy/tests/uzero2/physics.udewy#L505) gives boost a real velocity impulse, overcap allowance and sound. Wall contact costs energy; rails, pits and turns make passage consequential. Its dramatic cues accompany real changes. Translate to takeoff release, diving energy gain, and controllable coastal slaloms, not a seaplane boost button.

Perception support: ground optical flow rate depends on translation relative to eye height; [Andersen et al., Visual cues for manual control of headway](https://www.frontiersin.org/journals/behavioral-neuroscience/articles/10.3389/fnbeh.2013.00045/full). Flow displays also need sufficient visibility/density to support steering, and heading judgments alone do not establish good steering performance: [Kountouriotis & Wilkie, 2013](https://eprints.whiterose.ac.uk/id/eprint/78728/). The recommendations below are my game-specific inferences, not experimental effect-size claims.

## 3. Ranked techniques

### 1. Persistent, readable water texture before motion effects

**Perception/why:** the same patches creep during taxi, then sweep underneath during departure. Continuous spatial references let the eye measure actual travel.

**Sketch:** in `sea_fs`, evaluate unblurred `_fleck(p)` at every speed, mixed into body color at modest 5–12% contrast. Use world-hashed patches at ~1, 3 and 10 m scales, with irregular occupancy rather than three equally strong noise bands. Retain readable midscale crests. Fade/filter each band by projected footprint, preferably world-coordinate derivatives if the shader language supports them; otherwise conservative distance/height LOD with wide crossfades. Keep the field independent of aircraft heading and speed.

**Cost/risk:** low-to-medium shader cost; aliasing and a dirty sea. **Do not:** brighten everything white, use a checkerboard aesthetic, or make the fine band switch on at 60 m/s.

### 2. A bounded camera spring driven by actual vector acceleration

**Perception/why:** the aircraft gets ahead of its mount when accelerating and moves sideways against it in a turn; the camera catches up once the event ends. Motion has inertia and cause.

**Sketch:** replace position pursuit/surge/jitter with the model in section 4. Retain nose/velocity disagreement on screen. Treat mount framing and transient displacement separately.

**Cost/risk:** medium; clipping and excessive framing drift. **Do not:** get a spring by lowering the existing 9/s follow rate, or use repeated oscillation at constant cruise.

### 3. Lower the viewpoint deliberately, with measured framing

**Perception/why:** more near water in the lower/peripheral view supplies rapid flow. At a comparable viewing direction, flow scales approximately with speed/height.

**Sketch:** retain Gull back 14–16 m, lift initially 3–3.5 m relative to CG; the CG is itself above the sea. Test camera sea clearances ~4–7 m during the run. Keep the aircraft large enough to read float contact. Do not let speed simultaneously raise FOV, shrink following distance, lower mount and add shake; tune one at a time. Apply clearance to the actual integrated eye, not only the desired eye.

**Cost/risk:** low, but water/cliff clipping and plane occlusion. **Do not:** permanently pitch steeply down or drag the camera to wave-top height.

### 4. Make planing contact, spray and release one event

**Perception/why:** repeated visible float strikes, foam left behind, then sudden smooth airborne release establish speed, weight and a surface being escaped.

**Sketch:** share dominant rendered/contact wave phase and direction between `flight_env`, `sea_surface`, sea uniforms and spawn heights. Preserve stable physics substeps. Accumulate spray emission by traveled distance (~0.5–1 m spacing) with a particles/sec ceiling; use contact wetness and relative impact velocity. Resample fresh wake to ~1–2 m spacing at departure speed, with a point cap. Apply camera impulse only from measured contact impulse; stop the contact layer on liftoff.

**Cost/risk:** medium-to-high because wave agreement affects flight. **Do not:** make camera chatter proportional to speed alone, or triple every particle count.

### 5. Build a few strong coastal passage routes

**Perception/why:** a nearby rock/cliff sliding against a remote island makes speed and clearance immediately legible; upcoming decisions create urgency.

**Sketch:** add visual boulders, rock shelves, channel markers and anchored fishing boats through non-living world/object rendering paths. Choose existing channels with pass distances ~20–60 m and events roughly every 1–3 seconds at 70–90 m/s. Keep a broad safe bypass; silhouettes should be readable several seconds ahead. This is content placement, not a new mission system.

**Cost/risk:** medium, art/content and collision agreement. **Do not:** clutter open ocean uniformly, manufacture invisible collision, or turn every island into a race gate.

### 6. Replace long smear with short, optional exposure

**Perception/why:** slight edge softness reinforces displacement while preserving trackable patches.

**Sketch:** first remove `_rush` entirely for baseline trials. If needed restore normalized taps (divide by tap count), short exposure ~1/120–1/90 s and actual camera displacement velocity. At 85 m/s this is ~0.7–0.94 m world smear. A real screen-space velocity solution is a later renderer project; the sea-only approximation must remain subtle and cannot model turns correctly.

**Cost/risk:** low to remove; medium to implement well. **Do not:** retain 100 ms trails, gain contrast through the divisor, or implement full-scene motion blur before proving a benefit.

### 7. Separate engine effort, air rush and water rush in audio

**Perception/why:** more throttle immediately means effort, airspeed gradually means wind, and wet float contact means harsh spray. Their different timing makes acceleration intelligible.

**Sketch:** pass `length(velocity-env.wind)` for wind, throttle/RPM proxy for engine, and speed relative to water plus wetness for a new planing hiss. Crossfade a deeper wind loop and a brighter high-speed loop rather than pitching one loop across the whole range. Smooth gains over 0.1–0.3 s; allow contact transients to decay ~0.1 s. Leave headroom for pass-bys.

**Cost/risk:** medium, sound design; repeated loops and fatigue. **Do not:** apply Doppler to the player's own engine based on ground speed or make the world loud continuously.

### 8. Keep FOV modest and let acceleration move the plane

**Perception/why:** islands grow reliably instead of shrinking under a broad zoom; peripheral coverage remains useful.

**Sketch:** A/B fixed 65–68° against 64°+8°*smoothstep(30,100,airspeed), smoothing ~0.3–0.5 s. These assume the engine API takes vertical degrees; verify that before comparing to μZero2. Start without an acceleration FOV kick because the spring already conveys that event.

**Cost/risk:** low; narrow FOV can hide periphery. **Do not:** assume larger FOV monotonically increases speed perception, or run a dramatic zoom pulse on throttle input without real acceleration.

### 9. Add cloud-edge encounters at flight altitude

**Perception/why:** a bank of cloud supplies a near moving contour against distant sky; entering/exiting briefly changes visibility and apparent scale.

**Sketch:** retain big cumulus fields; add sparse 20–80 m fringe puffs near their edges, preserving global placement/wind drift and culling. Make cloud penetration visually coherent with a short local haze transition; current opaque sphere surfaces otherwise reveal their construction when crossed. Start with near skims before interior traversal.

**Cost/risk:** medium-to-high; opaque intersections, overdraw and popping. **Do not:** spawn white particles in front of the camera everywhere, or use low sea-level clouds solely to simulate ground speed.

### 10. Earn instability through the existing aircraft model

**Perception/why:** the airplane responds to gusts before the following camera, so the disturbance has a visible body and recoverable consequence.

**Sketch:** inspect existing `_fly_air` roughness with camera jitter off. If insufficient, replace time-only gust sampling with a smooth world-space field advected by wind, including localized lee-side amplitude near cliffs. Start with angular deviations below ~1–2° and keep assistance effective. Use measured acceleration to drive the camera, not the same noise twice.

**Cost/risk:** medium/high; handling regressions. **Do not:** weaken controls, add random yaw, or make clear calm air perpetually unstable merely to score speed points.

### 11. Use occasional real near objects, remove persistent HUD lines

**Perception/why:** a rare gull or mast sweeps across the periphery at actual depth; it marks a meaningful pass rather than announcing a speed threshold.

**Sketch:** retain coastal `build_flocks` and select a few route-adjacent centers; ensure their scale remains 1.3 m. Add spatial pass-by sounds only near actual sources. Disable `speed_streaks` while judging the core; if retained, limit to a deliberate stylistic extreme and provide an option. Existing 48 radial lines use screen width for both axes and are not depth or occlusion aware.

**Cost/risk:** low-to-medium; nuisance birds and contrivance. **Do not:** camera-follow particle shells, guaranteed near misses every few seconds, or opaque objects that magically spawn ahead.

## 4. Concrete chase camera model

Use a kinematic mount with a bounded inertial offset, not a free spring chasing absolute world position. This avoids velocity-dependent permanent towing distance. The airplane remains the anchor; a transient mass explains the camera's struggle.

Let `P,V,Q` be aircraft world pose/velocity. Maintain a smoothed mount forward `F` from a blend of nose and velocity: `Ftarget = normalize(0.8*nose + 0.2*normalize(V))` above 15 m/s; below that use nose. Smooth angularly with time constant 0.15 s. Guard zero vectors and antiparallel directions. Keep world-up framing except near vertical flight, where a transported previous right vector avoids singularities. Use the same mount basis for eye and aim.

For Gull, base eye `B=P-15*F+3.5*worldUp`; Heron `B=P-26*F+6*worldUp`. Set these by airframe framing; initially remove the existing speed-dependent offsets. Add world-space transient displacement `x` and velocity `u`, initialized to zero on boarding/reset/teleport:

```
aRaw = (V - previousV)/dt
a = exponentialLowPass(aRaw, tau=0.12 s)
a = clampComponentsInMountFrame(a, forward=+-12, right=+-15, up=+-15) # m/s²
x'' + 2*zeta*omega*x' + omega²*x = -gain*a
omega = (5.0 forward, 6.0 right, 7.0 up) # rad/s, not Hz
zeta  = (0.90, 0.95, 1.00)
gain  = (2.5, 1.8, 1.2) # dimensionless
E = B + x
```

Apply the diagonal coefficients along the current mount axes, with `x,u` stored in world space to avoid silently rotating stored energy when the mount turns. At 5 m/s² longitudinal acceleration, quasi-static displacement is -0.5 m; at 12 m/s², -1.2 m. Bound displacement to ±2.0 m forward, ±1.2 m sideways, ±0.7 m vertically. On hitting a bound remove outward offset velocity. The system should settle in roughly a second, with no visible repeated bob. Gain can be doubled only after testing framing; do not simply lower omega to produce long oscillation.

Integrate at <=1/120 s with semi-implicit Euler or a stable damped-spring integrator. With a world-space diagonal operator formed from the mount basis, update `u += (-K*x-D*u-gain*a)*h; x += u*h`. Low-pass acceleration once per frame (or consistently per substep), never recompute a new derivative from repeated identical frame velocities. For paused/zero dt skip derivative; initialize previousV to current V on camera placement. Reset on teleports, respawn and boarding.

Aim at `T=P+F*24+worldUp*1.0`, using the shared angularly smoothed mount frame; compute actual eye-to-target direction after displacement. At steady straight cruise, `a→0`, `x→0`: **speed alone creates no spring deflection**. During acceleration the eye drops back while the plane advances; in a turn lateral acceleration creates visible lag. If direction smoothing and offset together cause excessive lag, reduce lateral gain before speeding up aircraft steering.

Apply terrain/water safety to actual `E` after integration. Clamp minimum clearance to ~1.5–2 m above the shared surface, cancel inward vertical offset velocity, and sweep the segment from aircraft to eye against terrain to avoid a camera behind a cliff. Smooth outward release from safety constraints. Never smooth penetration itself. This may need a reusable terrain query/sweep; current `surface_height(want)` alone does not cover the actual eye or intervening terrain.

Do not add arbitrary look-target jitter. Later add measured contact impulses to `u` (starting 0.05–0.15 m/s per perceptible strike, bounded ~0.4 m/s), filtered from actual float events, and test that it matches visible crests. Use smooth event envelopes rather than raw derivative spikes. Optional horizon bank should be tiny (<=3°), delayed ~0.3 s, and omitted from the first trial; the airplane banking against a stable horizon is already a strong cue.

For vapor/loads, compute specific force from vector acceleration if a physical approximation is needed: `specific = a - gravity`, project on aircraft up, normalize by g. Avoid claiming the existing unsigned curvature measure is equivalent. Keep aerodynamic airspeed, ground-relative optic flow speed, water-relative contact speed, and actual camera velocity separate.

## 5. Pitfalls and evaluation

Do not promise F-Zero intensity during level cruise at 1000–1500 m over empty ocean. With no nearby objects, that flight should feel expansive and calmer; a convincing contrast with a 5–15 m sea skim is a success. Preserve 50–125 m/s speeds, travel times, scale, and safe handling. More visual vibration can conceal rather than improve flow. Greater contrast, denser geometry and shorter LOD distances can cause aliasing/popping that masquerades as speed.

Make comparable recordings from reproducible initial poses, matching weather, hour, aircraft, resolution, FOV convention and input. Keep changes outside the living simulation. Suggested clips: taxi 0–20 m/s; full takeoff through release; straight low pass at 50 and 85 m/s; same speed at 15/100/1000 m altitude; banked coastal pass; approach and skim of a cloud edge; rapid throttle reduction then recovery. Use at least 30/60/120 Hz runs to expose frame-dependent spray and camera behavior. Do not benchmark desktop wall-clock performance; machine rules reserve timing for quiet `redfox`. On desktop, use counters, shader invocation/sample counts and captured frame cadence as diagnostics, not comparative performance claims.

A/B in stages: (A) current; (B) no streaks/no noise/no rush; (C) persistent sea detail; (D) new camera; (E) contact/audio; (F) near-route content. Keep a fixed-FOV version throughout. Ask the designer to rank unlabeled equal-speed clips for perceived speed, control confidence, weight and comfort; a faster-looking clip that obscures control is a failure. This is a proposed feel test, not one performed here.

In footage look for:

- Track one water mark from middle distance toward the lower edge: is it the same mark, or does it flicker, multiply, brighten or disappear? Can you see acceleration without looking at the HUD?
- Does the airplane surge ahead of the camera on acceleration, then settle at the same cruise framing? Overlay speed, vector acceleration, camera offset and spring velocity in a diagnostic capture.
- Does every significant takeoff camera pulse correspond to visible contact, spray or an aircraft response? Does release remove harshness immediately without a new arbitrary shake?
- At steady speed does the camera sit calmly while world detail continues rushing past? Is the low run visibly more urgent than high cruise with effects off?
- During turns, are cliff/sea motion, airplane bank and camera path coherent? Do marks remain world anchored? Does camera safety introduce a vertical pop?
- Are foam density and spring decay comparable across update rates? Inspect slow motion for aliasing, but judge feel at normal playback too.
- Listen separately, then watch muted: the wind should communicate airspeed and the image should still communicate surface travel. Their combination should agree about onset, contact and release.

Implementation order: water baseline + remove effects → bounded camera + safety → shared water/contact cues → coastal passage content → audio separation → cloud fringes. Restore a subtle exposure effect only if the clean version demonstrably benefits. A major renderer motion-vector pass is not justified until these cheaper changes have been compared.
