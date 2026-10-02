// Scénario de VÉRIFICATION ADVERSARIALE du sprite Sons (scratch-vm, sans moteur audio).
//   node outils/test_vm.js outils/demos/sons/demo.sb3 outils/demos/sons/verif_sons.js
// Un faux « soundBank » journalise chaque départ de son avec le volume et le PAN de la cible À CET INSTANT
// (ce que le lecteur appliquerait) et fait durer « jouer jusqu'au bout » une image.
// Cas limites que test_sons.js ne couvre pas :
//  1. un clone « voix » émis avec son_pan = 0 après un effet panoramiqué doit JOUER à PAN 0
//     (scratch-vm copie l'état sonore de l'original vers le clone à la création) ;
//  2. le clone « musique » recréé après des effets panoramiqués doit jouer au centre (PAN 0) ;
//  3. un second « demarrer » pendant que la musique tourne ne doit laisser qu'UN clone musique,
//     et aucun clone ne doit se prendre pour l'original (son_estClone remis à 0 sur un clone) ;
//  4. « son musique_salon » pendant que la boucle tourne ne doit pas créer de second lecteur ;
//  5. valeurs hors bornes : son_volume négatif / vide, son_pan > 100 → pas d'erreur VM, volume et PAN bornés ;
//  6. diffusion d'un nom de son inconnu : rien ne se passe, pas d'erreur.
module.exports = async (T, verifier) => {
  const S = T.sprite('Sons');
  const clones = () => T.vm.runtime.targets.filter(t => t.sprite === S.sprite && !t.isOriginal);
  const locale = (t, n) => Object.values(t.variables).find(v => v.name === n).value;
  const panDe = t => t.getCustomState('Scratch.sound').effects.pan;
  const pas = async n => { for (let i = 0; i < n; i++) { T.vm.runtime._step(); await new Promise(r => setImmediate(r)); } };
  const diffuser = nom => T.diffuser(nom);

  // faux moteur audio : sans AudioEngine les sons n'ont pas de soundId, on leur donne leur nom
  S.sprite.sounds.forEach(x => { x.soundId = x.name; });
  const journal = [];
  S.sprite.soundBank = {
    playSound(cible, soundId) {
      journal.push({ son: soundId, cible: cible.isOriginal ? 'original' : 'clone ' + locale(cible, 'son_role'), volume: cible.volume, pan: panDe(cible) });
      return new Promise(r => setImmediate(r));     // « jusqu'au bout » dure une image
    },
    setEffects() {}, stop() {}, stopAllSounds() {}, dispose() {},
  };
  const departsDepuis = n => journal.slice(n);

  T.drapeau(); await pas(4);
  T.vm.runtime.stopForTarget(T.sprite('Demo'));          // la démo tourne en temps réel : on pilote nous-mêmes
  verifier('départ : clone musique présent sur « salon »', clones().length === 1 && locale(clones()[0], 'son_role') === 'musique');
  verifier('départ : musique_salon jouée par le clone à volume 50, PAN 0',
    journal.some(d => d.son === 'musique_salon' && d.cible === 'clone musique' && d.volume === 50 && d.pan === 0), journal);

  // --- 1. PAN hérité par un clone voix ---------------------------------------------------
  T.set('ecran', 'jeu'); await pas(4);
  let n0 = journal.length;
  T.set('son_volume', 100); T.set('son_pan', -70); diffuser('son tir_pompe'); await pas(4);
  verifier('effet tir_pompe : original, volume 80, PAN -70', JSON.stringify(departsDepuis(n0)) === JSON.stringify([{ son: 'tir_pompe', cible: 'original', volume: 80, pan: -70 }]), departsDepuis(n0));
  n0 = journal.length;
  T.set('son_pan', 0); diffuser('son compte'); await pas(1);
  verifier('clone voix créé pour « compte »', clones().some(c => locale(c, 'son_role') === 'compte'), clones().map(c => locale(c, 'son_role')));
  await pas(6);
  verifier('clone voix émis avec son_pan = 0 : joué à PAN 0 (et non le -70 hérité), volume 80, par le clone',
    JSON.stringify(departsDepuis(n0)) === JSON.stringify([{ son: 'compte', cible: 'clone compte', volume: 80, pan: 0 }]), departsDepuis(n0));
  verifier('l\'original garde PAN -70 et volume 80', panDe(S) === -70 && Number(S.volume) === 80, [panDe(S), S.volume]);
  verifier('clone voix disparu après lecture', clones().length === 0, clones().length);
  n0 = journal.length;
  T.set('son_pan', -70); diffuser('son compte'); await pas(7);
  verifier('clone voix émis avec le même PAN que l\'original (-70) : joué à -70 sans réglage inutile',
    JSON.stringify(departsDepuis(n0)) === JSON.stringify([{ son: 'compte', cible: 'clone compte', volume: 80, pan: -70 }]), departsDepuis(n0));

  // --- 2. PAN hérité par le clone musique ------------------------------------------------
  T.set('son_pan', 70); diffuser('son tir_pistolet'); await pas(3);
  verifier('effet : PAN de l\'original = 70', panDe(S) === 70, panDe(S));
  n0 = journal.length;
  T.set('ecran', 'salon'); await pas(5);
  const mus = clones().find(c => locale(c, 'son_role') === 'musique');
  verifier('retour au salon : clone musique recréé', !!mus);
  const dm = departsDepuis(n0).find(d => d.son === 'musique_salon');
  verifier('clone musique : joue à PAN 0 (musique au centre, pas le 70 du dernier coup de feu), volume 50',
    !!dm && dm.cible === 'clone musique' && dm.pan === 0 && dm.volume === 50, departsDepuis(n0));
  verifier('l\'original garde son PAN d\'effets (70)', panDe(S) === 70, panDe(S));

  // --- 3. second « demarrer » pendant la musique ------------------------------------------
  n0 = journal.length;
  diffuser('demarrer'); await pas(8);
  const roles = clones().map(c => locale(c, 'son_role') + '/estClone=' + locale(c, 'son_estClone'));
  verifier('second « demarrer » : exactement un clone musique', clones().length === 1 && roles[0] === 'musique/estClone=1', roles);
  verifier('aucun clone ne se prend pour l\'original (son_estClone = 1 partout)', clones().every(c => Number(locale(c, 'son_estClone')) === 1), roles);
  verifier('l\'original : son_estClone = 0, son_musiqueActive = 1', Number(locale(S, 'son_estClone')) === 0 && Number(locale(S, 'son_musiqueActive')) === 1,
    [locale(S, 'son_estClone'), locale(S, 'son_musiqueActive')]);
  await pas(10);
  verifier('… et toujours un seul clone 10 images plus tard (pas de cascade)', clones().length === 1, clones().length);
  verifier('PAN de l\'original remis à 0 par « demarrer », volume 100', panDe(S) === 0 && Number(S.volume) === 100, [panDe(S), S.volume]);
  verifier('la musique relancée joue au centre à 50', departsDepuis(n0).every(d => d.son === 'musique_salon' && d.cible === 'clone musique' && d.pan === 0 && d.volume === 50)
    && departsDepuis(n0).length >= 1, departsDepuis(n0).slice(0, 3));

  // --- 4. « son musique_salon » pendant la boucle ------------------------------------------
  n0 = journal.length;
  diffuser('son musique_salon'); await pas(4);
  verifier('« son musique_salon » pendant la boucle : aucun clone supplémentaire, un seul lecteur (le clone musique)',
    clones().length === 1 && departsDepuis(n0).every(d => d.cible === 'clone musique'), [clones().map(c => locale(c, 'son_role')), departsDepuis(n0)]);
  T.set('ecran', 'jeu'); await pas(4);
  verifier('écran « jeu » : plus aucun clone', clones().length === 0, clones().length);
  n0 = journal.length;
  diffuser('son musique_salon'); await pas(1);
  verifier('« son musique_salon » hors boucle : pris en charge par un clone « musique_salon »', clones().length === 1 && locale(clones()[0], 'son_role') === 'musique_salon',
    clones().map(c => locale(c, 'son_role')));
  await pas(6);
  verifier('… joué une fois comme un jingle (volume 50) puis clone supprimé',
    departsDepuis(n0).length === 1 && departsDepuis(n0)[0].cible === 'clone musique_salon' && departsDepuis(n0)[0].volume === 50 && clones().length === 0, departsDepuis(n0));

  // --- 5. valeurs hors bornes ----------------------------------------------------------------
  T.set('son_volume', -50); T.set('son_pan', 250); diffuser('son clic'); await pas(4);
  verifier('son_volume négatif : volume borné à 0', Number(S.volume) === 0, S.volume);
  verifier('son_pan 250 : PAN borné à 100', panDe(S) === 100, panDe(S));
  T.set('son_volume', ''); T.set('son_pan', ''); diffuser('son saut'); await pas(4);
  verifier('son_volume vide : volume 0, PAN vide → 0', Number(S.volume) === 0 && panDe(S) === 0, [S.volume, panDe(S)]);
  T.set('son_volume', 100); T.set('son_pan', 0); diffuser('son coffre'); await pas(4);
  verifier('retour à la normale : volume 80, PAN 0', Number(S.volume) === 80 && panDe(S) === 0, [S.volume, panDe(S)]);

  // --- 6. nom inconnu / arrêts à vide -------------------------------------------------------
  n0 = journal.length;
  diffuser('son inexistant'); diffuser('son stop musique'); diffuser('son stop tout'); await pas(4);
  verifier('nom inconnu et arrêts à vide : aucun clone, aucun départ, pas d\'erreur', clones().length === 0 && departsDepuis(n0).length === 0 && T.erreurs.length === 0,
    [departsDepuis(n0), T.erreurs.slice(0, 2)]);
  verifier('aucune erreur VM', T.erreurs.length === 0, T.erreurs.slice(0, 3));
};
