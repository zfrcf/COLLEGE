// Rendu réel dans Chromium (moteur de rendu officiel scratch-render) + captures PNG.
//   node capture.js [chemin.sb3] [script_de_capture.js]
// Le script de capture reçoit (page, aides) et peut appeler aides.capture('nom') ;
// sans script : capture « demarrage.png » après 2 s.
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const http = require('http');

function copierBundles() {
  const nm = path.join(__dirname, 'node_modules');
  const web = path.join(__dirname, 'web');
  const fichiers = {
    'scratch-vm.js': 'scratch-vm/dist/web/scratch-vm.js',
    'scratch-render.js': 'scratch-render/dist/web/scratch-render.js',
    'scratch-storage.js': 'scratch-storage/dist/web/scratch-storage.js',
    'scratch-svg-renderer.js': 'scratch-svg-renderer/dist/web/scratch-svg-renderer.js',
  };
  for (const [dest, src] of Object.entries(fichiers)) {
    const s = path.join(nm, src); const d = path.join(web, dest);
    if (!fs.existsSync(d) && fs.existsSync(s)) fs.copyFileSync(s, d);
  }
  const chunks = path.join(nm, 'scratch-storage/dist/web/chunks');
  if (fs.existsSync(chunks) && !fs.existsSync(path.join(web, 'chunks'))) fs.cpSync(chunks, path.join(web, 'chunks'), { recursive: true });
}

function servir(dossier) {
  const types = { '.html': 'text/html', '.js': 'application/javascript', '.sb3': 'application/zip', '.map': 'application/json' };
  return new Promise(resolve => {
    const srv = http.createServer((req, res) => {
      const f = path.join(dossier, decodeURIComponent(req.url.split('?')[0] === '/' ? '/index.html' : req.url.split('?')[0]));
      if (!f.startsWith(dossier) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); res.end(); return; }
      res.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' });
      fs.createReadStream(f).pipe(res);
    });
    srv.listen(0, '127.0.0.1', () => resolve(srv));
  });
}

(async () => {
  const args = process.argv.slice(2);
  const sb3 = args.find(a => a.endsWith('.sb3')) || path.join(__dirname, '..', 'Royale 3D.sb3');
  const script = args.filter(a => a.endsWith('.js'))[0];
  copierBundles();
  fs.copyFileSync(sb3, path.join(__dirname, 'web', 'projet.sb3'));
  const srv = await servir(path.join(__dirname, 'web'));
  const port = srv.address().port;
  const exe = fs.existsSync('/opt/pw-browsers/chromium-1194/chrome-linux/chrome') ? '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' : undefined;
  const browser = await chromium.launch({ executablePath: exe, args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 480, height: 360 } });
  page.on('pageerror', e => console.log('pageerror:', String(e).slice(0, 300)));
  await page.goto('http://127.0.0.1:' + port + '/index.html');
  await page.waitForFunction(() => window.pret === true, null, { timeout: 90000 });
  const dossierCaptures = path.join(__dirname, 'captures');
  fs.mkdirSync(dossierCaptures, { recursive: true });
  const aides = {
    page,
    async capture(nom) { const f = path.join(dossierCaptures, nom + '.png'); await page.screenshot({ path: f }); console.log('capture :', f); return f; },
    attendre: ms => page.waitForTimeout(ms),
    // exécute du code dans la page avec accès à `vm`, `V(nom)` (variable globale) et `L(nom)` (liste)
    evaluer: (fn, arg) => page.evaluate(({ src, arg }) => {
      const st = vm.runtime.getTargetForStage();
      const V = n => Object.values(st.variables).find(v => v.name === n);
      const L = n => Object.values(st.variables).find(v => v.name === n).value;
      return (new Function('vm', 'V', 'L', 'arg', 'return (' + src + ')(vm, V, L, arg)'))(vm, V, L, arg);
    }, { src: fn.toString(), arg }),
    touche: (k, enfonce) => page.evaluate(([k, d]) => vm.postIOData('keyboard', { key: k, isDown: d }), [k, !!enfonce]),
    souris: (x, y, enfonce) => page.evaluate(([x, y, d]) => vm.postIOData('mouse', { x: 240 + x, y: 180 - y, isDown: d, canvasWidth: 480, canvasHeight: 360 }), [x, y, !!enfonce]),
    async clic(x, y) { await aides.souris(x, y, true); await page.waitForTimeout(80); await aides.souris(x, y, false); await page.waitForTimeout(120); },
    log: () => page.evaluate(() => window.log),
  };
  if (script) await require(path.resolve(script))(aides);
  else { await aides.attendre(2000); await aides.capture('demarrage'); }
  const log = await aides.log();
  if (log.some(l => /ERREUR/.test(l))) console.log('log page :', log);
  await browser.close();
  srv.close();
})().catch(e => { console.log('ERREUR', e); process.exit(1); });
