// The numbers that set the photographic look, kept apart from the engine so they can be
// tuned (and re-tuned per property) without touching the update loop. Units are page units:
// irradiance as the baked volume stores it, exposure as a factor on the atmosphere's.
export const LOOK = {
  giFill: 2.2,            // fill on baked daylight, for the bounces past the two the bake traces (the brighter albedos bounce more themselves)
  giLamp: 0.22,           // baked lamp volume -> page units, at full dusk (the volume bounces off the brighter albedos now)
  giLampDay: 0.12,        // fraction of that by day (lamps on, dimmed)
  giWhiteBalance: [1.0, 1.0, 0.97],
  insideExposureDay: 4.2, // an interiors photographer opens up ~2 stops indoors (white bedding needs the headroom)
  insideExposureNight: 1.0, // lamp-lit rooms stay darker than day: pools near lamps, not an even wash
  // looking in through glazing from within 7 m, the inside weight the exposure blends towards:
  // about one stop, so the room opens up while the facade around the window only runs warm
  lookInExposure: 0.35,
  // the pool of night point lights fed from the recorded bulb positions: how many, how far they
  // reach (m) and their intensity at full dusk (candela-like, against the baked lamp volume)
  lampPool: 3,
  lampReach: 2.5,
  lampIntensity: 1.2,
  // bloom: the threshold rides with exposure so lamps halo at night while sunlit render by day does not
  bloomThresholdK: 2.5,   // threshold = bloomThresholdK / exposure
  bloomStrength: 0.15,
  dustSun: 0.4,           // sunlit dust mote brightness, times sun intensity
  dustAmbient: 0.012,     // unlit motes
};
