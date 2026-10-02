// Capture de verif_polices.py → outils/captures/texte_polices.png (+ loupe 3× du haut).
const path = require('path');
module.exports = async (aides) => {
  await aides.attendre(3500);
  await aides.capture('texte_polices');
  await aides.page.setViewportSize({ width: 1440, height: 1100 });
  await aides.page.evaluate(() => {
    vm.runtime.renderer.draw();
    const z = document.createElement('canvas'); z.id = 'zoom'; document.body.appendChild(z);
    z.width = 1440; z.height = 1080;
    const ctx = z.getContext('2d'); ctx.imageSmoothingEnabled = false;
    ctx.drawImage(document.getElementById('stage'), 0, 0, 480, 360, 0, 0, 1440, 1080);
  });
  const f = path.join(__dirname, '..', '..', 'captures', 'texte_polices_zoom.png');
  await aides.page.locator('#zoom').screenshot({ path: f });
  console.log('capture :', f);
  const log = await aides.log();
  if (log.length) console.log('log page :', log);
};
