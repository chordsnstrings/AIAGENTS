import * as THREE from 'three';

// Scroll progress -> camera. Positions and look targets are centripetal Catmull-Rom splines
// through hand-placed keyframes (world = plan coordinates of the hero unit, z = -d); a
// monotone cubic maps progress to spline parameter so speed changes stay smooth.

const K = [
  [0.000, [140, 60, 110], [-60, -8, -70], 50],
  [0.065, [100, 47, 78], [-40, -2, -48], 50],
  [0.125, [62, 38, 46], [-4, 3, -10], 52],
  [0.185, [28, 21, 18], [2.5, 4, -6], 52],
  [0.228, [13, 14, 10.5], [3.0, 4.5, -5], 52],
  [0.268, [-5, 6.5, 10.2], [3.3, 4.5, -5], 54],
  [0.305, [1.2, 2.6, 10.4], [3.0, 3.9, -5], 54],
  [0.340, [3.0, 1.65, 5.5], [2.6, 1.6, -6], 58],
  [0.372, [2.55, 1.6, -3.6], [2.55, 1.55, -9], 60],
  [0.398, [2.55, 1.6, -7.3], [2.7, 1.5, -12], 62],
  [0.420, [2.65, 1.62, -9.7], [3.4, 1.35, -14], 62],
  [0.445, [2.9, 1.75, -11.2], [1.2, 0.95, -13.8], 62],
  [0.472, [3.9, 1.75, -12.2], [5.3, 1.05, -10.9], 62],
  [0.500, [3.8, 1.65, -14.1], [3.8, 1.5, -19], 60],
  [0.522, [3.6, 2.2, -16.2], [3.5, 3.0, -21.5], 58],
  [0.540, [3.4, 3.2, -17.1], [7.5, 3.6, -15.8], 58],
  [0.558, [3.1, 3.9, -17.3], [3.2, 4.5, -12.0], 58],
  [0.578, [3.9, 5.2, -16.4], [3.9, 4.95, -12.0], 58],
  [0.598, [3.9, 5.15, -14.6], [3.9, 4.9, -10.5], 60],
  [0.618, [3.75, 5.15, -12.5], [5.4, 4.2, -12.8], 62],
  [0.638, [3.6, 5.12, -11.2], [3.6, 5.0, -8.0], 62],
  [0.655, [3.55, 5.1, -9.3], [3.7, 5.0, -5.5], 62],
  [0.674, [3.72, 5.1, -6.9], [4.4, 4.6, -3.6], 62],
  [0.696, [3.9, 5.05, -5.0], [5.4, 4.2, -5.3], 62],
  [0.718, [4.2, 5.0, -3.9], [4.0, 4.9, 2.0], 60],
  [0.738, [4.1, 5.2, -2.2], [3.5, 5.6, 8], 58],
  [0.758, [3.4, 6.0, 2.2], [3.2, 8.5, -6], 56],
  [0.782, [3.2, 10.8, -1.0], [3.0, 9.5, -9.0], 56],
  [0.805, [3.0, 11.8, -8.5], [3.0, 7.5, -13.5], 56],
  [0.825, [3.4, 11.3, -13.9], [3.8, 8.2, -9.5], 56],
  [0.845, [3.9, 8.75, -13.4], [4.3, 8.1, -8.5], 58],
  [0.866, [4.3, 8.7, -12.9], [0.8, 7.5, -12.0], 58],
  [0.888, [3.8, 8.75, -13.1], [-18, 9.6, -32], 56],
  [0.902, [4.8, 12.4, -14.5], [-16, 9.0, -32], 56],
  [0.930, [9.0, 15.5, -6.0], [-14, 8.0, -30], 54],
  [0.964, [38, 36, 22], [-20, 3, -40], 50],
  [1.000, [80, 64, 70], [-70, 0, -120], 48],
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

export class DronePath {
  constructor() {
    this.pos = new THREE.CatmullRomCurve3(K.map((k) => new THREE.Vector3(...k[1])), false, 'centripetal');
    this.look = new THREE.CatmullRomCurve3(K.map((k) => new THREE.Vector3(...k[2])), false, 'centripetal');
    const ps = K.map((k) => k[0]);
    this.u = monotone(ps, K.map((_, i) => i / (K.length - 1)));
    this.fov = monotone(ps, K.map((k) => k[3]));
    this.keys = ps;
  }
  sample(p, outPos, outLook) {
    const u = THREE.MathUtils.clamp(this.u(p), 0, 1);
    this.pos.getPoint(u, outPos);
    this.look.getPoint(u, outLook);
    return this.fov(p);
  }
}

// Gimbal feel: slight lag on orientation, tiny bank into turns, and a low-frequency hover.
export class DroneRig {
  constructor(camera) {
    this.camera = camera;
    this.q = new THREE.Quaternion();
    this.roll = 0;
    this.prevYaw = null;
    this.m = new THREE.Matrix4();
    this.up = new THREE.Vector3(0, 1, 0);
    this.init = false;
  }
  update(pos, look, fov, dt, time, { hover = 1, still = false } = {}) {
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
    if (this.prevYaw !== null && dt > 0 && !still) {
      let dy = yaw - this.prevYaw;
      dy = Math.atan2(Math.sin(dy), Math.cos(dy));
      const rollTarget = THREE.MathUtils.clamp(-dy / dt * 0.05, -0.045, 0.045);
      this.roll += (rollTarget - this.roll) * (1 - Math.exp(-dt * 3));
    }
    this.prevYaw = yaw;
    target.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), still ? 0 : this.roll));
    if (!this.init || still) { this.q.copy(target); this.init = true; }
    else this.q.slerp(target, 1 - Math.exp(-dt * 9));
    cam.quaternion.copy(this.q);
    let f = fov;
    if (cam.aspect < 1.25) f = Math.min(82, THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(fov) / 2) * Math.sqrt(1.25 / cam.aspect))));
    if (Math.abs(cam.fov - f) > 1e-3) { cam.fov = f; cam.updateProjectionMatrix(); }
  }
}
