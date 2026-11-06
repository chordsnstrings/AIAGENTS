import * as THREE from 'three';
import { ROOMS, PLOT } from './plan.js';

// DOM overlay: loader, chapter cards keyed to scroll progress, chapter rail, mini plans drawn
// from the same room data as the 3D model, and a pin that marks the plot from the air.

const SVGNS = 'http://www.w3.org/2000/svg';

function planSVG(floor, highlight) {
  const s = 10, W = PLOT.d * s, Hh = PLOT.w * s;
  const svg = document.createElementNS(SVGNS, 'svg');
  svg.setAttribute('viewBox', `-14 -4 ${W + 28} ${Hh + 8}`);
  svg.setAttribute('class', 'plan-svg');
  const rect = (x, y, w, h, cls) => {
    const r = document.createElementNS(SVGNS, 'rect');
    Object.entries({ x, y, width: w, height: h, class: cls }).forEach(([k, v]) => r.setAttribute(k, v));
    svg.appendChild(r);
  };
  rect(0, 0, W, Hh, 'plot');
  for (const r of ROOMS.filter((q) => q.f === floor)) {
    rect(r.d[0] * s, (PLOT.w - r.x[1]) * s, (r.d[1] - r.d[0]) * s, (r.x[1] - r.x[0]) * s, highlight.includes(r.key) ? 'room on' : 'room');
  }
  const t = document.createElementNS(SVGNS, 'text');
  t.setAttribute('x', -6); t.setAttribute('y', Hh / 2); t.setAttribute('class', 'street');
  t.setAttribute('transform', `rotate(-90 -6 ${Hh / 2})`);
  t.textContent = 'STREET';
  svg.appendChild(t);
  return svg;
}

export function initUI({ onMode, onJump }) {
  const loader = document.getElementById('loader');
  const bar = loader.querySelector('.bar i');
  const label = loader.querySelector('.label');
  const pct = loader.querySelector('.pct');
  const cards = [...document.querySelectorAll('.card')].map((el) => ({
    el, from: +el.dataset.from, to: +el.dataset.to, last: -1,
  }));
  for (const c of cards) {
    const p = c.el.querySelector('.plan');
    if (p) p.appendChild(planSVG(+p.dataset.floor, p.dataset.room.split(',')));
  }
  // rail
  const rail = document.getElementById('rail');
  const stops = cards.filter((c) => c.el.dataset.rail);
  stops.forEach((c, i) => {
    const b = document.createElement('button');
    b.innerHTML = `<span class="n">${String(i + 1).padStart(2, '0')}</span><span class="t">${c.el.dataset.rail}</span>`;
    b.addEventListener('click', () => onJump((c.from + c.to) / 2));
    rail.appendChild(b);
    c.rail = b;
  });
  // time of day
  const modeBtns = [...document.querySelectorAll('[data-mode]')];
  modeBtns.forEach((b) => b.addEventListener('click', () => {
    modeBtns.forEach((x) => x.classList.toggle('on', x === b));
    onMode(b.dataset.mode);
  }));
  const pin = document.getElementById('pin');
  const meter = document.querySelector('.meter i');
  const v = new THREE.Vector3();

  return {
    progress(f, text) {
      bar.style.transform = `scaleX(${f})`;
      pct.textContent = `${Math.round(f * 100)}%`;
      if (text) label.textContent = text;
    },
    ready() { document.body.classList.add('ready'); loader.classList.add('gone'); setTimeout(() => loader.remove(), 1400); },
    fatal(msg) { label.textContent = msg; loader.classList.add('err'); },
    update(p, camera, pinWorld, w, h) {
      for (const c of cards) {
        const fade = 0.012;
        const inn = c.from <= 0 ? 1 : THREE.MathUtils.smoothstep(p, c.from - fade, c.from + fade);
        let o = inn * (1 - THREE.MathUtils.smoothstep(p, c.to - fade, c.to + fade));
        if (c.to >= 1) o = THREE.MathUtils.smoothstep(p, c.from - fade, c.from + fade);
        o = Math.round(o * 100) / 100;
        if (o !== c.last) {
          c.last = o;
          c.el.style.opacity = o;
          c.el.style.transform = `translate3d(0, ${(1 - o) * 14}px, 0)`;
          c.el.style.visibility = o > 0 ? 'visible' : 'hidden';
          c.el.style.pointerEvents = o > 0.5 ? 'auto' : 'none';
        }
        if (c.rail) c.rail.classList.toggle('on', p >= c.from - 0.01 && p <= c.to + 0.01);
      }
      meter.style.transform = `scaleY(${p})`;
      // plot pin while airborne
      const po = THREE.MathUtils.smoothstep(p, 0.045, 0.07) * (1 - THREE.MathUtils.smoothstep(p, 0.17, 0.215));
      v.copy(pinWorld).project(camera);
      const vis = po > 0.01 && v.z < 1 && Math.abs(v.x) < 1.1 && Math.abs(v.y) < 1.1;
      pin.style.opacity = vis ? po : 0;
      if (vis) pin.style.transform = `translate3d(${(v.x * 0.5 + 0.5) * w}px, ${(-v.y * 0.5 + 0.5) * h}px, 0)`;
    },
  };
}
