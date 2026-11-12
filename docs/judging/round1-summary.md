# Judging round 1: summary

Pack: commit 12bfc07 (speech judged on world-latest/month.txt from 119afc1). Judges worked alone.

| | Look | Lived-in | Words | Something to do | Geography | Technical | First 10 min |
|---|---|---|---|---|---|---|---|
| Sol | 2 | 2 | 3 | 2 | 3 | 2 | 3 |
| Astra | 2 | 2 | 3 | 3 | 2 | 2 | 2 |
| Grok | 2 | 2 | 2 | 2 | 3 | 2 | 2 |

## Where they agree (act)

1. **The home harbor is too slow** on the weak laptop: 40.75 ms low, 52.9 medium, 75.85 high (GPU-bound,
   ~36-71 ms GPU). All three. The place every session starts.
2. **Sea holes and stepped shores at distance**: dark polygonal patches on the water, angular beach
   projections (capital-air, mainland-4000, port-air, lighthouse-air). All three.
3. **New speech bugs**: shift times in the past ("until yesterday", "29 days ago": 52 utterances),
   perspective errors (Enzo tells Lucia to ask Lucia; Father Andreas delivered oil "for Father
   Andreas"; "Dario told me this: Dario was attacked"), "pilot's gull", lowercase "i" after a name.
   All three. And whole sentences shared across voices (74x "And you? How has the day treated
   you?", 16x the same moored-aircraft sentence): Sol and Grok.
4. **Towns look assembled**: the same cafe/tree/fountain composition in every town, tree crowns
   floating above their branches, ground views inside blank walls. Sol and Astra; Grok on the ground
   cameras.
5. **The speech bubble runs off the right edge** of the screen on the quay. All three.
6. **Save doesn't restore damage** (the two long-known test failures). All three.

## One judge (checked)

- Sol: **aircraft deliveries stop after the first nine hours** of a month. Verified on the latest
  transcript: 126 aircraft jobs, 7 delivered, all before minute 547; 84 expired, 31 failed; foot jobs
  work (68 of 83). The most serious finding: the core loop of the game's people is broken.
- Grok: **the world beyond the six original harbours doesn't live** (no journey, price or story in a
  month leaves them). True by design so far (Sol's far tier is cohorts, not journeys); next big item.
- Grok: rain at 09:30 turns house lamps on (rain read as dusk). To check.
- Astra: help card says 1-9 for conversation choices but there are up to 13; the phone's boarding
  card shows a keyboard key. Both true (mine).
- Sol: the same news item twice on a board. To check.

## Disagreements

- Something to do: Astra 3 vs Sol/Grok 2. Astra credits the named errands; the others see the
  delivery stall and the empty far world. The stall is real, so 2 stands.

## Not acted on

- Clouds (user ruling: work in progress; next: the coordinator's art pass).
- Code size of aegean.jo/flight.jo: noted, no dead code found.

## What will change

- Sol: the delivery stall first; then the speech bugs and shared sentences; the duplicate news; the
  save/damage tests; then the far world's journeys.
- Astra: the harbour's GPU cost (target under 33 ms on low on redfox); the sea holes; floating tree
  crowns and town variety.
- Coordinator: the speech bubble, the help card's numbering, touch-appropriate prompt cards, the rain
  lamps; the cloud art pass after the Claude reset.
