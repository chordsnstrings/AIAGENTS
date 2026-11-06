// Renders stills of the page with headless Chromium (software GL) for review.
// Serve the folder first (npm run serve), then e.g.:
//   node scripts/capture.cjs http://localhost:8080 out high 0.40,0.70 "&ui=0"
// Writes out/p<progress>.png and prints load timings plus console errors.
// usage: node capture.cjs <baseUrl> <outDir> <q> <p1,p2,...> [extra query]
const { chromium } = require('playwright');
(async () => {
  const [base, out, q, list, extra = ''] = process.argv.slice(2);
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  for (const p of list.split(',')) {
    const page = await browser.newPage({ viewport: { width: +(process.env.W || 1024), height: +(process.env.H || 576) }, deviceScaleFactor: 1 });
    const errs = [];
    page.on('console', (m) => { if (['error', 'warning'].includes(m.type()) || m.text().startsWith('[t]')) errs.push(m.type() + ': ' + m.text().slice(0, 300)); });
    page.on('pageerror', (e) => errs.push('pageerror: ' + e.message));
    const t0 = Date.now();
    await page.goto(`${base}/index.html?p=${p}&q=${q}${extra}`);
    try { await page.waitForFunction(() => window.__shot === true, null, { timeout: 600000, polling: 1000 }); }
    catch (e) { errs.push('timeout waiting for __shot'); }
    await page.waitForTimeout(300);
    await page.screenshot({ path: `${out}/p${p}.png`, timeout: 180000 });
    console.log(`p=${p} ${((Date.now() - t0) / 1000).toFixed(1)}s`, errs.length ? '\n  ' + [...new Set(errs)].slice(0, 12).join('\n  ') : '');
    await page.close();
  }
  await browser.close();
})();
