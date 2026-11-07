import * as THREE from 'three';

// Scroll progress -> camera. Positions run on a centripetal Catmull-Rom spline through
// hand-placed keyframes (world = plan coordinates of the hero unit, z = -d); a monotone cubic
// maps progress to spline parameter so speed changes stay smooth and a repeated key holds.
//
// Orientation is NOT a spline through look points. A look point interpolated as a point can
// pass right beside the lens between two keys and flip the view (167 deg of yaw in one wheel
// notch, pitch -80: pitfall 19). Each key's look target is converted to yaw and pitch at build
// time, yaw is unwrapped across keys, and both are interpolated with the same monotone cubic, so
// the view between two keys is always between the two views. Look targets are still authored
// as points because that is how a shot is composed; scripts/check-path.mjs holds the limits
// (yaw and pitch rate, look distance, pitch range, clearance) rather than a runtime clamp,
// which would make the view depend on scroll history and break ?p= stills and rail jumps.
//
// Key: [progress, [x, y, z], [lookX, lookY, lookZ], fov, lensShift?]. The optional lens shift
// is a vertical view offset in fractions of frame height (|s| <= 0.5): positive lowers the frame
// (more floor, the horizon rises), negative raises it. It is how an interior stays level, with
// straight verticals, while the bed is framed low, as a tilt-shift lens would.

