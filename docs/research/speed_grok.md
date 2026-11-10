# Speed feel: Aegean Skies vs μZero2

Independent read of the tree as it sits now (`src/pilot.jo` `chase`, `src/sea.jo`, `src/flight.jo` `_fly_air`, `src/sound.jo`, `src/clouds.jo`, `src/birds.jo`, `src/terrain.jo`, `src/look.jo`) and of μZero2 on `archive/udewy` (`camera.udewy`, `constants.udewy`, `render_world.udewy`, `render_hud.udewy`, `physics.udewy`, `parallax_world.udewy`).

Opinion up front: the aircraft is already fast enough, and the new chase spring is already a decent *acceleration* cue. Cruise still reads as slow because the center of the picture is aimed at the horizon, and the sea's contrast lives on wavelengths of several meters to tens of meters. μZero2 feels fast because a high-contrast surface sits a few meters from the lens for the whole race. Its speed lines and FOV punch are the fakery. Copying those, or turning the spring gain up further, will not fix this game.

Do not raise `max_speed`. Gull's arcade model already terminates near 85 m/s (`arc_thrust` 15.5, `arc_drag` 0.00215 → √(15.5/0.00215) ≈ 85). End-to-end of a 22 km archipelago at 70 m/s is about five minutes. The budget is optic flow per meter of altitude, not meters per second.

## 1. Diagnosis

### The picture looks along the horizon, so the fast water is a strip

`chase` (`src/pilot.jo`) parks the Gull about 15 m behind the path and, when low, drops the eye toward the water. The look point is not a pitch angle. It is a point 35 m ahead, lowered by `3.7 * low` meters:

```233:236:src/pilot.jo
T = P + fh * 35.0 + rh * f32(clamp(yaw_rate * sp * 0.3, -12.0, 12.0)) - uh * f32(3.7 * low)
want = normalize(T - c)
```

`low` also drops the camera, and it drops the camera *more* than the aim (`Lh = height - (height+1)*low`, height 4 m, so a full `low` moves the eye down 5 m and the aim down only 3.7 m). The center-ray depression therefore stays about 3–5° from cruise height all the way down to a skim.

What that does to flow. For a camera at height `h` the angular rate of the ground along the centerline is `v * h / (x² + h²)`, with `x` the horizontal distance to the patch. A 4° ray from 15 m hits the sea near 200 m, and at 70 m/s that patch moves at about **1°/s**. The eye sits on that patch. The bottom of a ~60° frame is the only place the sea is close, and it is a thin band the player does not track.

Getting the camera down to ~1.3 m (the swell clamp in `chase`) does not fix the center. A 3° ray from 1.3 m still lands ~20 m out: ~10°/s at 70 m/s. Real rush at that height is only on the extreme lower edge. The comment in `chase` says flow is `v/h`. That is true of the *nadir*, which this camera never looks at.

So the "low and fast" arm is doing the wrong geometric thing. It changes meters of camera height and meters of aim height by almost the same amount, and the angle that would put near water in the middle of the frame never moves.

### The sea's contrast is an octave too big, and the smear deletes the rest

What the eye can track:

- Swells in `_swell`: wavelengths 61, 37, 23, 13, 7.3, 4.1 m. Crest strokes (`_crest_strokes`) are contours of that height field, so the brightest lines have the swell's wavelength. At 70 m/s a 23 m crest takes a third of a second to pass a fixed point, and from the horizon-stare camera it crawls.
- Ripples are normal slopes of ~0.07, wavelengths 0.8–3.1 m, and they fade with distance (`smoothstep(len*14, len*60, dist)`). Shading, not albedo. Easy to lose against the crest lines.
- Flecks (`_fleck`) are the right idea — world-locked, ~1–2 m, signed albedo — on a 2.6 m lattice, empty in 45% of cells. Then `_rush` smears them along velocity for `exposure = 0.1` s, 13 taps, divided by 5. At 70 m/s that is a **7 m** streak. Motion blur this long removes the temporal flicker speed perception uses. The marks do stay world-locked (the comment is honest); the blur is what makes them read as a trick. `rush_of` gates them with `smoothstep(15, 60, speed) * (1 - smoothstep(30, 260, camera height))`, and `draw_sea` passes `pc.state.velocity`, not the camera's.
- Glints (`_glints`) retile with `log2(dist)` so a glint stays 1–2 pixels, and they re-roll several times a second (`tick = floor(t * …)`). They shimmer in place. A stationary sparkle is a surface property, not flow.
- Gust darkening is 55–160 m noise (`gust` in `src/look.jo`). Cat's paws are weather, and they move at the wind's drift, a few meters per second.

