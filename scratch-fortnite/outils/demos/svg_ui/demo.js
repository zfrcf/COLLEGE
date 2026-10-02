// Script de capture des planches d'icônes (rendu réel Chromium).
//   node outils/capture.js outils/demos/svg_ui/demo.sb3 outils/demos/svg_ui/demo.js
// Pour chaque planche de planches.json : pose demo_planche = n, attend le redessin, capture
// outils/captures/svg_ui_<nom>.png et le copie en outils/demos/svg_ui/planche_<nom>.png.
const fs = require('fs');
const path = require('path');

module.exports = async (A) => {
  const planches = JSON.parse(fs.readFileSync(path.join(__dirname, 'planches.json'), 'utf8'));
  const seules = (process.env.PLANCHES || '').split(',').filter(Boolean);
  await A.attendre(1500);
  for (let i = 0; i < planches.length; i++) {
    const p = planches[i];
    if (seules.length && !seules.includes(p.nom)) continue;
    await A.evaluer((vm, V, L, arg) => { V('demo_planche').value = arg; }, i + 1);
    await A.attendre(1400);
    const clones = await A.evaluer(vm => vm.runtime.targets.filter(t => t.getName() === 'Planche' && !t.isOriginal).length);
    const f = await A.capture('svg_ui_' + p.nom);
    fs.copyFileSync(f, path.join(__dirname, 'planche_' + p.nom + '.png'));
    console.log('planche %s : %d clones (attendus %d)%s', p.nom, clones, p.clones, clones === p.clones ? '' : '  ✘');
  }
  const log = await A.log();
  if (log.length) console.log('log page :', log);
};