export const KEYS = [
  // aerial approach: the house stays centred from the first frame. The opener sits about 110 m
  // out, near enough that the hero row reads through the haze as houses rather than a field of
  // blocks, with the lagoon still in the top of the frame
  [0.000, [80, 40, 64], [3, 5, -9], 50],
  [0.040, [72, 37, 57], [3, 5, -9], 50],
  [0.090, [56, 33, 42], [3, 4.5, -9], 52],
  [0.130, [30, 22, 20], [3, 4.5, -8], 52],
  // facade: orbit down to the street
  [0.150, [13, 14, 10.5], [3.0, 4.5, -5], 52],
  [0.185, [-5, 6.5, 10.2], [3.3, 4.5, -5], 54],
  [0.208, [1.2, 2.6, 10.4], [3.0, 3.9, -5], 54],
  [0.225, [3.0, 1.65, 5.5], [2.6, 1.6, -6], 58],
  // carport and front door into the hall
  // carport and front door into the hall, the eye already drifting right to the kitchen window
  [0.240, [2.55, 1.65, -3.6], [3.6, 1.5, -9.5], 60],
  [0.252, [2.58, 1.62, -6.85], [4.1, 1.45, -10.55], 62],
  // a glance right through the kitchen opening (x 3.15-3.3, d 7.05-8.25) along the run, then on down the hall
  [0.272, [2.7, 1.6, -7.05], [5.0, 1.35, -9.0], 62],
  [0.290, [2.75, 1.6, -7.15], [5.45, 1.3, -8.25], 62],
  [0.297, [2.75, 1.6, -7.2], [5.45, 1.3, -8.3], 62],
  [0.318, [2.7, 1.6, -7.9], [4.4, 1.4, -10.35], 62],
  [0.340, [2.62, 1.6, -9.5], [2.8, 1.45, -14.5], 62],
  // living and dining: an arc along the left wall looking at the sofa, table and glazing...
  [0.370, [1.3, 1.5, -11.3], [4.2, 1.0, -13.6], 62],
  [0.392, [0.8, 1.5, -12.2], [4.6, 1.0, -13.6], 62],
  // ...then towards the glazing, turning to look back into the room
  [0.418, [1.6, 1.55, -13.3], [4.7, 1.1, -11.9], 62],
  [0.440, [3.0, 1.6, -14.3], [4.6, 1.2, -11.5], 60],
  [0.456, [3.8, 1.65, -14.95], [3.9, 1.3, -11.0], 58],
  // garden: a reverse pull-out through the open panel, rising to look back over the rear wall
  [0.470, [3.8, 2.4, -16.6], [3.5, 1.9, -11.5], 56, 0.1],
  [0.486, [3.4, 4.5, -19.5], [3.3, 3.1, -14.6], 52, 0.28],
  [0.496, [3.4, 4.5, -19.5], [3.3, 3.1, -14.6], 52, 0.28],
  // up to the rear balcony and in through the open panel (x 3.3-4.5), the view already
  // drifting towards the bed so the turn inside stays within the rate limit
  [0.510, [3.85, 4.8, -17.2], [4.6, 4.2, -12.7], 56, 0.2],
  [0.522, [4.15, 5.05, -15.3], [5.9, 4.7, -11.9], 58, 0.16],
  [0.534, [4.1, 4.9, -14.4], [6.2, 4.6, -12.1], 60, 0.14],
  // bedroom 2: a level hold just inside the glazing, the sheers at the shoulder. Looking
  // towards the street puts east on the left, so the view turns to the headboard until it
  // sits centre-right, clear of the card: bed, prints, lamps, the wardrobe wall by the door
  [0.548, [4.15, 4.85, -14.0], [6.35, 4.5, -12.15], 62, 0.12],
  [0.578, [4.15, 4.85, -14.0], [6.35, 4.5, -12.15], 62, 0.12],
  // out of the door and along the corridor
  [0.600, [3.65, 4.9, -10.65], [4.65, 4.7, -7.0], 62, 0.06],
  [0.608, [3.7, 4.9, -8.9], [3.85, 4.65, -5.0], 62, 0.05],
  [0.616, [3.75, 4.9, -7.6], [3.95, 4.6, -3.6], 62, 0.05],
  // master: through the door, then a 3/4 view from the foot of the bed, the front glazing,
  // sheers and lattice as the key light on the right. The two open leaves (master door at
  // x 3.3-3.4, bath door off the west wall) box the room's back corner, so the lens stays
  // east of them
  [0.620, [3.78, 4.88, -6.55], [4.2, 4.5, -3.8], 60, 0.08],
  [0.644, [3.75, 4.9, -6.1], [5.9, 4.45, -3.9], 56, 0.1],
  [0.660, [3.75, 4.9, -6.1], [5.9, 4.45, -3.9], 56, 0.1],
  // front balcony: out through the open panel to a hold at the balustrade, the frame lowered
  // onto the two loungers with the lattice at the left and the street beyond; then a reverse
  // dolly back through the room
  [0.672, [3.95, 4.9, -4.8], [6.0, 4.6, -1.0], 58, 0.15],
  [0.684, [4.22, 4.9, -3.3], [5.7, 4.25, 1.2], 58, 0.3],
  [0.700, [4.22, 4.9, -3.3], [5.7, 4.25, 1.2], 58, 0.3],
  [0.712, [4.05, 4.9, -5.2], [5.5, 4.9, -0.4], 58],
  [0.720, [3.75, 4.9, -6.9], [5.2, 4.9, -1.8], 58],
  // the stair: back into the well (x 0.95-2.95, d 7.5-8.6) and up over the half landing to a
  // hold that reads the dog-leg: the upper flight and its rail climbing to the roof landing and
  // its window, the first-floor hall below. The lens keeps to the rear of the well, half a metre
  // clear of the front flight's rail, then rises to the roof landing short of the bedroom wall
  [0.730, [3.5, 5.0, -7.7], [5.5, 5.0, -3.0], 60],
  [0.744, [2.45, 5.75, -8.05], [4.6, 5.45, -6.4], 60],
  [0.756, [1.2, 7.3, -8.18], [4.4, 6.2, -7.2], 62],
  [0.767, [1.1, 7.5, -8.2], [4.4, 6.2, -7.2], 62],
  [0.781, [2.85, 8.3, -7.3], [5.9, 7.7, -7.6], 60],
  [0.812, [3.2, 8.3, -7.1], [5.3, 7.9, -10.6], 58],
  [0.822, [3.72, 8.2, -8.05], [5.3, 7.9, -11.0], 58, 0.08],
  [0.834, [4.0, 8.2, -8.4], [5.3, 7.9, -11.0], 58, 0.1],
  [0.862, [4.0, 8.2, -8.4], [5.3, 7.9, -11.0], 58, 0.1],
  // out through the terrace glazing (open panel x 4.3-5.65) before the terrace card arrives,
  // since the sunlit terrace seen from inside is exposed for the room, then round to the sunset
  [0.876, [4.5, 8.2, -10.0], [4.6, 7.9, -14.0], 58, 0.05],
  [0.886, [4.75, 8.3, -11.4], [4.2, 8.1, -15.3], 56],
  // the hold sits at eye height with the frame lowered, so the sofa, loungers and fire bowl
  // share the picture with the pergola and the sun going down over the neighbours
  [0.908, [5.1, 8.5, -11.7], [-2.5, 8.2, -20.5], 54, 0.1],
  [0.928, [5.2, 8.5, -11.6], [-16, 7.6, -29], 54, 0.18],
  [0.950, [5.2, 8.5, -11.6], [-16, 7.6, -29], 54, 0.18],
  // ending: rise and pull back to the right, the lit rear elevation off-centre at blue hour
  [0.961, [5.4, 9.1, -13.4], [-3.85, 8.6, -17.2], 54],
  [0.972, [6.6, 10.8, -14.6], [-3.3, 9.3, -15.9], 52],
  [0.983, [9.5, 11.6, -16.5], [-0.4, 8.6, -15.3], 50],
  [0.992, [13, 12.3, -18.5], [3.5, 7.6, -15.3], 48],
  [1.000, [16, 12.5, -19.5], [-0.5, 5.5, -10.5], 48],
];

