# The pilot's name (reputation): design

People in the living world know the pilot, or don't, and treat him by what they have seen or
heard. Nothing is shown as a number: it is carried in who comes over, who sits down when asked,
how people say hello, what they remark on, the odd discount or spare room, and the occasional
short answer. Code: `src/reputation*.jo`; glossary: "The pilot's name".

## What people think: four leanings and a side

Each opinion has four leanings, each from -1000 to 1000 (0 = nothing either way):

- **warmth**: sociable, good company / keeps to himself. Company kept or turned away, stopping to
  talk, cutting talk short, tips and gifts.
- **honour**: fair dealing and mercy: debts paid or not, fair work, pulling a downed foe out of
  the water, leaving others in a fight.
- **daring**: feats and risks: victories, a rescue in a storm, flying when others won't.
- **reliability**: jobs done on time, late, failed; flying home in formation.

And **the side**: what he has done to and for each country's people. A Kalyran who hears that
he pulled a Kalyran out of the sea thinks better of him; one who hears he shot Kalyrans down
thinks worse, whatever the other leanings say. The side is read from the deeds the listener knows,
against the listener's own country; nothing about it is stored per person.

## Who knows: deeds, towns, people

- **Deeds** (`RepDeed`): the things worth telling, at most 48 kept (the least notable and oldest
  go first): kind, minute, town, the other person and their side, the leanings it moves, and its
  **weight** (how much talk it makes: a kept table 80, a job 200, a rescue 650, a rescue landed in
  a storm up to 1000). Small acts (a chat, a tip) touch only the people there and their town's
  leaning, and never travel by name.
- **The town's word** (`TownWord`, one per town that has heard anything, sparse): how widely the
  pilot is known there (**heard**, the share of the town, 0 to 1000), the town's four leanings,
  and up to four deeds it tells, each with its hop count from where it happened.
- **Personal opinions** (`RepOpinion`, sparse, at most 600, weakest dropped first): only for
  people who have dealt with him (talked, sat with him, been turned away, paid, hired, rescued)
  or witnessed a deed. Up to three deeds, and those already mentioned to him.
- **Everyone else** takes the town's word: a person knows of the pilot when a fixed draw from the
  world seed and their id falls under the town's *heard*. So as word spreads, more of the town
  knows him, the same people every time, at no cost per person, saved or not, promoted or not.

## How word travels

- **On the spot**: a deed's witnesses hold it at once; its town hears it with
  `heard` raised by its weight and witness count.
- **Within a town**: hourly, the town's *heard* grows toward a ceiling set by the weightiest deed
  it tells (a rescue can make almost everyone know; a kept table, a quarter of the bar's regulars),
  fastest in the hours people talk: the morning market and the dock, and evenings at the bar.
  Most of a town has it in two or three days.
- **Between towns**: hourly, a sixtieth of the towns each minute, each town hears from its
  neighbours (the town graph's neighbours and the trade and travel links: roads, carts, coasters
  and sea lanes). A deed passes on while `weight × 0.7^hops` stays above 150, so a storm rescue
  is talked of four or five towns away within a week, a kept table never leaves the town.
- **The wireless**: a deed of weight 650 or more reaches the stations two hours later and is read
  in the news for a day. On the hour it is read every town hears it (two hops), and *heard*
  rises to a quarter of the town at least.
- **Fading**: *heard* fades about 1% a day, leanings 1.5% a day toward nothing, and a town stops
  telling a deed after `weight / 8` days (a rescue: two to four months; a job: a few weeks).
  Personal opinions fade at half that pace; those who sat with him remember longest. A town with
  nothing left drops out of the store.
- **The pilot's face**: while he is about a town on foot, a little of it comes to know him by
  sight (*heard* toward 300).

## Inputs

| From | Deed or act |
| --- | --- |
| Company (`aegean.jo`): accepted / turned away / asked over and came / declined | warmth ±, to that person; small to the town |
| Conversation: stopping to talk (a greeting from the pilot); replies (reassure, tease, ask back +; decline, leave −) | warmth, personal |
| Tips to the band and the house | warmth, honour (small) |
| Living events with the pilot as actor: delivery (on time / late), defaulted | reliability, honour (job deeds) |
| Obligations the pilot owes: fulfilled / defaulted | honour, reliability |
| War rescue receipts (`w.war.rescue_receipts`), weather at the place | rescued foe/friend, daring by the storm |
| `src/deeds.jo` `deed_record(kind, actor, subject_side, place, witnesses)`: rescued_foe, rescued_friend, shot_down, flew_home_in_formation, left_the_fight | the combat deeds |

Inputs are read in the living world's minute (cursors over events, receipts and the deed queue),
so a scene, a headless run, near and far all record the same deeds at the same minute.

## Outputs, all in behaviour and words

- **Company**: the chance anyone comes over at all follows the town's warmth toward him (known as
  standoffish: about a third as often; known as good company: half again as often); each
  candidate's pull follows their own view. **Asking someone over** ("Ask … to join you"): they
  come if their view allows (strangers usually; known as standoffish, seldom; thought ill of, no),
  and say why in plain words when they don't. Being standoffish means fewer approaches, never
  punishment; sitting with people mends it.
- **Greetings**: someone who has heard of him and not met him says so ("You'll be the pilot from
  Porto Vecchio."), and may remark on a deed they know ("You're the one who pulled that Kalyran
  out of the water off Neravessa."), once. People who think ill of him give a short answer.
- **Prices and favours at the margin**: a keeper who thinks well of him rounds the bill down
  (up to 6%), one who thinks ill rounds it up (5%). A family who has heard well of him may offer
  the spare room.
- **The wireless**: the bulletin reads the big deeds.
- **The notebook's standing page**: a line or two in words ("Known in Porto Vecchio as good
  company, and as someone who keeps his word. In Kalyrassa, mostly unknown.").

## Determinism, saves and cost

Integer state only; draws from the world seed; maps written in key order. Everything lives in
`World.rep` and saves with the world. Per minute: at most 14 towns (one sixtieth) each read their
neighbours; personal opinions fade once a day; no per-person scan of the population.
