# Making Aegean Skies feel fast: research notes

Read: `aegean.jo`, `src/pilot.jo`, `src/sea.jo`, `src/flight.jo` (`_fly_air`, the water contacts, `sea_surface`),
`src/clouds.jo`, `src/birds.jo`, `src/sound.jo`, `src/terrain.jo` (detail only); uzero2 `camera.udewy`,
`constants.udewy`, `render_world.udewy`, `render_hud.udewy`, `physics.udewy`, `audio.udewy`,
`parallax_world.udewy` (branch `archive/udewy`; local copies in `~/dev/tmp/aegean-skies/research/uzero2/`).
Nothing in the repo was edited or run.

## TL;DR

The aircraft's speed is real (85 m/s for the Gull, up to 125 m/s for the Falco). The camera, the sea
shader and the FOV hide that speed, and noise and streaks cover the gap. The biggest single lever is
**how many eye-heights per second the camera covers**. uzero2 runs at about 83/s. Aegean Skies runs at
3–14/s even when flying low, mainly because the camera sits 3–5 m above an aircraft that is itself
10–30 m up. The second lever is **crisp marks fixed to the sea, 1–10 m across, close to the camera**.
The current `_rush` smears them into streaks that look nearly the same from frame to frame, which
takes away the edge rate the eye uses to judge speed. The third is **a camera that is pushed around
by real accelerations** (a spring in the aircraft's heading frame) **instead of by a noise
generator**. Fix these three and delete the screen-space streaks, then add near things to fly past
(net floats, rocks, boats, seabed, cloud wisps) and pass-by sound.

A useful test throughout: **a still frame should look calm, and only the motion should look fast.**
If a screenshot looks fast (streaks, blur, shake), the effect is fakery.

---

## 1. Diagnosis: why the current build reads as fake and slow

Numbers are for the Gull (`max_speed` 85, `_cam_offset` 16 back / 4.5 up), worked out from the code.

### 1a. The camera is too high above the water when it matters
`chase()` (pilot.jo) places the camera `lift` above the **aircraft** (4.5 m, down to 2.9 m when
"low and fast"), so the camera's height above the sea is roughly altitude + 3 m. Perceived speed of
self-motion is driven mainly by **global optical flow rate = v / eye height** (Larish & Flach 1990;
Owen's work on flow rate and edge rate). Representative numbers:

| Case | v (m/s) | camera height over the surface | eye-heights/s | flow at screen bottom* |
|---|---|---|---|---|
| uzero2 at top speed | 456 | ≈5.5 m (1.5 hover + 4 lift) | **83** | ≈41 rad/s |
| Aegean, cruise at 20 m | 85 | ≈23 m | 3.7 | ≈1.6 rad/s |
| Aegean, skimming at 5 m | 85 | ≈7.9 m | 10.8 | ≈4.6 rad/s |
| Aegean, skimming at 3 m (camera proposed below) | 85 | ≈2.0 m | **42** | ≈18 rad/s |
| Aegean, takeoff run | 40 | ≈3.5 m | 11 | ≈5 rad/s |

\*ω = v·sin²θ / h for the sea at the bottom edge of the frame (θ = half the vertical FOV).

Realistic speeds can produce F-Zero-class flow, but only when the camera is near the water. Right
now the camera stays well above the aircraft even when the aircraft is skimming.

### 1b. `_rush` removes the cue it was meant to add
`_rush` (sea.jo) averages 13 samples of `_fleck` along `vel * 0.1 s`. At 85 m/s that smears each
fleck over **8.5 m**, but the flecks sit in **2.6 m** cells, so neighbouring smears overlap into
continuous lines along the direction of motion. Because a pattern made of lines along the direction
of motion looks nearly the same in every frame, the sea within ~70 m reads as *striped*, not as
*moving*. The edge rate (marks crossing a point per second, about 85/2.6 ≈ 33/s here), which is the
other main speed cue (Denton's road-stripe studies; Larish & Flach), largely disappears. The streaks
also turn with the velocity vector when you bank, a cue that has nothing to do with the real motion.
A real camera's shutter at 60 fps lasts at most 1/60 s, which is 1.4 m of travel, not 8.5 m. This is
exactly the "pretending to be fast" effect.

### 1c. The shake is noise, not physics
`feel()` sets `shake` from speed alone (on the water `smoothstep(4, 40, sp) * 0.75`).
`place_chase_camera` then adds `noise(t·9..11)` jitter: about ±0.03 m of camera position and about
±0.5° of aim at maximum. It ramps up smoothly and steadily with speed, whatever the sea is doing, so
the player cannot connect it to any cause, hence "unearned". Meanwhile the **flight model's sea is a
different sea from the one drawn**: `sea_surface()` (flight.jo) is a two-sine wave, 35 m long and
0.05–0.5 m high, with `wave_time = 0` (flight_env, pilot.jo). The drawn sea is the 6-swell `_swell`
in sea.jo. The hull never visibly hits the crests you see, so a shake on top of that cannot be
believed.

### 1d. The FOV widening slows on-screen motion
`want_fov = 58 + 24·smoothstep(25, 110, sp)` gives about **77° vertical at 85 m/s** (camera3d takes the
vertical FOV). At a given world angle, on-screen speed scales with 1/tan(fov/2): tan 29° / tan 38.5° =
**0.70**, so the sea near the middle of the screen moves about 30% *slower* in pixels at cruise than
at rest, and the aircraft shrinks on screen. The widening also eases in over about 0.5 s
(`exp(-2dt)`) and follows speed rather than acceleration, so it reads as a gradual zoom rather than a
punch. uzero2's FOV is wider (90°→109°), but its eye height makes up for that many times over (see
1a); a wide FOV is only worth having when there is near detail to fill the edges of the frame.

### 1e. The camera follows speed, not acceleration
The position lerp `exp(-9dt)` is a first-order lag. At constant velocity it settles into a fixed lag
of v/k (≈9.4 m at 85 m/s), so at steady speed nothing moves relative to the aircraft. The `surge`
term (≤5.4 m) is the only acceleration cue, and it is smoothed at 3/s and clamped. Nothing pushes the
camera vertically or laterally, and the horizon is always kept level (`camera3d` up is world up). The
result is a perfectly stable shot, and perfectly stable reads as slow, the "too easy, too smooth"
point from the discussion.

### 1f. Nothing near passes beside you over open sea
uzero2's rails stand 19–22 m to each side and carry the same 5 m texture along their length. Lateral
flow is v/d, which is the strongest vection stimulus (peripheral and perpendicular to the motion;
Brandt et al. 1973). Over the Aegean sea there is nothing vertical near the aircraft: about 1–6 fishing
boats per town 300–1800 m out (`build_fishing_fleet`), gull flocks 14–70 m up near the coasts, clouds
made of 260–2300 m smooth spheres with bases at 640–860 m, and cliffs on a 14 m terrain mesh. The sea
at the far middle distance is the only flow source, and it is the weakest one.

### 1g. Smaller points
- `speed_streaks` (screen-space lines radiating from a point 10 s ahead) is the textbook fake. It
  contradicts the real flow field whenever the camera lags or the aircraft is crabbing in wind.
- Glints re-tip 1.5–4.5 times a second. They twinkle in place, which is fine, but they add
  "busyness" that is not motion.
- Engine pitch: `0.7 + 0.55·throttle + airspeed/250`. The airspeed part is right, but it is too small
  to hear changes in speed (85 m/s adds 0.34).
- Throttle lever rate 0.6/s: 1.7 s from closed to open, so the "kick" of acceleration is spread out.

---

## 2. What uzero2 does that matters (and how it translates)

| uzero2 (code) | Effect | Translation to a seaplane over water |
|---|---|---|
| `HOVER_HEIGHT` 1.5 m, `CAM_LIFT` 4 m, `CAM_BACK` 15 m (constants.udewy). Eye ≈5.5 m above the road | v/h ≈83/s at top speed | Bring the camera to about 2 m above the sea when the aircraft is low (§4). It cannot reach 83/s at 85 m/s, but 30–45/s is within reach and feels like a race car |
| `CHECKER_TILE` 5 m, 2×2 **nearest-filtered** checker textures (`build_checker_tex`, `gpu_texture_create(.. 1 1)`), Parallax Engine's 32×32 panels with seams and fasteners (`parallax_prepare`) | Hard-edged, high-contrast, discrete marks at 1–5 m scale give a huge edge rate (456/5 ≈ 90/s) | Crisp sea marks fixed to the water at 1–10 m scale (foam flecks, ripple patches, float lines), drawn sharp, not smeared (§3 #3) |
| Rails (`draw_segment_rails`) textured by arc length (`v_a = cumarc / (2·CHECKER_TILE)`) | Lateral flow from vertical surfaces close by | Things that stand up out of the water: net-float lines, buoys, skerries, moored boats, harbor moles, cliffs (§3 #5, #10) |
| `POS_ALPHA` 0.12/frame (k ≈7.7/s) with **no velocity feed-forward**: lag = v·0.88/0.12 ≈ **56 m** at top speed, about 100 m on boost | The craft visibly pulls away when accelerating (22 g thrust: `THRUST_ACCEL` 0.061 m/frame²) and the camera "struggles to catch up". The road between camera and craft becomes a measuring stick | A spring that responds to *acceleration* with gain (§4); seaplane accelerations are about 1 g, so the response must be amplified roughly 2–3× to read |
| `ORIENT_ALPHA` 0.10/frame. The camera up follows the craft's surface up | The horizon moves with the craft and track, never locked | Partial roll (about 20% of the bank, lagged); keep the horizon level on the water |
| `FOV_PUNCH` 0.4: tan(half-FOV) goes 1.0 → 1.4 (90° → 109° vertical) with speed fraction | Wider view, but it is filled with near track | FOV only as a small accent tied to acceleration transients, since the edges of the frame are mostly empty sea and sky |
| **No camera shake.** The only jitter is ±4 px on the speed lines (`SPEED_LINE_SHAKE_PX`) | Nothing unearned | Remove the noise jitter. Let the camera spring react to real bumps |
| Speed lines (`draw_speed_lines`): density = intensity², visible above 38% of top+boost, so about 20 lines at normal top speed and all 256 only on boost | Lines that signal boost / over-cap, not a constant overlay | If kept at all, show them only when the aircraft exceeds its level-flight maximum in a dive. Better still, delete them |
| Engine tone 60 → 360 Hz with speed (`audio_mix_chunk`) | Pitch tracks speed over 2.5 octaves; you hear every change | Make prop RPM respond to airspeed (a fixed-pitch prop windmills faster in a dive). Add a wind layer whose pitch rises with airspeed and pass-by Doppler (§3 #7) |
| Huge acceleration (0 to top in about 2.5 s) and an energy and boost economy | The player keeps changing speed | Speed changes on purpose: dives, unsticking from the water, throttle kicks. Make them felt; there is no need to add more of them |

What does *not* carry over: uzero2's absolute speed, and the temporal aliasing it gets from moving
7.6 m per frame over 5 m tiles (the checker strobes, which reads as chaos). At 1.4 m per frame we
need marks of about 3 m or more near the camera, or a one-frame shutter (§3 #3).

---

## 3. Techniques, ranked

Ranked by expected gain per unit of work. #1–#4 are the core and should be done together, because
each makes the others readable.

### 1. Sea-relative low camera (eye height)
- **Player perceives:** skimming at 3–6 m, the sea fills the lower half of the frame and pours under
  the camera. Climbing calms the view; diving to the deck makes it roar.
- **Why it works:** flow rate v/h. Dropping h from ~8 m to ~2 m multiplies the flow by four, with
  nothing faked.
- **Sketch:** in `chase()`, compute the camera height **above the sea** from the aircraft's height
  above the surface `a` (§4: `L(a)`), with a floor from the *visible* swell
  (`_swell_cpu(x, z, t) + 1.3`). Bias the camera pitch down by up to 6° when low, so the horizon sits
  at about 55% of the frame height and the aircraft just above the middle of the frame.
- **Cost/risk:** small (a few lines in `chase`). Risk: the camera dipping into a crest. That needs a
  CPU copy of the dominant swells (also needed for #4).
- **Don't:** put the camera below about 1.2 m, look up at the aircraft (it lifts the horizon and hides
  the sea), or apply this at altitude. Above about 60 m, let it fly calm; that contrast is what makes
  the low pass exciting.

### 2. A spring camera driven by real acceleration (replaces `surge`, the lerps and the jitter)
- **Player perceives:** the aircraft pulls ahead when you open the throttle or dive and eases back
  when you climb. It swings across the frame in hard turns and bobs as rough air or a wave crest hits
  it. Everything settles with a slight overshoot.
- **Why it works:** the vestibular system senses acceleration, not velocity. On screen, a lagging,
  overshooting viewpoint stands in for the "pushed into the seat" feeling. Because the camera reacts
  to the same events the aircraft does, the motion is earned.
- **Sketch:** see §4. Delete the jitter in `place_chase_camera` and the `feel().shake` path, and drive
  the spring from the aircraft's measured acceleration in a smoothed heading frame.
- **Cost/risk:** medium (about 80 lines, needs a fixed-substep integrator). Risk: motion sickness if
  it is underdamped in the 0.1–0.5 Hz band (§5).
- **Don't:** add noise afterwards to "sell" it, or tie the spring to speed. Speed only sets a small
  base-distance term.

### 3. Crisp sea marks fixed to the water at several scales, with a one-frame shutter
- **Player perceives:** individual specks, foam bits and ripple patches visibly flicking by under the
  aircraft, sharper the nearer they are.
- **Why it works:** edge rate (marks per second). The eye locks onto discrete features; smears that
  look the same from frame to frame cancel the cue.
- **Sketch (sea.jo):**
  - In `_rush`, set `exposure = u.frame_dt` (add the frame time to `SeaParams`, about 1/60), or about
    0.6× that, instead of 0.1. With 13 samples over 1.4 m the flecks keep their shape with a short
    tail. Better: cut it to 5 samples and spend the time on the scales below.
  - Replace the single 2.6 m `_fleck` with 2–3 octaves (cells of about 1.2, 3.5 and 10 m), each faded
    by distance so a mark stays 2–6 px across. Reuse `_glints`' `lev = floor(log2(dist·k))` step
    scheme: same density on screen at every distance, so no shimmer.
  - Contrast: light foam flecks against the darker body, plus darker "cat's-paw" ripple patches. Keep
    them **sparse** (30–45% occupancy). Gaps between marks matter as much as the marks.
  - Apply the effect at every speed. The marks are there at rest too. Today `_rush` switches on with
    `rush.w`, which is a fake gate; real foam does not appear only when you are fast.
  - Remove the `rush.w` mix that darkens or lightens the body. Marks should be marks, not a tint.
- **Cost/risk:** small to medium in the shader. Risk: temporal aliasing (wagon-wheel marks seeming to
  move backwards). The shutter of about one frame is the fix; check at 30 fps too.
- **Don't:** use long smears, radial blur, or any effect whose look depends on velocity rather than
  position.

### 4. An earned water ride: one sea for physics and pictures; slams; release at unstick
- **Player perceives:** on the takeoff run the hull bangs into crests: thud, spray puff, a dip of the
  camera. The bangs come faster as speed builds, sharpen at the hump, then stop when the hull leaves
  the water. The sudden smoothness at unstick is the strongest cue in the game that you are now
  really going.
- **Why it works:** an event-based vibration that the player can see causing it (the crest they just
  hit), plus a contrast. Research on vection finds that oscillation linked to the visual flow
  increases the sense of self-motion (Palmisano et al. 2000), while unrelated noise does not.
- **Sketch:**
  - Make `sea_surface()` (flight.jo) evaluate the same 2–3 longest swells as `_swell` in sea.jo (a
    shared CPU function with the same `turns`, `lens`, amplitude `0.003 + 0.0011·wind` and real time,
    not `wave_time = 0`). The buoyancy springs then hit the crests the player sees. The encounter rate
    v/λ at 40 m/s over a 13 m swell is about 3 bumps/s; at 23 m it is about 1.7/s. That is a good,
    readable rhythm.
  - Turn the already-computed `sink` (impact speed) and the vertical buoyancy impulse into: (a) the
    camera spring's vertical input (§4: it arrives as aircraft acceleration, so nothing extra is
    needed), (b) a spray burst in `spray()` scaled by impact, and (c) a "slap" one-shot (filtered
    noise burst, 60–120 ms) whose volume follows impact.
  - At unstick (`on_water` going false while speed > stall), play nothing new. The slaps stop, the
    water hiss fades over about 0.3 s, and the hull-drag drop makes acceleration jump, so the spring
    pushes the camera back. That is the release.
- **Cost/risk:** medium. The flight-model change needs re-tuning of porpoising damping (`pr -=
  pitch·1.7·wet`) and a quick check of `water_start` / mooring on a moving swell. Keep it small in a
  calm sea.
- **Don't:** fire slaps on a timer, add camera noise "while on water", or let calm-sea takeoffs shake
  at all (a calm takeoff should be smooth and hissing, which is also realistic).

### 5. Picket fences on the sea: things to pass close beside
- **Player perceives:** lines of net floats or lobster-pot buoys, mooring buoys, small skerries,
  anchored caiques, a harbor mole with bollards, rocks awash at headlands. Threading past them at
  5 m makes your speed obvious.
- **Why it works:** lateral flow v/d from vertical objects close by (the rail effect). Discrete items
  in a row give a beat frequency you can count (seven floats a second at 85 m/s with 12 m spacing).
- **Sketch:** a seeded scatter in `objects.jo` along coasts and harbor approaches, and especially on
  the routes between islands (`living_travel` routes). Each item is a few instanced primitives
  (float: a small sphere on a line; buoy: a cone with a colored band; skerry: a low rough rock).
  Density: lines of 20–60 floats spaced 8–15 m within 3 km of each town, a skerry cluster every few
  km of coast. Bob them with the shared swell function. Add an instance buffer culled to 1.5 km.
  Some lines should cross the open-sea routes, so that real passages have near content.
- **Cost/risk:** medium (content plus one instanced draw). Low technical risk. Collision is optional
  (floats are harmless; rocks crash you, which brings urgency, see #12).
- **Don't:** place them on a regular grid or uniformly. Adaptation is real: a monotonous stimulus
  feels slower after about 10–20 s (speed adaptation in driving). Clusters and gaps keep the eye fresh.

### 6. The seabed through clear water (two-layer parallax in the shallows)
- **Player perceives:** over the turquoise shallows, rocks, sand ripples and dark seagrass patches
  slide past *below* the surface marks, more slowly than the surface. Unmistakably Aegean, and
  unmistakably motion.
- **Why it works:** motion parallax between two surfaces at different depths gives depth and speed at
  once. It is also where low flying naturally happens (approaches to towns).
- **Sketch (sea.jo `sea_fs`):** where `depth < ~12 m`, trace the view ray to `y = -depth` (flat floor
  approximation: `pf = p + refr.xz · depth / -refr.y`, using a refracted ray from `n`). Sample a
  procedural floor at `pf`: a sand-ripple stripe pattern (period 0.6–1.5 m, oriented across a fixed
  direction), `vnoise` rock patches, and dark seagrass blobs of 3–8 m. Mix by the existing `sh`
  shallowness term, under the surface color. The depth texture already exists.
- **Cost/risk:** medium shader work, and a fill-rate cost in the shallows only. Risk: busy if it is
  too contrasty; keep it dim, with the water color on top.
- **Don't:** draw it in deep water (it would look like a texture painted on the surface).

### 7. Sound that moves: pass-bys, near-surface rush, a prop that responds to speed
- **Player perceives:** a "whsst" with a Doppler drop past every buoy, rock, boat and gull. The water
  noise thickens as you get low and speeds its rhythm with the crests. The engine climbs when you
  dive.
- **Why it works:** auditory motion cues add to the visual ones, and Doppler pass-bys are one of the
  most recognized speed cues in games and film. Rhythm (wave encounter rate) is a speed cue on its
  own.
- **Sketch (sound.jo):**
  - Pass-by: when a near object (from #5, boats, gulls, cliffs) has its closest approach in under
    ~40 m, play a short band-passed noise burst at its position via `play_at`, with volume ∝ (v/d)
    and its pitch swept from 1.15 down to 0.85 across the closest-approach time. That is a cheap
    Doppler, and only works if `play_at` cannot pitch.
  - Near-surface rush: a second noise loop with volume ∝ (1 − smoothstep(2, 25, height))·v/85,
    amplitude-modulated at the crest encounter rate v/λ.
  - Engine: model prop RPM as `rpm = mix(idle, max, throttle)·(0.75 + 0.35·airspeed/vmax)`, smoothed
    at about 3/s, and set the pitch from rpm. Keep the throttle's direct effect smaller than now.
  - A cliff slapback (a 60–150 ms delayed, quieter copy of the engine) when a cliff face is within
    ~80 m: the sound of being *close* to something.
- **Cost/risk:** small to medium. The audio is on the desktop's null sink for tests (agent rules), so
  tune by ear on another machine.
- **Don't:** layer generic "whoosh" ambience that rises with speed (that is the audio version of
  streaks).

### 8. Make acceleration events sharp; FOV only as an accent
- **Player perceives:** opening the throttle gives a shove (engine bark, slight yaw from prop torque,
  the aircraft pulling away). A dive builds visibly. The FOV breathes a few degrees with surges, never
  a slow zoom.
- **Why it works:** acceleration more than velocity. A step is perceived, a ramp is not.
- **Sketch:**
  - Throttle lever from 0.6/s to about 1.5/s, with the engine following on a 0.25 s lag plus a 5%
    overshoot in thrust. Add a small torque-yaw kick ∝ d(throttle)/dt.
  - FOV: `fov = 60 + 6·s + clamp(0.6·(a_fast − a_slow), −3, +4)` in degrees, where `s` = speed
    fraction, `a_fast` is longitudinal acceleration low-passed at 8/s and `a_slow` at 1/s (a high-pass
    on acceleration). Cruise FOV then drops from 77° to about 66°, which makes on-screen motion about
    22% faster than today.
- **Cost/risk:** small. Re-check the Sky Barons feel notes (no harder to fly).
- **Don't:** keep a large FOV that follows speed. It shrinks on-screen motion and the aircraft.

### 9. A trail on the water when skimming (downwash or prop wash)
- **Player perceives:** flying under about 8 m, a line of ruffled, darkened water and a thin spray
  sheet streams back from under the aircraft. Seen in the camera's lag, it shows how much sea you
  cover in a second.
- **Why it works:** a mark fixed to the world, laid down by your own motion. Its length per second
  *is* your speed, much like uzero2's engine trail (`draw_trail`, 36 points). It is real: aircraft
  skimming water do raise a visible disturbance.
- **Sketch:** reuse `wake.jo` (`wake_step`) with an "air" mode active when height < 8 m: strength ∝
  (1 − h/8)·smoothstep(30, 60, v). Render as darker ripple plus foam specks (the same flecks as #3,
  boosted inside the trail), fading over 3–4 s. Add a light spray emission from `spray()` under
  about 3 m.
- **Cost/risk:** small to medium (most of it already exists).
- **Don't:** make it bright or long-lived (it becomes a contrail-on-water gag).

### 10. Near detail on cliffs and the shore
- **Player perceives:** flying along a cliff at 30 m, strata, scrub clumps, boulders at the waterline,
  surf lines and goats or birds on ledges whip by.
- **Why it works:** a large vertical surface nearby with fine texture gives strong lateral flow (the
  rail effect again, at landscape scale).
- **Sketch:** `terrain.jo` already has strata and 0.35 and 1.3 cycles/m detail faded by `near`. Raise
  contrast in the 1–5 m band on steep faces (shadowed crevices). Instance boulders (1–4 m) along the
  waterline from the existing shore foam mask, and scrub clumps on ledges. The 14 m `MESH_STEP` makes
  the silhouettes smooth, so the boulders do the most work. The surf foam band (`edge`) can carry
  crisp flecks too (#3).
- **Cost/risk:** medium (content and instance counts).
- **Don't:** add high-frequency noise that is not anchored to geometry (it shimmers).

### 11. Clouds you can pass: scud and wisps at the base and edges
- **Player perceives:** climbing toward a cumulus, ragged fragments (5–40 m) flash past; punching
  through an edge gives a few frames of white, damp blur and a bump. Near clouds are the main speed
  reference at altitude.
- **Why it works:** near discrete objects at altitude, where the sea is too far to give flow.
- **Sketch:** for each cumulus within ~3 km of the camera, generate 30–80 small soft billboards or
  small `puff_mesh` instances around its base and sides, seeded from the cloud. Fade them by distance
  so they exist only near. Inside a big puff, add `fog` density and pass the puff into
  `_fly_air`'s `rough` (a real bump). Vapor from `vapor()` already gives "damp air".
- **Cost/risk:** medium (overdraw). Not the low case, so it ranks lower.
- **Don't:** add "speed particles" in clear air at altitude. Real flight at 1000 m feels slow; let it.

### 12. Small, earned instability near the water
- **Player perceives:** low and fast, the aircraft is alive: gust bumps of a meter matter when you
  are 4 m up, the ground-effect cushion bounces, and the stick feels a little twitchy. It stays easy
  to fly (the trim eases dives out).
- **Why it works:** urgency. Smooth plus safe reads as slow; risk and twitch read as speed.
- **Sketch:** `_fly_air` already has `rough` growing as height drops. Add a low-altitude heave term
  (vertical velocity noise at 1–2 Hz, ±0.4 m/s, ∝ rough), and make the ground-effect lift a stiff
  spring under ~0.5 span, so a dive toward the water rebounds slightly. Optionally, raise the control
  response when low (`response` ×1.2 below 10 m). The spring camera (#2) shows all of this.
- **Cost/risk:** small to medium. Risk: making it harder. Measure crash rates on a scripted
  low-level route before and after.
- **Don't:** increase random rotations of the aircraft (pitch and roll noise). Heave reads as air;
  rotation noise reads as bad controls.

### 13. Partial camera roll and lead into turns
- **Player perceives:** in a bank the horizon tilts slightly and the view leans into the turn, so the
  sea sweeps across the frame.
- **Why it works:** rotational flow adds to translational flow, and a locked horizon reads as a
  tripod.
- **Sketch:** camera roll = 0.2 × aircraft bank, low-passed at 3/s, zero on the water. Look-at target
  leads by `r · (yaw_rate · v · 0.3 s)` (§4).
- **Cost/risk:** small. Risk: sickness at more than about 25% roll.
- **Don't:** follow the bank fully (it turns the world into a seesaw).

### Delete: `speed_streaks` (pilot.jo) and the `rush.w` speed gate
Remove the screen-space streaks entirely. If something must signal "over the limit", keep it to a
slight edge vignette in a dive above `max_speed`. That is still a fake, so keep it minimal.

---

## 4. The camera model

All in a smoothed **heading frame** H built from the flight path, not the nose (the nose crabs in
wind and stalls; the path is what the player perceives as travel):

```
f̂  = normalize(lowpass(V̂, 6/s))          # path direction, yaw fully, pitch scaled ×0.6 (as now)
û  = normalize(world_up − f̂·(f̂·world_up))
r̂  = f̂ × û
H  = [r̂ û f̂]
```

### Anchor (where the camera rests)
```
s     = smoothstep(v_stall, v_max, v)                  # speed fraction
a     = height of aircraft above the surface (sea or land below it)
low   = 1 − smoothstep(6, 40, a)
D(s)  = D0 · (0.92 + 0.18·s)                           # Gull D0 = 15 m, Heron 24 m
L(a)  = L0 − (L0 + 1.0)·low                             # L0 = 4.0 m: 4 m above at altitude, 1 m BELOW when skimming
A     = P − f̂·D(s) + û·L(a)
A.y   = max(A.y, swell(A.x, A.z, t) + 1.3)              # never in a crest: the CPU copy of the visible swell
```
At a = 3 m the camera sits about 2 m above the water. At a = 20 m it is about 0.9 m above the
aircraft. Above 40 m it is 4 m above, as now. The small speed term keeps the aircraft's screen size
roughly constant across speeds.

### Dynamics (the spring): what conveys acceleration
State: e = Hᵀ(c − A) (camera offset from the anchor, in the heading frame) and ė.
A physical camera on a spring attached to the anchor obeys ë = −ω²e − 2ζωė − Ä. We amplify the
driving acceleration per axis by a gain g, because seaplane accelerations (≤1 g) are about 20×
smaller than uzero2's:

```
ä_H   = Hᵀ · lowpass(Ä, 20/s)            # anchor (≈ aircraft) acceleration, finite-differenced, de-noised
ë_i   = −ω_i² e_i − 2 ζ_i ω_i ė_i − g_i · ä_H,i
c     = A + H e
```

| Axis | ω (rad/s) | ζ | g | Response |
|---|---|---|---|---|
| Longitudinal (along f̂) | 2.2 | 0.60 | 2.5 | 0.52 m per m/s²: ~4 m farther back at 8 m/s² (takeoff, full-throttle dive), returns with ~10% overshoot. Soft-limit e_z to [−7, +3] m with `x·tanh`-style compression |
| Vertical (along û) | 4.5 | 0.45 | 1.4 | A 1 g bump gives ~0.7 m, a hull slam (Δv ≈ 1 m/s) about a 0.25 m dip and rebound in ~0.3 s. This replaces the shake. Clamp ±1.5 m |
| Lateral (along r̂) | 3.0 | 0.70 | 1.2 | A 1.7 g level turn swings ~2.3 m outward, showing the aircraft's flank and the sea sweeping. Clamp ±4 m |

Integrate with semi-implicit Euler in fixed substeps of ≤ 1/240 s (dt-independent; the current
`exp(-k dt)` lerps are fine, but a second-order system needs substeps). Because the damping acts on
the offset from the anchor rather than the world, **there is no speed-proportional lag at constant
velocity**. The camera holds its rest pose at steady speed and moves only when the aircraft
accelerates, which is the "acceleration more than velocity" principle. If playtests still want
uzero2's "it outruns the camera" feeling at steady top speed, raise the 0.18 in D(s) to about 0.35;
do not reintroduce a first-order lag.

### Orientation
```
T      = P + f̂·35 + r̂·clamp(yaw_rate·v·0.3, −12, 12) − û·(6°-equivalent drop · low)   # look-ahead with turn lead
look   = spring(look, normalize(T − c), ω = 7, ζ = 0.85)                            # critically-ish damped aim
roll   = lowpass(0.2 · bank, 3/s) · (not on_water)
camera3d(c, c + look·50, fov, …)  with up = rotate(world_up, roll about look)
```
The aim is stiffer than the position, so bumps show as *the aircraft* moving in the frame (that is
earned) rather than the world shaking.

### FOV
```
fov = 60 + 6·s + clamp(0.6·(a_fast − a_slow), −3, +4)    # degrees vertical; a_* = longitudinal accel lowpassed 8/s and 1/s
```

### What is removed
`place_chase_camera` jitter, `feel().shake` (keep `load`; the buffet becomes an input to the flight
model's `rough` when pulling hard, so it moves the aircraft, which moves the camera), `surge`, and
both `exp(-9dt)` / `exp(-5dt)` lerps.

### Starting constants per craft
Gull D0 15 / L0 4. Heron D0 24 / L0 6 (bigger, slower spring: ω_z 1.8). Falco D0 13 / L0 3.5
(stiffer: ω_z 2.6, g_z 2.2; it accelerates hardest).

---

## 5. Pitfalls and how to test the feel

### Over-tuning risks
- **Nausea band.** Vertical or roll oscillation at 0.1–0.5 Hz is the worst range for motion sickness.
  Keep vertical ω ≥ 3.5 rad/s (≥0.55 Hz) and ζ ≥ 0.4, and roll at 20% or less. The longitudinal axis
  at 0.35 Hz is fine, since fore-and-aft surging is well tolerated.
- **Sustained offsets.** If e_z sits pinned at its clamp during a long dive, the spring stops reading
  as a spring. Lower g_z rather than raising the clamp.
- **Temporal aliasing.** At 60 fps the aircraft moves 1.4 m per frame. Marks spaced under about 3 m
  near the camera strobe or appear to move backwards. Use a one-frame shutter or larger near marks,
  and test at 30 fps.
- **Adaptation.** Any uniform stimulus fades within 10–20 s. Variety (clusters, gaps, shallows, deep
  water) beats more density.
- **Camera in the water.** The low camera needs the CPU swell. Test it in a rough sea (`AEGEAN_WIND
  "12"`).
- **Sky Barons feel.** #8 and #12 touch the flight model. Check the "no harder to fly" rule against
  recorded routes.
- **Frame-rate dependence.** Springs with per-frame alphas (as in uzero2) change with fps. Use fixed
  substeps.

### Tests (record on `redfox` per the machine rules; headless captures on the desktop with
`env -u DISPLAY -u WAYLAND_DISPLAY SLOPPY_NO_AUDIO=1`)
1. **Still-frame test.** Take screenshots at 85 m/s low and at rest at the same spot. They should look
   almost the same apart from the aircraft's place in the frame. If the fast one looks fast, there is
   fakery left.
2. **Pause-world test.** Freeze the aircraft's position (keep it rendering at speed). The screen
   should look stationary. Any remaining "motion" is fake.
3. **Scripted runs.** Use `AEGEAN_FLYING="alt speed"` plus a small input script (throttle step at
   t = 2 s, dive at t = 6 s, 2 g turn at t = 10 s, skim at 4 m from t = 14 s). Add an
   `AEGEAN_CAMTRACE` that logs e (the offset in the heading frame), fov, a_H and height each frame.
   Plot e_z against a_long: it should lead by about 0.3 s with ~10% overshoot. e_y should spike on
   each hull slam and nowhere else.
4. **Flow measurement.** On a recording of the skim segment, run Farneback optical flow (OpenCV) on
   the bottom third of the frame. Report median flow in px/frame before and after. Expect ≥3× from #1
   and #3. Do the same on a uzero2 capture as the reference.
5. **Takeoff recording.** Count slaps per second against v/λ (should match). Confirm no camera
   motion in a calm sea, and audible and visible release at unstick.
6. **Blind A/B.** The designer flies the same route on old and new builds without being told which is
   which, and rates speed and naturalness separately. Naturalness must not drop.

### Order of work
#1 + #2 + delete streaks/jitter (camera, about a day) → #3 (sea shader, about half a day) → #4 (shared
swell, slams; about a day) → #7 sound → #5 / #9 content → #6 seabed → #10–#13. Judge after the first
three; that is where most of the 4/10 → 7/10 gain should come from.
