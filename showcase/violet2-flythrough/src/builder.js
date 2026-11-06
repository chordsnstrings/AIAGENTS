import * as THREE from 'three';

// Geometry is accumulated as raw arrays per material key and turned into one BufferGeometry
// per key at the end: thousands of small boxes become a handful of draw calls.

const FACES = [
  [[1, 0, 0], [0, 0, -1], [0, 1, 0]],
  [[-1, 0, 0], [0, 0, 1], [0, 1, 0]],
  [[0, 1, 0], [1, 0, 0], [0, 0, -1]],
  [[0, -1, 0], [1, 0, 0], [0, 0, 1]],
  [[0, 0, 1], [1, 0, 0], [0, 1, 0]],
  [[0, 0, -1], [-1, 0, 0], [0, 1, 0]],
];
const CORNERS = [[-1, -1], [1, -1], [1, 1], [-1, 1]];
export const F = { PX: 1, NX: 2, PY: 4, NY: 8, PZ: 16, NZ: 32, ALL: 63 };

const _v = new THREE.Vector3();
const _n = new THREE.Vector3();
const _nm = new THREE.Matrix3();

class Bucket {
  constructor() { this.p = []; this.n = []; this.u = []; this.i = []; }
  get count() { return this.p.length / 3; }
}

export class Builder {
  constructor() { this.b = new Map(); }

  bucket(k) {
    let b = this.b.get(k);
    if (!b) this.b.set(k, (b = new Bucket()));
    return b;
  }

  // Axis-aligned box between two corners. UVs are metres along each face's own axes, so a
  // wall cut into pieces around an opening keeps one continuous texture.
  box(k, x0, x1, y0, y1, z0, z1, faces = F.ALL) {
    if (x1 < x0) [x0, x1] = [x1, x0];
    if (y1 < y0) [y0, y1] = [y1, y0];
    if (z1 < z0) [z0, z1] = [z1, z0];
    if (x1 - x0 < 1e-4 || y1 - y0 < 1e-4 || z1 - z0 < 1e-4) return;
    const b = this.bucket(k);
    const c = [(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2];
    const h = [(x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2];
    for (let fi = 0; fi < 6; fi++) {
      if (!(faces & (1 << fi))) continue;
      const [n, u, v] = FACES[fi];
      const base = b.count;
      for (const [a, s] of CORNERS) {
        const px = c[0] + (n[0] + u[0] * a + v[0] * s) * h[0];
        const py = c[1] + (n[1] + u[1] * a + v[1] * s) * h[1];
        const pz = c[2] + (n[2] + u[2] * a + v[2] * s) * h[2];
        b.p.push(px, py, pz);
        b.n.push(n[0], n[1], n[2]);
        b.u.push(px * u[0] + py * u[1] + pz * u[2], px * v[0] + py * v[1] + pz * v[2]);
      }
      b.i.push(base, base + 1, base + 2, base, base + 2, base + 3);
    }
  }

  // Append any geometry. uv: 'keep' | 'box' (re-project in local metres by dominant normal).
  add(k, geo, matrix = null, uv = 'keep', uvScale = 1) {
    const b = this.bucket(k);
    const base = b.count;
    const pa = geo.attributes.position, na = geo.attributes.normal, ua = geo.attributes.uv;
    if (matrix) _nm.getNormalMatrix(matrix);
    for (let i = 0; i < pa.count; i++) {
      _v.fromBufferAttribute(pa, i);
      _n.fromBufferAttribute(na, i);
      if (uv === 'box') {
        const ax = Math.abs(_n.x), ay = Math.abs(_n.y), az = Math.abs(_n.z);
        if (ax >= ay && ax >= az) b.u.push(_v.z * uvScale, _v.y * uvScale);
        else if (ay >= az) b.u.push(_v.x * uvScale, _v.z * uvScale);
        else b.u.push(_v.x * uvScale, _v.y * uvScale);
      } else if (ua) b.u.push(ua.getX(i) * uvScale, ua.getY(i) * uvScale);
      else b.u.push(0, 0);
      if (matrix) { _v.applyMatrix4(matrix); _n.applyMatrix3(_nm).normalize(); }
      b.p.push(_v.x, _v.y, _v.z);
      b.n.push(_n.x, _n.y, _n.z);
    }
    const flip = matrix && matrix.determinant() < 0;
    const idx = geo.index;
    const count = idx ? idx.count : pa.count;
    for (let i = 0; i < count; i += 3) {
      const a = idx ? idx.getX(i) : i, c1 = idx ? idx.getX(i + 1) : i + 1, c2 = idx ? idx.getX(i + 2) : i + 2;
      if (flip) b.i.push(base + a, base + c2, base + c1);
      else b.i.push(base + a, base + c1, base + c2);
    }
  }

  // Quad p0..p3 counter-clockwise as seen from its front.
  quad(k, p0, p1, p2, p3, uv = [[0, 0], [1, 0], [1, 1], [0, 1]]) {
    const b = this.bucket(k), base = b.count;
    const e1 = [p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]], e2 = [p3[0] - p0[0], p3[1] - p0[1], p3[2] - p0[2]];
    const n = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]];
    const l = Math.hypot(...n) || 1;
    [p0, p1, p2, p3].forEach((p, i) => { b.p.push(...p); b.n.push(n[0] / l, n[1] / l, n[2] / l); b.u.push(...uv[i]); });
    b.i.push(base, base + 1, base + 2, base, base + 2, base + 3);
  }

  geometries() {
    const out = new Map();
    for (const [k, b] of this.b) {
      if (!b.i.length) continue;
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.Float32BufferAttribute(b.p, 3));
      g.setAttribute('normal', new THREE.Float32BufferAttribute(b.n, 3));
      g.setAttribute('uv', new THREE.Float32BufferAttribute(b.u, 2));
      g.setIndex(b.count > 65535 ? new THREE.Uint32BufferAttribute(b.i, 1) : new THREE.Uint16BufferAttribute(b.i, 1));
      g.computeBoundingSphere();
      out.set(k, g);
    }
    return out;
  }
}

