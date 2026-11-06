// The numbers that set the photographic look, kept apart from the engine so they can be
// tuned (and re-tuned per property) without touching the update loop. Units are page units:
// irradiance as the baked volume stores it, exposure as a factor on the atmosphere's.
export const LOOK = {
  giFill: 3.0,            // fill on baked daylight, for the bounces past the two the bake traces
  giLamp: 0.45,           // baked lamp volume -> page units, at full dusk
  giLampDay: 0.12,        // fraction of that by day (lamps on, dimmed)
  giWhiteBalance: [1.0, 1.0, 0.97],
  insideExposureDay: 5.5, // an interiors photographer opens up ~2.5 stops indoors
  insideExposureNight: 1.3,
  dustSun: 0.4,           // sunlit dust mote brightness, times sun intensity
  dustAmbient: 0.012,     // unlit motes
};
