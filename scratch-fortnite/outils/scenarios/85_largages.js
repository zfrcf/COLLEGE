// Scénario : largages de ravitaillement et lama à butin (royale/mod_largages.py + ouverture dans Joueur).
// On force l'écran « jeu » et l'état « vivant » (Partie laisse un état forcé tranquille quand enPartie = 0) et on
// pilote la phase de jeu à la main : phase 2 en attente → début du rétrécissement → largage, descente, ouverture
// par la touche « interagir » maintenue 2,5 s ; phase 3 sans largage ; phase 4 → second largage recalé ; lama ouvert
// par 5 coups de pioche puis, après une nouvelle manche, par 5 tirs de pistolet.
module.exports = async (T, verifier) => {
  const n = (v) => Number(T.g(v));
  const chrono = () => T.vm.runtime.ioDevices.clock.projectTimer();
  const Lset = (nomL, vals) => { const v = Object.values(T.stage.variables).find(x => x.name === nomL); v.value = vals; };
  const inv = () => T.L('Inventaire').map(Number), rar = () => T.L('Raretes').map(Number), qte = () => T.L('Quantites').map(Number);
  const libre = (x, y) => Number(T.L('Carte')[Math.floor(y) * 32 + Math.floor(x)]) === 0;
  const attendre = (cond, ms) => { const t0 = Date.now(); while (!cond() && Date.now() - t0 < ms) T.pas(1); return cond(); };
  T.pseudo('antoine'); T.souris(0, 0, false); T.drapeau(); T.set('param_bots', 0); T.pas(8);
  verifier('connecté (emplacement 1)', n('monSlot') === 1 && n('connecte') === 1, [T.g('monSlot'), T.g('connecte')]);
  verifier('sprites Largages / Largage / Lama présents et cachés', !T.visible('Largages') && !T.visible('Largage') && !T.visible('Lama'));

  // ---- lama : position déterministe (graine) sur une case libre ------------------------------------------------
  verifier('lama placé sur une case libre de la carte', n('lama_x') > 1 && n('lama_y') > 1 && libre(n('lama_x'), n('lama_y')), [T.g('lama_x'), T.g('lama_y')]);
  T.set('graine', 42); T.diffuser('evt nouvelle manche'); T.pas(2);
  const lx = n('lama_x'), ly = n('lama_y');
  T.set('lama_x', 0); T.set('graine', 42); T.diffuser('evt nouvelle manche'); T.pas(2);
  verifier('position du lama déterministe pour la graine 42', n('lama_x') === lx && n('lama_y') === ly && lx % 1 === 0.5, [lx, ly, T.g('lama_x'), T.g('lama_y')]);

  // ---- en jeu, phase 2 en attente : pas de largage ------------------------------------------------------------
  T.set('ecran', 'jeu'); T.set('etat', 1); T.set('px', 16.5); T.set('py', 4.5); T.set('dir', 90); T.set('mode', 5); T.set('monEquipe', 0);
  T.set('zoneX', 16.5); T.set('zoneY', 16.5); T.set('zoneR', 30); T.set('prochaineZoneX', 16.5); T.set('prochaineZoneY', 16.5); T.set('prochaineZoneR', 14);
  T.set('phase', 2); T.set('tempsAvantZone', 20); T.set('tempsPhase', 20); T.pas(3);
  verifier('phase 2 en attente : aucun largage', n('largage_num') === 0, T.g('largage_num'));

  // ---- début du rétrécissement → largage n° 1 ---------------------------------------------------------------------
  T.set('tempsAvantZone', 0); T.set('tempsPhase', 30); T.pas(2);
  verifier('largage n° 1 lancé au début du rétrécissement de la phase 2', n('largage_num') === 1 && n('largage_phase') === 2, [T.g('largage_num'), T.g('largage_phase')]);
  const gx = n('largage_x'), gy = n('largage_y');
  verifier('point de chute dans la prochaine zone (≤ 0,7 R + 2), sur une case libre', Math.hypot(gx - 16.5, gy - 16.5) <= 14 * 0.7 + 2 && libre(gx, gy) && gx % 1 === 0.5, [gx, gy]);
  verifier('altitude initiale 20 (30 s de rétrécissement restantes)', n('largage_alt') > 19 && n('largage_alt') <= 20, T.g('largage_alt'));
  verifier('notification « Largage en cours »', T.L('Notifications').some(l => /Largage en cours/.test(l)), T.L('Notifications'));
  const a0 = n('largage_alt'); const t0 = Date.now(); while (Date.now() - t0 < 600) T.pas(1);
  verifier('le largage descend (1 unité par seconde)', n('largage_alt') < a0 - 0.4 && n('largage_alt') > a0 - 1.6, [a0, T.g('largage_alt')]);
  T.pas(5);
  verifier('un seul largage par phase', n('largage_num') === 1, T.g('largage_num'));
  // panneau 3D : à 3 cases devant moi (visible sauf si un mur s'interpose : Profondeur au centre < 3)
  T.set('px', gx); T.set('py', gy - 3); T.set('dir', 90); T.pas(3);
  const prof = Number(T.L('Profondeur')[Math.round(n('colonnes') / 2) - 1]);
  verifier('panneau « Largage » affiché devant moi (ou masqué par un mur)', T.visible('Largage') || prof < 3, [T.visible('Largage'), prof]);
  // en l'air : pas d'interaction
  T.set('px', gx + 0.9); T.set('py', gy); T.touche('e', true); T.pas(3);
  verifier('largage encore en l’air : pas d’interaction proposée', n('interactionType') === 0, T.g('interactionType'));
  T.touche('e', false); T.pas(1);

  // ---- posé → ouverture (interaction de type 4, 2,5 s) ----------------------------------------------------------
  T.set('largage_debut', chrono() - 25); T.pas(2);
  verifier('descente terminée : altitude 0', n('largage_alt') === 0, T.g('largage_alt'));
  Lset('Inventaire', [1, 0, 0, 0, 0]); Lset('Quantites', [12, 0, 0, 0, 0]); Lset('Raretes', [1, 1, 1, 1, 1]);
  T.set('mat_bois', 0); T.set('mat_pierre', 50); T.set('mat_metal', 450);
  T.touche('e', true); T.pas(3);
  verifier('interaction de type 4 (ouvrir le largage), durée 2,5 s', n('interactionType') === 4 && n('interactionDuree') === 2.5 && n('interactionCible') === 1, [T.g('interactionType'), T.g('interactionDuree'), T.g('interactionCible')]);
  attendre(() => T.L('LargagesPris').length > 0, 8000); T.touche('e', false); T.pas(2);
  verifier('largage ouvert après 2,5 s (LargagesPris = [1])', T.L('LargagesPris').map(Number).join() === '1', T.L('LargagesPris'));
  verifier('arme légendaire reçue en case 2 (sniper / fusil d’assaut / lance-grenades, rareté 5)', [3, 4, 6].includes(inv()[1]) && rar()[1] === 5, [inv(), rar()]);
  verifier('potion de bouclier + 100 de chaque matériau (plafond 500)', inv()[2] === 10 && n('mat_bois') === 100 && n('mat_pierre') === 150 && n('mat_metal') === 500, [inv(), T.g('mat_bois'), T.g('mat_pierre'), T.g('mat_metal')]);
  verifier('notification « Largage ouvert ! » et bannière « coffre »', T.L('Notifications').some(l => /Largage ouvert/.test(l)) && T.g('message') === 'coffre', [T.L('Notifications'), T.g('message')]);
  T.set('px', gx); T.set('py', gy - 3); T.pas(3);
  verifier('panneau « Largage » caché une fois ouvert', !T.visible('Largage'), T.visible('Largage'));
  verifier('plus d’interaction sur un largage ouvert', (() => { T.touche('e', true); T.pas(3); const r = n('interactionType') === 0; T.touche('e', false); T.pas(1); return r; })());

  // ---- phase 3 : rien ; phase 4 : largage n° 2 recalé sur le temps écoulé --------------------------------------------
  T.set('phase', 3); T.set('tempsAvantZone', 0); T.set('tempsPhase', 20); T.pas(3);
  verifier('phase 3 : pas de largage', n('largage_num') === 1, T.g('largage_num'));
  T.set('phase', 4); T.set('tempsPhase', 5); T.pas(2);
  verifier('phase 4 (zone 3) : largage n° 2 ; 20 s de rétrécissement dont 15 écoulées → altitude ≈ 5', n('largage_num') === 2 && n('largage_phase') === 4 && Math.abs(n('largage_alt') - 5) < 1, [T.g('largage_num'), T.g('largage_alt')]);
  verifier('nouveau point de chute (différent du premier)', n('largage_x') !== gx || n('largage_y') !== gy, [gx, gy, T.g('largage_x'), T.g('largage_y')]);

  // ---- lama : 5 coups de pioche ---------------------------------------------------------------------------------
  T.set('px', lx - 1); T.set('py', ly); T.set('dir', 0); T.pas(1);
  T.touche('f', true); T.pas(1); T.touche('f', false); T.pas(1);
  verifier('pioche équipée (armeNum 11)', n('armeNum') === 11, T.g('armeNum'));
  verifier('panneau « Lama » affiché à 1 case devant moi', T.visible('Lama'), T.visible('Lama'));
  const bois1 = n('mat_bois'), moy0 = n('munitions_moyennes');
  T.souris(0, 0, true); T.pas(2); T.souris(0, 0, false); T.pas(1);
  verifier('premier coup de pioche compté (lama_coups 1, chrono du coup)', n('lama_coups') === 1 && n('lama_touche') > 0, [T.g('lama_coups'), T.g('lama_touche')]);
  for (let i = 0; i < 400 && T.L('LamasPris').length === 0; i++) { T.souris(0, 0, true); T.pas(1); T.souris(0, 0, false); T.pas(1); }
  verifier('lama ouvert après 5 coups (LamasPris = [1])', T.L('LamasPris').map(Number).join() === '1' && n('lama_coups') >= 5, [T.L('LamasPris'), T.g('lama_coups')]);
  verifier('butin du lama : +200 bois, 3 potions, +30 munitions moyennes', n('mat_bois') === bois1 + 200 && inv().includes(10) && qte()[inv().indexOf(10)] === 3 && n('munitions_moyennes') === moy0 + 30, [T.g('mat_bois'), inv(), qte(), T.g('munitions_moyennes')]);
  verifier('notification « Lama à butin ouvert ! »', T.L('Notifications').some(l => /Lama à butin/.test(l)), T.L('Notifications'));
  T.pas(2);
  verifier('panneau « Lama » caché une fois ouvert', !T.visible('Lama'), T.visible('Lama'));

  // ---- nouvelle manche : lama remis, ouvert par 5 tirs de pistolet ------------------------------------------------
  T.set('phase', 0); T.set('tempsAvantZone', 0); T.set('graine', 7); T.diffuser('evt nouvelle manche'); T.pas(3);
  verifier('nouvelle manche : largages et lama remis à zéro', n('largage_num') === 0 && T.L('LargagesPris').length === 0 && T.L('LamasPris').length === 0 && n('lama_coups') === 0, [T.g('largage_num'), T.L('LamasPris'), T.g('lama_coups')]);
  T.set('ecran', 'jeu'); T.set('etat', 1); T.set('px', n('lama_x') - 2); T.set('py', n('lama_y')); T.set('dir', 0); T.appui('1', 1); T.pas(2);
  verifier('pistolet en main (12 balles)', n('armeNum') === 1 && qte()[0] === 12, [T.g('armeNum'), qte()]);
  for (let i = 0; i < 400 && T.L('LamasPris').length === 0; i++) { T.souris(0, 0, true); T.pas(1); T.souris(0, 0, false); T.pas(1); }
  verifier('5 tirs de pistolet ouvrent le lama (munitions consommées)', T.L('LamasPris').map(Number).join() === '1' && qte()[0] <= 7, [T.L('LamasPris'), T.g('lama_coups'), qte()]);
  verifier('aucune erreur VM', T.erreurs.length === 0, T.erreurs.slice(0, 3));
};
