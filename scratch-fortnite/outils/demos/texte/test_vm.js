// Vérifications scratch-vm (sans rendu) du moteur de texte.
//   node outils/demos/texte/test_vm.js [test.sb3]
const path = require('path');
const { charger } = require(path.join(__dirname, '..', '..', 'vm_lib'));

(async () => {
  const sb3 = process.argv[2] || path.join(__dirname, 'test.sb3');
  const T = await charger(sb3);
  let echecs = 0, total = 0;
  const verifier = (libelle, ok, detail) => { total++; if (!ok) echecs++; console.log((ok ? '  ✔ ' : '  ✘ ') + libelle + (ok ? '' : '  → ' + JSON.stringify(detail))); };
  verifier('aucun opcode inconnu', T.opcodesInconnus().length === 0, T.opcodesInconnus());
  T.drapeau(); T.pas(5);
  verifier('aucune erreur VM', T.erreurs.length === 0, T.erreurs);
  const s = T.sprite('Demo');
  const L = n => Object.values(s.variables).find(v => v.name === n).value;
  const costumes = s.getCostumes().map(c => c.name);
  const num = n => costumes.indexOf(n) + 1;
  const R = L('resultats').map(String);
  console.log('résultats :', JSON.stringify(R));
  verifier('costumes « vide », « autre » conservés en 1 et 2, sentinelle « g_ » en 3', costumes[0] === 'vide' && costumes[1] === 'autre' && costumes[2] === 'g_', costumes.slice(0, 4));
  verifier('txt_largeurs alignée sur les numéros de costumes (0 pour les 3 premiers, 25.65 pour g_A)',
    L('txt_largeurs')[0] === 0 && L('txt_largeurs')[1] === 0 && L('txt_largeurs')[2] === 0 && Math.abs(L('txt_largeurs')[num('g_A') - 1] - 25.65) < 0.01,
    L('txt_largeurs').slice(0, 5));
  verifier('1. largeur(Jouer, 20) ≈ 49.5', Math.abs(Number(R[0]) - 49.53) < 0.1, R[0]);
  verifier('2. caractère inconnu ignoré (2 glyphes)', R[1] === '2', R[1]);
  verifier('3. émoji 👍 → 1 glyphe, costume g_👍', R[2] === '1/' + num('g_👍'), [R[2], num('g_👍')]);
  verifier('4. A et a → costumes différents', R[3] === num('g_A') + '/' + num('g_a') && num('g_A') !== num('g_a'), [R[3], num('g_A'), num('g_a')]);
  verifier('5. espace → 0 et 0.3 × taille', R[4] === '0/12', R[4]);
  const [l6, d6, n6] = R[5].split('/');
  verifier('6. troncature : largeur ≤ 100 et dernier glyphe = « … »', Number(l6) <= 100 && Number(l6) > 60 && d6 === String(num('g_…')) && Number(n6) < 36, R[5]);
  verifier('7. pas de troncature si ça tient', R[6] === '5/' + num('g_t'), R[6]);
  verifier('8. 12.000000001 → 2 glyphes', R[7] === '2', R[7]);
  verifier('9. txt_k = 0.5 après ecrire 20 px, 4 entrées pour « Hé ! »', R[8] === '0.5/4', R[8]);
  verifier('10. texte vide → 0 glyphe, largeur 0', R[9] === '0/0', R[9]);
  const [l11, p11] = R[10].split('/');
  verifier('11. largeur Scratch = largeur Python (« Royale 3D — 12 € », 30)', Math.abs(Number(l11) - Number(p11)) < 0.01, R[10]);
  verifier('effets graphiques remis à zéro', Object.values(s.effects).every(v => v === 0), s.effects);
  verifier('procédures présentes : ecrire, largeur texte, ecrire tronque, ecrire nombre',
    ['ecrire', 'largeur texte', 'ecrire tronque', 'ecrire nombre'].every(n => Object.values(s.blocks._blocks).some(b => b.opcode === 'procedures_prototype' && b.mutation.proccode.startsWith(n + ' '))));
  T.fin();
  console.log('\n%d vérifications, %d échec(s)', total, echecs);
  process.exit(echecs ? 1 : 0);
})().catch(e => { console.log('ERREUR', e); process.exit(1); });