The mesh is not the problem. Rings start at 1.5 m and grow by ~4.5% (`build_sea_mesh`). Near the camera the triangles are fine enough to show a 1 m albedo if the shader had one.

### The spring is an acceleration cue with a zoom-out side effect

The offset spring is real, and the equilibrium is large enough to see:

`ë = -ω² e - 2ζω ė - g * a`, so at a steady acceleration `e = -g a / ω²`.

Gull shape is `(back 15, height 4, ω_long 2.2, gain_long 2.5)`. Longitudinal equilibrium is `e_z ≈ -0.52 * a_long` meters. An 8 m/s² takeoff surge sits the camera **~4 m** behind the anchor (clamp is -7…+3). It then settles on `4/(ζω) ≈ 3 s` at `ζ = 0.6`. That is a visible fall-behind.

It is the wrong visible. The aim point stays tied to the aircraft, so 4 m of extra arm shrinks the plane in frame and shows more horizon. Widening the view of a frozen horizon reads as slowing down, which is the opposite of the surge you just spent. Steady cruise stores `a = 0`, so the spring returns to zero and contributes nothing at the speed the player actually holds. A spring cannot be the cruise-speed device. μZero2 does not use one (below).

Other camera nits, smaller than the gaze bug:

- `D` grows with speed (`0.92 + 0.18 * sfrac`), another steady-state zoom-out, about 10% from stall to `max_speed`.
- Vertical axis `ω = 4.5`, `ζ = 0.45` is underdamped (~20% overshoot). A slam will bounce. The water clamp (`c.y = max(c.y, swell+1.3)`) does not write back into `cam_e` / `cam_ev`, so the integrator winds up against the sea and then springs free.
- Look-ahead into the turn clamps at ±12 m at ~50 m range, ~13° of aim. Fine as urgency, loose if the world under it is not moving.
- Roll `0.2 * bank` into `cam_up`, smoothed at λ = 3, is the right *kind* of horizon tilt. Keep it small.
- FOV `60 + 6*sfrac + clamp(0.6*(a_fast-a_slow), -3, 4)` is a sane replacement for the old `58+24*smoothstep(25,110,speed)`. The accel kick is a few degrees; the 4 m spring arm will dominate it and they will fight.
- `feel` still writes `shake` (stall buffet). `place_chase_camera` no longer reads it. Screen-space `speed_streaks` are gone. Good. Do not put either back.
- The *mesh* still vibrates from speed: `airframe` adds `smoothstep(5, 40, speed)*0.04` on the water and a speed term up to 0.035 in the air, and `obj_vs` runs that through `sin(time*47)` and `sin(time*71)`. That is still an unearned buzz, just on the wings instead of the horizon. Wings may flutter under load. They should not buzz because the airspeed indicator is high.

### The air is empty, and the big things are too big

