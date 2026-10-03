// Captures du module Spectacle : feux d'artifice de victoire (2 instants), pluie de défaite, bannière
// « TRIPLE ÉLIMINATION ! », annonce « DERNIÈRE ZONE », étoiles du niveau, salon animé (2 instants).
//   node capture.js captures_scripts/spectacle.js   → outils/captures/spectacle_*.png
module.exports = async (A) => {
  const set = (obj) => A.evaluer((vm, V, L, arg) => { for (const k in arg) V(k).value = arg[k]; }, obj);
  const get = (nom) => A.evaluer((vm, V, L, arg) => V(arg).value, nom);
  // ne pas renvoyer les fils créés par startHats : Playwright tenterait de sérialiser tout le runtime (≈ 15 s de blocage)
  const diffuser = (nom) => A.evaluer((vm, V, L, arg) => { vm.runtime.startHats('event_whenbroadcastreceived', { BROADCAST_OPTION: arg.toUpperCase() }); return 0; }, nom);
  const chrono = () => A.evaluer((vm) => vm.runtime.ioDevices.clock.projectTimer());
  const mesurer = async (nom) => {           // opérations stylo (lignes + tampons) du sprite Spectacle par image
    const r = await A.evaluer(async (vm) => {
      const sp = vm.runtime.getSpriteTargetByName('Spectacle'); const R = vm.runtime.renderer;
      let n = 0, pas = 0; const o1 = R.penStamp, o2 = R.penLine, o3 = vm.runtime._step;
      R.penStamp = function (skin, dr) { if (dr === sp.drawableID) n++; return o1.apply(this, arguments); };
      R.penLine = function () { n++; return o2.apply(this, arguments); };
      vm.runtime._step = function () { pas++; return o3.apply(this, arguments); };
      await new Promise(r => setTimeout(r, 1000));
      R.penStamp = o1; R.penLine = o2; vm.runtime._step = o3;
      return [n, pas];
    });
    console.log('opérations stylo par image (' + nom + ', tous sprites pour les lignes) : ' + (r[0] / Math.max(1, r[1])).toFixed(0) + ' sur ' + r[1] + ' images ; spc_particules = ' + await get('spc_particules'));
  };
  await A.attendre(1500);
  await A.evaluer((vm, V) => { if (!V('RecapLignes').value.length) V('RecapLignes').value = ['Éliminations ×3 : +150 XP', 'Survie 4:12 : +120 XP', 'Top 1 : +300 XP', 'Coffres ×4 : +40 XP']; });

  // --- fin : victoire (deux instants) puis défaite ---
  await set({ px: 16.5, py: 4.5, dir: 90, ecran: 'fin', victoire: 1, rang: 1, participants: 6, '💀 Éliminations': 3, xpGagne: 610, mode: 1, finManche: 1, tempsPhase: 14, menu_sale: 1 });
  await A.attendre(900); await A.capture('spectacle_fin_victoire_1');
  await A.attendre(1100); await A.capture('spectacle_fin_victoire_2');
  await mesurer('fin victoire');
  await set({ victoire: 0, rang: 4, tempsPhase: 9 });
  await A.attendre(900); await A.capture('spectacle_fin_defaite');

  // --- jeu : bannière de série (au repos de l'animation, ~0,6 s après l'événement) ---
  // enPartie = 0 et connecte = 0 : ni Partie ni Joueur ne modifient l'état forcé
  await set({ ecran: 'jeu', etat: 1, connecte: 0, enPartie: 0, superposition: '', finManche: 0, victoire: 0, phase: 3,
              zoneX: 16.5, zoneY: 10.5, zoneR: 9, serie: 3, serieFin: (await chrono()) + 8, '💀 Éliminations': 3, message: '' });
  await A.attendre(400);
  await diffuser('evt elimination'); await A.attendre(650);
  console.log('bannière :', await get('spc_banniere'), '| ecran', await get('ecran'), 'etat', await get('etat'), 'file', await A.evaluer((vm) => vm.runtime.getSpriteTargetByName('Spectacle').lookupVariableByNameAndType('file', 'list').value));
  await A.capture('spectacle_triple_elimination');
  await A.attendre(250); await A.capture('spectacle_triple_elimination_b');
  await A.attendre(3600);                                     // TÊTE DE SÉRIE suit (2 s) puis plus rien

  // --- jeu : annonce DERNIÈRE ZONE (bandeau arrivé au centre) ---
  await set({ evt_valeur: 6, message: '' }); await diffuser('evt phase'); await A.attendre(700);
  console.log('annonce :', await A.evaluer((vm) => vm.runtime.getSpriteTargetByName('Spectacle').lookupVariableByNameAndType('annTexte').value));
  await A.capture('spectacle_derniere_zone');
  await A.attendre(2400);

  // --- jeu : NIVEAU 13 + étoiles ---
  await set({ niveau: 13, message: '' }); await diffuser('evt niveau'); await A.attendre(800);
  await A.capture('spectacle_niveau');
  await A.attendre(2400);

  // --- jeu, anglais : vivants 4 → 2 ---
  await set({ param_langue: 1, vivants: 4, message: '' }); await A.attendre(200); await set({ vivants: 2 }); await A.attendre(700);
  await A.capture('spectacle_2_players_left_en');
  await set({ param_langue: 0 }); await A.attendre(2400);

  // --- salon animé : deux instants (éclats de bordure, halo du personnage, halo JOUER) ---
  await set({ ecran: 'salon', etat: 5, enPartie: 0, onglet: 'accueil', connecte: 1, menu_sale: 1, message: '' });
  await A.attendre(900); await A.capture('spectacle_salon_1');
  await A.attendre(500); await A.capture('spectacle_salon_2');
  console.log('clones Spectacle :', await A.evaluer((vm) => vm.runtime.targets.filter(t => t.getName() === 'Spectacle' && !t.isOriginal).length));
  // survol de JOUER : le halo reste autour du bouton surligné
  await A.souris(55, -161, false); await A.attendre(500); await A.capture('spectacle_salon_survol_jouer');
};
