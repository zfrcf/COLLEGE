// Vérification adversariale scratch-vm (sans rendu) du moteur de texte.
//   node outils/demos/texte/verif_logique.js [verif_logique.sb3]
const path = require('path');
const { charger } = require(path.join(__dirname, '..', '..', 'vm_lib'));

(async () => {
  const sb3 = process.argv[2] || path.join(__dirname, 'verif_logique.sb3');
  const T = await charger(sb3);
  let echecs = 0, total = 0;
  const verifier = (libelle, ok, detail) => { total++; if (!ok) echecs++; console.log((ok ? '  ✔ ' : '  ✘ ') + libelle + (ok ? '' : '  → ' + JSON.stringify(detail))); };
  const proche = (a, b, eps = 0.01) => Math.abs(Number(a) - b) < eps;
  verifier('aucun opcode inconnu', T.opcodesInconnus().length === 0, T.opcodesInconnus());
  T.drapeau(); T.pas(5);
  verifier('aucune erreur VM', T.erreurs.length === 0, T.erreurs);
  const s = T.sprite('Demo');
  const L = n => Object.values(s.variables).find(v => v.name === n).value;
  const costumes = s.getCostumes().map(c => c.name);
  const num = n => costumes.indexOf(n) + 1;
  const R = L('resultats').map(String);
  console.log('résultats :', JSON.stringify(R));
  let i = 0;
  const suivant = () => R[i++];
  verifier('1. ecrire nombre −42 → 3 glyphes, le premier g_-', suivant() === '3/' + num('g_-'), R[i - 1]);
  verifier('2. ecrire nombre −0.4 → « 0 » (1 glyphe g_0)', suivant() === '1/' + num('g_0'), R[i - 1]);
  verifier('3. ecrire nombre « abc » → 1 glyphe', suivant() === '1', R[i - 1]);
  let p = suivant().split('/');
  verifier('4. « ❤️ 100 » : U+FE0F ignoré sans avaler l’espace → 5 entrées, 2e = espace, largeur 109.29', p[0] === '5' && p[1] === '0' && proche(p[2], 109.29), p);
  p = suivant().split('/');
  verifier('5. espace insécable = espace → 3 entrées, largeur 58.82', p[0] === '3' && p[1] === '0' && proche(p[2], 58.82), p);
  verifier('6. « ﬁn » : ligature ignorée, « n » conservé', suivant() === '1/' + num('g_n'), R[i - 1]);
  verifier('7a. couleur « ROUGE » (majuscules) → index rouge (txt_n = 9)', suivant() === '9', R[i - 1]);
  verifier('7b. couleur inconnue → blanc (txt_n = 0)', suivant() === '0', R[i - 1]);
  verifier('7c. couleur vide → blanc (txt_n = 0)', suivant() === '0', R[i - 1]);
  verifier('8a. alignement 2 sur x = 100 : curseur final = 100', proche(suivant(), 100, 1e-6), R[i - 1]);
  p = suivant().split('/');
  verifier('8b. alignement 1 sur x = 0 : curseur final = largeur / 2', proche(p[0], Number(p[1]) / 2, 1e-6) && proche(p[1], 49.53), p);
  p = suivant().split('/');
  verifier('9a. taille 10 : largeur(Jouer) = 24.765, txt_k = 0.25', proche(p[0], 24.765, 1e-3) && p[1] === '0.25', p);
  p = suivant().split('/');
  verifier('9b. taille 60 : largeur(Jouer) = 148.59, txt_k = 1.5', proche(p[0], 148.59, 1e-3) && p[1] === '1.5', p);
  p = suivant().split('/');
  verifier('10. « ␣␣␣ » → 3 entrées à 0, largeur 36', p[0] === '3' && p[1] === '0' && proche(p[2], 36), p);
  verifier('11. troncature extrême (5 px) → « … » seul', suivant() === '1/' + num('g_…'), R[i - 1]);
  p = suivant().split('/');
  verifier('12. « ab cd ef gh » tronqué à 100 → a b … (pas d’espace avant …), largeur 78.58',
    p[0] === '3' && p[1] === String(num('g_…')) && p[2] === String(num('g_b')) && proche(p[3], 78.58), p);
  verifier('13. txt_espacement = 4 → « ab » = 54.82', proche(suivant(), 54.82), R[i - 1]);
  verifier('14. texte numérique 42 → 2 glyphes', suivant() === '2', R[i - 1]);
  verifier('15a. « ok 👍 » → 4 entrées, 4e = g_👍', suivant() === '4/' + num('g_👍'), R[i - 1]);
  verifier('15b. « 👍 ok » → 4 entrées, 1re = g_👍, 2e = espace', suivant() === '4/' + num('g_👍') + '/0', R[i - 1]);
  verifier('16. « Dès » → 2e glyphe = g_è', suivant() === String(num('g_è')), R[i - 1]);
  verifier('17. « 00 » → 2 glyphes g_0 (« 0 » n’est pas un espace)', suivant() === '2/' + num('g_0'), R[i - 1]);
  verifier('18. texte à x = 300 (hors scène) : le curseur avance de la largeur (344.43)', proche(suivant(), 344.43), R[i - 1]);
  p = suivant().split('/');
  verifier('19. largeur Scratch = largeur Python avec espaces insécables', proche(p[0], Number(p[1]), 0.01), p);
  verifier('effets graphiques remis à zéro', Object.values(s.effects).every(v => v === 0), s.effects);
  const a = T.sprite('Autre');
  const LA = n => Object.values(a.variables).find(v => v.name === n).value;
  const costumesA = a.getCostumes().map(c => c.name);
  const RA = LA('resultats').map(String);
  verifier('2e sprite : « Autre » → 5 glyphes, g_A = costume 3, largeur 52.24',
    RA[0] && RA[0].split('/')[0] === '5' && RA[0].split('/')[1] === String(costumesA.indexOf('g_A') + 1) && costumesA.indexOf('g_A') + 1 === 3 && proche(RA[0].split('/')[2], 52.24), [RA, costumesA.slice(0, 4)]);
  T.fin();
  console.log('\n%d vérifications, %d échec(s)', total, echecs);
  process.exit(echecs ? 1 : 0);
})().catch(e => { console.log('ERREUR', e); process.exit(1); });