- Clouds: bases at 640–860 m, puffs 150–2300 m, a 34 km field wrapped on the camera (`src/clouds.jo`). No hard edge, no small scud. Passing one is a slow shading gradient. Useless as flow below the cloud deck, which is where this game is played.
- Birds: coast and harbor only, 14–70 m, circling at a few tens of meters (`src/birds.jo`, culled at 2500 m). Nothing over open water at 10–30 m range.
- Grass exists (`src/grass.jo`, 1 m tufts) and is rebuilt around the person on foot, not the aircraft.
- Islands are a 14 m grid (`MESH_STEP` in `src/world.jo`). Shader detail that does exist (noise at 0.35 and 1.3 /m, strata `sin(y*0.55)` ≈ 11 m) fades across 60–260 m (`src/terrain.jo`). A cliff 40 m off the wing can feel fast; the open sea cannot borrow that.
- Spray emits only while `on_water`, 1–6 particles per float contact (`spray`). It cuts off on unstick instead of decaying. The wake is a real world-locked ribbon (`src/wake.jo`, a point every 0.2 s — 8 m apart at 40 m/s, a bit chunky).

### Audio is a louder version of the same noise

`update_audio`: engine pitch `0.7 + 0.55*throttle + airspeed/250` (85 m/s is +0.34), wind volume `(airspeed-8)/90` squared, wind pitch `0.7+1.1*w`. One noise loop, no height in it, no hull slap, no brightness change when the water gets close. A steady whoosh at a steady pitch is how you tell the player the speed is constant and moderate. The prop visually spins at `8 + 70*throttle` rad/s and the engine loop does not follow that rate.

### Takeoff

Shake-from-speed on the *camera* is gone, which is what the designer was right to hate. What remains: wing buzz from `airframe` ramping over 5–40 m/s, so it is already maxed before unstick (Gull stall 28 m/s, planing by ~27, airborne somewhere above that). Unstick itself has no camera event. The spring will have been sitting ~4 m back for the whole run and will crawl forward over ~3 s after acceleration flattens, with no "released from the water" beat. Spray stops cold.

## 2. What μZero2 actually does

μZero2 is locked at 60 fps (`FPS_LOCK_DEFAULT`). `TOP_SPEED = 500000` Q16 is 7.6 m/frame, **~460 m/s**. Boost adds another ~6 m/frame. That number does not transfer. A seaplane at 460 m/s empties the archipelago. What transfers is the distance from the lens to a contrasted surface.

The chase arm is **constant**. `CAM_BACK = 15 m`, `CAM_LIFT = 4 m` (`constants.udewy`). Nothing in `update_chase` lengthens the arm with speed. Hover height is 1.5 m, minimum camera clearance 3.5 m plus another 3.5 m at top speed so the widened frustum does not clip. The road lives a few meters under the lens for the entire race, in the lower two-thirds of the picture, including through the center of the gaze. That is the whole trick. There is no sea-sized region whose nearest texture is 200 m away.

Position and orientation are first-order lags, not a spring: `POS_ALPHA = 0.12` per frame (λ ≈ 7.7/s), `ORIENT_ALPHA = 0.10` (λ ≈ 6.3/s). No overshoot, no accel gain, no steady-state lag at constant velocity on a straight. The "can't keep up" feeling is cornering at 460 m/s, where lateral acceleration is tens of g and a 0.12 follow leaves meters of error. At seaplane accelerations (a coordinated 45° bank is 1 g) the same alphas leave a fraction of a meter. Copying 0.12/0.10 will not reproduce μZero2, and the second-order gain now in `chase` (4 m at 8 m/s²) is a different machine than μZero2's camera.

`BANK_*` rolls a *visual* craft basis (`vrx`/`vux` in `camera.udewy`). The view matrix is built from the unbanked `cam_fx`/`cam_ux` (`apply_camera` in `render_world.udewy`). The horizon follows the craft's up, which on a track is the road's up. It is not world-up camera shake. Aegean's `0.2 * bank` into `cam_up` is the closer analogue for a plane, and it is enough.

