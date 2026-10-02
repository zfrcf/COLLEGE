// Vérifications scratch-vm (sans rendu) de la démo des icônes : opcodes connus, aucune erreur,
// nombre de clones par planche conforme à planches.json, suppression des clones au changement.
//   node outils/demos/svg_ui/test_vm.js [demo.sb3]
const path = require('path');
const fs = require('fs');
const { charger } = require(path.join(__dirname, '..', '..', 'vm_lib'));
const dormir = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const sb3 = process.argv[2] || path.join(__dirname, 'demo.sb3');
  const planches = JSON.parse(fs.readFileSync(path.join(__dirname, 'planches.json'), 'utf8'));
  const T = await charger(sb3);
  let echecs = 0, total = 0;
  const verifier = (libelle, ok, detail) => { total++; if (!ok) echecs++; console.log((ok ? '  ✔ ' : '  ✘ ') + libelle + (ok ? '' : '  → ' + JSON.stringify(detail))); };
  verifier('aucun opcode inconnu', T.opcodesInconnus().length === 0, T.opcodesInconnus());
  const sprite = T.sprite('Planche');
  verifier('≥ 300 costumes (icônes + glyphes)', sprite.getCostumes().length >= 300, sprite.getCostumes().length);
  const noms = sprite.getCostumes().map(c => c.name);
  verifier('noms de costumes uniques', new Set(noms).size === noms.length);
  T.drapeau();
  for (let i = 0; i < 12; i++) { T.pas(3); await dormir(100); }
  verifier('aucune erreur VM', T.erreurs.length === 0, T.erreurs);
  verifier('planche 1 : ' + planches[0].clones + ' clones', T.clones('Planche') === planches[0].clones, T.clones('Planche'));
  for (const n of [2, 4, planches.length]) {
    T.set('demo_planche', n);
    for (let i = 0; i < 8; i++) { T.pas(3); await dormir(80); }
    verifier('planche ' + n + ' (' + planches[n - 1].nom + ') : ' + planches[n - 1].clones + ' clones', T.clones('Planche') === planches[n - 1].clones, T.clones('Planche'));
  }
  verifier('≤ 120 clones par planche', planches.every(p => p.clones <= 120), planches.map(p => p.clones));
  verifier('aucune erreur VM après changements', T.erreurs.length === 0, T.erreurs);
  T.fin();
  console.log('\n%d vérifications, %d échec(s)', total, echecs);
  process.exit(echecs ? 1 : 0);
})().catch(e => { console.log('ERREUR', e); process.exit(1); });
