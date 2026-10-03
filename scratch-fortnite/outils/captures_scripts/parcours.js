// PARCOURS COMPLET en rendu réel : les écrans sont atteints dans l'ordre du jeu, par clics, touches et
// variables cloud (☁ Partie avancée dans le temps, paquets d'adversaires simulés), jamais en forçant
// « ecran » (sauf le retour à la connexion pour la version anglaise, qui n'a pas de bouton).
//   node capture.js captures_scripts/parcours.js   → outils/captures/parcours_NN_<ecran>.png
// Seules les positions px/py/dir sont réglées avant les vues 3D (point dégagé (16,5 ; 4,5) regard +y) pour
// que les adversaires soient dans le champ.
const contrat = require('../contrat.json');
const pad = (v, n) => String(Math.max(0, Math.round(Number(v) || 0))).padStart(n, '0').slice(-n);
const paquet = (o) => { let s = '1'; for (const [nom, l] of contrat.champs) { let v = o[nom] || 0; if (nom === 'x' || nom === 'y') v = v * 100; if (nom === 'nom') { s += String(v || '').padEnd(l, '0').slice(0, l); continue; } s += pad(v, l); } return s; };
const codeNom = (t) => { let s = ''; for (let i = 0; i < 8; i++) { const k = contrat.alphabet.indexOf((t[i] || '').toLowerCase()); s += pad(k >= 0 ? k + 1 : 0, 2); } return s; };

