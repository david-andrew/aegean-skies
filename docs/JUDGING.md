# Judging: an outside look, now and then

Every so often, a few models look at the whole game cold and say what they see. The point is to
catch the big things the people building it stop noticing (a look that drifted, a system that
reads as a template, a regression nobody measured, a loop with no reason to play), not to grade
each change.

## When

Rarely: at milestones, roughly two or three times over a stretch of work the size of the project
so far. A round is due when several large pieces have landed since the last one and the game has
settled (merged, tests passing, pushed), never in the middle of a change, never after small fixes.
Signs it's time: a cluster of big merges; before telling the user a phase is done; when something
feels off and there is no measurement for it. Rounds so far:

| Round | When | After |
|---|---|---|
| 1 | when the four streams of 2026-11-11 land (phone fix and sky, towns, aircraft, people and speech) | the world grew to the Aegean, cargo, towns, aircraft, speech |

## Who

Three judges, each from a different family so their blind spots differ, each working alone (no
judge sees another's take or the coordinator's opinion, so no one is anchored):

- **Sol** (GPT): thorough; good at reading the systems and transcripts against the design.
- **Astra** (GPT, a fresh instance, not one that built the parts under review): the technical and
  visual eye.
- **Grok** (through Cursor): a dissenting outsider's take.

A judge never edits code. Judges are fresh agents with only the capture pack and the rubric, never
an agent that built what is judged.

## What they get: the capture pack

One script (`tools/judge_pack.sh`) builds a named round folder in
~/dev/tmp/aegean-skies/judging/<round>/ from the selected checkout, the same way every round so
rounds compare:

- Screenshots from a fixed list of views and hours: the home harbor at dawn, noon, dusk and night;
  each kind of settlement from the air and from the ground; the mainland from 4000 m; a crossing low
  over the sea; a cliff coast; inside a town square in the evening; every aircraft type at its dock
  and in flight; the chart; the pause menu; a conversation; the notebook.
- Short frame sequences (stills a fraction of a second apart) of a takeoff, a loop, a landing, a
  dive into the sea, a fly-by of another aircraft.
- A transcript of a month of world time run headless: conversations sampled across people and
  places, the news, the notebook, errands offered and done, prices and events.
- Numbers: frame time on the laptop redfox at the fixed views (bench lock), the web build's size,
  load time and memory in a browser with phone limits, test results, code size by module and what
  changed since the last round.
