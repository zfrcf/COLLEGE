// Scénario scratch-vm (sans moteur audio) pour la démo de la banque de sons.
//   node outils/test_vm.js outils/demos/sons/demo.sb3 outils/demos/sons/test_sons.js
// Vérifie : 28 sons attachés (noms = contrat.SONS), aucun opcode inconnu, clone musique créé /
// supprimé selon `ecran`, volume et PAN des effets, clone « voix » au volume indépendant, arrêts.
const fs = require('fs');
const path = require('path');

module.exports = async (T, verifier) => {
  const contrat = JSON.parse(fs.readFileSync(path.join(__dirname, '..', '..', 'contrat.json'), 'utf8'));
  const S = T.sprite('Sons');
  const noms = S.sprite.sounds.map(s => s.name);
  verifier('28 sons attachés au sprite Sons', S.sprite.sounds.length === 28, S.sprite.sounds.length);
  verifier('noms des sons = contrat.SONS (même ordre)', JSON.stringify(noms) === JSON.stringify(contrat.sons), noms);
  verifier('tous en WAV, 22050 ou 11025 Hz, avec des échantillons',
    S.sprite.sounds.every(s => s.dataFormat === 'wav' && (s.rate === 22050 || s.rate === 11025) && s.sampleCount > 0));
  verifier('sprite Sons invisible', !S.visible);
  verifier('aucun opcode inconnu', T.opcodesInconnus().length === 0, T.opcodesInconnus());

  const roleClone = () => {
    const c = T.vm.runtime.targets.find(t => t.sprite === S.sprite && !t.isOriginal);
    return c ? Object.values(c.variables).find(v => v.name === 'son_role').value : null;
  };
  const diffuser = nom => T.diffuser(nom);     // vm_lib met le nom en majuscules (exigé par startHats)
  // Les blocs son (volume, effet, jouer jusqu'au bout) rendent une promesse résolue à l'image suivante :
  // il faut laisser tourner les micro-tâches entre deux images, comme le navigateur (T.pas est synchrone).
  const pas = async n => { for (let i = 0; i < n; i++) { T.vm.runtime._step(); await new Promise(r => setImmediate(r)); } };
  const pan = () => S.getCustomState('Scratch.sound').effects.pan;

  T.drapeau(); await pas(4);
  // le script de la démo tourne en temps réel (pan / volume toutes les 0,6 s) : on l'arrête pour piloter nous-mêmes
  T.vm.runtime.stopForTarget(T.sprite('Demo'));
  verifier('ecran = salon posé par la démo', T.g('ecran') === 'salon', T.g('ecran'));
  verifier('clone musique créé sur l\'écran salon', T.clones('Sons') === 1 && Number(T.l('Sons', 'son_musiqueActive')) === 1,
    [T.clones('Sons'), T.l('Sons', 'son_musiqueActive')]);
  verifier('le clone porte le rôle « musique »', roleClone() === 'musique', roleClone());
  verifier('l\'original garde son_estClone = 0 et son_role vide', Number(T.l('Sons', 'son_estClone')) === 0 && T.l('Sons', 'son_role') === '');

  T.set('ecran', 'jeu'); await pas(4);
  verifier('quitter le salon supprime le clone musique', T.clones('Sons') === 0 && Number(T.l('Sons', 'son_musiqueActive')) === 0,
    [T.clones('Sons'), T.l('Sons', 'son_musiqueActive')]);

  // effets : volume = param_volumeEffets (80) × son_volume / 100, PAN = son_pan
  T.set('son_volume', 50); T.set('son_pan', 30); diffuser('son clic'); await pas(4);
  verifier('volume effet = 80 × 50 / 100 = 40', Number(S.volume) === 40, S.volume);
  verifier('effet PAN = son_pan (30) et mémorisé', pan() === 30 && Number(T.l('Sons', 'son_dernierPan')) === 30, [pan(), T.l('Sons', 'son_dernierPan')]);
  T.set('son_pan', -15); diffuser('son tir_pistolet'); await pas(4);
  verifier('nouveau pan appliqué (-15)', pan() === -15 && Number(T.l('Sons', 'son_dernierPan')) === -15, [pan(), T.l('Sons', 'son_dernierPan')]);

  // voix : clone éphémère avec volume = param_volumeVoix (80) × son_volume / 100 et pan propre
  T.set('son_volume', 100); T.set('son_pan', -40); diffuser('son compte'); await pas(1);
  verifier('niveau transmis au clone voix = 80', Number(T.l('Sons', 'son_niveauClone')) === 80, T.l('Sons', 'son_niveauClone'));
  verifier('pan transmis au clone voix = -40', Number(T.l('Sons', 'son_panClone')) === -40, T.l('Sons', 'son_panClone'));
  verifier('l\'original ne garde ni rôle ni marque de clone', T.l('Sons', 'son_role') === '' && Number(T.l('Sons', 'son_estClone')) === 0);
  verifier('volume de l\'original inchangé par la voix (40)', Number(S.volume) === 40, S.volume);
  verifier('pan de l\'original inchangé par la voix (-15)', pan() === -15, pan());
  await pas(3);
  verifier('le clone voix se supprime après lecture (sans audio : immédiatement)', T.clones('Sons') === 0, T.clones('Sons'));

  // musique : retour au salon, « son stop tout », « son stop musique »
  T.set('ecran', 'salon'); await pas(4);
  verifier('retour au salon : clone musique recréé', T.clones('Sons') === 1 && roleClone() === 'musique', [T.clones('Sons'), roleClone()]);
  diffuser('son stop tout'); await pas(4);
  verifier('« son stop tout » : la musique reprend d\'elle-même sur un écran musical', T.clones('Sons') === 1 && roleClone() === 'musique',
    [T.clones('Sons'), roleClone()]);
  diffuser('son stop musique'); await pas(4);
  verifier('« son stop musique » : clone supprimé, silence maintenu sur cet écran',
    T.clones('Sons') === 0 && Number(T.l('Sons', 'son_musiqueActive')) === 1, [T.clones('Sons'), T.l('Sons', 'son_musiqueActive')]);
  T.set('ecran', 'chargement'); await pas(3);
  verifier('… même en passant à un autre écran musical', T.clones('Sons') === 0, T.clones('Sons'));
  T.set('ecran', 'prepartie'); await pas(3); T.set('ecran', 'connexion'); await pas(4);
  verifier('… et reprend après un passage par un écran non musical', T.clones('Sons') === 1 && roleClone() === 'musique', T.clones('Sons'));
  verifier('aucune erreur VM', T.erreurs.length === 0, T.erreurs.slice(0, 3));
};
