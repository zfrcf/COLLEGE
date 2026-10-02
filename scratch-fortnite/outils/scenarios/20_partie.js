// Scénario : déroulé d'une manche (sprite Partie) — ☁ Partie, île d'attente, bus, saut, parachute,
// atterrissage, zones, retardataires, compteurs, rang, fin de manche, Tempête éclair, zone en mouvement.
// Le temps est piloté en réécrivant ☁ Partie avec un `debut` décalé (debut = maintenant − t).
const { chargeurPaquets } = require('../vm_lib');
module.exports = async (T, verifier) => {
  const Pq = chargeurPaquets();
  const nom = (t) => Pq.codeNom(t);
  const now = () => Math.floor(Number(T.g('maintenant')));
  const pad = (v, n) => String(v).padStart(n, '0').slice(-n);
  const partie = (t, mode = 5, ltm = 0, graine = 42) => '1' + pad((now() - t + 100000) % 100000, 5) + mode + ltm + pad(graine, 2);
  const paquet = (o) => Pq.paquet(Object.assign({ pv: 100, battement: now(), etat: 1, niveau: 3 }, o));
  const local = (n) => T.l('Partie', n);
  const n = (v) => Number(T.g(v));
  const dist = (ax, ay, bx, by) => Math.hypot(ax - bx, ay - by);
  const setLocal = (nomV, val) => { Object.values(T.sprite('Partie').variables).find(v => v.name === nomV).value = val; };
  // gèle le compte à rebours de matchmaking de Menus (s'il est présent) pour tester l'attente de Partie
  const gelerMenus = () => { try { Object.values(T.sprite('Menus').variables).find(v => v.name === 'tCompte').value = 1e9; } catch (e) { /* projet sans Menus */ } };
  T.pseudo('antoine'); T.souris(0, 0, false); T.drapeau(); T.pas(8);

  // (a) ☁ Partie écrite au démarrage
  const cp = String(T.g('☁ Partie'));
  verifier('☁ Partie écrite : 1 + debut(5) + mode(1) + ltm(1) + graine(2)', /^1\d{9}$/.test(cp), cp);
  verifier('debut ≈ maintenant, mode = modeChoisi (5), ltm = 0', Math.abs(Number(cp.slice(1, 6)) - now()) <= 2 && cp[6] === '5' && cp[7] === '0', [cp, now()]);
  verifier('debut / mode / graine décodés dans les variables', n('debut') === Number(cp.slice(1, 6)) && n('mode') === 5 && n('graine') === Number(cp.slice(8, 10)), [T.g('debut'), T.g('mode'), T.g('graine')]);
  verifier('☁ Construction et ☁ Construction2 remises à 1', n('☁ Construction') === 1 && n('☁ Construction2') === 1, [T.g('☁ Construction'), T.g('☁ Construction2')]);
  verifier('phase 0, cercle initial, aucun dégât de zone', n('phase') === 0 && n('zoneR') === 30 && n('zoneDegats') === 0 && n('tempsManche') < 5, [T.g('phase'), T.g('zoneR'), T.g('tempsManche')]);
  verifier('hors partie : état salon et écran de connexion conservés', n('etat') === 5 && T.g('ecran') === 'connexion', [T.g('etat'), T.g('ecran')]);
  const carte = T.L('Carte');
  const cellule = (x, y) => Number(carte[Math.floor(y) * 32 + Math.floor(x)]);

  // (b) en partie pendant l'île d'attente
  T.set('enPartie', 1); T.pas(3);
  verifier('île d’attente : etat 8, ecran jeu, invulnérable', n('etat') === 8 && T.g('ecran') === 'jeu' && n('invulnerable') === 1, [T.g('etat'), T.g('ecran'), T.g('invulnerable')]);
  verifier('placé sur une case libre', cellule(n('px'), n('py')) === 0, [T.g('px'), T.g('py')]);
  verifier('tempsPhase = compte à rebours de l’île (1..25)', n('tempsPhase') >= 1 && n('tempsPhase') <= 25 && n('⏱ Zone') === n('tempsPhase'), [T.g('tempsPhase'), T.g('⏱ Zone')]);
  verifier('message « prepartie », menu_sale levé', T.g('message') === 'prepartie' && n('menu_sale') === 1, [T.g('message'), T.g('menu_sale')]);
  // 5 dernières secondes de l'île : t = 21 → tempsPhase 4 → « son compte » (dernierCompte suit tempsPhase)
  T.set('☁ Partie', partie(21)); T.pas(3);
  verifier('5 dernières secondes : son « compte » déclenché (dernierCompte = tempsPhase ≤ 5)', n('tempsPhase') <= 5 && n('tempsPhase') >= 1 && Number(local('dernierCompte')) === n('tempsPhase'), [T.g('tempsPhase'), local('dernierCompte')]);

  // (c) bus : debut = maintenant − 30
  T.set('☁ Partie', partie(30)); T.pas(3);
  verifier('t = 30 : phase 1, etat 6 (bus), ecran bus, altitude 99', n('phase') === 1 && n('etat') === 6 && T.g('ecran') === 'bus' && n('altitude') === 99, [T.g('phase'), T.g('etat'), T.g('ecran'), T.g('altitude')]);
  verifier('busProgression ≈ 0,25', Math.abs(n('busProgression') - 0.25) < 0.1, T.g('busProgression'));
  const borne = (v) => Math.min(30.8, Math.max(1.2, v));
  verifier('px/py suivent le bus', Math.abs(n('px') - borne(n('busX'))) < 1e-6 && Math.abs(n('py') - borne(n('busY'))) < 1e-6, [T.g('px'), T.g('busX'), T.g('py'), T.g('busY')]);
  verifier('direction du bus normalisée, bus sur la trajectoire', Math.abs(Math.hypot(n('busDirX'), n('busDirY')) - 1) < 1e-6 && n('busX') > 0 && n('busX') < 32, [T.g('busDirX'), T.g('busDirY'), T.g('busX')]);
  verifier('message « bus »', T.g('message') === 'bus', T.g('message'));
  verifier('« evt phase » diffusé avec evt_valeur = 1', n('evt_valeur') === 1, T.g('evt_valeur'));
  // saut à l'espace
  T.touche(' ', true); T.pas(2); T.touche(' ', false); T.pas(2);
  verifier('espace : saut → etat 7, ecran parachute, aSaute 1', n('etat') === 7 && T.g('ecran') === 'parachute' && n('aSaute') === 1, [T.g('etat'), T.g('ecran'), T.g('aSaute')]);
  // déplacement en parachute (touche avancer, regard +y) puis rotation aux flèches
  T.set('dir', 90); T.set('px', 16.5); T.set('py', 10.5);
  const py0 = n('py');
  T.touche('z', true); T.pas(3); T.touche('z', false); T.pas(1);
  verifier('parachute : déplacement avec « avancer » (vers +y)', n('py') > py0 + 0.1 && Math.abs(n('px') - 16.5) < 0.01, [py0, T.g('py'), T.g('px')]);
  T.touche('ArrowLeft', true); T.pas(2); T.touche('ArrowLeft', false); T.pas(1);
  verifier('parachute : flèche gauche tourne la vue', n('dir') > 90, T.g('dir'));
  verifier('toujours en l’air (altitude > 0, invulnérable)', n('altitude') > 0 && n('invulnerable') === 1, [T.g('altitude'), T.g('invulnerable')]);
  // descente → atterrissage
  T.set('altitude', 0); T.pas(3);
  verifier('atterrissage : etat 1, ecran jeu, invulnerable 0, altitude 0, message', n('etat') === 1 && T.g('ecran') === 'jeu' && n('invulnerable') === 0 && n('altitude') === 0 && T.g('message') === 'atterrissage', [T.g('etat'), T.g('ecran'), T.g('invulnerable'), T.g('altitude'), T.g('message')]);
  verifier('atterri sur une case libre', cellule(n('px'), n('py')) === 0, [T.g('px'), T.g('py')]);
  // atterrissage dans un mur → case libre la plus proche
  T.set('etat', 7); T.set('px', 2.5); T.set('py', 27.5); T.set('altitude', 0); T.pas(3);   // (2,27) est un mur de brique du fort
  verifier('atterrissage dans un mur → déplacé sur la case libre la plus proche', n('etat') === 1 && cellule(n('px'), n('py')) === 0 && dist(n('px'), n('py'), 2.5, 27.5) < 3.5, [T.g('px'), T.g('py')]);

  // (d) t = 100 : zone rétrécie
  T.set('☁ Partie', partie(100)); T.pas(3);
  verifier('t = 100 : phase 2, zoneR < 30, zoneDegats > 0, tempsAvantZone 0', n('phase') === 2 && n('zoneR') < 30 && n('zoneR') > 14 && n('zoneDegats') > 0 && n('tempsAvantZone') === 0, [T.g('phase'), T.g('zoneR'), T.g('zoneDegats'), T.g('tempsAvantZone')]);
  verifier('⏱ Zone ≈ 5 s avant la fin du rétrécissement', n('⏱ Zone') >= 4 && n('⏱ Zone') <= 6, T.g('⏱ Zone'));
  verifier('tempsPartie ≈ 55 s de combat', Math.abs(n('tempsPartie') - 55) <= 1, T.g('tempsPartie'));
  verifier('nouvelle manche : joueur en partie replacé en retard (parachute)', n('etat') === 7 && T.g('ecran') === 'parachute', [T.g('etat'), T.g('ecran')]);
  // (h) t = 110 : phase 3 en attente, retardataire au-dessus de la zone
  T.set('☁ Partie', partie(110)); T.pas(3);
  verifier('t = 110 : phase 3 en attente, zoneR 14, prochaineZoneR 9, tempsAvantZone ≈ 15', n('phase') === 3 && n('zoneR') === 14 && n('prochaineZoneR') === 9 && Math.abs(n('tempsAvantZone') - 15) <= 1, [T.g('phase'), T.g('zoneR'), T.g('prochaineZoneR'), T.g('tempsAvantZone')]);
  verifier('retardataire : etat 7, altitude 99, au-dessus de la zone', n('etat') === 7 && n('altitude') > 90 && dist(n('px'), n('py'), n('zoneX'), n('zoneY')) < n('zoneR'), [T.g('px'), T.g('py'), T.g('zoneX'), T.g('zoneY'), T.g('zoneR')]);
  const dz = dist(n('prochaineZoneX'), n('prochaineZoneY'), n('zoneX'), n('zoneY'));
  verifier('prochaine zone incluse dans la zone actuelle', dz + n('prochaineZoneR') <= n('zoneR') + 1e-6, [dz, T.g('prochaineZoneR'), T.g('zoneR')]);
  verifier('zone dans la carte', n('zoneX') > 4 && n('zoneX') < 28 && n('zoneY') > 4 && n('zoneY') < 28, [T.g('zoneX'), T.g('zoneY')]);
  // annonce du rétrécissement : t = 122 (l'attente de la phase 3 finit à 125) puis 3,4 s réelles → message « zone »
  T.set('message', ''); T.set('☁ Partie', partie(122)); T.pas(2);
  verifier('t ≈ 122 : encore en attente (tempsAvantZone 1..3, pas de message)', n('tempsAvantZone') >= 1 && n('tempsAvantZone') <= 3 && T.g('message') === '', [T.g('tempsAvantZone'), T.g('message')]);
  await new Promise(r => setTimeout(r, 3400)); T.pas(2);
  verifier('début du rétrécissement : message « zone », tempsAvantZone 0', T.g('message') === 'zone' && n('tempsAvantZone') === 0, [T.g('message'), T.g('tempsAvantZone'), local('etape')]);

  // (e) mode Solo, deux adversaires simulés dont un mort
  T.set('☁ Partie', partie(100, 1)); T.pas(3);
  verifier('mode Solo lu depuis ☁ Partie, sans équipe', n('mode') === 1 && n('monEquipe') === 0, [T.g('mode'), T.g('monEquipe')]);
  T.set('altitude', 0); T.pas(3);
  T.set('☁ J2', paquet({ x: 10, y: 10, nom: nom('riko'), elims: 2 }));
  T.set('☁ J3', paquet({ x: 12, y: 12, nom: nom('zed'), etat: 2, pv: 0, morts: 1 })); T.pas(4);
  verifier('vivants = 2 (moi + riko), participants = 3, equipesVivantes = 2', n('vivants') === 2 && n('participants') === 3 && n('equipesVivantes') === 2 && n('etat') === 1, [T.g('vivants'), T.g('participants'), T.g('equipesVivantes'), T.g('etat')]);
  verifier('manche en cours (2 vivants)', n('finManche') === 0 && n('phase') === 2, [T.g('finManche'), T.g('phase')]);
  T.set('☁ J4', paquet({ x: 14, y: 14, nom: nom('obs'), etat: 4 })); T.pas(8);
  verifier('un spectateur (etat 4) n’est pas un participant (toujours 3)', n('participants') === 3 && n('vivants') === 2, [T.g('participants'), T.g('vivants')]);
  T.set('☁ J4', 0); T.pas(8);
  const vivantsAvant = n('vivants');
  T.set('etat', 2); T.pas(8);
  verifier('ma mort : rang mémorisé = vivants avant la mort (2)', n('rang') === vivantsAvant && Number(local('rangMort')) === vivantsAvant, [T.g('rang'), local('rangMort'), vivantsAvant]);
  // (f) un seul vivant → fin de manche (défaite)
  verifier('fin de manche : finManche 1, phase 8, ecran fin, etat 9', n('finManche') === 1 && n('phase') === 8 && T.g('ecran') === 'fin' && n('etat') === 9, [T.g('finManche'), T.g('phase'), T.g('ecran'), T.g('etat')]);
  verifier('rang 2, défaite, statistiques (parties 1, top3 1, meilleur rang 2)', n('rang') === 2 && n('victoire') === 0 && n('stat_parties') === 1 && n('stat_top3') === 1 && n('stat_meilleurRang') === 2 && T.g('message') === 'defaite', [T.g('rang'), T.g('victoire'), T.g('stat_parties'), T.g('stat_top3'), T.g('stat_meilleurRang'), T.g('message')]);
  verifier('tempsPhase = compte à rebours des résultats (1..20)', n('tempsPhase') >= 1 && n('tempsPhase') <= 20, T.g('tempsPhase'));
  verifier('« evt phase » 8 émis l’image suivante (phasePrec = 8)', Number(local('phasePrec')) === 8, local('phasePrec'));
  // arrivée pendant les résultats : un joueur resté en « chargement » attend la manche suivante ; sinon spectateur
  T.set('etat', 5); T.set('ecran', 'chargement'); setLocal('tPret', 0); T.pas(3);
  verifier('résultats + écran chargement : le joueur attend (etat 5, écran conservé)', n('etat') === 5 && T.g('ecran') === 'chargement', [T.g('etat'), T.g('ecran')]);
  T.set('ecran', 'salon'); T.pas(2);
  verifier('résultats + Jouer hors attente : spectateur (etat 4, ecran spectateur)', n('etat') === 4 && T.g('ecran') === 'spectateur', [T.g('etat'), T.g('ecran')]);
  // « Rejouer » puis « Annuler » (Menus) : etat 9 hors partie → Partie le remet à 5 (sinon publié comme « fin »)
  T.set('etat', 9); T.set('enPartie', 0); T.set('ecran', 'salon'); T.pas(2);
  verifier('etat 9 hors partie (Rejouer puis Annuler) → 5', n('etat') === 5, T.g('etat'));
  T.set('etat', 9); T.set('enPartie', 1); T.set('ecran', 'fin'); T.pas(2);
  // relance automatique après DUREE_RESULTATS : on recule tFin de 30 s → ☁ Partie réécrite, retour à l'île
  setLocal('tFin', Number(local('t')) - 30); T.pas(3);
  const cp3 = String(T.g('☁ Partie'));
  verifier('après les résultats : nouvelle ☁ Partie écrite, phase 0, joueur sur l’île', /^1\d{9}$/.test(cp3) && Math.abs(Number(cp3.slice(1, 6)) - now()) <= 2 && n('phase') === 0 && n('etat') === 8 && n('finManche') === 0, [cp3, T.g('phase'), T.g('etat'), T.g('finManche')]);
  // victoire : nouvelle manche Solo, riko meurt → je suis le dernier vivant
  T.set('☁ Partie', partie(100, 1, 0, 7)); T.pas(3); T.set('altitude', 0); T.pas(3);
  T.set('☁ J2', paquet({ x: 10, y: 10, nom: nom('riko'), elims: 2 }));
  T.set('☁ J3', paquet({ x: 12, y: 12, nom: nom('zed'), etat: 2, pv: 0, morts: 1 })); T.pas(4);
  verifier('nouvelle manche : vivant après atterrissage, finManche 0, victoire 0', n('etat') === 1 && n('finManche') === 0 && n('victoire') === 0 && n('rang') === 0, [T.g('etat'), T.g('finManche'), T.g('victoire'), T.g('rang')]);
  T.set('☁ J2', paquet({ x: 10, y: 10, nom: nom('riko'), etat: 2, pv: 0, morts: 1, tueur: 1 })); T.pas(8);
  verifier('dernier vivant : Victoire Royale (rang 1, victoire 1, stat_victoires 1, message)', n('rang') === 1 && n('victoire') === 1 && n('stat_victoires') === 1 && T.g('message') === 'victoire' && n('finManche') === 1 && n('etat') === 9, [T.g('rang'), T.g('victoire'), T.g('stat_victoires'), T.g('message'), T.g('etat')]);
  verifier('stat_meilleurRang = 1, stat_parties = 2', n('stat_meilleurRang') === 1 && n('stat_parties') === 2, [T.g('stat_meilleurRang'), T.g('stat_parties')]);
  // Rumble : pas de fin anticipée
  T.set('☁ Partie', partie(100, 5, 0, 8)); T.pas(3); T.set('altitude', 0); T.pas(3);
  T.set('☁ J2', paquet({ x: 10, y: 10, nom: nom('riko'), etat: 2, pv: 0, morts: 2 })); T.pas(8);
  verifier('Rumble : la manche continue avec un seul vivant', n('finManche') === 0 && n('vivants') === 1 && n('phase') === 2, [T.g('finManche'), T.g('vivants'), T.g('phase')]);

  // (g) Tempête éclair (ltm 3) : durées halvées
  T.set('☁ J2', 0); T.set('☁ J3', 0);
  T.set('☁ Partie', partie(15, 5, 3, 9)); T.pas(3);
  verifier('ltm 3 : t = 15 → déjà la phase bus (12,5..22,5)', n('phase') === 1 && n('ltm') === 3 && n('etat') === 6, [T.g('phase'), T.g('ltm'), T.g('etat')]);
  T.set('☁ Partie', partie(50, 5, 3, 9)); T.pas(3);
  verifier('ltm 3 : t = 50 → phase 2 en rétrécissement (37,5..52,5)', n('phase') === 2 && n('zoneR') < 30 && n('tempsAvantZone') === 0, [T.g('phase'), T.g('zoneR'), T.g('tempsAvantZone')]);

  // (i) dernière phase : zone en mouvement, retardataire spectateur
  T.set('☁ Partie', partie(215, 5, 0, 9)); T.pas(3);
  const zx1 = n('zoneX'), zy1 = n('zoneY');
  verifier('t = 215 : phase 6, zoneEnMouvement 1, zoneDegats 10', n('phase') === 6 && n('zoneEnMouvement') === 1 && n('zoneDegats') === 10, [T.g('phase'), T.g('zoneEnMouvement'), T.g('zoneDegats')]);
  verifier('retardataire en dernière phase → spectateur', n('etat') === 4 && T.g('ecran') === 'spectateur', [T.g('etat'), T.g('ecran')]);
  T.set('☁ Partie', partie(235, 5, 0, 9)); T.pas(3);
  verifier('t = 235 : le centre a bougé et le rayon a baissé', (Math.abs(n('zoneX') - zx1) > 0.01 || Math.abs(n('zoneY') - zy1) > 0.01) && n('zoneR') < 2.5 && n('zoneR') >= 1.5, [zx1, T.g('zoneX'), zy1, T.g('zoneY'), T.g('zoneR')]);

  // manche périmée → ☁ Partie réécrite, retour en île d'attente
  T.set('☁ Partie', partie(400, 5, 0, 9)); T.pas(3);
  const cp2 = String(T.g('☁ Partie'));
  verifier('manche périmée : nouvelle ☁ Partie écrite (debut ≈ maintenant)', /^1\d{9}$/.test(cp2) && Math.abs(Number(cp2.slice(1, 6)) - now()) <= 2, [cp2, now()]);
  verifier('retour en île d’attente (phase 0, etat 8)', n('phase') === 0 && n('etat') === 8, [T.g('phase'), T.g('etat')]);
  // retour au salon : Menus met enPartie = 0 ET etat = 5 ; Partie ne touche pas à etat, elle nettoie ses variables
  T.set('enPartie', 0); T.pas(2);
  verifier('enPartie 0 seul : Partie laisse etat tel quel (8 conservé)', n('etat') === 8, T.g('etat'));
  T.set('etat', 5); T.pas(2);
  verifier('salon (etat 5) : plus d’invulnérabilité ni d’altitude', n('etat') === 5 && n('invulnerable') === 0 && n('altitude') === 0, [T.g('etat'), T.g('invulnerable'), T.g('altitude')]);
  // écrans d'attente de Menus : matchmaking, puis barre de chargement (2,5 s) avant la prise en charge
  gelerMenus(); T.set('ecran', 'matchmaking'); T.set('enPartie', 1); T.pas(3);
  verifier('matchmaking : Partie attend (etat 5, écran conservé)', n('etat') === 5 && T.g('ecran') === 'matchmaking' && n('phase') === 0, [T.g('etat'), T.g('ecran'), T.g('phase')]);
  T.set('ecran', 'chargement'); T.pas(3);
  verifier('chargement : attente de la barre (etat 5)', n('etat') === 5 && T.g('ecran') === 'chargement', [T.g('etat'), T.g('ecran')]);
  setLocal('tPret', 0); T.pas(3);
  verifier('barre terminée : placé sur l’île (etat 8, ecran jeu)', n('etat') === 8 && T.g('ecran') === 'jeu', [T.g('etat'), T.g('ecran')]);
  T.set('enPartie', 0); T.set('etat', 5); T.pas(2);
  // écran carte : les scripts de dessin tournent sans erreur (pas de rendu en VM)
  T.set('ecran', 'carte'); T.pas(3);
  verifier('écran carte : aucune erreur VM', T.erreurs.length === 0, T.erreurs);
  // Duo : équipe calculée depuis l'emplacement
  T.set('☁ Partie', partie(5, 2, 0, 11)); T.pas(3);
  verifier('Duo : monEquipe = plafond(1 / 2) = 1', n('monEquipe') === 1 && n('mode') === 2, [T.g('monEquipe'), T.g('mode')]);
  T.set('remplissage', 0); T.pas(2);
  verifier('sans remplissage : monEquipe 0', n('monEquipe') === 0, T.g('monEquipe'));
  // reconnexion en cours de combat : mon paquet (etat 1) encore frais sur l'emplacement 1, manche à t = 100
  T.set('☁ J1', Pq.paquet({ x: 9.5, y: 9.5, pv: 60, battement: now(), etat: 1, nom: nom('antoine'), elims: 3 }));
  T.set('☁ Partie', partie(100, 5, 0, 21)); T.set('enPartie', 0); T.set('ecran', 'connexion');
  T.drapeau(); T.pas(10);
  verifier('reconnexion : reprise en jeu sans replacement (etat 1, px 9,5, enPartie 1, ecran jeu)', n('reconnexion') === 1 && n('etat') === 1 && Math.abs(n('px') - 9.5) < 1e-6 && n('enPartie') === 1 && T.g('ecran') === 'jeu' && n('phase') === 2, [T.g('reconnexion'), T.g('etat'), T.g('px'), T.g('enPartie'), T.g('ecran'), T.g('phase')]);
};
