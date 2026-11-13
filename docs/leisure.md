# Leisure: optional activities (design)

The rule: nothing in the game needs eating, drinking or sleeping. There are no needs meters and no
penalties, ever. Every activity here is something the player may choose because it is pleasant,
funny or useful (time passes, people are met, the plane is looked after).

## Framework

- **Leisure place**: a spot in a town that offers activities. Data, not code: key, town (place
  id), name, kind (`bar`, `coffee house`, `inn`, `home`, `mooring`), position and facing, the
  person who keeps it (a living-world person: their purse receives the money), opening hours,
  and the menu it serves (food list by region, drinks list: full, short or coffee only).
  First places: the Hotel Ancora terrace bar in Porto Vecchio (Sofia Marinou keeps it), the
  Porto Vecchio coffee house (the town's existing cafe venue), the hotel's rooms, a helped
  family's spare room (any town), and the player's own mooring.
- **Activity**: sit down, order, listen, rest, tinker. Each has an optional duration. Time passes
  by advancing the living world's clock in steps (`living.advance_minutes`), with the screen's
  hour following it, so everyone else carries on: boats arrive, prices move, notices change.
  While sitting, time runs at the normal pace; resting skips ahead (to 07:00 or 18:00).
- **Costs through the ledger**: every order is one `transfer` from the player's account to the
  keeper's account (kind `trade`), so the money balance of the world is conserved and the keeper
  can spend it. Prices: drinks and dishes made from a living-world good (wine, fish, oil, grain)
  are priced from that town's market price for the good (a glass is a share of a package with the
  house's markup); everything else has an invented period price in lire. Nothing is free except a
  helped family's spare room (they won't take money).
- **People and standing**: pilots (people with aircraft or a flying trade) gather on the terrace
  in the evening as a living-world rule, so whoever is in town is really there and can be talked
  to in the normal conversation style. A spare room is offered by someone whose relationship with
  the player is warm (affinity, or a memory of a rescue or delivery by the player). The keeper's
  dry remarks about orders come from the drinks data, in her voice.
- **Presentation**: a prompt card near each place (tappable), a sitting camera, panels in the
  existing paper style (menu with categories and a search line; rest choices; tinkering list), a
  short card while time passes. A gentle sway after several strong drinks, off in Options.

## Built (first round)

1. The Hotel Ancora: a pier hotel on the Porto Vecchio waterfront with a terrace over the water;
   pilots at tables; from 19:00 a live singer and a small band (procedural synth, room acoustic,
   no radio filter).
2. Food and drink menus by place and region; a deliberately deep drinks list (hundreds of real
   drinks) with categories, search and the keeper's remarks; drinks arrive on the table.
3. Rest: a hotel room (paid) and a helped family's spare room (free); sleep until morning or
   evening.
4. Working on the plane at the mooring, by hand: the pilot walks to each job and does it (from
   the quay when it is within reach, else aboard: onto the float or deck, up a strut to the wing's
   root), with a pose that fits; time passes; a small real effect only on light engine/hull wear
   (heavier damage stays the workshop's job). See "Plane work" in the glossary.

## Controls

- On foot near the hotel: **F** at the player's table by the rail sits down; **F** at the bar
  orders standing; **F** at the land-side door asks for a room. **F** at the coffee house's table
  sits there. Near one's moored aircraft: **G** works on it. Every prompt card is tappable.
- Seated: the bar along the bottom (keys 1-5 or taps): the menu, wait an hour, take a room, talk to
  whoever is at the next table, get up (Escape). The menu: section chips, type to search, up/down
  (wheel, arrow keys, page buttons), order.
- A grateful family's member, at home: "Could I rest at yours a while?" in the conversation.

## Later (worth adding)

- Take the waters at hot springs; sea bathing from the beach; a siesta in the shade.
- Fishing from the quay or a hired boat (fish go into the living world's stock).
- Cards, backgammon (tavli) and dominoes with townsfolk at the coffee house, small stakes.
- The barber and a shave; tailor for a new flying jacket; laundry.
- A feast day dance in the square; a church service; the cinema in a capital (silent films).
- Picnic flights to beaches; sightseeing passengers; a photographer on the quay.
- Gardening a hotel garden; feeding the town cats (exists) and adopting one.
- Reading the newspapers (the world's news) at the coffee house; writing letters home.
- Teaching a youngster to fly; a flying club evening; model aircraft with the children.
- Music: request a song from the band; learn the bouzouki; sing along (the crowd's call).
- Cooking a meal for a family you stay with; bringing wine as a guest.
- Stargazing from a hilltop (celestial.jo already has the sky); a lighthouse visit.
- Night swimming; walking the hill paths; visiting monasteries.
