// The numbers that set the photographic look, kept apart from the engine so they can be
// tuned (and re-tuned per property) without touching the update loop. Units are page units:
// irradiance as the baked volume stores it, exposure as a factor on the atmosphere's.
export const LOOK = {
  giFill: 3.4,            // fill on baked daylight, past the two bounces the bake traces: white bedding at 0.85 of the range, walls light, the windows and sun patches untouched
  giLamp: 0.22,           // baked lamp volume -> page units, at full dusk (the volume bounces off the brighter albedos now)
  giLampDay: 0.12,        // fraction of that by day (lamps on, dimmed)
  giWhiteBalance: [1.0, 1.0, 0.97],   // on the baked sky light
  giSunBalance: [0.92, 1.0, 1.12],    // on the baked sun bounce: a golden-hour bounce left as it is turns white walls tan
  insideExposureDay: 4.2, // an interiors photographer opens up ~2 stops indoors; more clips the sheers and the sun patches
  insideExposureNight: 0.9, // lamp-lit rooms stay darker than day: pools near lamps, not an even wash
  // looking in through glazing from within 7 m, the inside weight the exposure blends towards:
  // about one stop, so the room opens up while the facade around the window only runs warm
  lookInExposure: 0.35,
  // looking out through glazing from inside, how far the exposure goes back towards the exterior's
  // (1 would expose for the garden and drop the room into silhouette)
  lookOutExposure: 0.6,
  // behind the house the rear elevation is in the sun's shade: the exposure lift there
  gardenShadeExposure: 2.5,
  // the street lamps' baked ground pools (community.js lampMap), in page units at full dusk
  streetLamp: 1.2,
  // the pool of night point lights fed from the recorded bulb positions: how many, how far they
  // reach (m) and their intensity at full dusk (candela-like, against the baked lamp volume)
  lampPool: 3,
  lampReach: 2.5,
  lampIntensity: 1.2,
  // bloom: the threshold rides with exposure so lamps halo at night while sunlit render by day does not
  bloomThresholdK: 2.5,   // threshold = bloomThresholdK / exposure
  bloomStrength: 0.15,
  dustSun: 0.05,          // sunlit dust mote brightness, times sun intensity (the motes are small and energy-conserving; more clips them white)
  dustAmbient: 0,         // unlit motes vanish; 0.003 for a hint of them in shadow
};