- The references the game is aiming at (the Porco Rosso stills in refs/, never committed; the
  user's map of the Aegean) and docs/DESIGN.md's goals.
- What the judges can't perceive, said plainly: sound (only a description and spectra), feel in
  the hands (only flight traces), and anything the user has already ruled on (docs/FEEL.md, the
  feedback in DESIGN.md), so they don't relitigate it.

## The rubric

Each judge scores 1-5 with evidence (which picture, which line, which number) and names the three
worst problems in the game as it is, whatever the categories:

1. **The look**: does it read as one coherent painted world close to the references? Anything
   jarring, broken, placeholder-looking?
2. **A place where people live**: towns, people, routines, traffic, signs of life; does it feel
   inhabited or staged?
3. **Words**: speech, news, notebook, errands; do people sound like people, distinct and specific,
   or like a template? Repetition?
4. **Something to do**: the loop (errands, money, the aircraft, danger, discovery); is there a reason
   to keep playing tomorrow?
5. **The world's scale and geography**: does the Aegean read as real: coasts, islands, mountains,
   distances?
6. **Technical health**: frame time on weak hardware and phones, load, memory, errors, test health,
   code that is drifting (duplicate systems, dead code, files that grew too big).
7. **First ten minutes**: could a new player understand what to do and how to fly?

## What comes back, and what happens to it

Each judge writes judging/<round>/<judge>.md: scores with evidence, the three worst problems, and
anything that looks like a regression since the last round. The coordinator merges them into
judging/<round>/summary.md: where the judges agree (act), where one judge alone sees something
(check it before acting: a single judge's claim is a lead, not a fact), and where they disagree
(say so, decide). Then the findings become work for the agents in the usual way, and the user gets
a short account of the round: scores side by side, what will change, what was set aside and why.
Scores are kept round to round, so the next round shows what moved.

Costs: one round is three judge agents for an hour or two each plus building the pack; well under
one heavy agent round of quota.

## Running the pack

`tools/judge_pack.sh round1` builds a private pack under `~/dev/tmp/aegean-skies/judging/round1`.
Run from the intended checkout; it records HEAD, any source patch, compiler version and hashes.
It never judges, edits gameplay settings persistently, pushes, or plays sound. Native capture
and test jobs run serially with one worker and isolated saves. It freezes the compiler and standard library in the round folder so shared upgrades cannot mix
toolchains mid-run. Start a new round to change toolchains. It uses the existing baked assets
(or runs the bake if missing). Python 3 with Pillow and Matplotlib, Sloppy, Node, ssh and rsync are required.
The reference source folders remain in `~/dev/tmp/aegean-skies/{refs,world}`.

The ordered stages are `build`, `images`, `sequences`, `world`, `audio`, `tests`, `web`, `bench`,
and `index`. Use `--stage STAGE` (repeatable) to resume; `--force` reruns completed work.
`--previous round1` adds the previous round's commit comparison. A round directory is a source
snapshot: use a fresh round when changing gameplay or assets. Embedded assets are copied into
the pack and checked before/after builds; restore those copies if a shared asset changed mid-run.
`--force` reruns collection from the same inputs. Image receipts check binary and
exact environment before reuse. The index and SHA-256 manifest are regenerated by `--stage index`.
Every image still requires human/agent inspection against its index description before handoff.

Timing uses an isolated `~/dev/tmp/aegean-judge-ROUND` folder on redfox and its shared bench lock.
It rejects a one-minute load of 1.5 or above before each run, records loads before and after, and
leaves a failed gate resumable without claiming a measurement. The laptop must have its cached
Chromium and `/home/linuxbrew/.linuxbrew/bin/node`. `JUDGE_REDFOX` can change the SSH address,
but the remote helper requires hostname `redfox`. Browser mobile emulation is a proxy, not a
physical phone result. Local phone-sized captures preserve 844×390; WebGL uses the game's own
low-tier pixel cap. Remove the isolated remote folder after retrieving a completed pack.

`AEGEAN_CAPTURE` accepts `home`, `dock`, `flight`, `cliff`, `mainland`, or `place:KIND_ID:air|ground|old`.
Generated place IDs are selected deterministically, and the actual place, camera and hour are
logged. `AEGEAN_CAPTURE_PANEL=notebook` pins actual board notices; it never invents a completed
errand. `AEGEAN_CAPTURE_ATTITUDE` supplies an initial pitch for flight fixtures;
`AEGEAN_CAPTURE_TRACE=1` emits a flight row every nine physics frames. These hooks do nothing
without their environment variables. `JUDGE_TRANSCRIPT=1` adds job transitions and daily prices
to the existing month transcript; it does not change world decisions.

`AEGEAN_CAPTURE_READY=1` skips the transient opening title/help overlay for catalog shots; the
pack separately captures the unmodified first view. `AEGEAN_CAPTURE_MINUTES` advances the actual
world clock to match a lighting-hour fixture. No in-game key binding is added.
For isolated Python dependencies, create `~/dev/tmp/aegean-skies/judging/.venv` and install
`pillow matplotlib`; the shell runner uses that interpreter when present (`JUDGE_PYTHON` overrides).

The refreshed round-1 list also includes saved-weather fixtures (storm, overcast above/below,
rain and fog), vessel fixtures (morning harbor, steamer, convoy and the eighteen-type catalog),
cockpit compass/radio, pocket compass on the maps, desktop/phone Options, and two bailout states.
`--stage additions` collects just these supplemental fixtures for framing checks.
