// Diagnostic : charge un .sb3 dans la page de rendu avec la console relayée (délai court).
//   node outils/demos/svg_ui/debug_page.js chemin.sb3 [secondes]
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const http = require('http');
const web = path.join(__dirname, '..', '..', 'web');
(async () => {
  const sb3 = process.argv[2]; const secondes = Number(process.argv[3] || 25);
  fs.copyFileSync(sb3, path.join(web, 'projet.sb3'));
  const types = { '.html': 'text/html', '.js': 'application/javascript', '.sb3': 'application/zip' };
  const srv = http.createServer((req, res) => {
    const f = path.join(web, decodeURIComponent(req.url.split('?')[0] === '/' ? '/index.html' : req.url.split('?')[0]));
    if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' }); fs.createReadStream(f).pipe(res);
  });
  await new Promise(r => srv.listen(0, '127.0.0.1', r));
  const exe = fs.existsSync('/opt/pw-browsers/chromium-1194/chrome-linux/chrome') ? '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' : undefined;
  const browser = await chromium.launch({ executablePath: exe, args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 480, height: 360 } });
  page.on('console', m => { const t = m.text(); if (!/Translation/.test(t)) console.log('console[' + m.type() + ']:', t.slice(0, 400)); });
  page.on('pageerror', e => console.log('pageerror:', String(e).slice(0, 400)));
  page.on('requestfailed', r => console.log('requête échouée :', r.url()));
  await page.goto('http://127.0.0.1:' + srv.address().port + '/index.html');
  const t0 = Date.now();
  let pret = false;
  while (Date.now() - t0 < secondes * 1000) { pret = await page.evaluate(() => window.pret === true); if (pret) break; await page.waitForTimeout(500); }
  console.log('pret =', pret, 'après', ((Date.now() - t0) / 1000).toFixed(1), 's ; log :', JSON.stringify(await page.evaluate(() => window.log)));
  if (pret) { await page.waitForTimeout(2000); await page.screenshot({ path: path.join(__dirname, '..', '..', 'captures', (process.env.NOM || 'debug') + '.png') }); console.log('capture faite'); }
  await browser.close(); srv.close();
})().catch(e => { console.log('ERREUR', e); process.exit(1); });