module.exports = async (A) => {
  let num = 0;
  const cap = (nom) => A.capture('parcours_' + pad(++num, 2) + '_' + nom);
  const set = (obj) => A.evaluer((vm, V, L, arg) => { for (const k in arg) V(k).value = arg[k]; }, obj);
  const get = (nom) => A.evaluer((vm, V, L, arg) => V(arg).value, nom);
  const now = () => A.evaluer((vm, V) => Math.floor(Number(V('maintenant').value)));
  const chrono = () => A.evaluer((vm) => vm.runtime.ioDevices.clock.projectTimer());
  const partie = async (t, mode = 5, ltm = 0, graine = 42) => '1' + pad(((await now()) - t + 100000) % 100000, 5) + mode + ltm + pad(graine, 2);
  const adv = async (slot, o) => set({ ['☁ J' + slot]: paquet(Object.assign({ pv: 100, battement: await now(), etat: 1, niveau: 7 }, o)) });
  const touche = async (k) => { await A.touche(k, true); await A.attendre(90); await A.touche(k, false); await A.attendre(150); };
  const attendre = async (cond, ms) => { const t0 = Date.now(); while (Date.now() - t0 < ms) { if (await cond()) return true; await A.attendre(100); } return cond(); };
  const etat = async () => ({ ecran: await get('ecran'), etat: await get('etat'), phase: await get('phase'), enPartie: await get('enPartie') });
  const journal = async (libelle) => console.log(libelle, JSON.stringify(await etat()));
  // deux paquets ne doivent pas arriver dans la même image (Reseau n'en décode qu'un par image de façon sûre)
  const riko = async (o) => adv(2, Object.assign({ nom: codeNom('riko'), niveau: 12, skin: 3, elims: 4 }, o));
  const zed = async (o) => { await A.attendre(120); await adv(3, Object.assign({ nom: codeNom('zed'), niveau: 4, skin: 5, elims: 1 }, o)); };
  const poste = async () => set({ px: 16.5, py: 4.5, dir: 90 });

  // ---- 0. pseudo Scratch puis drapeau vert (la page a déjà lancé le projet sans nom d'utilisateur) ----
  await A.evaluer((vm) => { vm.postIOData('userData', { username: 'antoine' }); vm.greenFlag(); });
  await A.attendre(1800);
  await journal('démarrage');

  // ---- 1. connexion ----
  await cap('connexion');
  // joueurs simulés dans le salon (barre sociale) : riko au salon, zed en jeu
  await riko({ etat: 5, x: 10, y: 10 }); await zed({ etat: 1, x: 12, y: 12 });
  await A.attendre(300);

  // ---- 2. salon et ses onglets (clics) ----
  await A.clic(0, -44); await A.attendre(700); await set({ message: '' }); await A.attendre(300);
  await journal('après CONTINUER');
  await cap('salon');
  for (const [nom, x] of [['passe', -126], ['boutique', -52], ['casier', 9], ['quetes', 64], ['carriere', 123], ['parametres', 196]]) {
    await A.clic(x, 163); await A.attendre(500); await set({ message: '' }); await A.attendre(250);
    await cap(nom);
  }
  await A.clic(-202, 163); await A.attendre(400);
  // mode Rumble dans le sélecteur, puis JOUER
  await A.clic(55, -127); await A.attendre(300); await A.clic(55, -48); await A.attendre(300);
  console.log('modeChoisi :', await get('modeChoisi'));
  await A.clic(55, -161); await A.attendre(900);
  await journal('après JOUER');
  await cap('matchmaking');
  await attendre(async () => (await get('ecran')) === 'chargement', 7000); await A.attendre(900);
  await journal('chargement');
  await cap('chargement');
  await attendre(async () => Number(await get('etat')) === 8, 5000);
  await journal('île d’attente');

  // ---- 3. île d'attente (3D) : deux joueurs devant moi ----
  // ☁ Partie a été écrite au drapeau vert (≈ 25 s plus tôt) : on repart d'une manche fraîche (t = 5 s) pour voir l'île
  await set({ '☁ Partie': await partie(5, 5, 0, 42) }); await A.attendre(600);
  await poste();
  await riko({ etat: 8, x: 15.5, y: 7.2, dir: 270 }); await zed({ etat: 8, x: 18.0, y: 6.5, dir: 230 });
  await A.attendre(3600);                                   // la bannière « ÎLE D'ATTENTE » dure 3 s
  await journal('île d’attente (manche fraîche)');
  await cap('prepartie');

  // ---- 4. bus (t = 30 s) ----
  await set({ '☁ Partie': await partie(30, 5, 0, 42) }); await A.attendre(900);
  await riko({ etat: 6, x: 10, y: 20, altitude: 99 }); await zed({ etat: 7, x: 14, y: 18, altitude: 60 });
  await A.attendre(600);
  await journal('bus');
  await cap('bus');

  // ---- 5. parachute (espace) ----
  await touche(' '); await A.attendre(1500);
  await journal('parachute');
  await cap('parachute');
  await set({ altitude: 1 }); await attendre(async () => Number(await get('etat')) === 1, 2500);
  await journal('atterrissage');

  // ---- 6. jeu : HUD complet, deux adversaires (riko devant, zed à droite), un 4e joueur (nina) éliminé par riko
  //         (journal), ping de zed, tir reçu de riko (flèche de dégâts), mon tir sur riko (chiffre de dégâts) ----
  await poste();
  await riko({ x: 16.5, y: 7.0, dir: 270, pv: 75, bouclier: 20 }); await zed({ x: 18.2, y: 6.5, dir: 250, pv: 60 });
  await A.attendre(150);
  await adv(4, { nom: codeNom('nina'), niveau: 9, x: 12, y: 12 }); await A.attendre(300);
  await zed({ x: 18.2, y: 6.5, dir: 250, pv: 60, pingX: 16, pingY: 9, pingSeq: 1 }); await A.attendre(250);
  await riko({ x: 16.5, y: 7.0, dir: 270, pv: 75, bouclier: 20, cible: 1, seq: 1, degats: 30, arme: 1 }); await A.attendre(250);
  await adv(4, { nom: codeNom('nina'), niveau: 9, x: 12, y: 12, pv: 0, etat: 2, morts: 1, tueur: 2 }); await A.attendre(250);
  await riko({ x: 16.5, y: 7.0, dir: 270, pv: 75, bouclier: 20, cible: 1, seq: 1, degats: 30, arme: 1, elims: 5 }); await A.attendre(300);
  // je tire sur riko (clic au centre : viseur)
  await A.souris(0, 0, true); await A.attendre(60); await A.souris(0, 0, false); await A.attendre(150);
  console.log('tir : cible', await get('cible'), 'dégâts', await get('degats'), 'PV', await get('❤ PV'));
  await set({ message: '' }); await A.attendre(400);
  await journal('jeu');
  await cap('jeu');
  // performance réelle : durée moyenne d'un pas de scratch-vm (toute la VM) sur 1,5 s, et tampons par image
  const perf = await A.evaluer(async (vm) => {
    const R = vm.runtime.renderer; let pas = 0, duree = 0, tampons = 0; const o1 = vm.runtime._step, o2 = R.penStamp;
    vm.runtime._step = function () { const t = performance.now(); const r = o1.apply(this, arguments); duree += performance.now() - t; pas++; return r; };
    R.penStamp = function () { tampons++; return o2.apply(this, arguments); };
    await new Promise(r => setTimeout(r, 1500));
    vm.runtime._step = o1; R.penStamp = o2;
    return { pas, moyen: duree / Math.max(1, pas), tamponsParImage: tampons / Math.max(1, pas) };
  });
  console.log('performance (écran jeu, Chromium) : ' + perf.moyen.toFixed(1) + ' ms par pas, ' + perf.tamponsParImage.toFixed(0) + ' tampons par image, ' + perf.pas + ' pas en 1,5 s');

  // ---- 7. carte (M) ----
  await touche('m'); await A.attendre(700);
  await journal('carte');
  await cap('carte');
  await touche('m'); await A.attendre(400);

  // ---- 8. pause (P) puis Reprendre ----
  await touche('p'); await A.attendre(600);
  await journal('pause');
  await cap('pause');
  await A.clic(0, 52); await A.attendre(400);
  await journal('reprendre');

  // ---- 9. chat rapide (T) puis roue d'émotes (Y) ----
  await riko({ x: 15.5, y: 7.2, dir: 270, pv: 55, bouclier: 20, chat: 4, chatSeq: 1, elims: 5 }); await A.attendre(400);
  await touche('t'); await A.souris(-72, 20, false); await A.attendre(500);
  await cap('chat');
  await touche('t'); await A.attendre(300);
  await touche('y'); await A.souris(54, 41, false); await A.attendre(500);
  await cap('emotes');
  await A.clic(54, 41); await A.attendre(600); await A.souris(0, 0, false);

  // ---- 10. à terre : manche en Duo (t = 60, zone initiale), coéquipier riko (équipe 1), zed (équipe 2) me met à terre ----
  await set({ '☁ Partie': await partie(60, 2, 0, 11), remplissage: 1 }); await A.attendre(900);
  await journal('nouvelle manche Duo');
  await set({ altitude: 1 }); await attendre(async () => Number(await get('etat')) === 1, 2500);
  await poste();
  await riko({ x: 15.0, y: 6.0, dir: 300, equipe: 1 }); await zed({ x: 18.2, y: 6.5, dir: 250, equipe: 2, arme: 3 });
  await A.attendre(400);
  await zed({ x: 18.2, y: 6.5, dir: 250, equipe: 2, arme: 3, cible: 1, seq: 1, degats: 99 }); await A.attendre(350);
  await zed({ x: 18.2, y: 6.5, dir: 250, equipe: 2, arme: 3, cible: 1, seq: 2, degats: 99 }); await A.attendre(350);
  await riko({ x: 15.0, y: 6.0, dir: 300, equipe: 1, reanime: 1 });      // riko commence à me réanimer
  await A.attendre(1200);
  await journal('à terre');
  await cap('aterre');

  // ---- 11. spectateur : manche Solo (t = 60), riko me tue, 3 s plus tard la caméra suit un vivant ----
  await set({ '☁ Partie': await partie(60, 1, 0, 7) }); await A.attendre(900);
  await set({ altitude: 1 }); await attendre(async () => Number(await get('etat')) === 1, 2500);
  await poste();
  await riko({ x: 15.5, y: 7.2, dir: 270, equipe: 0 }); await zed({ x: 25.0, y: 25.0, dir: 0, equipe: 0 });
  await A.attendre(400);
  await riko({ x: 15.5, y: 7.2, dir: 270, cible: 1, seq: 3, degats: 99, arme: 3 }); await A.attendre(350);
  await riko({ x: 15.5, y: 7.2, dir: 270, cible: 1, seq: 4, degats: 99, arme: 3, elims: 6 }); await A.attendre(350);
  await journal('mort');
  await attendre(async () => (await get('ecran')) === 'spectateur', 5000);
  await riko({ x: 15.5, y: 7.2, dir: 270, elims: 6 }); await zed({ x: 25.0, y: 25.0, dir: 0 });
  await A.attendre(1500);
  await journal('spectateur');
  await cap('spectateur');

  // ---- 12. fin de manche (défaite) : zed meurt, riko dernier vivant ----
  await zed({ x: 25.0, y: 25.0, dir: 0, pv: 0, etat: 2, morts: 1, tueur: 2 });
  await attendre(async () => (await get('ecran')) === 'fin', 3000); await A.attendre(1200);
  await journal('fin défaite');
  await cap('fin_defaite');

  // ---- 13. REJOUER → matchmaking → chargement → île → manche Solo où je suis le dernier vivant ----
  await A.clic(-80, -145); await A.attendre(500);
  await journal('rejouer');
  // matchmaking (5 s), chargement (2,5 s) puis attente de la manche suivante, lancée par Partie 20 s après la fin
  await attendre(async () => Number(await get('etat')) === 8, 28000);
  await journal('île (2e manche)');
  await set({ '☁ Partie': await partie(60, 1, 0, 8) }); await A.attendre(900);
  await set({ altitude: 1 }); await attendre(async () => Number(await get('etat')) === 1, 2500);
  await poste();
  await riko({ x: 15.5, y: 7.2, dir: 270, elims: 6 }); await zed({ x: 25.0, y: 25.0, dir: 0, pv: 0, etat: 2, morts: 1, tueur: 1 });
  await A.attendre(500);
  await riko({ x: 15.5, y: 7.2, dir: 270, elims: 6, pv: 0, etat: 2, morts: 1, tueur: 1 });
  await attendre(async () => (await get('ecran')) === 'fin', 3000); await A.attendre(1200);
  await journal('fin victoire');
  await cap('fin_victoire');

  // ---- 14. anglais : connexion, salon, jeu ----
  await A.clic(80, -145); await A.attendre(500);                       // Salon
  await set({ param_langue: 1, ecran: 'connexion', menu_sale: 1 });
  await A.attendre(3600);                                  // bannière « QUEST COMPLETE » de la manche précédente (3 s)
  await cap('connexion_en');
  await riko({ etat: 5, x: 10, y: 10 }); await zed({ etat: 5, x: 12, y: 12 }); await A.attendre(300);
  await A.clic(0, -44); await A.attendre(700); await set({ message: '' }); await A.attendre(300);
  await cap('salon_en');
  await A.clic(55, -161); await A.attendre(300);
  await attendre(async () => Number(await get('etat')) === 8, 12000);
  await set({ '☁ Partie': await partie(60, 5, 0, 9) }); await A.attendre(900);
  await set({ altitude: 1 }); await attendre(async () => Number(await get('etat')) === 1, 2500);
  await poste();
  await riko({ x: 15.5, y: 7.2, dir: 270, pv: 75, bouclier: 20, elims: 6 }); await zed({ x: 18.2, y: 6.5, dir: 250, pv: 60, pingX: 16, pingY: 9, pingSeq: 2 });
  await A.attendre(300);
  await riko({ x: 15.5, y: 7.2, dir: 270, pv: 75, bouclier: 20, elims: 6, cible: 1, seq: 5, degats: 25, arme: 1 }); await A.attendre(400);
  await set({ message: '' }); await A.attendre(500);
  await journal('jeu EN');
  await cap('jeu_en');
};
