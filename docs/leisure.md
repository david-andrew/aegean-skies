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
  house's markup); everything else has an invented period price in phoenixes. Nothing is free except a
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

## Built (round six)

5. **Tavli** at the coffee house (Portes): played against a townsperson who plays with a
   personality, for stakes both can stand, through the ledger. Those near the table come first,
   then the town's regulars at leisure. The board is drawn in code: a walnut case with a Greek-key
   inlay, bone and ebony checkers, and dice thrown with a little physics. Each opponent remembers
   the games, which warms their regard a little and gives them a word for the next meeting.
6. **A song from the band**: pick a number from the evening set and tip a phoenix; it is played
   next, and the set carries on after it.
7. **Today's paper** at the coffee house: the Porto Vecchio Courier, made from what the town has
   heard (see "The paper" in the glossary).
8. **Fishing from a dock**: cast, wait, and strike. The catch enters the world's stock as
   production, to be sold to the fish market or grilled at the hotel.

## Built (fishing, round two)

9. **The catch is physical**: the fish is in the pilot's hand, at its size and colours, flapping
   at first; he carries it as he walks. Holding one he can't cast: into the bucket, or back into
   the sea with a splash. The bucket is bought at a chandler's or the town's market, stands beside
   him on the dock while he fishes, holds six, and is carried, fish and all, by its handle.
10. **Sold at the real market**: no selling from the dock. He walks to the town's market and sells
   there through the ledger, or takes the catch to the Hotel Ancora's kitchen to have it grilled.
   Held and bucketed fish are outside the world's stock until sold or eaten, so conservation holds;
   saves keep them.

## Built (round seven)

11. **Table service and one's own pace.** What is ordered is brought, not conjured: the hotel's
   waiter carries it on a tray from the end of the bar (three things at a time), the barkeep along
   the counter to one standing at the bar, the coffee house's boy from the door. He sets each
   thing down on a free spot and comes back for the empties after they have stood a while. Each
   thing is eaten or drunk at the player's pace: hold its number (or its button) and the pilot
   lifts the glass to his lips, bending his elbow, and the level goes down; with a plate, the
   fork goes from plate to mouth with a bite on it. Let go and he holds the glass at his chest;
   another item, or Escape, puts it down. Paid once, when ordered.
