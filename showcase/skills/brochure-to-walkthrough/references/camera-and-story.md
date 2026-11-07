# Camera and story: the route, the chapters, the overlay

The route is what a viewer actually experiences; everything else is set dressing. The reference
build's audit found its worst faults here (whip pans of 160° in one wheel notch, bedrooms shot
top-down, a garden chapter framing the neighbour's wall, a 0.09 stretch of roof with no card),
so these rules are written as limits a script checks, not as taste.

## How the route is defined (`src/path.js`)

- `K` is a table of keyframes `[progress, [x, y, z], [lookX, lookY, lookZ], fov]` in world
  metres (x across the plot, y up, z = −d from the street). Position is a centripetal
  Catmull-Rom through the keys; a monotone cubic maps scroll progress to the spline parameter so
  speed changes stay smooth and a key can hold.
- Orientation: derive it per key from `look − pos` and interpolate yaw/pitch (unwrapped) with the
  same monotone cubic, never a look *point* on a spline: a look point that passes near the lens
  flips the view. A vertical lens shift per key (fraction of frame height, |s| ≤ 0.5, applied with
  `camera.setViewOffset`) lets interiors stay level with the bed framed low, the way an
  architectural photographer shoots.
- `DroneRig` adds the gimbal feel: slerp lag on orientation, a small bank into turns, a hover
  whose amplitude falls with altitude, and a portrait fov cap. Nothing in the rig may depend on
  scroll history: `?p=` stills and rail jumps must give the same frame as scrolling there.
- `scripts/check-path.mjs` samples the route at 0.001 and exits 1 on: yaw > 12° or pitch > 6° per
  0.005 of progress, pitch outside −35°…+40°, authored look target < 2.4 m from the lens, lens <
  0.3 m from any surface (hero shell, interior, rooftop kit and the two attached neighbours), lens
  shift beyond ±0.5, or a story-table breach. It reads the chapters from `src/story.js`. Run it
  after every keyframe edit; do not loosen its limits to pass. Where a shot can afford it, keep
  more than the minimum: the stair hold passes the front flight's rail at 0.5 m, which reads as
  a deliberate move rather than a graze.

## One chapter table

Keep chapter ranges in one place (`src/story.js`: key, rail label, `from`, `to`, `jump` — the
progress of the chapter's best still, used for rail clicks) and derive the cards' windows, the
time-of-day ramp (sunset start, night by), the sun swing window and the plot-pin window from it.
Retiming the route then moves the sunset and the pin with it. Each card fades over ±`FADE`
(0.008) around its window, so consecutive windows sit at least `2 × FADE` (0.016) apart and two
cards never show at once; `jump` lies inside its window. The rail lights one chapter, and
`ui.js` writes each card's number from the table, so card and rail cannot disagree.

## Pacing

- Outdoor approach (arrival, community, plot) about 0.16 of progress; it is scenery, not the product.
- Every room the buyer cares about gets a hold of ≥ 0.03 with a card; bedrooms ≥ 0.05 each,
  the terrace or garden ≥ 0.06 with the sunset inside it.
- Transits between levels ≤ 0.03, inside the stair core, never an exterior flip or a roof skim.
- No stretch > 0.03 without a card. Dead stretches are where people stop scrolling.

## Composition by chapter type

| Chapter | Shoot it as | Avoid |
| --- | --- | --- |
| Arrival | from about 110 m: near enough that the hero row reads through the haze as houses, the lagoon still in the top of the frame; house centred, plot pin on from p = 0, hero text off-centre | an opener from 190 m that reads as a field of identical blocks with the house behind the title |
| Facade | three-quarter from street level, rising to the balcony | flat elevation, camera inside the opposite row |
| Entrance / kitchen | a slow turn that puts the kitchen in frame if the card names it (needs ≥ 0.07 at the yaw limit) | a hall shot under a "kitchen" card |
| Living | an arc around a fixed target ≥ 2.4 m away, moving sideways 1–1.5 m | a pan from a fixed point (no parallax), the sofa arm filling the frame |
| Garden | a rear elevation: patio, lit glazing, rear balcony, planting | the boundary wall, the neighbour's balconies |
| Bedroom | level, eye height 1.35–1.45 m, 3/4 view: bed centred, sheers as the key light, wardrobe or prints in frame, held ≥ 0.03 | pitching −30° onto the bedding; prints cut by the top edge |
| Master | 3/4 from the room's corner with the front glazing lighting the bed; the print beside the bath door | a top-down bedding close-up |
| Stair | back into the rear of the well, rise over the half landing to a hold that reads the dog-leg (upper flight and rail climbing to the roof landing and its window, the hall below), then up to the landing short of the next wall; ≥ 0.5 m from the rails | a lens grazing the rail at the 0.3 m limit, a climb with nothing but a wall in frame |
| Roof terrace | pergola and seating with the sun behind, the sun setting during the hold | the sun and the neighbours with no terrace |
| Finale | a pull-out that keeps the house visible beside the summary card | the house hidden behind a centred data table |

Compose every chapter with a still before locking it: `?p=` for a route progress, or a camera
override (`&cam=x,y,z,lx,ly,lz[,fov[,shift]]`, read only in the still mode, so always with `?p=`)
for a candidate vantage. Stage the furniture for the key frame, not the room: bedroom 4's desk,
vase and tray moved from the west corner, 58° off the lens axis and never seen, to the fixed pane
of the terrace glazing inside the frame from the foot of the bed.

## Copy and cards

The card is checked against the still at its mid progress: if the card says kitchen, the kitchen
is on screen; if it says golden hour, it is golden hour. Rewrite the copy or re-aim the camera.
Eyebrows and rail labels agree; sizes come from `plan.js`; no price, no buyer contact unless
asked; the summary says "visualisation" and credits the sources.

## Overlay, phone, accessibility

- Height media queries (700, 560 and 480 px in `style.css`) drop the mini plan and the style line,
  then the figures, then the paragraphs, before a card can collide with the top bar; every card
  must fit at 1024 × 576 and 1280 × 620. Text contrast ≥ 4.5:1 over bright interiors and sky (set
  the same values on `-webkit-backdrop-filter`).
- Phone portrait: smaller card, no meter line, 44 px targets, the fov cap reconsidered with the
  lens shift so interiors are not door-slot views; check 390 × 844 and 844 × 390.
- A real `<main>` around the cards, `aria-current` on the rail, `aria-pressed` on toggles, a
  polite live region naming the chapter, visible focus; reduced motion removes the lag and the
  bank, never adds speed.
- Keyboard: arrow, page and space keys step between chapters' `jump` frames, Home and End go to
  the ends. Step from the landing last requested, not from the eased progress, or a second press
  mid-flight asks for the same landing again; wheel, touch or pointer input (or 4 s) hands
  control back.
- Inactive cards are hidden from assistive tech, so give the whole story as text: a skip link
  (`a.skip`) to a visually hidden `#story-text` section that `ui.js` clones from the cards (every
  chapter's heading and copy, the credits in full, no controls or plans).
- Ending: Replay, Copy link to this style, a printable plan drawn from `plan.js`; a one-sentence
  visualisation note (`p.vis-note`) visible at every size, the long disclaimer and credits in a
  collapsible `details.fine`; no placeholder `mailto:`/`tel:` links.
- Controls: the style pill shows from the facade to the terrace; "Auto" is titled for what it
  does (day → night).

## Verify

`node scripts/check-path.mjs` exits 0; a 16-frame contact sheet with the overlay on; phone
frames; a still at every chapter's `jump` progress, read one by one against its card.