FOV: frustum top at the 2 m near plane goes from 2.0 to 2.0×(1+0.4×speed_norm) (`FOV_PUNCH = 0.4`). Vertical FOV runs from about 90° to about 109°. They can spend that because the extra periphery is still road. Aegean's extra periphery at 15 m and 4° depression is sky and horizon. The current +6° with speed is plenty. Do not import 0.4.

The surface itself:

- `CHECKER_TILE = 5 m` (the apron actually uses 40 m). Track UVs are baked; parallax mode's textures are 32×32 with panel seams and fastener pixels (`parallax_prepare` in `parallax_world.udewy`). High contrast, repeated, world-locked, smaller than the travel in a few frames.
- At 70 m/s the matching feature size is about `v/60 ≈ 1.2 m` if you want roughly one feature per frame at 60 fps, in the band the center of the screen actually sees. μZero2's 5 m tiles at 460 m/s are the same *temporal* frequency (~11 ms per tile). Aegean's 2.6 m flecks, smeared over 7 m, seen at 200 m, are not.
- LOD (`parallax_mesh_step`) only drops triangles with distance. It does not delete the albedo.

What does **not** transfer, and is the same family as the thing the designer already called fake:

- `draw_speed_lines` (`render_hud.udewy`) is an overlay of radial segments in *pixels*, from the screen center, gated on `vis_boost_norm > SPEED_LINE_THRESHOLD` (25000/65536 of speed/(top+boost), i.e. only once already well up the speed range). Peak alpha 0.8, plus a 4 px shake. Aegean already deleted this. Leave it deleted.
- Sparks are collision bursts. The boost trail is attached to the craft. Both are garnish on top of the road, not a substitute for it.
- Hover bob (`BOB_AMP ≈ 0.3 m`) is a hover character. Do not bob a seaplane.

Translation, one sentence: build a patch of sea the gaze cannot avoid, a few tens of meters out, covered in world-locked contrast about a meter across, and stop blurring it. The camera's job is to keep that patch in the middle of the frame whenever the aircraft is low. The spring's job is only to shove the aircraft a little in the frame when acceleration changes, then get out of the way.

## 3. Ranked techniques

Each one: what the player perceives, why, where it goes in this code, cost, and what not to do.

### 1. Pitch the gaze by an angle, not by a few meters

**Perceives:** at 10–25 m over the water the middle of the picture is sea, streaming; at 80 m it is horizon and islands again.

**Why:** flow at the fovea is `v h / (x²+h²)`. `x` has to be a small multiple of `h`, which means a depression of order 10–20°, not 4°.

**Sketch:** in `chase`, stop using `-uh * 3.7 * low` as the look-down. Set the aim on the water:

```
h   = height of the eye above the swell
low = 1 - smoothstep(8, 70, aircraft altitude above the sea)
δ   = radians(4 + 12*low)          # 4° high, 16° when low
x   = clamp(h / tan(δ), 12, 250)
T   = eye_xz + flatten(path) * x
T.y = swell_at(T)                  # on the surface, not under it
```

Check, Gull, 70 m/s: at 8 m, `low ≈ 1`, δ = 16°, the center hits water near 28 m, flow ≈ 0.7 rad/s ≈ 40°/s. At 40 m, δ ≈ 9°, flow ≈ 3°/s. The bottom of the frame gets faster still; the point is the *center* must move. Keep the turn lead, but add it after this, and clamp the lead in *degrees* (±6°), not ±12 m, or the lead will cancel the pitch.

**Cost:** a day, plus retuning so landings still show the runway of water ahead. Risk: too much nose-down feels like a camera mounted on the belly. 16° at the low end is a lot; if playtests hate it, 12° still beats 4°.

**Don't:** drop the camera to 1 m and leave the aim on the horizon. Don't look down at 200 m of altitude; the horizon is the instrument there.

### 2. Sharp meter-scale albedo on the near sea, and delete the smear

**Perceives:** individual flecks you can follow for a fraction of a second, then lose off the bottom. Speed becomes countable.