function monotone(xs, ys) {
  const n = xs.length, d = new Array(n - 1), m = new Array(n);
  for (let i = 0; i < n - 1; i++) d[i] = (ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]);
  m[0] = d[0]; m[n - 1] = d[n - 2];
  for (let i = 1; i < n - 1; i++) m[i] = d[i - 1] * d[i] <= 0 ? 0 : (d[i - 1] + d[i]) / 2;
  for (let i = 0; i < n - 1; i++) {
    if (d[i] === 0) { m[i] = m[i + 1] = 0; continue; }
    const a = m[i] / d[i], b = m[i + 1] / d[i], s = a * a + b * b;
    if (s > 9) { const t = 3 / Math.sqrt(s); m[i] = t * a * d[i]; m[i + 1] = t * b * d[i]; }
  }
  return (x) => {
    if (x <= xs[0]) return ys[0];
    if (x >= xs[n - 1]) return ys[n - 1];
    let i = 0;
    while (x > xs[i + 1]) i++;
    const h = xs[i + 1] - xs[i], t = (x - xs[i]) / h, t2 = t * t, t3 = t2 * t;
    return (2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h * m[i] + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h * m[i + 1];
  };
}

const LOOK_DIST = 10; // m; the returned look point sits this far along the view direction
export const MAX_SHIFT = 0.5;

export class DronePath {
  constructor() {
    this.pos = new THREE.CatmullRomCurve3(KEYS.map((k) => new THREE.Vector3(...k[1])), false, 'centripetal');
    const ps = KEYS.map((k) => k[0]);
    const yaws = [], pitches = [];
    for (const [, p, l] of KEYS) {
      const dx = l[0] - p[0], dy = l[1] - p[1], dz = l[2] - p[2];
      let yaw = Math.atan2(dx, dz);
      const prev = yaws[yaws.length - 1];
      if (prev !== undefined) yaw += Math.round((prev - yaw) / (2 * Math.PI)) * 2 * Math.PI;
      yaws.push(yaw);
      pitches.push(Math.atan2(dy, Math.hypot(dx, dz)));
    }
    this.u = monotone(ps, KEYS.map((_, i) => i / (KEYS.length - 1)));
    this.yaw = monotone(ps, yaws);
    this.pitch = monotone(ps, pitches);
    this.fov = monotone(ps, KEYS.map((k) => k[3]));
    this.shiftAt = monotone(ps, KEYS.map((k) => k[4] || 0));
    this.keys = ps;
    this.shift = 0;
    this.fixed = null;
  }
  // A fixed pose for composing stills (?cam=x,y,z,lx,ly,lz[,fov[,shift]]); progress is ignored while set.
  override(pose) { this.fixed = pose; }
  sample(p, outPos, outLook) {
    if (this.fixed) {
      outPos.copy(this.fixed.pos);
      outLook.copy(this.fixed.look);
      this.shift = this.fixed.shift || 0;
      return this.fixed.fov || 56;
    }
    const u = THREE.MathUtils.clamp(this.u(p), 0, 1);
    this.pos.getPoint(u, outPos);
    const yaw = this.yaw(p), pitch = this.pitch(p), c = Math.cos(pitch);
    outLook.set(outPos.x + Math.sin(yaw) * c * LOOK_DIST, outPos.y + Math.sin(pitch) * LOOK_DIST, outPos.z + Math.cos(yaw) * c * LOOK_DIST);
    this.shift = this.shiftAt(p);
    return this.fov(p);
  }
}

