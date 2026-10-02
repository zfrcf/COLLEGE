// Captures du module Social : barre sociale (salon), chat rapide, roues d'émotes et de sprays,
// écran spectateur, caméra libre, panneau de signalement, émote en cours.
//   node capture.js captures_scripts/social.js      → outils/captures/social_*.png
module.exports = async (A) => {
  const contrat = require('../contrat.json');
  const pad = (v, n) => String(Math.max(0, Math.round(Number(v) || 0))).padStart(n, '0').slice(-n);
  const paquet = (o) => { let s = '1'; for (const [nom, l] of contrat.champs) { let v = o[nom] || 0; if (nom === 'x' || nom === 'y') v = v * 100; if (nom === 'nom') { s += String(v || '').padEnd(l, '0').slice(0, l); continue; } s += pad(v, l); } return s; };
  const codeNom = (t) => { let s = ''; for (let i = 0; i < 8; i++) { const k = contrat.alphabet.indexOf((t[i] || '').toLowerCase()); s += pad(k >= 0 ? k + 1 : 0, 2); } return s; };
  await A.attendre(900);
  const now = await A.evaluer((vm, V) => Math.floor(Number(V('maintenant').value)));
  const chrono = () => A.evaluer((vm) => vm.runtime.ioDevices.clock.projectTimer());
  // mode Solo : Partie (s'il est présent) relance une manche à partir de modeChoisi quand ☁ Partie est vide
  await A.evaluer((vm, V) => { V('modeChoisi').value = 1; V('☁ Partie').value = ''; });
  await A.attendre(600);
  await A.evaluer((vm, V) => { V('mode').value = 1; });
  // paquets des 3 joueurs simulés ; le battement est repris à chaque appel (un emplacement expire après 15 s)
  const joueurs = async (etats) => { const now = await A.evaluer((vm, V) => Math.floor(Number(V('maintenant').value))); await A.evaluer((vm, V, L, arg) => {
    V('☁ J2').value = arg[0]; V('☁ J3').value = arg[1]; V('☁ J4').value = arg[2];
  }, [
    paquet({ x: 15.5, y: 7.2, dir: 270, pv: 75, bouclier: 20, battement: now, etat: etats[0], nom: codeNom('riko'), niveau: 12, skin: 3 }),
    paquet({ x: 18.2, y: 6.5, dir: 200, pv: 100, battement: now, etat: etats[1], nom: codeNom('zed'), niveau: 4, skin: 5 }),
    paquet({ x: 25.0, y: 25.0, dir: 0, pv: 100, battement: now, etat: etats[2], nom: codeNom('nina_longnom'), niveau: 133, skin: 2 }),
  ]); };

  // ---------- (1) salon : barre sociale, 3 joueurs (états variés), un masqué ----------
  await A.evaluer((vm, V, L) => { V('ecran').value = 'salon'; V('etat').value = 5; V('niveau').value = 9; V('codeSalon').value = 0; V('superposition').value = ''; });
  await joueurs([5, 1, 6]);
  await A.evaluer((vm, V) => { V('Muets').value = ['3']; });
  await A.attendre(400);
  await A.evaluer((vm, V) => { V('menu_rafraichi').value = 1; });
  await A.attendre(250);
  await A.evaluer((vm, V) => { V('menu_rafraichi').value = 0; });
  await A.attendre(200);
  await A.capture('social_salon');
  // survol du bouton « … » de la 1re ligne puis menu ouvert
  await A.souris(226, 85, false); await A.attendre(200);
  await A.evaluer((vm, V) => { V('menu_rafraichi').value = 1; }); await A.attendre(150);
  await A.evaluer((vm, V) => { V('menu_rafraichi').value = 0; });
  await A.clic(226, 85); await A.attendre(150);
  await A.evaluer((vm, V) => { V('menu_rafraichi').value = 1; }); await A.attendre(150);
  await A.evaluer((vm, V) => { V('menu_rafraichi').value = 0; }); await A.attendre(150);
  await A.capture('social_salon_menu');
  // fermer le menu, puis « Pseudo Epic »
  await A.clic(50, 0); await A.attendre(100);
  await A.clic(192, -139); await A.attendre(150);
  await A.evaluer((vm, V) => { V('menu_rafraichi').value = 1; }); await A.attendre(150);
  await A.evaluer((vm, V) => { V('menu_rafraichi').value = 0; }); await A.attendre(150);
  await A.capture('social_salon_pseudo');
  await A.souris(0, 0, false);

  // ---------- (2) en jeu : chat ouvert avec 2 messages reçus ----------
  await A.evaluer((vm, V) => { V('ecran').value = 'jeu'; V('etat').value = 1; V('px').value = 16.5; V('py').value = 4.5; V('dir').value = 90; V('zoneX').value = 16.5; V('zoneY').value = 10.5; V('zoneR').value = 9; V('phase').value = 2; V('Muets').value = []; V('infoMode') && 0; });
  await joueurs([1, 3, 1]);
  const t0 = await chrono();
  await A.evaluer((vm, V, L, arg) => { V('Chat').value = ['riko : Salut !', 'zed : Par ici', 'nina_longnom : Besoin de soins']; V('ChatFin').value = [arg + 30, arg + 30, arg + 30]; V('Pings').value = ['2' + '1650' + '0900' + '999999']; }, t0);
  await A.attendre(400);
  await A.capture('social_jeu_zone_chat');
  await A.touche('t', true); await A.attendre(80); await A.touche('t', false);
  await A.souris(-72, 20, false);         // survol de la 2e phrase
  await A.attendre(400);
  await A.capture('social_chat');
  await A.touche('t', true); await A.attendre(80); await A.touche('t', false); await A.attendre(150);

  // ---------- (3) roue d'émotes ----------
  await A.touche('y', true); await A.attendre(80); await A.touche('y', false);
  await A.souris(54, 41, false);          // survol du secteur 2
  await A.attendre(400);
  await A.capture('social_emotes');
  await A.clic(54, 41); await A.attendre(500);
  await A.souris(0, 0, false);
  await A.capture('social_emote_en_cours');

  // ---------- (4) roue de sprays ----------
  await A.touche('h', true); await A.attendre(80); await A.touche('h', false);
  await A.souris(0, 72, false);
  await A.attendre(400);
  await A.capture('social_sprays');
  await A.clic(0, 72); await A.attendre(400);
  await A.souris(0, 0, false);
  await A.capture('social_spray_pose');

  // ---------- (7) panneau de signalement (ouvert comme depuis la pause) ----------
  await A.evaluer((vm, V) => { V('soc_cible').value = 0; V('superposition').value = 'signaler'; });
  await A.souris(0, 42, false);
  await A.attendre(400);
  await A.capture('social_signaler');
  await A.clic(0, 42); await A.attendre(200); await A.souris(0, 0, false); await A.attendre(100);
  await A.capture('social_signaler_raison');
  await A.clic(0, 26); await A.attendre(300);
  await A.capture('social_signaler_confirme');
  await A.clic(0, -75); await A.attendre(200);

  // ---------- (5) spectateur après la mort (Solo) ----------
  await A.evaluer((vm, V) => { V('Muets').value = []; V('etat').value = 2; V('mortX').value = 16.5; V('mortY').value = 4.5; });
  await joueurs([1, 1, 1]);
  await A.attendre(3800);
  await A.capture('social_spectateur');
  // pause depuis le spectateur (le passage automatique ne se refait pas), puis « Signaler un joueur » depuis la pause
  // (bouton de Menus en (0, −16) ; Social revient sur l'écran spectateur sous-jacent le temps du panneau)
  await A.touche('p', true); await A.attendre(80); await A.touche('p', false); await A.attendre(500);
  await A.capture('social_spectateur_pause');
  await A.clic(0, -16); await A.attendre(500);
  await A.souris(0, 42, false); await A.attendre(300);
  await A.capture('social_signaler_depuis_pause');
  await A.clic(0, -75); await A.attendre(400);                               // Fermer → retour à la pause
  await A.touche('p', true); await A.attendre(80); await A.touche('p', false); await A.attendre(300);   // reprendre

  // ---------- (6) caméra libre ----------
  await A.evaluer((vm, V) => { V('ecran').value = 'cinema'; V('px').value = 16.5; V('py').value = 4.5; V('dir').value = 90; V('menu_sale').value = 1; });
  await A.touche(' ', true); await A.attendre(400); await A.touche(' ', false);
  await A.attendre(300);
  await A.capture('social_cinema');
  await A.evaluer((vm, V) => { V('ecran').value = 'jeu'; });
};