**Why:** the visual system reads speed from high-contrast transients. A 100 ms shutter averages them away. Crest lines at 10–60 m give the eye a slow thing to track, and it will prefer them.

**Sketch:** in `sea_fs`, remove the `_rush` branch (the 13-tap, `exposure = 0.1` loop). Keep `_fleck` world-locked. Add a second lattice at ~0.55 m, higher contrast, drawn only for `dist < 50` and faded by 8–45 m, albedo mixed at ~0.35 so it does not become snow. When `v/h` is large (pass `speed` and `eye height` in `SeaParams`, you already have `rush.w`), multiply `_crest_strokes` by something like `smoothstep(8, 25, dist)` inside the near band so the big white lines do not win the contrast war at the range you now look at. Leave crests alone past ~40 m; they are the painted sea and they are good there. Leave far glints on their log2 LOD. Add a *second* glint population inside 40 m with a fixed 0.4 m cell and no per-tick re-roll, so a few points actually travel.

Target period in the 10–40 m band: **0.5–1.5 m**. At 70 m/s and 60 fps that is about one feature per frame at the new center-ray distance. Do not go finer than ~0.3 m or it aliases into shimmer, which reads as a material again.

**Cost:** shader only. Risk: busy water. If it looks like noise, cut density before you cut contrast, and never "fix" busyness by blurring.

**Don't:** longer exposure, radial screen lines, a fullscreen velocity buffer. Don't darken the flecks out inside the aircraft shadow; the shadow is a moving ruler over them (`_shadowed` already multiplies the body down — keep the fleck mix *after* the shadow, or the ruler has nothing to pass over).

### 3. Keep the spring, cut the longitudinal gain, kill the zoom

**Perceives:** the aircraft shoves toward the bottom of the frame when you open the throttle or push over, then settles back to one screen position. Constant speed does not slowly zoom.

**Why:** acceleration is a change. A camera that only lags while `a ≠ 0`, then returns, matches that. A camera that also sits further back at high *speed* (`D`'s `sfrac` term, FOV's `6*sfrac`) makes the fast state look smaller and calmer.

**Sketch:** equilibrium lag you can see without a zoom: about 0.6–1.0 m at 8 m/s², not 4 m. With `ω_long = 3.5` and gain `1.0`, `e = a/ω² ≈ 0.65 m`. Shorten the settle: `ζ_long = 0.85`. Set `D` to the shape's back distance and leave it. Put the "closer when low" into eye height and into δ (technique 1), not into a speed term. Lateral: keep `ω ≈ 3`, gain ≈ 1, clamp ±1.5 m (the current ±4 m is a lot once the aim is also leading). Vertical: `ω = 8`, `ζ = 1.05`, gain ≤ 0.6, clamp ±0.6 m. When the sea clamp raises `c.y`, zero the downward part of `cam_ev` and lift `cam_e.y` to match, or the spring stores a grudge.

FOV: keep the transient `a_fast - a_slow` kick, drop `6*sfrac` to 0. Steady cruise is one focal length (~60–62°). A few degrees of kick on the throttle is the seat; a permanent wide angle is a new normal, and then you have no acceleration left to show.

**Cost:** constants. Risk: if technique 1 is not in, a stiffer spring feels like "nothing happened." Ship them together.

**Don't:** ω so low that landing wallows (the current vertical ζ = 0.45). Don't damp against zero instead of against the craft; the current form (drive by acceleration, rest at the anchor) is the right structure. Don't add shake back on top.

### 4. Takeoff and unstick as one mechanical event

**Perceives:** the run gets harsher as the hull stops displacing and starts skipping, then one release: the buzz stops, the nose settles, spray falls behind.

**Why:** the camera should be coupled to a force that exists, and the interesting instant is the disappearance of that force. A smoothstep of airspeed has no such instant.

