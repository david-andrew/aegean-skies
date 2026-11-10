# Flight feel: what is done and what is next

From the designer's playtests and three independent research reports (docs/research/speed_*.md).
The principle they agree on: speed is felt through the ground's flow under the eye (speed over the
camera's height above the surface), discrete marks passing, acceleration (not speed), and causes
one can see; spectacle laid on top reads as fake.

## Done
- Chase camera in the flight path's frame, low (about 2 m over the sea) when skimming, per-axis
  springs driven by the aircraft's real acceleration, no noise shake, a small FOV kick on changes
  of pace (src/pilot.jo `chase`).
- The sea's own crisp marks at three sizes with a one-frame shutter (src/sea.jo `_marks`).
- The floats meet the sea that is drawn (FlightEnv.swell).
- Airframe flex and flutter (wings bow under load, tips shake, tail flutters) instead of shaking
  the whole aircraft.

## Next
- Things to pass close by over open water: net-float lines, buoys, skerries, moored boats, harbor
  moles; routes along cliffs.
- Audio: engine pitch tracking airspeed over a wide range (windmilling in a dive), a water-rush
  layer while planing, pass-by whooshes with Doppler for things near.
- Planing as one event: spray, sound and release from the water together; spray and a skimming
  wake from the downwash when fast and within a few meters of the water without touching it.
- Wakes overhauled: real Kelvin wakes (a displaced, shaded strip mesh whose ridges spread out from
  where the hull or floats touched), not painted foam.
- Cloud wisps and edges to pass at cloud height.
- The camera mirror effect: view vibration from the airframe, tied to its flex (subtle; tune).
- Wrecks: parts (floats, wing panels) torn off by what actually hit them, energetic crashes, damage
  that follows plainly from what the pilot did.
