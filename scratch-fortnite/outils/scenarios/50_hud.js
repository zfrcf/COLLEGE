// Scénario : sprite HUD (interface en jeu). On force l'écran « jeu » et des données riches
// (journal, notifications, chiffres de dégâts, bruits, inventaire, interaction…), on vérifie que
// la boucle reste légère, que fps / hud_glyphes sont écrits et qu'aucun écran ne lève d'erreur.
const { chargeurPaquets } = require('../vm_lib');
module.exports = async (T, verifier) => {
  const Pq = chargeurPaquets();
  const now = () => Math.floor(Number(T.g('maintenant')));
  const chrono = () => T.vm.runtime.ioDevices.clock.projectTimer();
  const paquet = (o) => Pq.paquet(Object.assign({ pv: 100, battement: now(), etat: 1, niveau: 7 }, o));
  T.pseudo('antoine'); T.souris(0, 0, false); T.drapeau(); T.pas(8);
  verifier('sprite HUD présent et caché', !T.visible('HUD'), T.visible('HUD'));

  // --- hors des écrans de jeu : rien n'est dessiné -------------------------------------------
  T.set('ecran', 'salon'); T.set('hud_glyphes', 0); T.pas(3);
  verifier('aucun glyphe sur l’écran salon', Number(T.g('hud_glyphes')) === 0, T.g('hud_glyphes'));

  // --- écran jeu avec données riches ---------------------------------------------------------
  T.set('ecran', 'jeu'); T.set('etat', 1); T.set('connecte', 1); T.set('px', 16.5); T.set('py', 4.5); T.set('dir', 90);
  T.set('zoneX', 16.5); T.set('zoneY', 10.5); T.set('zoneR', 9); T.set('phase', 3); T.set('tempsAvantZone', 42); T.set('tempsPartie', 125);
  T.set('mode', 2); T.set('monEquipe', 1); T.set('🛡 Bouclier', 50); T.set('surbouclier', 20); T.set('endurance', 60);
  T.set('vivants', 7); T.set('💀 Éliminations', 3); T.set('equipesVivantes', 4);
  T.set('☁ J2', paquet({ x: 15.5, y: 7.2, dir: 270, pv: 75, bouclier: 20, nom: Pq.codeNom('riko'), equipe: 2 }));
  T.set('☁ J3', paquet({ x: 18.2, y: 6.5, dir: 270, pv: 60, nom: Pq.codeNom('zed'), equipe: 1, etat: 3, knockPar: 2 }));
  T.pas(3);
  const fin = Math.round((chrono() + 60) * 10);
  const Lset = (nom, vals) => { const v = Object.values(T.stage.variables).find(x => x.name === nom); v.value = vals; };
  Lset('Inventaire', [1, 2, 3, 4, 6]); Lset('Quantites', [12, 5, 3, 5, 3]);
  Lset('Journal', ['riko a éliminé zed (Sniper)', 'Tu as mis à terre riko']); Lset('JournalFin', [chrono() + 60, chrono() + 60]);
  Lset('Notifications', ['+ Fusil à pompe', '📍 Place Brique']); Lset('NotificationsFin', [chrono() + 60, chrono() + 60]);
  Lset('DegatsAffiches', ['045' + '2100' + '2010' + String(fin).padStart(6, '0') + '0', '095' + '1950' + '2030' + String(fin).padStart(6, '0') + '1']);
  Lset('Bruits', ['045' + String(fin).padStart(6, '0') + '1', '300' + String(fin).padStart(6, '0') + '2']);
  Lset('Pings', ['3' + '1650' + '0900' + '999999']);
  // budget de glyphes en configuration standard (journal, notifications, dégâts, bruits, équipe, inventaire)
  T.pas(3);
  const g0 = Number(T.g('hud_glyphes'));
  verifier('glyphes tamponnés par image ≤ 250 (HUD standard)', g0 > 0 && g0 <= 250, g0);
  verifier('facteur d’échelle s = 1 (tailleHUD 100)', Number(T.l('HUD', 's')) === 1, T.l('HUD', 's'));
  // tout en même temps : interaction, soin, rechargement, tempête, sous-titres, FPS, ping, infos réseau
  T.set('interactionType', 1); T.set('interactionDebut', chrono() - 0.5); T.set('interactionDuree', 1.2);
  T.set('utilisationFin', chrono() + 3); T.set('utilisationDebut', chrono()); T.set('utilisationObjet', 4);
  T.set('rechargeFin', chrono() + 1.5); T.set('rechargeDebut', chrono());
  T.set('horsZone', 1); T.set('param_sousTitres', 1); T.set('param_afficherFPS', 1); T.set('param_afficherPing', 1); T.set('param_infosReseau', 1);
  // flèche de dégâts
  T.set('evt_angle', 135); T.diffuser('evt degats'); T.pas(2);
  verifier('flèche de dégâts mémorisée (angle 135, chrono de fin)', Number(T.l('HUD', 'angleDeg')) === 135 && Number(T.l('HUD', 'degatsFin')) > chrono(), [T.l('HUD', 'angleDeg'), T.l('HUD', 'degatsFin')]);
  verifier('sous-titre « [Dégâts] » armé', /Dégâts/.test(String(T.l('HUD', 'sousTitre'))) && Number(T.l('HUD', 'sousTitreFin')) > chrono(), T.l('HUD', 'sousTitre'));
  T.diffuser('evt tir'); T.pas(1);
  verifier('sous-titre « [Coup de feu] »', /Coup de feu/.test(String(T.l('HUD', 'sousTitre'))), T.l('HUD', 'sousTitre'));
  // boucle : temps moyen d'un pas
  const t0 = Date.now(); T.pas(30); const moyen = (Date.now() - t0) / 30;
  verifier('temps moyen d’un pas < 60 ms (écran jeu, tout affiché)', moyen < 60, moyen.toFixed(1) + ' ms');
  const g = Number(T.g('hud_glyphes'));
  verifier('glyphes ≤ 330 même avec toutes les options de débogage', g > g0 && g <= 330, g);
  // fps : attendre > 1 s réelle pour une mesure
  T.set('fps', 0); const t1 = Date.now(); while (Date.now() - t1 < 1300) T.pas(1);
  verifier('fps mesuré et écrit (> 0)', Number(T.g('fps')) > 0, T.g('fps'));

  // --- autres états / écrans : aucune erreur, HUD toujours actif ----------------------------------
  T.set('etat', 3); T.set('pvAterre', 62); T.set('reanimationProgres', 2); T.pas(3);
  verifier('à terre : HUD dessiné', Number(T.g('hud_glyphes')) > 0, T.g('hud_glyphes'));
  T.set('etat', 2); T.set('mode', 5); T.set('respawnT', chrono() + 4); T.pas(3);
  verifier('mort (Rumble) : HUD dessiné', Number(T.g('hud_glyphes')) > 0, T.g('hud_glyphes'));
  T.set('mode', 2); T.set('☁ J3', paquet({ x: 18.2, y: 6.5, dir: 270, pv: 60, nom: Pq.codeNom('zed'), equipe: 1, reanime: 1 })); T.pas(3);
  verifier('mort (Duo) redéployé par zed : HUD dessiné', Number(T.g('hud_glyphes')) > 0, T.g('hud_glyphes'));
  T.set('etat', 1); T.set('param_tailleHUD', 120); T.set('param_daltonisme', 1); T.pas(3);
  verifier('tailleHUD 120 : s = 1.2 et palette daltonisme (équipe bleue)', Math.abs(Number(T.l('HUD', 's')) - 1.2) < 1e-9 && T.l('HUD', 'cEquipe') === 'bleu', [T.l('HUD', 's'), T.l('HUD', 'cEquipe')]);
  T.set('param_tailleHUD', 100); T.set('param_daltonisme', 0);
  T.set('ecran', 'spectateur'); T.set('spectSlot', 2); T.pas(3);
  verifier('spectateur : HUD dessiné (bandeau)', Number(T.g('hud_glyphes')) > 0, T.g('hud_glyphes'));
  T.set('ecran', 'pause'); T.pas(3);
  verifier('pause : HUD dessiné sous le menu', Number(T.g('hud_glyphes')) > 0, T.g('hud_glyphes'));
  T.set('ecran', 'parachute'); T.set('altitude', 50); T.set('hud_glyphes', 0); T.pas(3);
  verifier('parachute : seul l’altimètre (≤ 30 glyphes)', Number(T.g('hud_glyphes')) > 0 && Number(T.g('hud_glyphes')) <= 30, T.g('hud_glyphes'));
  T.set('altitude', 22); T.pas(2);
  verifier('parachute sous 30 : icône de planeur tamponnée en dernier', T.costume('HUD') === 'hud_planeur' && Number(T.g('hud_glyphes')) <= 30, [T.costume('HUD'), T.g('hud_glyphes')]);
  T.set('altitude', 50); T.pas(2);
  verifier('parachute au-dessus de 30 : pas d’icône de planeur', T.costume('HUD') !== 'hud_planeur', T.costume('HUD'));
  T.set('ecran', 'prepartie'); T.set('etat', 8); T.set('invulnerable', 1); T.set('phase', 0); T.set('tempsPhase', 12); T.pas(3);
  verifier('pré-partie : HUD dessiné', Number(T.g('hud_glyphes')) > 0, T.g('hud_glyphes'));
  T.set('param_langue', 1); T.pas(2);
  verifier('langue anglaise : pas d’erreur', Number(T.g('hud_glyphes')) > 0, T.g('hud_glyphes'));
  T.set('param_langue', 0);
  T.set('ecran', 'fin'); T.set('hud_glyphes', 0); T.pas(2);
  verifier('écran fin : rien', Number(T.g('hud_glyphes')) === 0, T.g('hud_glyphes'));
};
