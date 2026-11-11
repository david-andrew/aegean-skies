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

One script (tools/judge_pack.sh, to be written for round 1) builds a dated folder in
~/dev/tmp/aegean-skies/judging/<round>/ from the current main, the same way every round so rounds
compare:

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
