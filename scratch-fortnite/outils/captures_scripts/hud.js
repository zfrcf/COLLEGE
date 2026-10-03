// Captures du HUD : on force l'écran « jeu » (comme jeu_base.js) avec adversaires et coéquipier,
// puis chaque état remarquable. Sorties : outils/captures/hud_*.png
// Les états figés (à terre, mort, coffre) mettent connecte = 0 pour geler la boucle du sprite Joueur.
module.exports = async (A) => {
  await A.attendre(1500);                      // chargement asynchrone des costumes SVG (≈ 500 ressources)
  await A.evaluer((vm, V) => { V('ecran').value = 'jeu'; V('etat').value = 1; V('connecte').value = 1; V('px').value = 16.5; V('py').value = 4.5; V('dir').value = 90; V('zoneX').value = 16.5; V('zoneY').value = 10.5; V('zoneR').value = 9; V('phase').value = 3; V('monEquipe').value = 1; V('mode').value = 2; });
  const contrat = require('../contrat.json');
  const pad = (v, n) => String(Math.max(0, Math.round(Number(v) || 0))).padStart(n, '0').slice(-n);
  const paquet = (o) => { let s = '1'; for (const [nom, l] of contrat.champs) { let v = o[nom] || 0; if (nom === 'x' || nom === 'y') v = v * 100; if (nom === 'nom') { s += String(v || '').padEnd(l, '0').slice(0, l); continue; } s += pad(v, l); } return s; };
  const now = await A.evaluer((vm, V) => Math.floor(Number(V('maintenant').value)));
  const p2 = paquet({ x: 15.5, y: 7.2, dir: 270, pv: 75, bouclier: 20, battement: now, etat: 1, nom: '1809111500000000', niveau: 12, skin: 3, equipe: 2 });
  const p3 = paquet({ x: 18.2, y: 6.5, dir: 270, pv: 60, bouclier: 35, battement: now, etat: 1, nom: '2605040000000000', niveau: 4, skin: 5, equipe: 1 });
  // les deux paquets à une image d'écart : Reseau ne décode de façon sûre qu'un nouveau paquet par image
  await A.evaluer((vm, V, L, arg) => { V('☁ J2').value = arg; }, p2);
  await A.attendre(150);
  await A.evaluer((vm, V, L, arg) => {
    V('☁ J3').value = arg[1];
    const st = vm.runtime.getTargetForStage();
    const Lv = n => Object.values(st.variables).find(v => v.name === n);
    const t = vm.runtime.ioDevices.clock.projectTimer();
    const fin = String(Math.round((t + 600) * 10)).padStart(6, '0');
    Lv('Pings').value = ['3' + '1650' + '0900' + '999999'];
    Lv('Inventaire').value = [1, 2, 3, 7, 9]; Lv('Quantites').value = [12, 5, 3, 5, 3]; Lv('Raretes').value = [1, 3, 5, 1, 2];
    Lv('Journal').value = ['riko a éliminé zed (Sniper)', 'Tu as mis à terre riko']; Lv('JournalFin').value = [t + 600, t + 600];
    Lv('Notifications').value = ['+ Fusil à pompe (Rare)', '📍 Place Brique']; Lv('NotificationsFin').value = [t + 600, t + 600];
    Lv('DegatsAffiches').value = ['045' + '2060' + '2020' + fin + '1'];
    Lv('Bruits').value = ['115' + fin + '1', '250' + fin + '2'];
    V('🛡 Bouclier').value = 50; V('surbouclier').value = 20; V('endurance').value = 60;
    V('munitions_legeres').value = 36; V('mat_bois').value = 120; V('mat_pierre').value = 45; V('mat_metal').value = 10; V('🧱 Matériaux').value = 175;
    V('vivants').value = 7; V('💀 Éliminations').value = 3; V('equipesVivantes').value = 4;
    V('tempsAvantZone').value = 42; V('tempsPartie').value = 125; V('slotActif').value = 1; V('armeNum').value = 1;
  }, [p2, p3]);
  await A.attendre(1200);
  await A.capture('hud_1_standard');

  // (2) hors zone + flèche de dégâts + rechargement (Joueur gelé pour que la tempête ne réécrive pas evt_angle)
  await A.evaluer((vm, V) => {
    const t = vm.runtime.ioDevices.clock.projectTimer();
    V('connecte').value = 0; V('zoneX').value = 28; V('zoneR').value = 6; V('zoneDegats').value = 5; V('horsZone').value = 1; V('❤ PV').value = 80;
    V('rechargeDebut').value = t; V('rechargeFin').value = t + 6;
    const st = vm.runtime.getTargetForStage(); const Lv = n => Object.values(st.variables).find(v => v.name === n);
    Lv('DegatsAffiches').value = []; Lv('Bruits').value = [];
  });
  await A.attendre(200);
  await A.evaluer((vm, V) => { V('evt_angle').value = 135; vm.runtime.startHats('event_whenbroadcastreceived', { BROADCAST_OPTION: 'EVT DEGATS' }); });
  await A.attendre(250);
  await A.capture('hud_2_tempete_recharge');

  // (3) à terre avec réanimation en cours (Joueur gelé : connecte = 0)
  await A.evaluer((vm, V) => { V('zoneX').value = 16.5; V('zoneR').value = 9; V('horsZone').value = 0; V('rechargeFin').value = 0; V('etat').value = 3; V('❤ PV').value = 0; V('pvAterre').value = 62; V('reanimationProgres').value = 2; V('message').value = ''; });
  await A.attendre(500);
  await A.capture('hud_3_aterre');

  // (4) mort en Rumble
  await A.evaluer((vm, V) => { const t = vm.runtime.ioDevices.clock.projectTimer(); V('etat').value = 2; V('mode').value = 5; V('monEquipe').value = 0; V('respawnT').value = t + 4; V('message').value = ''; });
  await A.attendre(500);
  await A.capture('hud_4_mort_rumble');

  // (5) interaction coffre
  await A.evaluer((vm, V) => { const t = vm.runtime.ioDevices.clock.projectTimer(); V('etat').value = 1; V('mode').value = 2; V('monEquipe').value = 1; V('interactionType').value = 1; V('interactionDebut').value = t - 0.5; V('interactionDuree').value = 60; });
  await A.attendre(500);
  await A.capture('hud_5_coffre');

  // (6) tailleHUD 120 + daltonisme 1 + FPS + infos réseau
  await A.evaluer((vm, V) => { V('interactionType').value = 0; V('param_tailleHUD').value = 120; V('param_daltonisme').value = 1; V('param_afficherFPS').value = 1; V('param_afficherPing').value = 1; V('param_infosReseau').value = 1; V('latence').value = 48; });
  await A.attendre(1500);
  await A.capture('hud_6_grand_daltonisme');

  // (7) spectateur
  await A.evaluer((vm, V) => { V('connecte').value = 1; V('param_tailleHUD').value = 100; V('param_daltonisme').value = 0; V('param_afficherFPS').value = 0; V('param_afficherPing').value = 0; V('param_infosReseau').value = 0; V('ecran').value = 'spectateur'; V('etat').value = 4; V('spectSlot').value = 2; });
  await A.attendre(500);
  await A.capture('hud_7_spectateur');

  // (8) altimètre en parachute (fond vide si Partie n'est pas là)
  await A.evaluer((vm, V) => { V('ecran').value = 'parachute'; V('etat').value = 7; V('altitude').value = 50; });
  await A.attendre(400);
  await A.capture('hud_8_parachute');
  await A.evaluer((vm, V) => { V('altitude').value = 22; });
  await A.attendre(300);
  await A.capture('hud_8b_parachute_planeur');

  // (9) pré-partie invulnérable, anglais, HUD à 80 %, mode construction (pierre), pioche équipée, sous-titre,
  //     coéquipier mort (carte ramassée) + coéquipier en l'air, soin en cours (Joueur gelé)
  const now2 = await A.evaluer((vm, V) => Math.floor(Number(V('maintenant').value)));
  const p2b = paquet({ x: 15.5, y: 7.2, dir: 270, pv: 0, battement: now2, etat: 2, nom: '1809111500000000', niveau: 12, equipe: 1 });
  const p3b = paquet({ x: 18.2, y: 6.5, dir: 270, pv: 100, bouclier: 50, battement: now2, etat: 1, nom: '2605040000000000', niveau: 4, equipe: 1, altitude: 40 });
  await A.evaluer((vm, V, L, arg) => {
    V('☁ J2').value = arg[0]; V('☁ J3').value = arg[1];
    const t = vm.runtime.ioDevices.clock.projectTimer();
    const st = vm.runtime.getTargetForStage(); const Lv = n => Object.values(st.variables).find(v => v.name === n);
    Lv('CartesRamassees').value = [2];
    V('ecran').value = 'prepartie'; V('etat').value = 8; V('connecte').value = 0; V('monSlot').value = 1; V('invulnerable').value = 1;
    V('phase').value = 0; V('tempsPhase').value = 12; V('altitude').value = 0; V('horsZone').value = 0;
    V('param_langue').value = 1; V('param_tailleHUD').value = 80; V('param_sousTitres').value = 1;
    V('modeConstruction').value = 1; V('materiauActif').value = 2; V('armeNum').value = 11; V('slotActif').value = 1;
    V('utilisationFin').value = t + 60; V('utilisationDebut').value = t - 2; V('utilisationObjet').value = 8;
    V('❤ PV').value = 100; V('surbouclier').value = 0; V('endurance').value = 100;
  }, [p2b, p3b]);
  // sous-titre armé directement (diffuser « evt tir » déclenche la synthèse sonore de Sons : plusieurs secondes ici)
  await A.evaluer((vm) => { const H = vm.runtime.getSpriteTargetByName('HUD'); H.lookupVariableByNameAndType('sousTitre').value = '[Gunshot]'; H.lookupVariableByNameAndType('sousTitreFin').value = vm.runtime.ioDevices.clock.projectTimer() + 60; });
  await A.attendre(400);
  await A.capture('hud_9_prepartie_en_80_construction');

  // (10) mort en Duo, redéployé par zed ; fusil à pompe tenu avec munitions infinies (LTM 4) ; HUD 100 %
  const now3 = await A.evaluer((vm, V) => Math.floor(Number(V('maintenant').value)));   // battement < 15 s
  const p3c = paquet({ x: 18.2, y: 6.5, dir: 270, pv: 100, battement: now3, etat: 1, nom: '2605040000000000', niveau: 4, equipe: 1, reanime: 1 });
  await A.evaluer((vm, V, L, arg) => {
    V('☁ J3').value = arg;
    V('ecran').value = 'jeu'; V('etat').value = 2; V('invulnerable').value = 0; V('phase').value = 3; V('tempsAvantZone').value = 42;
    V('param_langue').value = 0; V('param_tailleHUD').value = 100; V('param_sousTitres').value = 0;
    V('modeConstruction').value = 0; V('materiauActif').value = 1; V('armeNum').value = 2; V('slotActif').value = 2; V('ltm').value = 4;
    V('utilisationFin').value = 0; V('mode').value = 2; V('monEquipe').value = 1; V('❤ PV').value = 0;
  }, p3c);
  await A.attendre(400);
  await A.capture('hud_10_mort_duo_infini');

  // (11) consommable tenu (bandages ×5, code 7) + réanimation de zed en cours + soin : les deux barres du centre ; HUD 120 %
  await A.evaluer((vm, V) => {
    const t = vm.runtime.ioDevices.clock.projectTimer();
    V('etat').value = 1; V('ltm').value = 0; V('armeNum').value = 7; V('slotActif').value = 4; V('❤ PV').value = 55; V('param_tailleHUD').value = 120;
    V('interactionType').value = 2; V('interactionCible').value = 3; V('interactionDebut').value = t - 1; V('interactionDuree').value = 60;
    V('utilisationFin').value = t + 60; V('utilisationDebut').value = t - 1; V('utilisationObjet').value = 7;
  });
  await A.attendre(400);
  await A.capture('hud_11_consommable_reanimation_120');
};