// Mirror about the plane x = cx, keeping triangles front-facing.
export function mirrorX(geo, cx) {
  const g = geo.clone();
  const p = g.attributes.position, n = g.attributes.normal;
  for (let i = 0; i < p.count; i++) { p.setX(i, 2 * cx - p.getX(i)); n.setX(i, -n.getX(i)); }
  const idx = g.index.array;
  for (let i = 0; i < idx.length; i += 3) { const t = idx[i + 1]; idx[i + 1] = idx[i + 2]; idx[i + 2] = t; }
  g.computeBoundingSphere();
  return g;
}

export function meshes(geos, mats, { cast = true, receive = true } = {}) {
  const group = new THREE.Group();
  for (const [k, g] of geos) {
    const m = mats[k];
    if (!m) { console.warn('missing material', k); continue; }
    const mesh = new THREE.Mesh(g, m);
    mesh.name = k;
    mesh.castShadow = cast && !m.userData.noShadow;
    mesh.receiveShadow = receive;
    mesh.matrixAutoUpdate = false;
    group.add(mesh);
  }
  return group;
}

export function instanced(geos, mats, matrices, { cast = true, receive = true } = {}) {
  const group = new THREE.Group();
  if (!matrices.length) return group;
  for (const [k, g] of geos) {
    const m = mats[k];
    if (!m) { console.warn('missing material', k); continue; }
    const im = new THREE.InstancedMesh(g, m, matrices.length);
    matrices.forEach((mx, i) => im.setMatrixAt(i, mx));
    im.instanceMatrix.needsUpdate = true;
    im.computeBoundingSphere();
    im.castShadow = cast && !m.userData.noShadow;
    im.receiveShadow = receive;
    im.matrixAutoUpdate = false;
    im.name = k;
    group.add(im);
  }
  return group;
}
