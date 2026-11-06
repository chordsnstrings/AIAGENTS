import * as THREE from 'three';
import { ROOMS, PLOT, STAIR, FACTS } from './plan.js';
import { CHAPTERS, FADE, PIN, STYLE_PILL, TOD, chapter, chapterAt } from './story.js';

// DOM overlay: loader, chapter cards keyed to the story table, chapter rail, mini plans drawn
// from the same room data as the 3D model, a printable plan sheet, and a pin that marks the
// plot from the air. One chapter is active per frame (story.js chapterAt) and both the cards
// and the rail follow it, so two cards never show at once and the rail lights one stop.

const SVGNS = 'http://www.w3.org/2000/svg';
const S = 10; // px per metre in the plans

function planSVG(floor, highlight, { stair = false, labels = false } = {}) {
  const W = PLOT.d * S, Hh = PLOT.w * S;
  const svg = document.createElementNS(SVGNS, 'svg');
  svg.setAttribute('viewBox', `-14 -4 ${W + 28} ${Hh + 8}`);
  svg.setAttribute('class', 'plan-svg');
  svg.setAttribute('aria-hidden', 'true');
  const el = (tag, attrs, text) => {
    const e = document.createElementNS(SVGNS, tag);
    Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v));
    if (text !== undefined) e.textContent = text;
    svg.appendChild(e);
    return e;
  };
  // plan coordinates to the sheet: d runs along the sheet (street on the left), x up it
  const rect = (x, d, cls) => el('rect', { x: d[0] * S, y: (PLOT.w - x[1]) * S, width: (d[1] - d[0]) * S, height: (x[1] - x[0]) * S, class: cls });
  el('rect', { x: 0, y: 0, width: W, height: Hh, class: 'plot' });
  for (const r of ROOMS.filter((q) => q.f === floor)) {
    rect(r.x, r.d, highlight.includes(r.key) ? 'room on' : 'room');
    if (labels) {
      const cx = (r.d[0] + r.d[1]) / 2 * S, cy = (PLOT.w - (r.x[0] + r.x[1]) / 2) * S;
      el('text', { x: cx, y: cy - (r.size ? 1.6 : -1.4), class: 'name' }, r.name);
      if (r.size) el('text', { x: cx, y: cy + 3.4, class: 'size' }, r.size);
    }
  }
  rect(STAIR.x, STAIR.d, stair ? 'stair on' : 'stair');
  el('text', { x: -6, y: Hh / 2, class: 'street', transform: `rotate(-90 -6 ${Hh / 2})` }, 'STREET');
  return svg;
}

const FLOORS = ['Ground floor', 'First floor', 'Roof level'];

// A sheet the visitor can print or save as PDF: the three floors at a readable scale, every
// room named and sized, drawn from plan.js rather than redistributing the developer's plans.
function printSheet() {
  const sheet = document.createElement('section');
  sheet.id = 'print-plans';
  sheet.setAttribute('aria-hidden', 'true');
  sheet.innerHTML = `<h1>${FACTS.project} · Plot ${FACTS.plot} · ${FACTS.type}</h1><p>${FACTS.community}. Plot ${PLOT.w.toFixed(2)} × ${PLOT.d.toFixed(2)} m (${PLOT.areaM2} m²); saleable ${FACTS.areasSqft.total.toLocaleString('en')} sq ft. Room sizes follow the developer's floor plans; the drawing is a visualisation, not a construction document.</p>`;
  for (const [f, name] of FLOORS.entries()) {
    const fig = document.createElement('figure');
    const cap = document.createElement('figcaption');
    const sqft = [FACTS.areasSqft.ground, FACTS.areasSqft.first, FACTS.areasSqft.roof][f];
    cap.textContent = `${name} · ${sqft.toLocaleString('en')} sq ft`;
    fig.appendChild(cap);
    fig.appendChild(planSVG(f, [], { labels: true }));
    sheet.appendChild(fig);
  }
  document.body.appendChild(sheet);
}

