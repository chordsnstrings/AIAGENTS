import * as THREE from 'three';

// Canvas-generated textures for things no photo-scan covers well (alpha foliage, lattice
// screens, artwork) or that must be cheap at distance (facade atlas for far houses).

function rng(seed) {
  let s = seed >>> 0;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
}

function canvas(w, h) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return [c, c.getContext('2d')];
}

function tex(c, { srgb = true, repeat = false, mips = true } = {}) {
  const t = new THREE.CanvasTexture(c);
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  if (repeat) t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.generateMipmaps = mips;
  t.anisotropy = 4;
  return t;
}

// Pinnate date-palm frond: base at v=0, tip at v=1, rachis down the centre.
export function frondTexture() {
  const [c, g] = canvas(256, 1024);
  const r = rng(7);
  const cx = 128;
  g.lineCap = 'round';
  for (let i = 0; i < 70; i++) {
    const t = i / 70;
    const y = 1000 - t * 980;
    const len = 118 * Math.sin(Math.PI * Math.min(1, t * 1.15 + 0.08)) * (0.85 + r() * 0.2);
    for (const side of [-1, 1]) {
      const ang = (0.95 + r() * 0.25) * side;
      const ex = cx + Math.sin(ang) * len, ey = y - Math.cos(Math.abs(ang)) * len * 0.75;
      const grad = g.createLinearGradient(cx, y, ex, ey);
      const shade = 0.8 + r() * 0.3;
      grad.addColorStop(0, `rgb(${38 * shade},${56 * shade},${26 * shade})`);
      grad.addColorStop(0.6, `rgb(${62 * shade},${84 * shade},${38 * shade})`);
      grad.addColorStop(1, `rgb(${104 * shade},${108 * shade},${58 * shade})`);
      g.strokeStyle = grad;
      g.lineWidth = 7 + r() * 4;
      g.beginPath();
      g.moveTo(cx + side * 3, y);
      g.quadraticCurveTo(cx + Math.sin(ang) * len * 0.5, y - len * 0.25, ex, ey);
      g.stroke();
    }
  }
  g.strokeStyle = '#6b6a3c';
  g.lineWidth = 9;
  g.beginPath(); g.moveTo(cx, 1024); g.lineTo(cx, 20); g.stroke();
  return tex(c);
}

// Leaf clusters on transparent ground; optional flowers (bougainvillea bracts etc.).
export function foliageTexture({ seed = 1, leaf = ['#3f5f2c', '#55763a', '#2f4a22', '#6c8a45'], flower = null, flowerRatio = 0.35, size = 512, narrow = false }) {
  const [c, g] = canvas(size, size);
  const r = rng(seed);
  const n = 900;
  for (let i = 0; i < n; i++) {
    const a = r() * Math.PI * 2, rad = Math.sqrt(r()) * size * 0.47;
    const x = size / 2 + Math.cos(a) * rad, y = size / 2 + Math.sin(a) * rad;
    const isFlower = flower && r() < flowerRatio * (1 - rad / size);
    const palette = isFlower ? flower : leaf;
    const col = palette[Math.floor(r() * palette.length)];
    const s = (isFlower ? 7 : narrow ? 10 : 9) * (0.6 + r() * 0.8) * size / 512;
    g.save();
    g.translate(x, y);
    g.rotate(r() * Math.PI * 2);
    g.fillStyle = col;
    g.globalAlpha = 0.95;
    g.beginPath();
    if (isFlower) {
      for (let k = 0; k < 3; k++) { g.rotate(Math.PI * 2 / 3); g.ellipse(s * 0.6, 0, s * 0.75, s * 0.5, 0, 0, Math.PI * 2); }
    } else {
      g.ellipse(0, 0, s * (narrow ? 1.6 : 1.1), s * (narrow ? 0.32 : 0.55), 0, 0, Math.PI * 2);
    }
    g.fill();
    if (!isFlower) { // vein highlight
      g.globalAlpha = 0.25; g.strokeStyle = '#d7e3b5'; g.lineWidth = 0.8;
      g.beginPath(); g.moveTo(-s, 0); g.lineTo(s, 0); g.stroke();
    }
    g.restore();
  }
  return tex(c);
}

