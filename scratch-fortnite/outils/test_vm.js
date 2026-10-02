// Lance un ou plusieurs scénarios de test contre le projet.
//   node test_vm.js [chemin.sb3] [scenarios/*.js ...]
// Sans scénario : charge le projet, vérifie les opcodes et fait tourner 60 images.
const path = require('path');
const fs = require('fs');
const { charger } = require('./vm_lib');

(async () => {
  const args = process.argv.slice(2);
  const sb3 = args.find(a => a.endsWith('.sb3')) || path.join(__dirname, '..', 'Royale 3D.sb3');
  let scenarios = args.filter(a => a.endsWith('.js'));
  if (!scenarios.length) {
    const dossier = path.join(__dirname, 'scenarios');
    if (fs.existsSync(dossier)) scenarios = fs.readdirSync(dossier).filter(f => f.endsWith('.js')).map(f => path.join(dossier, f));
  }
  let echecs = 0, total = 0;
  const T0 = await charger(sb3);
  const inconnus = T0.opcodesInconnus();
  console.log('Projet : %s — %d blocs, %d sprites, opcodes inconnus : %s', path.basename(sb3), T0.nbBlocs(), T0.vm.runtime.targets.filter(t => t.isOriginal).length - 1, inconnus.length ? inconnus.join(', ') : 'aucun');
  if (inconnus.length) echecs++;
  T0.drapeau(); T0.pas(60);
  if (T0.erreurs.length) { echecs++; console.log('ERREURS VM au démarrage :', T0.erreurs.slice(0, 5)); }
  T0.fin();
  for (const sc of scenarios) {
    const nom = path.basename(sc, '.js');
    const T = await charger(sb3);
    const verifs = [];
    const verifier = (libelle, condition, detail) => { total++; const ok = !!condition; if (!ok) echecs++; verifs.push((ok ? '  ✔ ' : '  ✘ ') + libelle + (ok || detail === undefined ? '' : '  → ' + JSON.stringify(detail))); };
    try {
      await require(path.resolve(sc))(T, verifier);
    } catch (e) { echecs++; verifs.push('  ✘ exception : ' + (e.stack || e)); }
    if (T.erreurs.length) { echecs++; verifs.push('  ✘ erreurs VM : ' + T.erreurs.slice(0, 3).join(' | ')); }
    T.fin();
    console.log('\n[%s]\n%s', nom, verifs.join('\n'));
  }
  console.log('\n%d vérifications, %d échec(s)', total, echecs);
  process.exit(echecs ? 1 : 0);
})().catch(e => { console.log('ERREUR', e); process.exit(1); });
