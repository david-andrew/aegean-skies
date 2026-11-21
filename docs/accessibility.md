# Accessibility: colour vision

How Aegean Skies tells sides apart for players who do not see every colour, how that is checked,
and where the thresholds come from.

## What the game does

The Settings page's Accessibility section has "Colours of the sides": Standard, Red-green,
Blue-yellow and No colour, and a switch for a shape on every mark.

Each preset is a different set of colours drawn for the player. None of them is a filter over
the picture, and none shows a sighted player what colour blindness looks like. That is the trap
to avoid: a simulation helps nobody who is colour-blind. Here the simulation is used only in the
test, to check that the colours a preset draws are still far apart to the eye it is for.

| Preset | For | Enemy | Friend | Others |
| --- | --- | --- | --- | --- |
| Standard | most players | red-orange | blue | cream |
| Red-green | protanopia, deuteranopia | orange (Okabe-Ito #E69F00) | blue (the standard friend's) | dark, in a pale halo |
| Blue-yellow | tritanopia | orange (Okabe-Ito #E69F00) | bright teal | dark, in a pale halo |
| No colour | achromatopsia, greyscale screens | white | dark, in a pale halo | grey |

Three things carry a side, so that colour is never the only one (WCAG 2.2 SC 1.4.1, "Use of
Color"; the Game Accessibility Guidelines say the same):

- **Colour**, from the preset.
- **Shape.** A target's brackets and a person in the water always carry their side's sign: a
  chevron for an enemy, a ring for a friend, a dot for anyone else. The lead ring is only ever an
  enemy's and the marks over one's own flight only ever friends', so their kind says the side.
  With "A shape for each side on every mark" on (always on with No colour) those carry the sign
  too.
- **Light against dark.** In the three presets one side is a dark mark in a pale halo while the
  others are light marks in a dark halo. No eye loses that difference, and it is what puts each
  preset's weakest pair far past the threshold.

In the three presets the marks are also drawn at full strength, a pixel heavier, with a whole
halo, and names sit on an outline wide enough to count as their background. The standard look
keeps its lighter halo and thinner lines.

The war chart's country inks change with the preset too (nations, not sides). The two colour
presets use Okabe and Ito's orange and blue, and black. With No colour the three inks are dark
steps of lightness and each country's held ground is hatched its own way; every mark's words
name its country in any preset.

## How it is checked

`tests/colour_vision_test.jo` runs in CI with the rest of the tests. It follows the process of
the palette checkers (Viz Palette, Adobe Color's accessibility tools, Coblis, Color Oracle):
simulate the eye, then measure what is left.

1. **Simulate** each deficiency at full severity, in linear light: protanopia, deuteranopia and
   tritanopia with both standard models (Machado et al. 2009; Brettel, Viénot and Mollon 1997,
   the reference for tritanopia), and no colour at all as luminance alone. Every check must pass
   under both models.
2. **Measure the sides against each other**: CIEDE2000 and the CAM02-UCS distance between every
   pair of side colours.
3. **Measure each mark against what is behind it**: the sea near and far, the sky high, low and
   at the horizon, cloud lit, shaded and in shadow, and the sky over an overcast. Those colours
   are sampled from captures of the game (`GROUNDS` in `src/colour_vision_scores.jo`). A mark
   passes on a ground by its own colour, or by its halo if the colour then stands off the halo.
4. **Measure contrast** with WCAG 2.2's contrast ratio: marks against their grounds, names
   against theirs.

The instruments are checked first against published values: Sharma, Wu and Dalal's CIEDE2000
test data, the worked examples of CIE 159:2004 for CIECAM02, WCAG's own reference greys, and
that both simulations keep white and grey unchanged.

### The thresholds

| Check | Threshold | Where it comes from |
| --- | --- | --- |
| Two sides, CAM02-UCS | 20 or more | Petroff (2021) required a minimum perceptual distance of 20 in CAM02-UCS between colours, under normal vision and under Machado's simulation at full severity, for his six-colour accessible sets (18 and 16 for eight and ten colours). |
| Two sides, CIEDE2000 | 20 or more | The same figure in the CIE's current colour-difference formula, which most checkers report. Petroff's own measure is CAM02-UCS, so both must pass. |
| Two sides with no colour, CAM02-UCS lightness | 20 or more | Petroff required a lightness distance of 5 for monochromacy; the test asks four times that. |
| A mark against its ground, CIEDE2000 | 15 or more | Ours. No published figure exists for a mark over a natural scene; 15 is far past the point where two colours are plainly different side by side. |
| A mark against its ground, contrast | 3:1 or more | WCAG 2.2 SC 1.4.11, "Non-text Contrast": graphical objects need 3:1 against adjacent colours. |
| A name against its ground, contrast | 4.5:1 or more | WCAG 2.2 SC 1.4.3, "Contrast (Minimum)", for text under 18 point. WCAG treats a wide outline that fills the letters' inner details as the text's background, and a narrow one as part of the letter. |

A mark's two tones (line and halo) are between 8.3:1 and 9.6:1 apart in the presets, as each eye
sees them. Two tones that far apart keep 2.9:1 or better, with one or the other, against any
background at all, so the contrast nearly holds beyond the grounds that were sampled, and it
holds at 3:1 on every one of those.

## The scores

Each preset under the eye it is for. Regenerate with `sloppy --release tools/colour_vision_report.jo`.

| Preset | Seen by | Sides: least ΔE2000 | Sides: least CAM02-UCS | Sides: least lightness ΔJ' | Colour alone on a ground: least ΔE2000 | Mark with halo on a ground: least ΔE2000 | Mark contrast (WCAG 1.4.11) | Name contrast (WCAG 1.4.3) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Red-green | protanopia (Machado) | 53.3 (enemy/friend) | 54.2 | 7.8 | 14.3 (friend on low sky) | 32.0 | 3.16:1 (enemy on far sea) | 8.3:1 |
| Red-green | protanopia (Brettel) | 53.8 (enemy/friend) | 55.3 | 4.0 | 14.4 (friend on low sky) | 31.7 | 3.03:1 (enemy on far sea) | 8.7:1 |
| Red-green | deuteranopia (Machado) | 56.5 (enemy/friend) | 56.9 | 2.9 | 13.3 (friend on low sky) | 30.8 | 3.36:1 (friend on far sea) | 9.5:1 |
| Red-green | deuteranopia (Brettel) | 54.8 (enemy/friend) | 56.7 | 0.4 | 13.6 (friend on low sky) | 31.0 | 3.32:1 (enemy on far sea) | 9.6:1 |
| Blue-yellow | tritanopia (Machado) | 61.0 (enemy/other) | 56.4 | 14.9 | 17.4 (enemy on lit cloud) | 34.1 | 3.05:1 (enemy on far sea) | 9.2:1 |
| Blue-yellow | tritanopia (Brettel) | 60.6 (enemy/other) | 49.8 | 13.7 | 16.5 (enemy on lit cloud) | 34.1 | 3.14:1 (enemy on far sea) | 9.3:1 |
| No colour | achromatopsia | 20.5 (enemy/other) | 28.3 | 28.2 | 2.4 (friend on deep sea) | 29.7 | 3.01:1 (other on far sea) | 8.9:1 |

The standard look under every eye: what a player who never opens the setting gets.

| Preset | Seen by | Sides: least ΔE2000 | Sides: least CAM02-UCS | Sides: least lightness ΔJ' | Colour alone on a ground: least ΔE2000 | Mark with halo on a ground: least ΔE2000 | Mark contrast (WCAG 1.4.11) | Name contrast (WCAG 1.4.3) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Standard | normal | 34.4 (enemy/other) | 33.9 | 3.0 | 5.7 (other on lit cloud) | 28.2 | 2.38:1 (enemy on sky over cloud) | 2.5:1 |
| Standard | protanopia (Machado) | 23.5 (enemy/other) | 30.4 | 14.1 | 4.3 (other on lit cloud) | 22.2 | 2.20:1 (enemy on far sea) | 2.6:1 |
| Standard | protanopia (Brettel) | 23.6 (enemy/other) | 30.8 | 13.2 | 4.4 (other on lit cloud) | 22.3 | 2.14:1 (enemy on far sea) | 2.5:1 |
| Standard | deuteranopia (Machado) | 17.7 (enemy/other) | 22.6 | 0.0 | 3.9 (other on lit cloud) | 27.4 | 2.40:1 (enemy on sky over cloud) | 2.8:1 |
| Standard | deuteranopia (Brettel) | 18.2 (enemy/other) | 23.3 | 2.4 | 3.9 (other on lit cloud) | 27.8 | 2.36:1 (enemy on sky over cloud) | 2.7:1 |
| Standard | tritanopia (Machado) | 29.5 (enemy/other) | 37.0 | 6.4 | 4.4 (other on lit cloud) | 27.4 | 2.36:1 (enemy on far sea) | 2.5:1 |
| Standard | tritanopia (Brettel) | 26.8 (enemy/other) | 33.0 | 3.4 | 4.1 (other on lit cloud) | 27.0 | 2.38:1 (enemy on sky over cloud) | 2.5:1 |
| Standard | achromatopsia | 5.5 (enemy/friend) | 6.9 | 6.9 | 1.4 (friend on cloud shade) | 20.3 | 2.38:1 (enemy on sky over cloud) | 2.5:1 |

What that says about the standard look:

- For the three dichromacies its sides stay past Petroff's 20 in CAM02-UCS under both models. In
  CIEDE2000 it passes for protanopia and tritanopia and falls a little short for deuteranopia
  (about 18), where the red-orange enemy and the cream neutral are closest.
- With no colour, enemy and friend are the same lightness (about 6 apart). There the standard
  look rests on the signs that targets and people in the water carry; No colour is the remedy.
- Its marks and names fall short of WCAG's 3:1 and 4.5:1 on the grounds between light and dark
  (the far sea, the sky over cloud): the lighter halo is not enough there. Giving the standard
  look the presets' whole halo and wide outline, with no colour changed, would take its marks to
  about 3:1 and its names to 6:1 or better (`tools/colour_vision_report.jo firm`).

The war chart's inks (`tools/colour_vision_report.jo inks`):

| Preset | Seen by | Least ΔE2000 between inks | On paper | On the chart's sea | On land |
| --- | --- | --- | --- | --- | --- |
| Standard | normal | 40.4 (ink 1/ink 2) | 44.3 | 36.9 | 13.1 |
| Standard | protanopia (Machado) | 8.9 (ink 1/other ink) | 40.6 | 37.5 | 11.0 |
| Standard | protanopia (Brettel) | 10.3 (ink 1/other ink) | 39.7 | 35.9 | 11.0 |
| Standard | deuteranopia (Machado) | 7.7 (ink 1/other ink) | 41.7 | 37.0 | 11.9 |
| Standard | deuteranopia (Brettel) | 8.0 (ink 1/other ink) | 42.5 | 36.7 | 11.8 |
| Standard | tritanopia (Machado) | 12.6 (ink 2/other ink) | 48.6 | 26.2 | 16.2 |
| Standard | tritanopia (Brettel) | 12.2 (ink 2/other ink) | 45.6 | 25.7 | 14.0 |
| Standard | achromatopsia | 2.3 (ink 1/other ink) | 41.4 | 25.2 | 11.4 |
| Red-green | protanopia (Machado) | 41.3 (ink 2/other ink) | 24.0 | 20.4 | 15.7 |
| Red-green | protanopia (Brettel) | 39.8 (ink 2/other ink) | 23.6 | 22.5 | 16.1 |
| Red-green | deuteranopia (Machado) | 38.2 (ink 2/other ink) | 22.0 | 23.8 | 19.6 |
| Red-green | deuteranopia (Brettel) | 39.1 (ink 2/other ink) | 22.6 | 22.3 | 19.5 |
| Blue-yellow | tritanopia (Machado) | 41.5 (ink 2/other ink) | 21.5 | 16.0 | 20.7 |
| Blue-yellow | tritanopia (Brettel) | 38.8 (ink 2/other ink) | 20.6 | 19.0 | 20.5 |
| No colour | achromatopsia | 10.8 (ink 1/ink 2) | 46.7 | 30.3 | 15.4 |

## Compared with the established palettes

The presets were searched against Okabe and Ito's Color Universal Design set, Paul Tol's bright,
vibrant, high-contrast and muted schemes, and IBM's colour-blind-safe palette, scoring every
enemy, friend and neutral triple with the checks above.

- Orange against blue is the strongest warm and cool pair for every dichromat, as those palettes
  say. The presets use Okabe and Ito's orange.
- For the friend, the palettes' blues and teals are close to the game's own teal sky. The
  standard friend's blue stands off it best for red-green eyes, and a bright teal for blue-yellow
  eyes, so those are kept.
- A dichromat has one axis of hue, so three light colours crowd it: the first presets' weakest
  pairs were about 32 (red-green), 24 (blue-yellow) and 10 (no colour). Making one side dark
  raises them to 53, 60 and 20.
- One set (orange, the standard blue, dark) scores 50 or more for all three dichromacies. The
  two colour presets could be merged into it; they are kept apart because teal stands off the
  sky better for tritanopia.
- For the chart, Okabe and Ito's orange, blue and black are the three of their set that stay 38
  or more apart for every dichromat while standing off the paper, the sea and the land.

## Limits

- With no colour, lightness alone cannot part three inks widely on a chart of many tones (about
  11 between them); the hatching and the words carry the country.
- The No colour preset's white and grey are 20.5 apart, just past the threshold: CIEDE2000
  compresses differences between light colours. Shape is what tells an enemy from a bystander
  there.
- The standard chart's green ink on green land is weak (about 13) for every eye, as it always was.
- A simulation is a model of a typical dichromat at full severity, not of any one person. Passing
  is evidence, not proof; a colour-blind player's report outranks it.
- Friends far off are drawn fainter on purpose, in every preset, and the figures above are for
  marks at their usual strength.

## Running it

- The test: `sloppy test tests/colour_vision_test.jo` (CI runs it on every push).
- The tables: `sloppy --release tools/colour_vision_report.jo [before|inks|firm]`.
- A capture as an eye sees it: `sloppy --release tools/colour_vision_view.jo in.png out.png
  protan|deutan|tritan|achromat|sheet`.
- Captures of every mark over the view: `AEGEAN_CAPTURE_SIDES=4` with
  `AEGEAN_COLOUR_VISION=standard|red_green|blue_yellow|monochrome` (add `+shapes` for the shapes
  option).
- New ground colours: `tools/colour_vision_view.jo capture.png sample x y`, then `GROUNDS` in
  `src/colour_vision_scores.jo`.

## Sources

- M. Okabe and K. Ito, "Color Universal Design (CUD): How to make figures and presentations that
  are friendly to Colorblind people", 2002, revised 2008. https://jfly.uni-koeln.de/color/
  (the set's colours are in its figure 16; orange #E69F00 and blue #0072B2 as usually transcribed).
- P. Tol, "Colour Schemes". https://sronpersonalpages.nl/~pault/
- IBM Design Language, colour-blind-safe palette (#648FFF, #785EF0, #DC267F, #FE6100, #FFB000),
  as transcribed at https://lospec.com/palette-list/ibm-color-blind-safe.
- G. M. Machado, M. M. Oliveira and L. A. F. Fernandes, "A Physiologically-based Model for
  Simulation of Color Vision Deficiency", IEEE Transactions on Visualization and Computer
  Graphics 15(6), 2009.
- H. Brettel, F. Viénot and J. D. Mollon, "Computerized simulation of color appearance for
  dichromats", Journal of the Optical Society of America A 14(10), 1997. Parameters for sRGB from
  libDaltonLens (N. Burrus, public domain), https://github.com/DaltonLens/libDaltonLens.
- G. Sharma, W. Wu and E. N. Dalal, "The CIEDE2000 Color-Difference Formula: Implementation Notes,
  Supplementary Test Data, and Mathematical Observations", Color Research and Application 30(1),
  2005. Test data: https://hajim.rochester.edu/ece/sites/gsharma/ciede2000/
- CIE 159:2004, "A colour appearance model for colour management systems: CIECAM02"; M. R. Luo,
  G. Cui and C. Li, "Uniform colour spaces based on CIECAM02 colour appearance model", Color
  Research and Application 31(4), 2006.
- M. A. Petroff, "Accessible Color Sequences for Data Visualization", 2021. https://arxiv.org/abs/2107.02270
- W3C, Web Content Accessibility Guidelines 2.2: Understanding SC 1.4.1 (Use of Color), 1.4.3
  (Contrast (Minimum)) and 1.4.11 (Non-text Contrast). https://www.w3.org/WAI/WCAG22/Understanding/
- Game Accessibility Guidelines, "Ensure no essential information is conveyed by a fixed colour
  alone". http://gameaccessibilityguidelines.com/ensure-no-essential-information-is-conveyed-by-a-colour-alone/