12. **A bill of fare** per house: the hotel's printed card and the coffee house's chalk board,
   each with a handful of dishes and drinks and their prices. The faint line at the foot ("Other
   wines and spirits on request", or "and whatever else the house has") opens the house's whole
   book, the deep drinks list as it was.
13. **Tavli, polished.** The opponent sits across the coffee house table, seen through a window
   the board leaves open, with gestures (a shrug, a checker slapped down, a laugh); dice and
   checker sounds made in code; Plakoto as a second game, chosen with the stake.
14. **The barber** at the Hotel Ancora's corner of the waterfront: a shave and a trim, or a new
   shape for the mustache (clean-shaven, handlebar, walrus, chevron) seen in the mirror as one
   chooses; one payment to the house; Stavros talks while he works. The style is saved.
15. **Swimming** from a beach or the end of a dock: wade in, swim the crawl once it is deep, ride
   the swell, dive off a dock, climb out onto one; the moon's glitter on the water at night.
16. **Stargazing** at night on a hilltop or the end of the hotel's pier: lie back and the view
   drifts round the sky; the brighter stars at their places on the game's celestial sphere, and
   the names of stars, constellations, the planets and the moon in transliterated period Greek and
   in English, shown faintly as one looks at them. An hour can pass under the stars.
17. **Notes rising from music in the world** (not the radio): small notes float up from whoever
   is playing, so the music can be found by looking round. See "Rising notes" in the glossary.

## Built (fishing, round three)

18. **Fish stalls in the open**:
    - each harbour town's stall stands on open quay ground (or its square), found from the town's
      fixed geometry and checked by the world audit;
    - its trestle and poles are solid to walk round;
    - the smugglers' cove has none.
19. **Buckets that come from somewhere**: every bucket is an object in the world with an owner
    and a place.
    - his own waits in his locker on the home quay;
    - fishermen, the harbour office and the chandler lend theirs (by their boat or counter), by
      standing, and remember it coming back;
    - a chandler's sells new ones, put on the counter;
    - a bucket set down stays there, and saves keep every bucket where it is.

## Built (round eight)

18. **Sitting down at the bar too**: ordering at the bar seats the pilot on a stool, and what is
   ordered is brought there. Seated anywhere, the view turns about him (a drag with either mouse
   button off the table's bar, a finger; never a controller's stick) and the wheel or a pinch brings it
   nearer or farther, kept out of the walls; Get up stands apart at the end of the bar.
19. **Each thing's button is a bar** of how much of it is left, draining as one eats or drinks,
   as the plate and the glass on the table do.
20. **Company, now and then** (about one sitting in seven): someone from the town (a pilot, at
   the hotel, or someone the pilot knows, more likely than a stranger) comes over. At a table
   they ask first; at the bar they take the next stool, and may or may not talk. Sitting, they
   pass an ordinary remark now and then, and Talk to them opens the whole conversation. See
   "Company" in the glossary.

## Built (round nine)

21. **A night under a roof**: a room at the hotel, or a grateful family's spare room, is now a
   place one is in. You pay at the desk as before, then go up to the hotel's room: an iron bed, a
   washstand, a chair by the French window, and the harbour beyond its balcony. You can sleep
   until morning, rest until evening, take an hour's nap, or look out of the window. The time
   passes in the room, seen: the light at the window turns through the night, with a small clock
   instead of a dark card. A family that offers its room takes you home to their own house in the
   town. In the evening there is supper with the household they look after, real people of the
   living world. The host talks of their day and the weather, the children ask their questions,
   and there is a bowl each, bread and a bottle of their own. The bed is in the room at the back
   under the low beam, and there is coffee in the morning before you go. They take nothing for it.
   The notebook remembers the night. See "A night under a roof" in the glossary.

## Built (round ten)

22. **A pleasure flight** with someone from the town. Now and then, as the pilot comes to the
   aircraft at the dock, someone near asks to be taken up; or the pilot offers (K). They walk
   over and sit in the second seat, drawn there, and talk as it goes: nerves on the water, the
   take-off run, what they see below, their own house pointed out as the town passes under them,
   another town by its name, the landing. Back at a dock they thank the pilot and go. There is no
   fare. The world remembers it as a private meeting. See "Pleasure flight" in the glossary.
23. **The rooms lived in.** The hotel's room and the families' houses have pictures and a mirror,
   curtains, a wardrobe, jars on a shelf, garlic and herbs hung from the beam, a rug and a kilim,
   and the pilot's bag. A family's trade shows in its house: nets, floats and an oar for those who
   live by the sea; oil jars, sacks and a hoe for the land; a workbench and its tools for a
   craftsman; a desk and books for those who read; a sewing table otherwise. The rooms are lit as
   rooms are: the lamp's warm pool of an evening with dark corners beyond it, the window's cool
   light by day, moonlight while one sleeps.

## Built (round eleven)

24. **A passenger waits.** Stepping ashore with someone in the second seat asks: "Back in a few
   minutes" and they wait in the seat, up to an hour, with a word if it runs long; "Sorry, another
   day" and they go home politely. Back aboard, the flight goes on. If they give up waiting they
   say so the next time they pass, and the pilot's name takes a mild mark.
25. **Left at the table.** Getting up leaves the plates and glasses where they were. Sitting down
   again finds them; otherwise a waiter comes for them a while later and carries them off. While
   seated, only empties are cleared unasked; something untouched a good while brings "Finished
   with this?". The buttons keep the plain names, and the drain bar shows what is left.
26. **The seated view keeps its turn.** Each drag, by finger, mouse or stick, goes on from where
   the last one left it, at a table, on a stool, at supper and at the hotel room's window.

## Built (round twelve)

27. **The rooms by their things.** No buttons in a room. Tap or click the bed to lie down (sleep
   of an evening, rest by day), the chair to sit, the window to look out, the door to leave. The
   pilot gets up, walks round the furniture and sits or lies down by degrees, never jumping. What
   the pointer, the arrow keys or a pad's d-pad picks out is a shade brighter, with a small label.
   A tap wakes him early.
28. **Over to the table.** On foot, tapping or clicking the pilot's table, the bar's stool or the
   coffee house's table walks him over and sits him down.
29. **A passenger answers out loud** when offered a flight, and a marker at the screen's edge
   points to them while they're out of view.

## Built (round thirteen)

30. **Things to tap, everywhere cheap.** One's own aircraft (the cockpit to climb aboard, the engine
   to work on her), the hotel's desk, the barber's chair, the band's jar and stand, and the coffee
   house's tavli board and paper are tapped or clicked instead of their cards. He walks over and
   does what the card would. The people about are clicked to talk, as touch already did. Seated,
   the band, the jar, the board and the paper are no longer buttons on the table's bar.
31. **The gleam.** On a touch screen, what can be tapped catches the light for a moment when the
   view comes to rest. There are no words.
32. **A family's view** is up over the door. His way round the table to the back room stays in
   sight.

## Built (round fourteen)

33. **Taking the waters.** At a hot spring's terraces: tap the keeper at the bathhouse door (thirty
   lepta), change in the cabin, and tap the pool. He walks down by the stairs and settles into the
   water among a few of the town's people, who talk now and then (small talk, their own remarks,
   once a lead) while the morning passes unhurried. Tap the steps to get out and change back.
   Now and then the one who asks for a flight wants a lift to the springs' harbour, and pays a
   little there.
