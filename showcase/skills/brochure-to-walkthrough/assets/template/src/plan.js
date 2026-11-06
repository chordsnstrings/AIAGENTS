// Unit TH12-4M, plot XJ407B, Violet 2 - DAMAC Hills 2.
// Coordinates in metres: x across the 6.10 m plot (0 = left party line seen from the street),
// d = depth from the street plot line (0) to the rear boundary (18.50). World z = -d.
// Positions are measured off the developer floor plans (brochure p.27 / sales offer unit plan).

export const PLOT = { w: 6.1, d: 18.5, areaM2: 112.85 };

// Finished levels: ground plinth, GF floor, GF ceiling, FF floor, FF ceiling, roof floor, roof ceiling, roof top.
export const H = { G: 0.05, F0: 0.25, C0: 3.25, F1: 3.55, C1: 6.5, F2: 6.8, C2: 9.7, R2: 10.0 };

export const FACTS = {
  project: 'Violet 2',
  community: 'DAMAC Hills 2, Dubai',
  unit: 'VOT2/SD143/XJ407B',
  plot: 'XJ407B',
  type: 'TH12-4M',
  beds: 4,
  parking: 2,
  completion: 'Q4 2027 (anticipated)',
  areasSqft: { ground: 589.22, first: 632.92, roof: 296.12, outdoor: 834.0, total: 2352.26 },
};

export const ROOMS = [
  { f: 0, key: 'carport', name: 'Covered parking', x: [0.1, 6.0], d: [1.5, 5.75], size: '2 cars' },
  { f: 0, key: 'kitchen', name: 'Kitchen', x: [3.3, 6.0], d: [6.0, 8.95], size: '2.65 × 3.10 m' },
  { f: 0, key: 'study', name: 'Study & stair hall', x: [0.1, 3.25], d: [6.75, 9.5], size: '3.15 × 2.75 m' },
  { f: 0, key: 'powder', name: 'Powder room', x: [3.3, 4.85], d: [9.05, 10.55] },
  { f: 0, key: 'laundry', name: 'Laundry', x: [4.95, 6.0], d: [9.05, 10.55] },
  { f: 0, key: 'living', name: 'Living & dining', x: [0.1, 6.0], d: [10.6, 14.8], size: '5.90 × 4.20 m' },
  { f: 0, key: 'patio', name: 'Patio', x: [0.1, 6.0], d: [15.0, 16.45] },
  { f: 0, key: 'garden', name: 'Private garden', x: [0.1, 6.0], d: [16.45, 18.4] },
  { f: 1, key: 'balF', name: 'Front balcony', x: [0.1, 6.0], d: [1.5, 3.4], size: '6.00 × 1.60 m' },
  { f: 1, key: 'master', name: 'Master bedroom', x: [2.45, 6.0], d: [3.55, 6.6], size: '3.40 × 3.00 m' },
  { f: 1, key: 'masterBath', name: 'Master bathroom', x: [0.1, 2.35], d: [5.0, 6.6], size: '2.45 × 1.60 m' },
  { f: 1, key: 'wic', name: 'Walk-in wardrobe', x: [4.3, 6.0], d: [6.7, 7.7] },
  { f: 1, key: 'bath2', name: 'Family bathroom', x: [4.3, 6.0], d: [7.8, 10.0], size: '1.60 × 2.15 m' },
  { f: 1, key: 'bed3', name: 'Bedroom 3', x: [0.1, 2.95], d: [9.55, 13.29], size: '2.90 × 3.00 m' },
  { f: 1, key: 'bed2', name: 'Bedroom 2', x: [3.05, 6.0], d: [10.7, 14.11], size: '2.90 × 3.15 m' },
  { f: 1, key: 'balR', name: 'Rear balcony', x: [0.1, 6.0], d: [13.45, 15.28], size: '6.00 × 1.60 m' },
  { f: 2, key: 'roofFront', name: 'Roof', x: [0.1, 6.0], d: [3.6, 6.6] },
  { f: 2, key: 'bed4', name: 'Bedroom 4', x: [2.25, 6.0], d: [7.95, 11.05], size: '3.65 × 3.15 m' },
  { f: 2, key: 'bath4', name: 'Bathroom', x: [0.1, 2.15], d: [9.6, 11.05], size: '2.00 × 1.50 m' },
  { f: 2, key: 'terrace', name: 'Roof terrace', x: [0.1, 6.0], d: [11.2, 14.1], size: '5.95 × 2.50 m' },
];

// Stair core shared by all floors (stacked dog-leg stair).
export const STAIR = { x: [0.1, 2.95], d: [6.65, 9.45] };
