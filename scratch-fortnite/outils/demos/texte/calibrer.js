// Script de capture pour calibrer.py : mesure la boîte des pixels rouge pur autour
// de l'origine (le « H » brut) et imprime sa position en coordonnées Scratch.
//   node outils/capture.js calibrer.sb3 outils/demos/texte/calibrer.js
module.exports = async (aides) => {
  await aides.attendre(2500);
  const skins = await aides.page.evaluate(() => { const S = vm.runtime.renderer._allSkins.filter(s => s && s._svgImageLoaded !== undefined); return [S.length, S.filter(s => !s._svgImageLoaded).length]; });
  console.log('skins SVG :', skins[0], 'non chargés :', skins[1]);
  await aides.capture('texte_calibrer');
  const res = await aides.page.evaluate(() => {
    const c = document.getElementById('stage');
    vm.runtime.renderer.draw();
    const c2 = document.createElement('canvas'); c2.width = c.width; c2.height = c.height;
    const ctx = c2.getContext('2d'); ctx.drawImage(c, 0, 0);
    const sx = c.width / 480, sy = c.height / 360;
    const d = ctx.getImageData(0, 0, c.width, c.height).data;
    let minx = 1e9, maxx = -1, miny = 1e9, maxy = -1, n = 0;
    for (let y = 0; y < c.height; y++) for (let x = 0; x < c.width; x++) {
      const i = (y * c.width + x) * 4;
      const X = x / sx - 240, Y = 180 - y / sy;
      if (X < -5 || X > 60 || Y < -20 || Y > 50) continue;
      if (d[i] > 180 && d[i + 1] < 90 && d[i + 2] < 90) { n++; if (x < minx) minx = x; if (x > maxx) maxx = x; if (y < miny) miny = y; if (y > maxy) maxy = y; }
    }
    return { taille: [c.width, c.height], n, gauche: minx / sx - 240, droite: (maxx + 1) / sx - 240, haut: 180 - miny / sy, bas: 180 - (maxy + 1) / sy };
  });
  console.log('pixels rouges du H :', JSON.stringify(res));
  console.log('attendu : bas ≈ 0 (ligne de base), haut ≈ 28 (majuscule), gauche ≈ 3.6 (approche gauche du H)');
};