34. **Rooms, from the phone:** a tap while he sleeps wakes him and sends him to what was tapped;
   Back gets him up in the room, not out of it. The night paid for, the desk offers his room. The
   hotel's terrace no longer offers to fish.

## Built (round fifteen)

35. **A picnic.** A basket from the hotel or the coffee house goes along on his arm, and in the
   aircraft. On a quiet shore, tap the sand: the blanket is spread, he sits facing the sea, and the
   afternoon goes by, a bite now and then. Tap the basket to pack up.

## Controls

- On foot near the hotel: **F** at the player's table by the rail sits down; **F** at the bar
  orders standing; **F** at the land-side door asks for a room. **F** at the coffee house's table
  sits there. Near one's moored aircraft: **G** works on it. Every prompt card is tappable.
- Seated (at a table or on a stool at the bar): the bar along the bottom. What is on the table, 1 to 6 (or
  their buttons): hold to drink or eat, let go to keep it in hand; another, or Escape, puts it
  down. Then the actions, each on a letter: M the bill of fare, W wait an hour, G have one's catch
  grilled, T tavli, P the paper, S ask for a song, R take a room, K talk to whoever is near, Escape
  get up (with nothing in hand). The bill of fare: 1 to 9 or a click orders; 0 or the foot line
  opens the house's whole book (section chips, type to search, up/down by wheel, arrows or page
  buttons).
- A grateful family's member, at home: "Could I rest at yours a while?" in the conversation.
- At the coffee house: "Play tavli" and "Buy the paper" (then "Read the paper") on the bar.
- Tavli: click a checker, then where it goes (or drag it; a single place to go moves at once).
  Arrows and Enter choose by keyboard. Space throws and finishes the turn, Backspace takes it
  back, and Escape asks before giving up. By finger: tap, tap.
- The paper: wheel, arrow and page keys, a finger's drag, or the up and down buttons; Escape
  puts it down.
- At the hotel, any hour it is open: "Ask for a song" (a player who isn't here can be sent for: the panel offers the boy, for a tip). With fish: "Have your catch grilled" seated, or
  the card at the bar or the terrace table ("have the kitchen grill your catch").
- Fishing: **F** at the water's edge on a dock in a harbour town. F, Space or the first button
  casts and strikes. With a fish in the hand: **B** (or the button) puts it in the bucket, **X** throws
  it back; Escape stops (he walks off holding it, and picks up the bucket).
- On foot with a catch: at the town's fish stall, F sells it all; X at the water's edge throws the
  held fish back; B puts it in a bucket within reach.
- Buckets, on B: take yours from the locker, or put it back; pick up a bucket within reach (your
  own, or one lent you); put one back at its owner's boat or counter; put the bucket down where
  you stand. In talk: "Could I borrow a bucket?" and "I've brought your bucket back." At a
  chandler's: buy one (it's put on the counter). Holding a fish he can't start fishing, stroke a cat, haul in the line, take the waters or work on the aircraft; carrying a bucket of fish, he can't haul, bathe or work on the aircraft either.
- The barber: **F** at his chair on the waterfront by the hotel's corner.
- Swimming: **G** at the water's edge of a beach or the end of a dock; walk to swim (Shift: a
  strong stroke); out where the ground rises, or **F** to climb onto a dock.
- Stargazing: **L** at night on a hilltop or the end of the hotel's pier; Q, E and the arrows (or a
  finger) look round; **T** lets an hour pass; **L** gets up. On a phone both are buttons.
- Options: "Musical notes rising from music played nearby" (on).
- At one's moored aircraft with someone near: **K** offers them a flight (a seat to spare).

## Later (worth adding)

- Take the waters at hot springs; a siesta in the shade. (Swimming is built.)
- Fishing from a hired boat (fishing from a dock is built).
- Cards and dominoes with townsfolk at the coffee house, small stakes (tavli is built).
- A tailor for a new flying jacket; laundry. (The barber is built.)
- A feast day dance in the square; a church service; the cinema in a capital (silent films).
- Picnic flights to beaches; sightseeing passengers; a photographer on the quay.
- Gardening a hotel garden; feeding the town cats (exists) and adopting one.
- Writing letters home (the newspaper is built).
- Teaching a youngster to fly; a flying club evening; model aircraft with the children.
- Music: learn the bouzouki; sing along (the crowd's call). (Requests are built.)
- Cooking a meal for a family you stay with; bringing wine as a guest.
- A lighthouse visit. (Stargazing is built.)
- Night swimming; walking the hill paths; visiting monasteries.
