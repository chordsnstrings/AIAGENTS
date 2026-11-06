# Handoff: route & story pass

Things this pass needed in files it does not own, for whoever owns them.

## src/main.js (performance owner)

- `body.lowfx`: `style.css` carries a rule that swaps the overlay's backdrop blur for solid
  glass under `body.lowfx` (and already does so under `@media (pointer: coarse)`). Add
  `if (TIER === 'low') document.body.classList.add('lowfx');` next to the `noui` line
  (`main.js` line 46) so the low tier gets the same swap on desktops without a coarse pointer.
- Garden exposure: the Garden chapter now holds over the rear wall looking back at the house
  (`path.js` keys 0.47–0.502, camera about (3.4, 4.5, d 19.5)). The rear elevation is in the
  sun's shade at azimuth −55°, and `exposure` there is the sunlit-exterior value (`st.exp`),
  so by day the frame reads as dusk even though the lit glazing shows well. Expose for the
  shade as a photographer would: when the camera is behind the house (x −1..7, z −15..−21.5,
  y < 7.5) lift `expTarget` by about ×2.5, blended like `inside` (the box sits next to the
  `inHouse` test, `main.js` line 184). Check with `?p=0.493&ui=0`.
- Loader: the loader's presentation is done (poster, progress, WebGL fallback). It reads
  nothing new from `main.js`; `ui.progress(f, text)` and `ui.fatal(msg)` keep their contracts.
  If texture loading is deferred, keep calling `ui.progress` with a real fraction.

- Look-out exposure: the mirror of the look pass's look-in request. Where the lens is inside
  the house box but the view goes out through glazing, `expTarget` is the room's lifted value
  and the sunlit exterior blows out: bedroom 4 towards the terrace (`path.js` 0.862–0.886,
  the card starts at 0.882 once the lens is through the panel, but the last frames inside are
  white) and the living room towards the garden (0.418–0.456). Blend `expTarget` back towards
  `st.exp` by a look-out weight (look point outside the box and within about 7 m), as the
  look-in item does the other way. Check with `?p=0.875&ui=0` and `?p=0.44&ui=0`.

## src/interior.js (realism owner)

- Bedroom 4's door (`door(3.3, 8.0, F2, 0.85, 1.0, true)`) swings only 1.0 rad into the room,
  so its free end sits at x 3.76, d 8.72: the doorway leaves at most 0.2 m of clearance on a
  straight run and the route threads it diagonally (`path.js` keys 0.812–0.834). Swinging it
  to ±1.45 rad like the other doors would let the camera pass straight at x 3.775 with 0.375 m
  clearance. Re-run `node scripts/check-path.mjs` after any door or wall change.
- The roof landing is a 1.45 × 1.2 m lobby (x 2.95–4.4, d 6.75–7.95) and the potted tree
  `plant(4.1, F2, 7.4, 0.9, 'leaf')` fills it: its canopy (radius 0.77 m, 0.4–1.9 m above the
  floor) covers x 3.3–4.9 in front of the bedroom-4 door, so the route cannot hold on the
  landing and brushes the canopy's edge on the way to the door (0.818–0.823). Move it onto the
  gravel roof outside the landing glazing, e.g. `plant(5.2, F2, 7.3, 0.9, 'leaf')` (gravel
  x 4.5–6.0, d 6.6–7.95): it still reads through the glazing from the stair top (0.765–0.78)
  and the lobby is free for a landing hold if the route ever wants one.

## Skill references (`showcase/skills/brochure-to-walkthrough/references/`)

- `template-architecture.md`: the chapter windows now live in `src/story.js` (cards carry
  `data-chapter`, not `data-from`/`data-to`/`data-rail`); `check-path.mjs` imports the table
  instead of parsing `index.html`, tests look distance at the authored keys, and checks the
  lens shift and the table's own rules. `DronePath.sample` returns `pos` plus a look point 10 m
  along the view; `path.shift` is the lens shift for the rig (`DroneRig.update(..., { shift })`).
- `decisions-and-pitfalls.md`: pitfall 19 is now the implemented design (yaw/pitch
  interpolation, limits in `check-path.mjs`, no runtime slew clamp).
