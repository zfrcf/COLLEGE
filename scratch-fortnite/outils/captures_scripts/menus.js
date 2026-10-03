// Captures des écrans du module Menus : connexion, salon × 7 onglets, sélecteur de mode, paramètres × 3,
// matchmaking, chargement, pause (sur fond 3D), fin victoire et fin défaite.
//   node capture.js captures_scripts/menus.js
const contrat = require('../contrat.json');
const pad = (v, n) => String(Math.max(0, Math.round(Number(v) || 0))).padStart(n, '0').slice(-n);
const paquet = (o) => { let s = '1'; for (const [nom, l] of contrat.champs) { let v = o[nom] || 0; if (nom === 'x' || nom === 'y') v = v * 100; if (nom === 'nom') { s += String(v || '').padEnd(l, '0').slice(0, l); continue; } s += pad(v, l); } return s; };
const codeNom = (t) => { let s = ''; for (let i = 0; i < 8; i++) { const k = contrat.alphabet.indexOf((t[i] || '').toLowerCase()); s += pad(k >= 0 ? k + 1 : 0, 2); } return s; };

module.exports = async (A) => {
  const mesurer = async (nom) => {           // tampons du sprite Menus par image (via renderer.penStamp)
    const r = await A.evaluer(async (vm) => {
      const menus = vm.runtime.getSpriteTargetByName('Menus'); const R = vm.runtime.renderer;
      let n = 0, pas = 0; const o1 = R.penStamp, o2 = vm.runtime._step;
      R.penStamp = function (skin, dr) { if (dr === menus.drawableID) n++; return o1.apply(this, arguments); };
      vm.runtime._step = function () { pas++; return o2.apply(this, arguments); };
      await new Promise(r => setTimeout(r, 1000));
      R.penStamp = o1; vm.runtime._step = o2;
      return [n, pas];
    });
    console.log('tampons Menus par image (' + nom + ') : ' + (r[0] / Math.max(1, r[1])).toFixed(0) + ' sur ' + r[1] + ' images');
  };
  const set = (obj) => A.evaluer((vm, V, L, arg) => { for (const k in arg) V(k).value = arg[k]; }, obj);
  const get = (nom) => A.evaluer((vm, V, L, arg) => V(arg).value, nom);
  const sale = () => set({ menu_sale: 1, message: '' });
  const local = (obj) => A.evaluer((vm, V, L, arg) => { const t = vm.runtime.getSpriteTargetByName('Menus'); for (const k in arg) Object.values(t.variables).find(v => v.name === k).value = arg[k]; }, obj);
  await A.attendre(1500);
  await A.capture('menus_connexion');

  // --- données simulées (listes vides si le module Systèmes ne les a pas remplies) ---
  const now = await A.evaluer((vm, V) => Math.floor(Number(V('maintenant').value)));
  await A.evaluer((vm, V, L, arg) => {
    const vide = (n) => !V(n).value || V(n).value.length === 0;
    if (vide('Boutique')) V('Boutique').value = ['skin|4|800', 'pioche|3|500', 'planeur|2|500', 'spray|5|200', 'emote|6|300', 'banniere|7|150'];
    if (vide('PasseRecompenses')) { const t = ['skin', 'pioche', 'planeur', 'spray', 'emote', 'banniere', 'jetons', 'style']; const l = []; for (let i = 1; i <= 100; i++) { const ty = i % 10 === 0 ? 'skin' : (i % 7 === 0 ? 'style' : t[i % t.length]); l.push(ty + '|' + (ty === 'jetons' ? 100 : 1 + (i % 6))); } V('PasseRecompenses').value = l; }
    if (vide('QuetesActives')) V('QuetesActives').value = ['1|1|3|5|0|200', '2|1|5|5|1|250', '3|1|2|2|2|150', '4|2|12|30|0|800', '5|2|4|10|0|600', '6|3|1|3|0|1000', '7|3|0|1|0|1500'];
    if (vide('QueteTitres')) V('QueteTitres').value = ['Élimine 5 adversaires', 'Ouvre 5 coffres', 'Survis 2 minutes', 'Inflige 30 dégâts au fusil', 'Construis 10 murs', 'Visite 3 lieux nommés', 'Gagne une partie', 'Eliminate 5 opponents', 'Open 5 chests', 'Survive 2 minutes', 'Deal 30 shotgun damage', 'Build 10 walls', 'Visit 3 named places', 'Win a match'];
    if (vide('Succes')) { const l = []; for (let i = 1; i <= 20; i++) l.push(i + '|' + (i <= 7 ? 1 : 0)); V('Succes').value = l; }
    if (vide('Possedes')) V('Possedes').value = ['skin|1', 'skin|2', 'skin|3', 'style|3', 'pioche|1', 'pioche|2', 'planeur|1', 'spray|1', 'spray|2', 'emote|1', 'emote|2', 'emote|3', 'banniere|1', 'banniere|2'];
    if (vide('RecapLignes')) V('RecapLignes').value = ['Éliminations ×3 : +150 XP', 'Survie 4:12 : +120 XP', 'Top 1 : +300 XP', 'Coffres ×4 : +40 XP'];
    V('Record_nom').value = ['riko', 'nina', 'zed']; V('Record_elims').value = [42, 31, 18]; V('Record_victoires').value = [5, 3, 1];
    V('jetons').value = 1250; V('niveau').value = 12; V('passeNiveau').value = 17; V('etoiles').value = 3; V('xpNiveau').value = 450; V('xpSuivant').value = 1000;
    V('hype').value = 320; V('division').value = 3; V('joursSaison').value = 41; V('bonusXP').value = 20; V('skin').value = 3; V('banniere').value = 2;
    V('stat_victoires').value = 4; V('stat_parties').value = 23; V('stat_elims').value = 37; V('stat_top3').value = 9; V('stat_meilleurRang').value = 1; V('stat_morts').value = 19;
    V('stat_degats').value = 1240; V('stat_coffres').value = 14; V('stat_tempsSurvie').value = 252; V('stat_materiaux').value = 310;
    V('codeSauvegarde').value = 'R3D-7F2A-9K1Q-ZX4M'; V('codeCreateur').value = 'LAMA42'; V('latence').value = 48;
  });
  await set({ '☁ J2': paquet({ x: 10, y: 10, pv: 100, battement: now, etat: 5, nom: codeNom('riko'), niveau: 15, elims: 9, skin: 2 }),
              '☁ J3': paquet({ x: 12, y: 12, pv: 100, battement: now, etat: 1, nom: codeNom('nina'), niveau: 8, elims: 3, skin: 4 }) });
  await A.attendre(300);

  // --- salon : clic sur CONTINUER puis chaque onglet ---
  await set({ connecte: 1 }); await sale(); await A.attendre(300);
  await A.clic(0, -44); await A.attendre(600);
  console.log('ecran après CONTINUER :', await get('ecran'));
  await set({ message: '' }); await A.attendre(300);      // la bannière « QUÊTE TERMINÉE » (Systemes) masquerait l'écran
  await A.capture('menus_salon_accueil');
  const onglets = [['passe', -126], ['boutique', -52], ['casier', 9], ['quetes', 64], ['carriere', 123], ['parametres', 196]];
  for (const [nom, x] of onglets) {
    await A.clic(x, 163); await A.attendre(400); await set({ message: '' }); await A.attendre(250);
    console.log('onglet :', await get('onglet'));
    await A.capture('menus_salon_' + nom);
  }
  // paramètres : sections Commandes et Vidéo
  await A.clic(-188, 98); await A.attendre(500); await A.capture('menus_parametres_commandes');
  await A.clic(-188, 70); await A.attendre(500); await A.capture('menus_parametres_video');
  await A.clic(-188, 42); await A.attendre(500); await A.capture('menus_parametres_audio');
  await A.clic(-188, -14); await A.attendre(500); await A.capture('menus_parametres_compte');
  // casier : catégorie émotes ; carrière : survol d'un badge ; quêtes : hebdo
  await A.clic(9, 163); await A.attendre(300); await A.clic(50, 129); await A.attendre(500); await A.capture('menus_casier_emotes');
  await A.clic(123, 163); await A.attendre(300); await A.souris(-64, -62, false); await A.attendre(500); await A.capture('menus_carriere_survol');
  // sélecteur de mode ouvert
  await A.clic(-202, 163); await A.attendre(300);
  await A.clic(55, -127); await A.attendre(500); await A.capture('menus_selecteur_mode');
  await A.clic(55, -8); await A.attendre(400);           // Trio
  console.log('modeChoisi :', await get('modeChoisi'));
  // survol du bouton JOUER (surlignage)
  await A.souris(55, -161, false); await A.attendre(500); await A.capture('menus_survol_jouer');
  // partie en cours : bouton Regarder
  const now2 = await A.evaluer((vm, V) => Math.floor(Number(V('maintenant').value)));
  await set({ '☁ Partie': '1' + pad(now2 - 70, 5) + '5' + '0' + '07' }); await A.attendre(400); await sale(); await A.attendre(500);
  console.log('phase/debut :', await get('phase'), await get('debut'));
  await A.capture('menus_salon_partie_en_cours');
  await set({ '☁ Partie': '0' }); await A.attendre(300);
  // --- matchmaking puis chargement ---
  await A.clic(55, -161); await A.attendre(300);
  console.log('ecran après JOUER :', await get('ecran'), 'enPartie', await get('enPartie'));
  const t0 = await A.evaluer((vm) => vm.runtime.ioDevices.clock.projectTimer());
  await set({ enPartie: 0, ecran: 'matchmaking', menu_sale: 1, message: '' }); await local({ tCompte: t0 + 4 });
  await A.attendre(900); await A.capture('menus_matchmaking'); await mesurer('matchmaking');
  await set({ ecran: 'chargement', message: '' }); await local({ tChargement: t0 + 1 });
  await A.attendre(600); await mesurer('chargement'); await A.capture('menus_chargement');
  // --- pause sur fond 3D ---
  await set({ ecran: 'jeu', etat: 1, px: 16.5, py: 4.5, dir: 90, zoneX: 16.5, zoneY: 10.5, zoneR: 9, phase: 2, enPartie: 1, superposition: '' });
  await A.attendre(600);
  await A.touche('p', true); await A.attendre(120); await A.touche('p', false); await A.attendre(300);
  await set({ message: '' }); await A.attendre(300);
  console.log('ecran après P :', await get('ecran'));
  await A.capture('menus_pause'); await mesurer('pause');
  await A.clic(0, 18); await A.attendre(600); await A.capture('menus_pause_parametres'); await mesurer('pause + paramètres');
  await A.clic(0, -135); await A.attendre(300);
  // --- signalement ouvert sur la pause : Social dessine son panneau, Menus seulement un voile autour ---
  await set({ ecran: 'jeu', superposition: 'signaler' }); await A.attendre(300);   // Social mémorise la superposition
  await set({ ecran: 'pause', ecranPrecedent: 'jeu', message: '' }); await A.attendre(600);
  console.log('ecran pause + signaler :', await get('ecran'), await get('superposition'));
  await A.capture('menus_pause_signaler');
  await set({ superposition: '' }); await A.attendre(300);
  // --- fin : victoire puis défaite (lignes de récapitulatif garanties) ---
  await A.evaluer((vm, V) => { if (!V('RecapLignes').value.length) V('RecapLignes').value = ['Éliminations ×3 : +150 XP', 'Survie 4:12 : +120 XP', 'Top 1 : +300 XP', 'Coffres ×4 : +40 XP']; });
  await set({ ecran: 'fin', victoire: 1, rang: 1, participants: 6, '💀 Éliminations': 3, xpGagne: 610, mode: 6, menu_sale: 1 });
  await A.attendre(700); await A.capture('menus_fin_victoire'); await mesurer('fin victoire');
  await set({ victoire: 0, rang: 4, mode: 1 });
  await A.attendre(500); await A.capture('menus_fin_defaite');
  // --- signalement ouvert dans le salon (depuis le menu « … » d'un ami) : Menus ignore les clics sous le panneau ---
  await set({ ecran: 'salon', onglet: 'parametres', etat: 5, enPartie: 0, menu_sale: 1 }); await A.attendre(500);
  await set({ superposition: 'signaler' }); await A.attendre(600);
  const ct0 = await get('param_constructionTurbo');
  await A.clic(110, 80); await A.attendre(400);
  console.log('clic sous le panneau de signalement : Construction turbo', ct0, '→', await get('param_constructionTurbo'));
  await A.capture('menus_salon_signaler');
  await set({ superposition: '' }); await A.attendre(300);
  // --- anglais ---
  await set({ ecran: 'salon', onglet: 'accueil', param_langue: 1, menu_sale: 1 });
  await A.attendre(700); await A.capture('menus_salon_en'); await mesurer('salon au repos');
  await A.clic(-126, 163); await A.attendre(500); await A.capture('menus_salon_passe_en');
  await A.clic(9, 163); await A.attendre(500); await A.capture('menus_salon_casier_en');
  await A.clic(64, 163); await A.attendre(500); await A.capture('menus_salon_quetes_en');
  await A.clic(123, 163); await A.attendre(300); await A.clic(60, 129); await A.attendre(500); await A.capture('menus_carriere_classement_en');
  await A.clic(196, 163); await A.attendre(300); await A.clic(-188, 98); await A.attendre(500); await A.capture('menus_parametres_commandes_en');
  await A.clic(-188, -14); await A.attendre(500); await A.capture('menus_parametres_compte_en');
  await set({ ecran: 'connexion', menu_sale: 1, message: '' }); await A.attendre(600); await A.capture('menus_connexion_en');
  // entrée tardive : une partie est en cours (☁ Partie commencée il y a 70 s → phase 2, calculée par Partie)
  const now3 = await A.evaluer((vm, V) => Math.floor(Number(V('maintenant').value)));
  await set({ '☁ Partie': '1' + pad(now3 - 70, 5) + '5' + '0' + '07' }); await A.attendre(400);
  await set({ ecran: 'matchmaking', menu_sale: 1 }); await local({ tCompte: 1e9 }); await A.attendre(600);
  console.log('phase (entrée tardive) :', await get('phase'));
  await A.capture('menus_matchmaking_tardif_en');
  await set({ '☁ Partie': '0' }); await A.attendre(300);
  await set({ ecran: 'jeu', etat: 2, phase: 2, superposition: '' }); await A.attendre(300);
  await set({ ecran: 'pause', ecranPrecedent: 'jeu' }); await A.attendre(500); await A.capture('menus_pause_mort_en');
  await set({ ecran: 'fin', victoire: 1, rang: 1 }); await A.attendre(600); await A.capture('menus_fin_victoire_en');
  await set({ ecran: 'salon', etat: 5, param_langue: 0, menu_sale: 1 }); await A.attendre(300);
};