export function initUI({ onMode, onJump, onStyle, styles }) {
  const loader = document.getElementById('loader');
  const bar = loader.querySelector('.bar i');
  const label = loader.querySelector('.label');
  const pct = loader.querySelector('.pct');
  const live = document.getElementById('live');
  const cards = [...document.querySelectorAll('.card')].map((el) => {
    const ch = chapter(el.dataset.chapter);
    if (!ch) throw new Error(`card without a chapter in story.js: ${el.dataset.chapter}`);
    return { el, ch, title: el.querySelector('h2, h3')?.textContent.trim() || ch.rail, last: -1 };
  });
  for (const c of cards) {
    const p = c.el.querySelector('.plan');
    if (p) p.appendChild(planSVG(+p.dataset.floor, (p.dataset.room || '').split(',').filter(Boolean), { stair: 'stair' in p.dataset }));
    // the card's number is the chapter's place in the rail, so the two can never disagree
    const n = c.el.querySelector('.eyebrow .n');
    if (n) n.textContent = String(CHAPTERS.indexOf(c.ch) + 1).padStart(2, '0');
  }
  printSheet();
  let lastP = 0, active = null, announceT = 0, styleNow = null;

  // rail: one stop per chapter, landing on the chapter's best frame rather than its midpoint
  const rail = document.getElementById('rail');
  const stops = CHAPTERS.map((ch, i) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.innerHTML = `<span class="n">${String(i + 1).padStart(2, '0')}</span><span class="t">${ch.rail}</span>`;
    b.setAttribute('aria-label', `${ch.rail}, chapter ${i + 1} of ${CHAPTERS.length}`);
    b.addEventListener('click', () => onJump(ch.jump));
    rail.appendChild(b);
    return b;
  });

  // keyboard: chapters, not screens. Arrow and page keys step between the chapters' best
  // frames; Home and End go to the ends. Keys on a focused control are left to it.
  addEventListener('keydown', (e) => {
    if (e.altKey || e.ctrlKey || e.metaKey || e.defaultPrevented) return;
    const onControl = e.target instanceof Element && e.target.closest('button, a, input, select, textarea, summary');
    // from between two landings, the first step goes to the nearer one in that direction
    const cur = chapterAt(lastP), i = CHAPTERS.indexOf(cur);
    const next = lastP < cur.jump - 0.003 ? cur : CHAPTERS[Math.min(i + 1, CHAPTERS.length - 1)];
    const prev = lastP > cur.jump + 0.003 ? cur : CHAPTERS[Math.max(i - 1, 0)];
    let to = null;
    if (['ArrowRight', 'ArrowDown', 'PageDown'].includes(e.key) || (e.key === ' ' && !e.shiftKey && !onControl)) to = next;
    else if (['ArrowLeft', 'ArrowUp', 'PageUp'].includes(e.key) || (e.key === ' ' && e.shiftKey && !onControl)) to = prev;
    else if (e.key === 'Home') to = CHAPTERS[0];
    else if (e.key === 'End') to = CHAPTERS[CHAPTERS.length - 1];
    if (!to) return;
    e.preventDefault();
    onJump(to.jump);
  });

  // time of day
  const modeBtns = [...document.querySelectorAll('[data-mode]')];
  const setMode = (m) => modeBtns.forEach((x) => { const on = x.dataset.mode === m; x.classList.toggle('on', on); x.setAttribute('aria-pressed', on); });
  modeBtns.forEach((b) => b.addEventListener('click', () => { setMode(b.dataset.mode); onMode(b.dataset.mode); }));
  setMode(modeBtns.find((b) => b.classList.contains('on'))?.dataset.mode || 'auto');

  // interior style switcher
  const box = document.getElementById('styles');
  const sbtn = {};
  for (const [k, st] of Object.entries(styles)) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.title = st.name;
    btn.setAttribute('aria-pressed', 'false');
    btn.innerHTML = `<i style="background:conic-gradient(${st.palette.map((c, i) => `${c} ${i * 60}deg ${(i + 1) * 60}deg`).join(',')})"></i><span>${st.short}</span>`;
    // the switch is asynchronous; a rejection is the engine's to report, not an unhandled one
    btn.addEventListener('click', () => { const r = onStyle(k); if (r && r.catch) r.catch(() => {}); });
    box.appendChild(btn);
    sbtn[k] = btn;
  }
  const toast = document.getElementById('toast');
  let toastT = 0, firstStyle = true, sunsetTold = false;
  const say = (html, ms = 2800) => {
    toast.innerHTML = html;
    toast.classList.add('show');
    clearTimeout(toastT);
    toastT = setTimeout(() => toast.classList.remove('show'), ms);
  };

  // ending actions
  document.querySelectorAll('[data-action]').forEach((b) => b.addEventListener('click', async () => {
    const a = b.dataset.action;
    if (a === 'replay') onJump(0);
    else if (a === 'print') window.print();
    else if (a === 'copy') {
      const url = location.href.split('#')[0] + '#' + (styleNow || 'minimal');
      try { await navigator.clipboard.writeText(url); say('<b>Link copied</b><span>It opens the flight in this interior style.</span>'); }
      catch (e) { say(`<b>Copy this link</b><span>${url}</span>`, 6000); }
    }
  }));
  // phones: the figures sit behind a Details tap so the card stays short
  document.querySelectorAll('.card .more').forEach((b) => b.addEventListener('click', () => {
    const open = b.closest('.card').classList.toggle('open');
    b.setAttribute('aria-expanded', open);
    b.textContent = open ? 'Less' : 'Details';
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
    setStyle(k) {
      const st = styles[k];
      styleNow = k;
      for (const [key, btn] of Object.entries(sbtn)) { btn.classList.toggle('on', key === k); btn.setAttribute('aria-pressed', key === k); }
      const sw = st.palette.map((c) => `<i style="background:${c}"></i>`).join('');
      document.querySelectorAll('[data-style-line]').forEach((el) => { el.innerHTML = `<span class="sw">${sw}</span><b>${st.name}</b> ${st.blurb}`; });
      if (!firstStyle) say(`<b>${st.name}</b><span>${st.blurb}</span>`);
      firstStyle = false;
    },
    styleLoading(b) { box.classList.toggle('loading', b); },
    ready() { document.body.classList.add('ready'); loader.classList.add('gone'); setTimeout(() => loader.remove(), 1400); },
    // No WebGL (or a failed start): keep the loader as a page with the poster, the message and
    // the facts, so the visitor still gets the house and its numbers.
    fatal(msg) {
      label.textContent = msg;
      loader.classList.add('err');
      const facts = document.querySelector('.card.outro table');
      if (facts && !loader.querySelector('table')) {
        const box = document.createElement('div');
        box.className = 'facts';
        box.innerHTML = `<p class="eyebrow">Plot ${FACTS.plot} · ${FACTS.type} · ${FACTS.beds} bedrooms</p>`;
        box.appendChild(facts.cloneNode(true));
        loader.querySelector('.inner').appendChild(box);
      }
    },
    update(p, camera, pinWorld, w, h) {
      lastP = p;
      const cur = chapterAt(p);
      for (const c of cards) {
        const { from, to } = c.ch;
        let o = (from <= 0 ? 1 : THREE.MathUtils.smoothstep(p, from - FADE, from + FADE)) * (to >= 1 ? 1 : 1 - THREE.MathUtils.smoothstep(p, to - FADE, to + FADE));
        o = Math.round(o * 100) / 100;
        if (o !== c.last) {
          c.last = o;
          c.el.style.opacity = o;
          c.el.style.transform = `translate3d(0, ${(1 - o) * 14}px, 0)`;
          c.el.style.visibility = o > 0 ? 'visible' : 'hidden';
          c.el.style.pointerEvents = o > 0.5 ? 'auto' : 'none';
          c.el.setAttribute('aria-hidden', o <= 0.5);
        }
      }
      if (cur !== active) {
        active = cur;
        stops.forEach((b, i) => { const on = CHAPTERS[i] === cur; b.classList.toggle('on', on); if (on) b.setAttribute('aria-current', 'step'); else b.removeAttribute('aria-current'); });
        // announce once the visitor has settled on a chapter, not every one passed through
        clearTimeout(announceT);
        announceT = setTimeout(() => { if (live) live.textContent = `${CHAPTERS.indexOf(cur) + 1} of ${CHAPTERS.length}: ${cards.find((c) => c.ch === cur)?.title || cur.rail}`; }, 600);
      }
      document.body.classList.toggle('interior', p >= STYLE_PILL[0] && p <= STYLE_PILL[1]);
      if (!sunsetTold && p >= TOD.sunsetFrom && p < TOD.nightBy && modeBtns.find((b) => b.classList.contains('on'))?.dataset.mode === 'auto') { sunsetTold = true; say('<b>Sunset</b><span>The light follows the flight; switch to Day or Night any time at the top right.</span>', 4200); }
      meter.style.transform = `scaleY(${p})`;
      // plot pin while airborne: on from the first frame, off for the facade, back for the ending
      let po = 0;
      for (const win of PIN.windows) po = Math.max(po, THREE.MathUtils.smoothstep(p, win.in[0], win.in[1]) * (1 - THREE.MathUtils.smoothstep(p, win.out[0], win.out[1])));
      v.copy(pinWorld).project(camera);
      const vis = po > 0.01 && v.z < 1 && Math.abs(v.x) < 1.1 && Math.abs(v.y) < 1.1;
      pin.style.opacity = vis ? po : 0;
      if (vis) {
        const px = (v.x * 0.5 + 0.5) * w, py = (-v.y * 0.5 + 0.5) * h;
        pin.style.transform = `translate3d(${px}px, ${py}px, 0)`;
        // keep the label clear of the top bar and of the card it would otherwise run into
        pin.classList.toggle('below', py < 150);
        const card = cards.find((c) => c.ch === cur && c.last > 0.5 && !c.el.classList.contains('hero'));
        const edge = card ? card.el.getBoundingClientRect().right : -1e3;
        pin.classList.toggle('aside', px - 70 < edge && px + 70 > edge - 420);
      }
    },
  };
}
