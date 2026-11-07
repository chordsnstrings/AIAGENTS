import * as THREE from 'three';

// Procedural plants built once and instanced everywhere. Crown height of the palm is fixed at
// 7 m in local space; the frond sway shader is anchored there.

function rng(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }

// The default is the full model (1.1k tris). The far model keeps every other frond of the same
// phyllotaxis, unfolded and shorter, on a coarser trunk: about 190 tris with the same silhouette,
// so the swap at the LOD distance reads as detail arriving rather than a different tree.
export function palmGeometry({ radial = 10, rings = 22, segs = 7, every = 1, flat = false } = {}) {
  const r = rng(5);
  const H = 7.0;
  // trunk: gently curved, tapered, with leaf-scar rings
  const pos = [], nor = [], uv = [], idx = [];
  for (let j = 0; j <= rings; j++) {
    const t = j / rings, y = t * H;
    const bend = Math.sin(t * Math.PI * 0.5) * 0.35;
    const rad = (0.24 - 0.07 * t) * (1 + 0.06 * Math.sin(y * Math.PI * 2 / 0.32)) + (t > 0.93 ? (t - 0.93) * 2.4 : 0);
    for (let i = 0; i <= radial; i++) {
      const a = i / radial * Math.PI * 2;
      const cx = Math.cos(a), cz = Math.sin(a);
      pos.push(bend + cx * rad, y, cz * rad);
      nor.push(cx, 0.08, cz);
      uv.push(i / radial * 1.4, y);
    }
  }
  for (let j = 0; j < rings; j++) for (let i = 0; i < radial; i++) {
    const a = j * (radial + 1) + i, b = a + radial + 1;
    idx.push(a, b, a + 1, b, b + 1, a + 1);
  }
  const trunk = new THREE.BufferGeometry();
  trunk.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  trunk.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
  trunk.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  trunk.setIndex(idx);

  // fronds: V-folded strips along a drooping arc, spiral phyllotaxis
  const fp = [], fn = [], fu = [], fi = [];
  const top = new THREE.Vector3(0.35, H, 0);
  const up = new THREE.Vector3(0, 1, 0);
  const n = 24, fold = 0.42, perRow = flat ? 2 : 3;
  let built = 0;
  for (let k = 0; k < n; k++) {
    // the random draws run for every frond so the kept ones match the full model's
    const az = k * 2.39996 + r() * 0.2;
    const tier = k / n;
    const elev = THREE.MathUtils.lerp(1.0, -0.35, tier) + (r() - 0.5) * 0.15;
    const L = 2.6 + r() * 0.9 - tier * 0.3, W = 1.05;
    if (k % every) continue;
    const dirH = new THREE.Vector3(Math.cos(az), 0, Math.sin(az));
    const droop = 0.55 + tier * 0.5;
    const pts = [];
    for (let s = 0; s <= segs; s++) {
      const t = s / segs;
      const p = top.clone()
        .addScaledVector(dirH, t * L * Math.cos(elev) + 0.12)
        .addScaledVector(up, t * L * Math.sin(elev) - droop * t * t * L * 0.6);
      pts.push(p);
    }
    for (let s = 0; s <= segs; s++) {
      const t = s / segs;
      const p = pts[s];
      const T = (s < segs ? pts[s + 1].clone().sub(p) : p.clone().sub(pts[s - 1])).normalize();
      const S = new THREE.Vector3().crossVectors(T, up).normalize();
      const N = new THREE.Vector3().crossVectors(S, T).normalize();
      const w = W * (0.25 + 0.75 * Math.sin(Math.PI * Math.min(1, 0.15 + t * 0.95))) * 0.5;
      const lift = flat ? 0 : w * Math.sin(fold);
      const L0 = p.clone().addScaledVector(S, -w * Math.cos(fold)).addScaledVector(N, lift);
      const R0 = p.clone().addScaledVector(S, w * Math.cos(fold)).addScaledVector(N, lift);
      for (const [q, u] of flat ? [[L0, 0], [R0, 1]] : [[L0, 0], [p, 0.5], [R0, 1]]) {
        fp.push(q.x, q.y, q.z); fn.push(N.x, N.y, N.z); fu.push(u, t);
      }
    }
    const base = built * (segs + 1) * perRow;
    built++;
    for (let s = 0; s < segs; s++) {
      const a = base + s * perRow, b = a + perRow;
      if (flat) fi.push(a, b, a + 1, b, b + 1, a + 1);
      else fi.push(a, b, a + 1, b, b + 1, a + 1, a + 1, b + 1, a + 2, b + 1, b + 2, a + 2);
    }
  }
  const fronds = new THREE.BufferGeometry();
  fronds.setAttribute('position', new THREE.Float32BufferAttribute(fp, 3));
  fronds.setAttribute('normal', new THREE.Float32BufferAttribute(fn, 3));
  fronds.setAttribute('uv', new THREE.Float32BufferAttribute(fu, 2));
  fronds.setIndex(fi);
  return { trunk, fronds };
}

// Shrub / canopy: randomly oriented leaf cards inside a unit sphere with soft spherical normals.
export function bushGeometry(cards = 14, seed = 2, flat = 0.75) {
  const r = rng(seed);
  const p = [], n = [], u = [], idx = [];
  const tmp = new THREE.Vector3(), q = new THREE.Quaternion(), e = new THREE.Euler();
  for (let c = 0; c < cards; c++) {
    const center = new THREE.Vector3((r() - 0.5) * 0.7, (r() - 0.35) * 0.55 * flat, (r() - 0.5) * 0.7);
    q.setFromEuler(e.set((r() - 0.5) * 1.2, r() * Math.PI, (r() - 0.5) * 1.2));
    const s = 0.55 + r() * 0.35;
    const base = p.length / 3;
    for (const [a, b] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) {
      tmp.set(a * s * 0.5, b * s * 0.5, 0).applyQuaternion(q).add(center);
      p.push(tmp.x, tmp.y + 0.45 * flat, tmp.z);
      const nn = tmp.clone().normalize();
      n.push(nn.x, nn.y * 0.7 + 0.3, nn.z);
      u.push((a + 1) / 2, (b + 1) / 2);
    }
    idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(p, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(n, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(u, 2));
  g.setIndex(idx);
  return g;
}

export function instancedFrom(geo, mat, matrices, { cast = true, receive = true } = {}) {
  const im = new THREE.InstancedMesh(geo, mat, Math.max(1, matrices.length));
  im.count = matrices.length;
  matrices.forEach((m, i) => im.setMatrixAt(i, m));
  im.instanceMatrix.needsUpdate = true;
  im.computeBoundingSphere();
  im.castShadow = cast; im.receiveShadow = receive;
  im.matrixAutoUpdate = false;
  return im;
}
