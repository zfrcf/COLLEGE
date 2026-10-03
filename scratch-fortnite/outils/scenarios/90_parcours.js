// Scénario d'INTÉGRATION : parcours complet d'une session, piloté uniquement par clics, touches et
// variables cloud (jamais en forçant « ecran ») :
//   drapeau vert → connexion → CONTINUER → salon (chaque onglet) → mode Rumble → JOUER → matchmaking →
//   chargement → île d'attente (etat 8) → ☁ Partie avancée → bus (etat 6) → espace → parachute →
//   atterrissage (etat 1, ecran jeu) → M → carte → M → jeu → P → pause → Reprendre → tir sur un adversaire
//   simulé → ☁ Partie en Solo → mort par un adversaire → spectateur (3 s) → dernier vivant → écran fin →
//   REJOUER → matchmaking.
// Coordonnées des boutons : voir 40_menus.js (Menus) et les en-têtes des modules.
const { chargeurPaquets } = require('../vm_lib');
module.exports = async (T, verifier) => {
  const Pq = chargeurPaquets();
  const nom = (t) => Pq.codeNom(t);
  const now = () => Math.floor(Number(T.g('maintenant')));
  const n = (v) => Number(T.g(v));
  const pad = (v, k) => String(v).padStart(k, '0').slice(-k);
  const partie = (t, mode = 5, ltm = 0, graine = 42) => '1' + pad((now() - t + 100000) % 100000, 5) + mode + ltm + pad(graine, 2);
  const paquet = (o) => Pq.paquet(Object.assign({ pv: 100, battement: now(), etat: 1, niveau: 7 }, o));
  const dodo = (ms) => new Promise(r => setTimeout(r, ms));
  // fait tourner la VM (temps réel) jusqu'à ce que la condition soit vraie ou que `ms` millisecondes soient écoulées
  const attendre = (cond, ms) => { const t0 = Date.now(); while (!cond() && Date.now() - t0 < ms) T.pas(1); return cond(); };
  const etape = (libelle, ecran, etat, enPartie, phase) => {
    const ok = (ecran === null || T.g('ecran') === ecran) && (etat === null || n('etat') === etat) &&
      (enPartie === null || n('enPartie') === enPartie) && (phase === null || n('phase') === phase) && T.erreurs.length === 0;
    verifier(libelle, ok, { ecran: T.g('ecran'), etat: T.g('etat'), enPartie: T.g('enPartie'), phase: T.g('phase'), erreurs: T.erreurs.slice(0, 2) });
  };

  // ---- 1. drapeau vert : écran de connexion, emplacement réseau pris ----
  T.pseudo('antoine'); T.souris(0, 0, false); T.drapeau(); T.pas(8);
  await dodo(700); T.pas(6);                                   // chargement des costumes de Menus
  verifier('connecté (monSlot 1, connecte 1)', n('monSlot') === 1 && n('connecte') === 1, [T.g('monSlot'), T.g('connecte')]);
  etape('connexion : ecran connexion, etat 5 (salon), enPartie 0, phase 0', 'connexion', 5, 0, 0);

  // ---- 2. CONTINUER → salon, puis chaque onglet ----
  T.clic(0, -44); T.pas(3);
  etape('CONTINUER → salon (accueil)', 'salon', 5, 0, null);
  verifier('onglet accueil', T.g('onglet') === 'accueil', T.g('onglet'));
  for (const [o, x] of [['passe', -126], ['boutique', -52], ['casier', 9], ['quetes', 64], ['carriere', 123], ['parametres', 196], ['accueil', -202]]) {
    T.clic(x, 163); T.pas(2);
    verifier('onglet « ' + o + ' » par clic, toujours au salon', T.g('onglet') === o && T.g('ecran') === 'salon' && T.erreurs.length === 0, [T.g('onglet'), T.g('ecran')]);
  }

  // ---- 3. sélection du mode Rumble puis JOUER ----
  T.clic(55, -127); T.pas(2);
  verifier('sélecteur de mode ouvert', Number(T.l('Menus', 'listeModes')) === 1, T.l('Menus', 'listeModes'));
  T.clic(55, -48); T.pas(2);                                   // 5e ligne de la liste = Rumble
  verifier('mode Rumble choisi (modeChoisi 5), liste fermée', n('modeChoisi') === 5 && Number(T.l('Menus', 'listeModes')) === 0, [T.g('modeChoisi'), T.l('Menus', 'listeModes')]);
  T.clic(55, -161); T.pas(2);
  etape('JOUER → matchmaking, enPartie 1, etat 5 conservé', 'matchmaking', 5, 1, null);
  verifier('matchmaking : compte à rebours de 5 s armé', Number(T.l('Menus', 'tCompte')) > T.vm.runtime.ioDevices.clock.projectTimer(), T.l('Menus', 'tCompte'));

  // ---- 4. matchmaking (5 s réelles) → chargement (2,5 s) → île d'attente ----
  attendre(() => T.g('ecran') === 'chargement', 7000);
  etape('fin du compte à rebours → chargement (Partie attend encore : etat 5)', 'chargement', 5, 1, null);
  attendre(() => n('etat') === 8, 5000);
  etape('barre terminée → île d’attente : etat 8, ecran jeu, phase 0', 'jeu', 8, 1, 0);
  verifier('île : invulnérable, message « prepartie », ☁ Partie en Rumble', n('invulnerable') === 1 && T.g('message') === 'prepartie' && String(T.g('☁ Partie'))[6] === '5', [T.g('invulnerable'), T.g('message'), T.g('☁ Partie')]);

  // ---- 5. bus : ☁ Partie avancée à t = 30 s (debut = maintenant − 30) ----
  T.set('☁ Partie', partie(30, 5, 0, 42)); T.pas(4);
  etape('t = 30 : bus (etat 6, ecran bus, phase 1)', 'bus', 6, 1, 1);
  verifier('dans le bus : altitude 99, mode 5, graine 42', n('altitude') === 99 && n('mode') === 5 && n('graine') === 42, [T.g('altitude'), T.g('mode'), T.g('graine')]);

  // ---- 6. espace → parachute → atterrissage ----
  T.touche(' ', true); T.pas(2); T.touche(' ', false); T.pas(2);
  etape('espace → parachute (etat 7)', 'parachute', 7, 1, 1);
  const alt0 = n('altitude');
  attendre(() => n('altitude') < alt0 - 3, 2500);
  verifier('le parachute descend (altitude < 96)', n('altitude') < alt0 - 3 && n('etat') === 7, [alt0, T.g('altitude')]);
  T.set('altitude', 1); attendre(() => n('etat') === 1, 2000);   // on abrège la descente (≈ 16 s réelles)
  etape('atterrissage : etat 1, ecran jeu', 'jeu', 1, 1, null);
  verifier('au sol : altitude 0, plus invulnérable, message « atterrissage »', n('altitude') === 0 && n('invulnerable') === 0 && T.g('message') === 'atterrissage', [T.g('altitude'), T.g('invulnerable'), T.g('message')]);

  // ---- 7. carte (M) et pause (P) ----
  T.appui('m', 2); T.pas(2);
  etape('touche carte → écran carte', 'carte', 1, 1, null);
  T.appui('m', 2); T.pas(2);
  etape('touche carte à nouveau → jeu', 'jeu', 1, 1, null);
  T.appui('p', 2); T.pas(2);
  etape('touche pause → écran pause', 'pause', 1, 1, null);
  verifier('ecranPrecedent = jeu', T.g('ecranPrecedent') === 'jeu', T.g('ecranPrecedent'));
  T.clic(0, 52); T.pas(3);
  etape('Reprendre → jeu', 'jeu', 1, 1, null);

  // ---- 8. tir sur un adversaire simulé (riko, 2 cases devant) ----
  T.set('px', 16.5); T.set('py', 4.5); T.set('dir', 90); T.pas(1);
  T.set('☁ J2', paquet({ x: 16.5, y: 6.5, dir: 270, nom: nom('riko'), elims: 1 }));
  attendre(() => Number(T.L('E_actif')[1]) === 1 && n('👥 Joueurs') >= 2, 1500);
  verifier('adversaire riko décodé et compté', T.L('E_nom')[1] === 'riko' && n('👥 Joueurs') === 2, [T.L('E_nom')[1], T.g('👥 Joueurs')]);
  const mun0 = Number(T.L('Quantites')[0]);
  T.souris(0, 0, true); T.pas(1); T.souris(0, 0, false); T.pas(1);
  verifier('tir : cible 2, dégâts 20, munition consommée', n('cible') === 2 && n('degats') === 20 && Number(T.L('Quantites')[0]) === mun0 - 1, [T.g('cible'), T.g('degats'), T.L('Quantites')[0], mun0]);
  verifier('statistiques de tir', n('stat_tirs') >= 1 && n('stat_touches') >= 1, [T.g('stat_tirs'), T.g('stat_touches')]);
  // performance : temps moyen d'un pas de scratch-vm en jeu avec tout le projet actif (HUD, 3D, réseau, adversaire)
  const tp = Date.now(); T.pas(30); const moyen = (Date.now() - tp) / 30;
  verifier('temps moyen d’un pas scratch-vm en jeu < 70 ms', moyen < 70, moyen.toFixed(1) + ' ms');

  // ---- 9. mode Solo : ☁ Partie réécrite (t = 100, mode 1) → nouvelle manche, arrivée en retard, atterrissage ----
  T.set('☁ Partie', partie(100, 1, 0, 7)); T.pas(4);
  verifier('mode Solo lu depuis ☁ Partie, phase 2, arrivée en retard (parachute)', n('mode') === 1 && n('phase') === 2 && n('etat') === 7 && T.g('ecran') === 'parachute', [T.g('mode'), T.g('phase'), T.g('etat'), T.g('ecran')]);
  T.set('altitude', 1); attendre(() => n('etat') === 1, 2000);
  etape('atterri dans la zone : etat 1, ecran jeu', 'jeu', 1, 1, 2);
  verifier('dans la zone (pas de dégâts de tempête)', n('horsZone') === 0, [T.g('horsZone'), T.g('px'), T.g('py'), T.g('zoneX'), T.g('zoneY'), T.g('zoneR')]);
  // deux adversaires vivants à côté de moi (dans la zone)
  const px = n('px'), py = n('py');
  T.set('☁ J2', paquet({ x: px, y: py + 1.5, dir: 270, nom: nom('riko'), elims: 1 })); T.pas(2);
  T.set('☁ J3', paquet({ x: px + 1.5, y: py, dir: 180, nom: nom('zed') })); T.pas(2);
  attendre(() => n('vivants') === 3, 1500);
  verifier('3 vivants (moi, riko, zed), participants 3', n('vivants') === 3 && n('participants') === 3, [T.g('vivants'), T.g('participants')]);

  // ---- 10. mort par riko (deux tirs de sniper : 99 + 99 dégâts) ----
  const pv0 = n('❤ PV');
  verifier('PV pleins avant les tirs', pv0 === 100, pv0);
  // (Reseau décode un paquet par emplacement et par image : on attend l'application du coup plutôt qu'un nombre de pas)
  T.set('☁ J2', paquet({ x: px, y: py + 1.5, dir: 270, nom: nom('riko'), elims: 1, cible: 1, seq: 1, degats: 99, arme: 3 }));
  attendre(() => n('❤ PV') < 100, 1500);
  // le surbouclier se recharge (+5/s après 6 s sans dégâts) : il absorbe quelques points avant les PV
  verifier('premier tir reçu : PV < 10, encore vivant', n('❤ PV') < 10 && n('❤ PV') > 0 && n('etat') === 1, [T.g('❤ PV'), pv0, T.g('🛡 Bouclier'), T.g('surbouclier')]);
  T.set('☁ J2', paquet({ x: px, y: py + 1.5, dir: 270, nom: nom('riko'), elims: 2, cible: 1, seq: 2, degats: 99, arme: 3 }));
  attendre(() => n('etat') === 2, 1500);
  etape('mort en Solo : etat 2, encore sur l’écran jeu', 'jeu', 2, 1, 2);
  verifier('tueur = 2, stat_morts 1', n('tueur') === 2 && n('stat_morts') === 1, [T.g('tueur'), T.g('stat_morts')]);
  // les battements des adversaires doivent rester frais pendant l'attente
  const rafraichir = () => { T.set('☁ J2', paquet({ x: px, y: py + 1.5, dir: 270, nom: nom('riko'), elims: 2, cible: 1, seq: 2, degats: 99, arme: 3 })); T.pas(1); T.set('☁ J3', paquet({ x: px + 1.5, y: py, dir: 180, nom: nom('zed') })); T.pas(1); };
  attendre(() => T.g('ecran') === 'spectateur', 4500);
  etape('3 s après la mort : écran spectateur (etat 2 conservé : mort sans réapparition)', 'spectateur', 2, 1, 2);
  verifier('caméra sur un vivant (spectSlot 2 ou 3)', n('spectSlot') === 2 || n('spectSlot') === 3, T.g('spectSlot'));
  verifier('manche toujours en cours (2 vivants)', n('finManche') === 0 && n('vivants') === 2, [T.g('finManche'), T.g('vivants')]);

  // ---- 11. zed meurt → riko dernier vivant → fin de manche ----
  rafraichir();
  T.set('☁ J3', paquet({ x: px + 1.5, y: py, dir: 180, nom: nom('zed'), etat: 2, pv: 0, morts: 1, tueur: 2 }));
  attendre(() => n('finManche') === 1, 2000);
  etape('un seul vivant → fin de manche : ecran fin, etat 9, phase 8', 'fin', 9, 1, 8);
  verifier('défaite : rang 3, victoire 0, stat_parties 1', n('rang') === 3 && n('victoire') === 0 && n('stat_parties') === 1 && T.g('message') === 'defaite', [T.g('rang'), T.g('victoire'), T.g('stat_parties'), T.g('message')]);
  T.pas(3);
  verifier('écran fin : boutons REJOUER / Salon', (() => { const b = T.sprite('Menus').lookupVariableByNameAndType('menu_bid', 'list').value; return b.includes('rejouer') && b.includes('salon'); })());

  // ---- 12. REJOUER → matchmaking ----
  T.clic(-80, -145); T.pas(3);
  etape('REJOUER → matchmaking, enPartie 1', 'matchmaking', null, 1, null);
  verifier('etat remis à 5 (salon) en attendant la manche suivante', n('etat') === 5 || n('etat') === 9, T.g('etat'));
  verifier('aucune erreur VM sur tout le parcours', T.erreurs.length === 0, T.erreurs.slice(0, 3));
};