// Interlaced eight-point star lattice (white = solid) used as an alpha map.
export function latticeTexture() {
  const [c, g] = canvas(256, 256);
  g.fillStyle = '#000'; g.fillRect(0, 0, 256, 256);
  g.strokeStyle = '#fff'; g.lineWidth = 7; g.lineJoin = 'miter';
  const cell = 128;
  for (let y = 0; y <= 256; y += cell) for (let x = 0; x <= 256; x += cell) {
    for (const rot of [0, Math.PI / 4]) {
      g.save(); g.translate(x, y); g.rotate(rot);
      g.strokeRect(-38, -38, 76, 76);
      g.restore();
    }
    g.beginPath(); g.arc(x, y, 18, 0, Math.PI * 2); g.stroke();
  }
  g.lineWidth = 6;
  for (let i = 0; i <= 256; i += cell) {
    g.beginPath(); g.moveTo(i + 64, 0); g.lineTo(i + 64, 256); g.stroke();
    g.beginPath(); g.moveTo(0, i + 64); g.lineTo(256, i + 64); g.stroke();
  }
  return tex(c, { srgb: false, repeat: true });
}

// Vertical-baluster railing seen from a distance (alpha map, 1 m wide tile).
export function railTexture() {
  const [c, g] = canvas(128, 128);
  g.fillStyle = '#000'; g.fillRect(0, 0, 128, 128);
  g.fillStyle = '#fff';
  for (let x = 4; x < 128; x += 13) g.fillRect(x, 0, 3, 128);
  g.fillRect(0, 0, 128, 8);
  g.fillRect(0, 120, 128, 8);
  return tex(c, { srgb: false, repeat: true });
}

export function radialTexture(inner = 'rgba(255,255,255,1)', outer = 'rgba(255,255,255,0)', size = 128) {
  const [c, g] = canvas(size, size);
  const gr = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  gr.addColorStop(0, inner); gr.addColorStop(1, outer);
  g.fillStyle = gr; g.fillRect(0, 0, size, size);
  return tex(c, { srgb: false });
}

// Quiet abstract canvas: colour fields in sand, ivory and violet with dry-brush texture.
export function artTexture(seed, palette) {
  const [c, g] = canvas(512, 640);
  const r = rng(seed);
  g.fillStyle = palette[0]; g.fillRect(0, 0, 512, 640);
  for (let i = 1; i < palette.length; i++) {
    g.fillStyle = palette[i];
    g.globalAlpha = 0.85;
    g.beginPath();
    if (i % 2) g.ellipse(120 + r() * 280, 150 + r() * 340, 90 + r() * 120, 60 + r() * 140, r() * 3, 0, Math.PI * 2);
    else g.rect(40 + r() * 200, 60 + r() * 300, 120 + r() * 220, 80 + r() * 200);
    g.fill();
  }
  g.globalAlpha = 0.07;
  for (let i = 0; i < 2500; i++) {
    g.fillStyle = r() > 0.5 ? '#000' : '#fff';
    g.fillRect(r() * 512, r() * 640, 1 + r() * 18, 1);
  }
  g.globalAlpha = 1;
  g.strokeStyle = '#2b2a2e'; g.lineWidth = 3;
  g.beginPath(); g.moveTo(60 + r() * 100, 560); g.bezierCurveTo(200, 400 + r() * 100, 300, 500, 460, 120 + r() * 200); g.stroke();
  return tex(c);
}

