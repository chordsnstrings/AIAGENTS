// The one chapter table. Every progress number the page shows the visitor comes from here:
// the cards' windows (ui.js reads them by data-chapter key), the rail, where a rail click or
// an arrow key lands, when the light turns from day to sunset to night, when the sun swings
// for the terrace and when the plot pin shows. The camera keys in path.js are authored to the
// same numbers; keeping them in one place means a retime cannot leave the sunset on the
// wrong chapter or a card over a stretch the camera has already left.
//
// Rules the table obeys (scripts/check-path.mjs asserts them): consecutive windows are at
// least FADE * 2 apart so two cards never show at once, no stretch longer than 0.03 has no
// card, and `jump` (where the rail lands) lies inside the window. Windows sit a little inside
// the camera's dwell so the card arrives once the shot has settled.

export const FADE = 0.008; // a card fades over +-FADE around each edge of its window

export const CHAPTERS = [
  { key: 'hero', rail: 'Arrival', from: 0, to: 0.04, jump: 0 },
  { key: 'community', rail: 'The community', from: 0.056, to: 0.13, jump: 0.1 },
  { key: 'facade', rail: 'Facade', from: 0.146, to: 0.215, jump: 0.19 },
  { key: 'ground', rail: 'Ground floor', from: 0.235, to: 0.31, jump: 0.289 },
  // the living card stays until the lens is through the glazing: the garden copy describes
  // the house seen from outside, so its card must not arrive while the stair is on screen
  { key: 'living', rail: 'Living', from: 0.335, to: 0.452, jump: 0.385 },
  { key: 'garden', rail: 'Garden', from: 0.474, to: 0.505, jump: 0.49 },
  { key: 'bedrooms', rail: 'Bedrooms', from: 0.521, to: 0.58, jump: 0.56 },
  { key: 'master', rail: 'Master suite', from: 0.602, to: 0.664, jump: 0.655 },
  { key: 'balcony', rail: 'Front balcony', from: 0.68, to: 0.712, jump: 0.695 },
  { key: 'stair', rail: 'The stair', from: 0.728, to: 0.784, jump: 0.765 },
  { key: 'bed4', rail: 'Bedroom 4', from: 0.8, to: 0.866, jump: 0.85 },
  { key: 'terrace', rail: 'Roof terrace', from: 0.882, to: 0.944, jump: 0.938 },
  { key: 'summary', rail: 'Summary', from: 0.96, to: 1, jump: 1 },
];

export const chapter = (key) => CHAPTERS.find((c) => c.key === key);

// progress a fraction f of the way through a chapter
const at = (key, f) => { const c = chapter(key); return c.from + f * (c.to - c.from); };

// the chapter the visitor is in: the window containing p, else the last one passed
export function chapterAt(p) {
  let cur = CHAPTERS[0];
  for (const c of CHAPTERS) if (p >= c.from) cur = c;
  return cur;
}

// Time of day in auto mode: daylight until the camera is out on the roof terrace, sunset
// mid-chapter, night by the time the summary shows.
export const TOD = { sunsetFrom: at('terrace', 0.3), nightBy: at('summary', 0.55) };

// The sun holds south-west through the master suite and swings north-west while the camera
// is in the stair core (the one stretch with no sunlit view), then sets over the terrace.
export const SUN = {
  swing: [chapter('stair').from, chapter('stair').to],
  set: [at('terrace', 0.55), at('terrace', 0.9)],
};

// Plot pin: on from the first frame until the facade orbit, back for the blue-hour ending.
export const PIN = {
  windows: [
    { in: [-1, 0], out: [chapter('community').to - 0.012, chapter('facade').from + 0.01] },
    { in: [chapter('summary').from - 0.01, chapter('summary').from + 0.012], out: [2, 3] },
  ],
};

// The interior style switcher shows only where a change is visible: from the facade (the
// master suite reads through the glazing) to the end of the roof terrace.
export const STYLE_PILL = [chapter('facade').from, chapter('terrace').to];