**Sketch:** `airframe`'s on-water shake should follow planing and wave slope, not `smoothstep(5, 40, speed)`. Sample `swell_at` under the floats (it already matches the drawn sea) and drive a pitch/heave on the *mesh* at the spatial frequency the hull is crossing: amplitude a centimeter or two times `smoothstep(8, 25, speed)`, frequency `speed / λ` for λ ~ 13–23 m, gated by `on_water`. Kill the `sin(time*47)` term that ignores the sea. On the frame `on_water` falls (there is already `water_age`), snap the mesh excitation to zero and let `spray` keep emitting for ~0.4 s on a decaying rate instead of returning immediately. The spring (technique 3) will already be behind during the run and will catch up when acceleration drops; don't also fire a scripted shake at unstick.

**Cost:** small, all in `pilot.jo` / `spray`. Risk: porpoising the camera. Keep the excitation on the mesh and on a ≤0.4° aim tremble sampled from the same swell, not on `cam_e`.

**Don't:** noise() on the look target. Don't max the effect out at 40 m/s so unstick has nothing left to change.

### 5. A ground-rush layer in the audio, brightness tied to height

**Perceives:** the hiss gets thinner and louder as the water comes up, and it falls off within a second of climbing, even if airspeed does not change. The engine note moves when the prop does.

**Why:** hearing is how you disambiguate "fast and high" from "fast and low" when both can be made to look dramatic. A single whoosh with pitch linear in speed cannot do that. Acceleration is a pitch *sweep*; a steady pitch means a steady speed.

**Sketch:** in `update_audio`, add a second noise loop, highpassed (the existing `_noise_loop` `cut` parameter — use something like 0.35), volume `0.5 * (v/55)² * (1 - smoothstep(6, 50, h))`, pitch `0.8 + 1.4*(v/80)`. Engine pitch should track a lagged RPM: `rpm = throttle` smoothed at the existing `spool_time` (1.5 s) is already `state.throttle`; add a real airspeed term that matters, e.g. `airspeed/90` instead of `/250`, and drop it when the throttle closes so a closed-throttle dive whistles (wind) without the engine screaming. On water, a low thump whose rate is `speed / 12` Hz (one per short swell) until `water_age > 0`, then silence.

**Cost:** a few loops. Risk: constant noise fatigue. The height gate is the point; at 100 m this layer is off.

**Don't:** pitch up the same loop forever with speed. Don't add a whoosh sample that plays on a speed threshold; that is the audio version of speed lines.

### 6. Near clutter that is actually near, over open water

**Perceives:** something at 10–30 m range whips through the lower frame a few times a minute. The empty sea stops being the only scale.

**Why:** even a correct water shader is one surface. A second depth a few meters off it (a buoy, a weed line, a gull that is *not* circling a harbor) gives parallax, which is the cue μZero2 gets free from road vs wall.

**Sketch:** a camera-relative field, the way clouds wrap but only drawn inside ~150 m, of world-locked objects on the sea surface: foam patches and driftwood on a ~40 m jittered lattice, each 0.4–2 m, using `afloat` (already in `sea.jo`) so they ride `swell_at`. Density like one object per 40×40 m, not a carpet. Cull hard. Same idea for rock when `surface_height > 0` and the aircraft is within 80 m of a cliff: a ring of cards or reused grass tufts (`build_tuft`) at 1 m spacing, because the 14 m island grid cannot carry it. Birds: a handful of open-water individuals at 8–20 m AGL on long crossings, not more harbor flocks.

**Cost:** the real one. Instancing is already the pattern (`birds`, `clouds`). Risk: clutter that reads as a game asset. Keep it sparse and unlit-simply; if you notice the asset, there are too many.

**Don't:** particles parented to the camera. Don't fill the view. Don't depend on clouds for this; their scale is wrong by 100×.

### 7. Horizon roll stays a fraction; lateral lag stays smaller than the lead

**Perceives:** the horizon tips a little in a bank, and the aircraft steps toward the outside of the turn, then back.

