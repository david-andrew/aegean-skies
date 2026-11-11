# Daily life and conversations

`living_world.jo` is the UI entry point. Inspecting content never consumes a line or alters a
relationship. Speaking is an explicit saved action.

| API/data | Contract |
| --- | --- |
| `talk_topics(w,speaker,listener=0)` | Available topic labels, with optional job/event/subject IDs. Same settlement only. |
| `talk_preview(w,speaker,topic,listener=0)` | Pure next-turn preview. |
| `talk(w,speaker,topic,listener=0,private=false)` | Commit a turn: words, question, replies, source event/person, confidence, privacy and job ID. |
| `reply(w,speaker,answer,listener=0)` | Consume one pending question, at most once, within 30 game minutes. A kind answer promises no money or work. |
| `daily_intent(w,person)` | Saved venue, activity, walking/bicycle, mood, reason, companion/meeting, target, route, movement ownership and arrival. |
| `w.people[person].pose` | Actual authoritative adult position/orientation. Never move decorative duplicates. |
| `w.households` | Named children with guardian, age, actual pose/target and routine. They share existing background population; no extra wallets, goods or production. |
| `personal_story_notes(w,person)` | Participant's own story journal. Private content: do not expose arbitrary NPC journals as player knowledge. |
| `heard_notes(w,person)` | Public accounts actually carried by that person, no global event lookup. Raw provenance remains in `Person.news`. |
| `town_regard(w,place,person=0)` | Existing evidence-driven reputation, -1000..1000. Different towns may disagree. |
| `venues_at(w,place)` | Semantic anchors for the actual core Town or the sparse far registry, without duplicate authority. |
| `place_context(w,sparse_id)`, `place_name(w,sparse_id)` | Saved settlement/country/region/landmark/neighbour context. Registry IDs are not array slots. |

Topic and reply selection, transcript layout, source/date/confidence cues and notebook presentation
remain coordinator UI work. Existing T contact, the existing news action and proximity barks use
committed speech already. A bark commits during update, not during drawing. Silence after a topic
is exhausted is intentional. If the spoken body already asks a question, `question` is empty and `replies` still supplies
the response choices; render the body once. Keep the NPC's name separately; the spoken line does not announce it.

A conversation has a speaker-wide four-hour use window, including questions and replies. Its
bounded journal holds 64 lines; incessant requests reach silence instead of evicting fresh lines.
This prevents repeating the same statement to the player immediately after saying it to a neighbour.
Source quotations are dated beliefs, not current omniscient prices. Debts/private courtship are
only disclosed in an explicitly private conversation with a trusted listener and nobody else near.
News may be incomplete or stale; the game does not quietly refresh its occurrence date.

`living_life_seed.set_life_venues(w,core_place,venues)` publishes stable semantic anchors.
`life_scene.configure_life_scene` publishes the merged settlement registry, uses real original
quays/house frontages for core routines and grounds targets. New places use `place_landmarks`.
The saved sparse catalog currently provides context, not new far-world people, markets or flights.
Kalyra/Orenthia capital IDs are independent of optional detailed authority seats. See DESIGN for
far/coarse economy migration, funded forces and escalation; there is no running war yet.

Only free people follow routines. Delivery, repair, paid shifts, injury and actual trips have
priority. Nearby walking leases use the player's collision checks. A blocked route remains blocked
when folded; the next different goal or geometry publication can replan it. Actual meetings have
bounded size/duration and transmit carried accounts/prices only within earshot. Merely living in
the same settlement is not a meeting or proof that somebody heard a private conversation.

`life_scene.step_life_scene` returns path searches used; traffic allows one new search per render
frame, including catch-up ticks. Regular motion stays at fixed 60 Hz. `life_view.set_life_density`
reduces background children (0 disables children); attached bicycles/instruments and named adults remain authoritative.
There are no new shaders/textures. `life_audio` plays only the nearest arrived musician within
70 m; `SLOPPY_NO_AUDIO` skips all synthesis and playback.

Acceptance tools, headless and silent:

```
SLOPPY_THREADS=1 SLOPPY_NO_AUDIO=1 sloppy --release tools/lifelog.jo
LIFE_CAPTURE=morning SLOPPY_FRAMES=33 SLOPPY_SCREENSHOT=morning.png sloppy --release tools/lifelab.jo
LIFE_CAPTURE=evening SLOPPY_FRAMES=33 SLOPPY_SCREENSHOT=evening.png sloppy --release tools/lifelab.jo
```

Unset DISPLAY/WAYLAND_DISPLAY on the shared desktop and isolate SLOPPY_SAVE_DIR in scratch.
Lifelog advances a real month, checks conservation hourly, canonical save round-trips daily,
records physically nearby conversations and carried public news, and checks recent-line uniqueness.
Lifelab advances normal routines from startup and walks them under scene leases; it never moves
people for the camera. Evening captures the second day's dusk square, when the mechanic plays.