// Warm interior seen through glass of houses we don't model inside.
export function roomTexture() {
  const [c, g] = canvas(256, 256);
  let gr = g.createLinearGradient(0, 0, 0, 256);
  gr.addColorStop(0, '#d9c7ad'); gr.addColorStop(0.55, '#a8916f'); gr.addColorStop(1, '#4a3d30');
  g.fillStyle = gr; g.fillRect(0, 0, 256, 256);
  for (const x of [60, 190]) {
    gr = g.createRadialGradient(x, 30, 0, x, 30, 120);
    gr.addColorStop(0, 'rgba(255,236,200,0.9)'); gr.addColorStop(1, 'rgba(255,236,200,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 256, 256);
  }
  g.fillStyle = 'rgba(40,32,26,0.55)'; g.fillRect(30, 150, 120, 50); g.fillRect(170, 120, 60, 90);
  return tex(c);
}

// Front and rear elevations of the townhouse for far-distance blocks (u 0-0.5 front, 0.5-1 rear).
export function facadeAtlas() {
  const W = 512, Hh = 256;
  const [c, g] = canvas(W, Hh);
  const [ce, ge] = canvas(W, Hh);
  ge.fillStyle = '#000'; ge.fillRect(0, 0, W, Hh);
  const px = (x) => x / 6.1 * 256, py = (y) => Hh - y / 10.2 * Hh;
  for (const side of [0, 1]) {
    g.save(); ge.save();
    g.translate(side * 256, 0); ge.translate(side * 256, 0);
    g.fillStyle = '#ece8e1'; g.fillRect(0, 0, 256, Hh);
    const win = (x0, x1, y0, y1, lit) => {
      const gr = g.createLinearGradient(0, py(y1), 0, py(y0));
      gr.addColorStop(0, '#7f8d9c'); gr.addColorStop(1, '#2c3238');
      g.fillStyle = gr; g.fillRect(px(x0), py(y1), px(x1) - px(x0), py(y0) - py(y1));
      g.strokeStyle = '#1b1c1e'; g.lineWidth = 2; g.strokeRect(px(x0), py(y1), px(x1) - px(x0), py(y0) - py(y1));
      if (lit) { ge.fillStyle = '#ffcf94'; ge.fillRect(px(x0) + 2, py(y1) + 2, px(x1) - px(x0) - 4, py(y0) - py(y1) - 4); }
    };
    if (side === 0) {
      g.fillStyle = '#3a3836'; g.fillRect(px(0.1), py(3.2), px(6.0) - px(0.1), py(0) - py(3.2));
      win(3.9, 5.6, 1.3, 2.5, true);
      win(2.6, 5.8, 3.6, 6.3, true);
      g.fillStyle = '#5d5e60'; g.fillRect(px(0.2), py(6.3), px(2.4) - px(0.2), py(3.6) - py(6.3));
      win(3.3, 4.2, 6.8, 9.2, false);
    } else {
      win(0.1, 6.0, 0.3, 3.2, true);
      g.fillStyle = '#5d5e60'; g.fillRect(px(0.1), py(6.4), px(6.0) - px(0.1), py(3.6) - py(6.4));
      win(0.4, 2.6, 3.6, 6.2, true);
      win(3.3, 5.7, 3.6, 6.2, false);
      win(2.9, 5.5, 6.8, 9.4, true);
    }
    g.fillStyle = '#7a5b3e';
    for (const y of [3.55, 6.8]) { g.fillRect(0, py(y + 1.05), 256, 3); for (let x = 4; x < 256; x += 9) g.fillRect(x, py(y + 1.05), 1.5, py(y) - py(y + 1.05)); }
    g.fillStyle = '#f6f3ee';
    g.fillRect(0, py(6.95), 256, py(6.45) - py(6.95));
    g.fillRect(0, 0, 10, Hh); g.fillRect(246, 0, 10, Hh);
    g.fillStyle = '#8a6646'; g.fillRect(0, py(10.2), 256, py(9.7) - py(10.2));
    g.restore(); ge.restore();
  }
  return { map: tex(c), emissive: tex(ce) };
}

// Tileable water normal map from integer-frequency waves.
export function waterNormals(size = 256) {
  const [c, g] = canvas(size, size);
  const img = g.createImageData(size, size);
  const r = rng(11);
  const waves = Array.from({ length: 14 }, () => ({ kx: Math.round((r() - 0.5) * 16), ky: Math.round((r() - 0.5) * 16), a: 0.4 + r(), p: r() * 6.28 }));
  const h = (x, y) => waves.reduce((s, w) => s + w.a / (1 + Math.hypot(w.kx, w.ky)) * Math.sin(6.2832 * (w.kx * x + w.ky * y) / size + w.p), 0);
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const dx = h(x + 1, y) - h(x - 1, y), dy = h(x, y + 1) - h(x, y - 1);
    const nx = -dx * 2.2, ny = -dy * 2.2, nz = 1, l = Math.hypot(nx, ny, nz);
    const i = (y * size + x) * 4;
    img.data[i] = (nx / l * 0.5 + 0.5) * 255; img.data[i + 1] = (ny / l * 0.5 + 0.5) * 255; img.data[i + 2] = (nz / l * 0.5 + 0.5) * 255; img.data[i + 3] = 255;
  }
  g.putImageData(img, 0, 0);
  return tex(c, { srgb: false, repeat: true });
}
