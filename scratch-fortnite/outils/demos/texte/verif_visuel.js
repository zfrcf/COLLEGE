// Capture de verif_visuel.py : image complète + trois loupes 3× (plus proche voisin)
// pour juger la lisibilité réelle des petits corps.
//   node outils/capture.js outils/demos/texte/verif_visuel.sb3 outils/demos/texte/verif_visuel.js
const path = require('path');

module.exports = async (aides) => {
  await aides.attendre(3000);
  await aides.capture('texte_verif');
  await aides.page.setViewportSize({ width: 1440, height: 1100 });
  const bandes = { haut: [0, 125], milieu: [125, 250], bas: [250, 360] };
  for (const [nom, [y0, y1]] of Object.entries(bandes)) {
    await aides.page.evaluate(([y0, y1]) => {
      vm.runtime.renderer.draw();
      let z = document.getElementById('zoom');
      if (!z) { z = document.createElement('canvas'); z.id = 'zoom'; document.body.appendChild(z); }
      z.width = 1440; z.height = (y1 - y0) * 3;
      const ctx = z.getContext('2d');
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(document.getElementById('stage'), 0, y0, 480, y1 - y0, 0, 0, 1440, (y1 - y0) * 3);
    }, [y0, y1]);
    const f = path.join(__dirname, '..', '..', 'captures', 'texte_verif_zoom_' + nom + '.png');
    await aides.page.locator('#zoom').screenshot({ path: f });
    console.log('capture :', f);
  }
  const log = await aides.log();
  if (log.length) console.log('log page :', log);
};