**Why:** a perfectly level, perfectly centered aircraft is the "too smooth = slow" case. Full aircraft roll on the camera makes the horizon useless, which this game cannot afford (you fly by it).

**Sketch:** keep `want_roll = 0.2 * bank` (about 12° at a 60° bank). Smooth faster than now if it feels late (λ = 3 is a bit soft; λ = 6 matches the path smoothing). Cap displayed roll at ~0.25 rad. The current lateral spring is the right axis; don't also add μZero2's craft-only visual bank on top or the wings and the horizon will disagree.

**Cost:** none if 0.2 already feels right in a recording. **Don't:** roll the camera 1:1. Don't roll it with yaw rate independent of bank; the aircraft's bank is the real signal.

### 8. Scud, only because climbs are currently a dead zone

**Perceives:** punching a small cloud edge at 100–200 m is a thump of white and then clear air, faster than the cumulus field ever moves.

**Why:** between the sea and the 640 m bases there is nothing with an edge.

**Sketch:** a separate instance buffer, 8–25 m wisps, bases 80–220 m, hard-ish alpha, not wrapped on a 34 km square — real positions, a few hundred in the world, drawn only inside 800 m. One pass through one is worth more than retuning the cumulus shader.

**Cost:** modest. **Don't:** more noise on the big puffs. Don't make them screen-aligned.

### 9. Wake and shadow as the rulers you already have

**Perceives:** on the run, a continuous white tear peeling out from under the floats; in the air, your shadow crossing flecks.

**Why:** a mark that stays attached to you, drawn on a surface that is moving in frame, is a speed reference. A mark broken into 8 m segments looks like a chain of decals.

**Sketch:** `WAKE_EVERY = 0.2` → 0.08 s while `speed > 20`. Keep the shadow quad; with technique 2 the flecks stay visible inside it.

**Cost:** trivial. **Don't:** a fake spray ribbon in screen space.

## 4. Camera model

This replaces the look-down and the gains in `chase`. It keeps the path frame, the per-axis spring, the 0.2 bank, and `camera3d(..., cam_up)`.

Notation: `P` CG, `v` velocity, `s = |v|`, `f̂` smoothed path (existing `path`, λ = 6 is fine), `h_cg` CG height above the swell, eye built from the anchor before the spring.

```
low = 1 - smoothstep(8, 70, h_cg)

D   = 15                          # Gull. Heron 24, Falco 13. Not a function of s.
H   = lerp(4.0, 2.2, low)         # meters above CG. Heron 6 → 3.
A   = P - flatten(f̂)*D + up*H
A.y = max(A.y, swell(A)+1.6)

# gaze angle, applied to the eye, not to the CG
h     = A.y - swell(A)
δ     = radians(4 + 12*low)
x     = clamp(h / tan(δ), 12, 250)
aim   = xz(A) + flatten(f̂)*x
aim.y = swell(aim)

# turn lead in degrees, after the pitch
lead  = clamp(yaw_rate_rad_s * 0.35, -0.10, 0.10)
aim   = aim + right * (x * tan(lead))

Tdir  = normalize(aim - C)        # C is the sprung eye, below
```

Spring, offset `e` in the path frame `(right, up, forward)`, driven by craft acceleration `a` in that frame. Integrate the substeps you already have. Equilibrium `e = -g ⊙ a / ω²`, with `⊙` elementwise.

| axis | ω (rad/s) | ζ | gain | clamp (m) | lag at a reference accel |
|---|---|---|---|---|---|
| forward | 3.5 | 0.85 | 1.0 | −1.2 … +0.6 | 0.65 m at 8 m/s² (behind) |
| right | 3.2 | 0.80 | 1.0 | ±1.5 | 1.0 m at 1 g |
| up | 8.0 | 1.05 | 0.5 | ±0.6 | 0.15 m at 2 g, no bounce |