// Gimbal feel: slight lag on orientation, tiny bank into turns, and a low-frequency hover.
// hover 0 is a locked gimbal (no hover, no bank), which is what reduced motion asks for.
export class DroneRig {
  constructor(camera) {
    this.camera = camera;
    this.q = new THREE.Quaternion();
    this.roll = 0;
    this.prevYaw = null;
    this.m = new THREE.Matrix4();
    this.up = new THREE.Vector3(0, 1, 0);
    this.init = false;
    this.shift = 0;
  }
  update(pos, look, fov, dt, time, { hover = 1, still = false, shift = 0 } = {}) {
    const cam = this.camera;
    const alt = Math.max(0, pos.y);
    const amp = still ? 0 : hover * (alt > 20 ? 0.35 : alt > 7 ? 0.08 : 0.012);
    const hx = Math.sin(time * 0.37) * 0.6 + Math.sin(time * 0.91 + 1.3) * 0.4;
    const hy = Math.sin(time * 0.53 + 0.7) * 0.6 + Math.sin(time * 1.17) * 0.4;
    const hz = Math.sin(time * 0.29 + 2.1) * 0.6 + Math.sin(time * 0.83 + 0.4) * 0.4;
    cam.position.set(pos.x + hx * amp, pos.y + hy * amp, pos.z + hz * amp);
    this.m.lookAt(cam.position, look, this.up);
    const target = new THREE.Quaternion().setFromRotationMatrix(this.m);
    const yaw = Math.atan2(look.x - pos.x, look.z - pos.z);
    if (this.prevYaw !== null && dt > 0 && !still && hover > 0) {
      let dy = yaw - this.prevYaw;
      dy = Math.atan2(Math.sin(dy), Math.cos(dy));
      const rollTarget = THREE.MathUtils.clamp(-dy / dt * 0.05, -0.045, 0.045);
      this.roll += (rollTarget - this.roll) * (1 - Math.exp(-dt * 3));
    } else this.roll = 0;
    this.prevYaw = yaw;
    target.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), still ? 0 : this.roll));
    if (!this.init || still) { this.q.copy(target); this.init = true; }
    else this.q.slerp(target, 1 - Math.exp(-dt * 9));
    cam.quaternion.copy(this.q);
    // portrait: widen the vertical field so the room is not a door slot, and lift the frame so
    // the subject sits above the card at the bottom of a phone screen
    let f = fov, s = THREE.MathUtils.clamp(shift, -MAX_SHIFT, MAX_SHIFT);
    const portrait = cam.aspect < 1;
    if (cam.aspect < 1.25) f = Math.min(portrait ? 88 : 82, THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(fov) / 2) * Math.sqrt(1.25 / cam.aspect))));
    if (portrait) s = s * 0.5 + 0.1;
    if (Math.abs(cam.fov - f) > 1e-3) { cam.fov = f; cam.updateProjectionMatrix(); }
    if (Math.abs(s - this.shift) > 1e-4) {
      this.shift = s;
      // setViewOffset takes the full frame in any unit; 1000 px tall keeps the aspect exact
      if (Math.abs(s) > 1e-4) cam.setViewOffset(1000 * cam.aspect, 1000, 0, s * 1000, 1000 * cam.aspect, 1000);
      else cam.clearViewOffset();
    }
  }
}
