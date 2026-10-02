// Script de capture de la démo du moteur de texte.
//   node outils/capture.js outils/demos/texte/demo.sb3 outils/demos/texte/demo.js
// Produit outils/captures/texte_demo.png et le copie en outils/demos/texte/demo.png.
const fs = require('fs');
const path = require('path');

module.exports = async (aides) => {
  await aides.attendre(2500);
  const f = await aides.capture('texte_demo');
  fs.copyFileSync(f, path.join(__dirname, 'demo.png'));
  console.log('copie :', path.join(__dirname, 'demo.png'));
  const log = await aides.log();
  if (log.length) console.log('log page :', log);
};