Look direction, separate and quicker, so the aircraft is what moves in frame: critically damped, `ω_look = 9`, `ζ = 1`, toward `Tdir`. Roll as now, `0.2 * bank`, λ = 6, zero on the water. FOV `62 + clamp(0.35*(a_long_fast - a_long_slow), -2.5, 3.5)` with the fast smoother at λ = 8 and the slow at λ = 1.5. No speed term.

What this does *not* do: at a steady 75 m/s the offset is zero, the FOV is 62°, and the only reason it feels fast is δ and the sea shader. If a recording at constant speed still feels slow, the spring is not the knob to turn. The sea is.

Settle of the longitudinal axis is `4/(ζω) ≈ 1.3 s`. Enough to notice on a throttle chop, short enough to be quiet before a landing flare if you reduce power on the approach. If the flare still has the camera wandering, drop the forward gain to 0.6 before you touch ζ.

Sea clamp: if you push `C.y` up to `swell+1.6`, set `e_up` to the value that produces that height and set `ė_up = 0` when it was downward. Otherwise the first climb off the water launches the eye.

## 5. Pitfalls and how to test

**The spring will be blamed for a sea problem.** If constant-speed flight at 15 m and at 80 m feel similar, no camera constant will separate them. Cover the instruments and watch the center of the frame.

**Zoom-out masquerading as weight.** Any change that shrinks the aircraft at high speed (arm, FOV, both) will be reported as "floaty" or "slow." The aircraft's screen size at 50 m/s and at 80 m/s, level flight, should match within a few percent.

**Blur as a substitute for contrast.** If the new flecks shimmer or alias, the temptation is to smear them. That returns you to `_rush`. Reduce density, keep the edges.

**Looking down too far.** If the horizon leaves the upper third during a 15 m cruise, δ is too big and you have lost the flight instrument. 16° is the proposed low-altitude *center* ray, so the horizon stays well inside the frame; if it doesn't, the FOV assumption is wrong (measure it — `camera3d`'s third argument is not documented in this repo).

**Vertical bounce vs the sea clamp.** The current `ζ = 0.45` plus a hard `max` on position is the landing bug waiting. Test a firm touchdown and a skip.

**Winding the gain until the takeoff "feels like something."** 4 m of arm at 8 m/s² already does. More will clip the −7 m clamp and then feel like a rubber band.

**Empty-world cheat.** Spawning a screen-full of spray to fake flow will hide the sea and then read as fog. Sparse, world-locked, or nothing.

**Audio lying.** If the rush layer stays loud at 100 m, players will distrust the picture. The layer is a height cue first.

### What to look at in a recording

Same Gull, same wind, 1080p60, instruments covered. Three shots, before and after, same start states (`AEGEAN_FLYING` is enough for the air shots):

1. **Level 70 m/s at ~15 m, then the same speed at ~120 m.** Pause on a frame and look at the center, not the lower edge. After the change the low shot's center should be water with features you can point at; the high shot's center should be horizon. If you cannot tell the shots apart with the sound off, gaze and flecks are not in yet. Rough count: features crossing a horizontal line through the center per second should be several at 15 m and nearly zero at 120 m.

2. **Takeoff through unstick.** The wing buzz should die as the spray detaches, not a second before and not a second after. No noise on the horizon. The aircraft may sit slightly low in frame during the run and return within about a second of the acceleration easing. It should not shrink steadily as speed rises.

3. **Throttle chop at constant height, then a 45° bank.** Chop: aircraft shifts in frame and returns, FOV returns with it, horizon stays put. Bank: horizon tips on the order of 10°, not 45°, and un-tips when the wings level. If the horizon is busy during either of these, something is still shaking the camera.

Cliff pass at 40 m lateral distance is the control case. It should feel faster than open water *before* the sea work, and only a little faster after. If open water with streaks or blur ever feels faster than the cliff, the fakery is winning again.
