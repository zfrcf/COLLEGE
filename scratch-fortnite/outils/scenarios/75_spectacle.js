// Scénario : module Spectacle (royale/mod_spectacle.py) + musique dynamique (royale/sons.py).
//   node test_vm.js ../"Royale 3D.sb3" scenarios/75_spectacle.js
// Vérifie : la bannière « TRIPLE ÉLIMINATION ! » apparaît quand serie = 3 et « evt elimination » est diffusé, puis
// disparaît après ~2 s ; RAMPAGE à 5 éliminations ; pas de bannière pour serie = 1 ; annonces DERNIÈRE ZONE /
// LA TEMPÊTE AVANCE / IL RESTE 3 JOUEURS / NIVEAU N ; feux d'artifice (spc_particules) seulement sur l'écran fin
// (victoire : fusées + confettis ≤ 150 opérations ; défaite : pluie) ; clones du salon créés puis cachés hors salon ;
// musique_combat (son_musiqueJeu = 1, clone « combat ») quand un ennemi est à moins de 12 cases, hystérésis,
// musique_tempete (2) hors zone, retour au silence puis à la musique du salon.
const { chargeurPaquets } = require('../vm_lib');
module.exports = async (T, verifier) => {
  const Pq = chargeurPaquets();
  const now = () => Math.floor(Number(T.g('maintenant')));
  const chrono = () => T.vm.runtime.ioDevices.clock.projectTimer();
  const paquet = (o) => Pq.paquet(Object.assign({ pv: 100, battement: now(), etat: 1, niveau: 7 }, o));
  const loc = (n) => T.l('Spectacle', n);
  // les blocs son/volume rendent une promesse résolue à l'image suivante : laisser tourner les micro-tâches entre deux images
  const pas = async (n) => { for (let i = 0; i < n; i++) { T.vm.runtime._step(); await new Promise(r => setImmediate(r)); } };
  const attendre = async (ms) => { const t0 = Date.now(); while (Date.now() - t0 < ms) await pas(1); };
  const Sons = T.sprite('Sons');
  const clonesSons = () => T.vm.runtime.targets.filter(t => t.sprite === Sons.sprite && !t.isOriginal);
  const roles = () => clonesSons().map(c => Object.values(c.variables).find(v => v.name === 'son_role').value);
  const clonesSpectacle = () => T.vm.runtime.targets.filter(t => t.sprite === T.sprite('Spectacle').sprite && !t.isOriginal);

  T.pseudo('antoine'); T.souris(0, 0, false); T.drapeau(); await pas(8);
  verifier('sprite Spectacle présent et caché', !T.visible('Spectacle'), T.visible('Spectacle'));
  verifier('aucun opcode inconnu', T.opcodesInconnus().length === 0, T.opcodesInconnus());
  verifier('hors de l’écran fin : spc_particules = 0, aucune bannière', Number(T.g('spc_particules')) === 0 && T.g('spc_banniere') === '', [T.g('spc_particules'), T.g('spc_banniere')]);

  // --- bannière de série ----------------------------------------------------------------------
  T.set('ecran', 'jeu'); T.set('etat', 1); T.set('enPartie', 1); T.set('connecte', 0); T.set('superposition', '');
  T.set('px', 16.5); T.set('py', 4.5); T.set('dir', 90); T.set('monSlot', 1);
  T.set('serie', 3); T.set('serieFin', chrono() + 8); T.set('💀 Éliminations', 3);
  await pas(2);
  T.diffuser('evt elimination'); await pas(2);
  verifier('serie = 3 + evt elimination → bannière « TRIPLE ÉLIMINATION ! »', /TRIPLE/.test(String(T.g('spc_banniere'))) && /TRIPLE/.test(String(loc('banTexte'))), [T.g('spc_banniere'), loc('banTexte')]);
  verifier('… en or, départ daté', loc('banCouleur') === 'or' && Number(loc('banDebut')) > 0, [loc('banCouleur'), loc('banDebut')]);
  verifier('… « TÊTE DE SÉRIE » en file (3 éliminations, personne devant)', T.sprite('Spectacle').lookupVariableByNameAndType('file', 'list').value.some(t => /TÊTE DE SÉRIE/.test(t)), T.sprite('Spectacle').lookupVariableByNameAndType('file', 'list').value);
  await attendre(2200);
  verifier('la bannière TRIPLE a disparu après ~2 s (la suivante de la file a pris le relais)', !/TRIPLE/.test(String(T.g('spc_banniere'))), T.g('spc_banniere'));
  await attendre(2200);
  verifier('plus aucune bannière après la file (teteSerie = 1, une seule fois par manche)', T.g('spc_banniere') === '' && Number(loc('teteSerie')) === 1, [T.g('spc_banniere'), loc('teteSerie')]);
  T.set('serie', 1); T.diffuser('evt elimination'); await pas(2);
  verifier('serie = 1 : pas de bannière', T.g('spc_banniere') === '' && loc('banTexte') === '', [T.g('spc_banniere'), loc('banTexte')]);
  T.set('serie', 2); T.set('💀 Éliminations', 5); T.diffuser('evt elimination'); await pas(2);
  verifier('serie = 2 et 5 éliminations : DOUBLE puis RAMPAGE en file', /DOUBLE/.test(String(T.g('spc_banniere'))) && T.sprite('Spectacle').lookupVariableByNameAndType('file', 'list').value.some(t => /RAMPAGE/.test(t)), [T.g('spc_banniere'), T.sprite('Spectacle').lookupVariableByNameAndType('file', 'list').value]);
  // en anglais la bannière suivante est traduite
  T.set('param_langue', 1); T.set('serie', 5); T.set('💀 Éliminations', 7); T.diffuser('evt elimination'); await pas(2);
  verifier('EN : « MONSTROUS! » en file', T.sprite('Spectacle').lookupVariableByNameAndType('file', 'list').value.some(t => /MONSTROUS/.test(t)), T.sprite('Spectacle').lookupVariableByNameAndType('file', 'list').value);
  T.set('param_langue', 0);
  T.diffuser('evt nouvelle manche'); await pas(2);
  verifier('evt nouvelle manche : files vidées, bannière effacée', T.g('spc_banniere') === '' && T.sprite('Spectacle').lookupVariableByNameAndType('file', 'list').value.length === 0, T.g('spc_banniere'));

  // --- annonces -------------------------------------------------------------------------------
  T.set('evt_valeur', 6); T.diffuser('evt phase'); await pas(2);
  verifier('evt phase 6 → annonce « DERNIÈRE ZONE »', /DERNIÈRE ZONE/.test(String(loc('annTexte'))), loc('annTexte'));
  T.set('evt_valeur', 4); T.diffuser('evt phase'); await pas(2);
  verifier('evt phase 4 → « LA TEMPÊTE AVANCE » en file', T.sprite('Spectacle').lookupVariableByNameAndType('fileA', 'list').value.some(t => /TEMPÊTE AVANCE/.test(t)), T.sprite('Spectacle').lookupVariableByNameAndType('fileA', 'list').value);
  T.set('evt_valeur', 2); T.diffuser('evt phase'); await pas(2);
  verifier('evt phase 2 : rien de plus (une seule entrée en file)', T.sprite('Spectacle').lookupVariableByNameAndType('fileA', 'list').value.length === 1, T.sprite('Spectacle').lookupVariableByNameAndType('fileA', 'list').value);
  T.set('phase', 3); T.set('finManche', 0); T.set('vivants', 5); await pas(2); T.set('vivants', 3); await pas(2);
  verifier('vivants 5 → 3 : « IL RESTE 3 JOUEURS » en file', T.sprite('Spectacle').lookupVariableByNameAndType('fileA', 'list').value.some(t => /IL RESTE 3 JOUEURS/.test(t)), T.sprite('Spectacle').lookupVariableByNameAndType('fileA', 'list').value);
  T.set('niveau', 13); T.diffuser('evt niveau'); await pas(2);
  const fileA = T.sprite('Spectacle').lookupVariableByNameAndType('fileA', 'list').value;
  verifier('evt niveau → « NIVEAU 13 » en file avec étoiles', fileA.some(t => /NIVEAU 13/.test(t)) && T.sprite('Spectacle').lookupVariableByNameAndType('fileAE', 'list').value.includes('1'), [fileA, T.sprite('Spectacle').lookupVariableByNameAndType('fileAE', 'list').value]);
  // ~2,6 s par annonce : l'annonce courante change bien
  await attendre(2800);
  verifier('après 2,8 s l’annonce suivante est affichée (TEMPÊTE AVANCE)', /TEMPÊTE AVANCE/.test(String(loc('annTexte'))), loc('annTexte'));
  T.diffuser('evt fin manche'); await pas(2);
  verifier('evt fin manche : annonces vidées', loc('annTexte') === '' && T.sprite('Spectacle').lookupVariableByNameAndType('fileA', 'list').value.length === 0, loc('annTexte'));
  // boucle légère en jeu
  const t0 = Date.now(); await pas(30); const moyen = (Date.now() - t0) / 30;
  verifier('temps moyen d’un pas < 60 ms (écran jeu)', moyen < 60, moyen.toFixed(1) + ' ms');

  // --- feux d'artifice : seulement sur l'écran fin -----------------------------------------------
  await pas(2);
  verifier('écran jeu : spc_particules = 0', Number(T.g('spc_particules')) === 0, T.g('spc_particules'));
  T.set('ecran', 'fin'); T.set('victoire', 1); T.set('etat', 9); await pas(3);
  await attendre(1200); await pas(1);
  const p1 = Number(T.g('spc_particules'));
  verifier('écran fin + victoire : feux d’artifice et confettis (spc_particules > 24)', p1 > 24, p1);
  let max = 0; for (let n = 0; n < 40; n++) { await attendre(40); max = Math.max(max, Number(T.g('spc_particules'))); }
  verifier('≤ 150 opérations stylo par image (maximum observé sur 1,6 s)', max <= 150 && max >= 24, max);
  const fx = T.sprite('Spectacle').lookupVariableByNameAndType('fx', 'list').value;
  verifier('5 fusées dans la scène (x ∈ [−175, 175])', fx.length === 5 && fx.every(x => Math.abs(Number(x)) <= 175), fx);
  T.set('victoire', 0); await pas(3);
  verifier('écran fin + défaite : pluie grise (spc_particules = 30)', Number(T.g('spc_particules')) === 30, T.g('spc_particules'));
  T.set('ecran', 'jeu'); T.set('etat', 1); await pas(3);
  verifier('retour en jeu : plus de particules', Number(T.g('spc_particules')) === 0, T.g('spc_particules'));

  // --- salon : clones visibles ---------------------------------------------------------------------
  T.set('ecran', 'salon'); T.set('etat', 5); T.set('enPartie', 0); T.set('onglet', 'accueil'); await pas(4);
  verifier('salon : 20 clones Spectacle (12 bordure + 6 éclats + 2 halos)', clonesSpectacle().length === 20, clonesSpectacle().length);
  verifier('… tous visibles sur l’onglet accueil', clonesSpectacle().every(c => c.visible), clonesSpectacle().filter(c => !c.visible).length);
  const halo = clonesSpectacle().find(c => Object.values(c.variables).find(v => v.name === 'role').value === 'haloJouer');
  verifier('halo JOUER centré sur le bouton (55, −161), costume spc_halo_jouer', halo && Math.round(halo.x) === 55 && Math.round(halo.y) === -161 && halo.getCostumes()[halo.currentCostume].name === 'spc_halo_jouer', halo && [halo.x, halo.y]);
  const bord = clonesSpectacle().filter(c => Object.values(c.variables).find(v => v.name === 'role').value === 'bordure');
  verifier('éclats de bordure sur le bord de l’écran (|x| = 238 ou |y| = 178), jamais au centre', bord.length === 12 && bord.every(c => Math.abs(Math.abs(c.x) - 238) < 1 || Math.abs(Math.abs(c.y) - 178) < 1), bord.map(c => [Math.round(c.x), Math.round(c.y)]));
  T.set('onglet', 'passe'); await pas(3);
  verifier('onglet passe : éclats du personnage et halo du personnage cachés, halo JOUER visible', clonesSpectacle().filter(c => c.visible).length === 13, clonesSpectacle().filter(c => c.visible).length);
  T.set('ecran', 'jeu'); T.set('etat', 1); await pas(3);
  verifier('hors salon : clones conservés mais tous cachés', clonesSpectacle().length === 20 && clonesSpectacle().every(c => !c.visible), clonesSpectacle().filter(c => c.visible).length);

  // --- musique dynamique (sprite Sons) ---------------------------------------------------------------
  // enPartie = 0 : Partie ne touche pas à etat ; connecte = 1 : Joueur calcule horsZone depuis la zone (et Reseau décode)
  T.set('ecran', 'jeu'); T.set('etat', 1); T.set('connecte', 1); T.set('enPartie', 0); T.set('invulnerable', 1); T.set('monEquipe', 0);
  T.set('px', 16.5); T.set('py', 4.5); T.set('zoneX', 16.5); T.set('zoneY', 4.5); T.set('zoneR', 9); T.set('horsZone', 0); await pas(4);
  verifier('en jeu sans ennemi proche : son_musiqueJeu = 0, aucun clone musique', Number(T.g('son_musiqueJeu')) === 0 && roles().length === 0 && Number(T.g('etat')) === 1, [T.g('son_musiqueJeu'), roles(), T.g('etat')]);
  T.set('☁ J2', paquet({ x: 16.5, y: 9.0, dir: 270, nom: Pq.codeNom('riko') })); await pas(6);
  verifier('ennemi à 4,5 cases → musique_combat (son_musiqueJeu = 1, clone « combat »)', Number(T.g('son_musiqueJeu')) === 1 && roles().includes('combat'), [T.g('son_musiqueJeu'), roles(), T.L('E_actif')]);
  T.set('☁ J2', paquet({ x: 30.5, y: 30.5, dir: 270, nom: Pq.codeNom('riko') })); await pas(6);
  verifier('ennemi parti (26 cases) : la musique de combat tient (hystérésis 6 s)', Number(T.g('son_musiqueJeu')) === 1 && roles().includes('combat') && Number(T.l('Sons', 'son_combatFin')) > chrono(), [T.g('son_musiqueJeu'), T.L('E_x'), T.l('Sons', 'son_combatFin') - chrono()]);
  Sons.lookupVariableByNameAndType('son_combatFin').value = chrono() - 1;      // les 6 s sont écoulées
  await pas(4);
  verifier('hystérésis écoulée : silence (son_musiqueJeu = 0, clone supprimé)', Number(T.g('son_musiqueJeu')) === 0 && roles().length === 0, [T.g('son_musiqueJeu'), roles()]);
  T.set('zoneX', 30); T.set('zoneY', 30); T.set('zoneR', 2); await pas(4);
  verifier('hors zone → musique_tempete (son_musiqueJeu = 2, clone « tempete »)', Number(T.g('horsZone')) === 1 && Number(T.g('son_musiqueJeu')) === 2 && roles().includes('tempete') && !roles().includes('combat'), [T.g('horsZone'), T.g('son_musiqueJeu'), roles()]);
  T.set('☁ J2', paquet({ x: 16.5, y: 9.0, dir: 270, nom: Pq.codeNom('riko'), seq: 1 })); await pas(6);
  verifier('ennemi proche ET hors zone : la tempête est prioritaire', Number(T.g('son_musiqueJeu')) === 2 && roles().length === 1, [T.g('son_musiqueJeu'), roles()]);
  T.set('zoneX', 16.5); T.set('zoneY', 4.5); T.set('zoneR', 9); await pas(4);
  verifier('retour dans la zone avec l’ennemi proche → combat', Number(T.g('horsZone')) === 0 && Number(T.g('son_musiqueJeu')) === 1 && roles().includes('combat') && !roles().includes('tempete'), [T.g('son_musiqueJeu'), roles()]);
  T.set('param_volumeMusique', 35); await pas(5);
  verifier('param_volumeMusique suivi par le clone combat (35)', clonesSons().some(c => Number(c.volume) === 35), clonesSons().map(c => c.volume));
  T.set('param_volumeMusique', 50);
  T.set('etat', 2); await pas(4);
  verifier('mort (etat 2) : plus de musique de combat', Number(T.g('son_musiqueJeu')) === 0 && roles().length === 0, [T.g('son_musiqueJeu'), roles()]);
  T.set('etat', 1); await pas(4);
  T.set('ecran', 'salon'); T.set('etat', 5); await pas(5);
  verifier('retour au salon : musique de combat arrêtée, musique du salon seule', Number(T.g('son_musiqueJeu')) === 0 && roles().length === 1 && roles()[0] === 'musique', [T.g('son_musiqueJeu'), roles()]);
  // sons supplémentaires : diffusions sans erreur
  const nbErreurs = T.erreurs.length;
  for (const s of ['explosion', 'serie', 'largage']) { T.diffuser('son ' + s); await pas(2); }
  verifier('« son explosion / serie / largage » diffusés sans erreur', T.erreurs.length === nbErreurs, T.erreurs.slice(nbErreurs));
  verifier('aucune erreur VM', T.erreurs.length === 0, T.erreurs.slice(0, 3));
};
