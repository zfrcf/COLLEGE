// Captures du contenu façon Fortnite : HUD avec un inventaire des 5 raretés (fusil d'assaut, PM, lance-grenades,
// potion, mini-potion), largage de ravitaillement en descente, lama à butin. Sorties : outils/captures/contenu_*.png
// Comme hud.js : écran « jeu » forcé, Joueur actif (connecte = 1), enPartie = 0 (Partie laisse l'état forcé).
module.exports = async (A) => {
  await A.attendre(1500);                      // chargement asynchrone des costumes SVG
  await A.evaluer((vm, V) => {
    const st = vm.runtime.getTargetForStage();
    const Lv = n => Object.values(st.variables).find(v => v.name === n);
    const t = vm.runtime.ioDevices.clock.projectTimer();
    V('ecran').value = 'jeu'; V('etat').value = 1; V('connecte').value = 1; V('px').value = 16.5; V('py').value = 4.5; V('dir').value = 90;
    V('zoneX').value = 16.5; V('zoneY').value = 16.5; V('zoneR').value = 14; V('phase').value = 2; V('tempsAvantZone').value = 0; V('tempsPhase').value = 25;
    V('prochaineZoneX').value = 16.5; V('prochaineZoneY').value = 16.5; V('prochaineZoneR').value = 9;
    V('mode').value = 5; V('monEquipe').value = 0; V('🛡 Bouclier').value = 75; V('surbouclier').value = 10; V('vivants').value = 5; V('💀 Éliminations').value = 2;
    // inventaire : 5 cases, une par rareté (commune → légendaire)
    Lv('Inventaire').value = [4, 5, 6, 10, 9]; Lv('Quantites').value = [30, 25, 4, 2, 3]; Lv('Raretes').value = [1, 2, 3, 4, 5];
    V('slotActif').value = 1; V('armeNum').value = 4; V('armeTenue').value = 4; V('munitions_moyennes').value = 60;
    V('mat_bois').value = 240; V('mat_pierre').value = 120; V('mat_metal').value = 80; V('🧱 Matériaux').value = 440;
    // (le sprite Largages ajoute lui-même « Largage en cours » : phase 2, tempsAvantZone 0)
    Lv('Notifications').value = ['+ Fusil d\'assaut (Épique)']; Lv('NotificationsFin').value = [t + 600];
  });
  await A.attendre(2500);                      // le HUD attend le chargement de ses glyphes et icônes
  await A.capture('contenu_1_inventaire_raretes');

  // (2) largage en descente, 4 cases devant moi (altitude 12 : largage_debut reculé de 8 s), marqueur bleu sur la minicarte
  await A.evaluer((vm, V) => {
    const t = vm.runtime.ioDevices.clock.projectTimer();
    V('largage_num').value = 1; V('largage_phase').value = 2; V('largage_x').value = 16.5; V('largage_y').value = 8.5 - 1;
    V('largage_debut').value = t - 8; V('largage_alt').value = 12; V('message').value = 'largage';
    V('slotActif').value = 2; V('armeNum').value = 5; V('armeTenue').value = 5; V('munitions_legeres').value = 48;
  });
  await A.attendre(700);
  await A.capture('contenu_2_largage_descente');

  // (3) largage posé devant moi : interaction « Ouvrir le largage » (touche E maintenue), lance-grenades légendaire en main
  await A.evaluer((vm, V) => {
    const t = vm.runtime.ioDevices.clock.projectTimer();
    V('largage_debut').value = t - 30; V('message').value = '';
    V('slotActif').value = 3; V('armeNum').value = 6; V('armeTenue').value = 6; V('munitions_roquettes').value = 6;
    const st = vm.runtime.getTargetForStage(); const Lv = n => Object.values(st.variables).find(v => v.name === n);
    Lv('Raretes').value = [1, 2, 5, 4, 5];
    V('px').value = 16.5; V('py').value = 6.6;
  });
  await A.attendre(300);
  await A.evaluer((vm) => vm.postIOData('keyboard', { key: 'e', isDown: true }));
  await A.attendre(900);
  await A.capture('contenu_3_largage_ouverture');
  await A.evaluer((vm) => vm.postIOData('keyboard', { key: 'e', isDown: false }));

  // (4) lama à butin à 2,5 cases devant moi, déjà touché 2 fois (bulle « 2/5 »), pioche en main
  await A.evaluer((vm, V) => {
    const t = vm.runtime.ioDevices.clock.projectTimer();
    const st = vm.runtime.getTargetForStage(); const Lv = n => Object.values(st.variables).find(v => v.name === n);
    Lv('LargagesPris').value = [1]; Lv('Notifications').value = []; Lv('NotificationsFin').value = [];
    V('px').value = 16.5; V('py').value = 4.5; V('lama_x').value = 16.5; V('lama_y').value = 7.5; V('lama_coups').value = 2; V('lama_touche').value = t;
    Lv('LamasPris').value = [];
    V('slotActif').value = 1; V('armeNum').value = 11; V('armeTenue').value = 0;
    vm.runtime.getSpriteTargetByName('Joueur').lookupVariableByNameAndType('pioches').value = 1;
  });
  await A.attendre(700);
  await A.capture('contenu_4_lama');
};
