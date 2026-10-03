// Scénario : bots de remplissage (sprite Bots). Les bots rejoignent pendant l'attente pré-partie (île), en temps
// réel et un par un ; puis ☁ Partie est avancée en combat : paquets, décodage, déplacement, tir sur moi, vrai joueur
// qui reprend un emplacement, bot éliminé par mon tir, nouvelle manche, param_bots = 0.
const { chargeurPaquets } = require('../vm_lib');
module.exports = async (T, verifier) => {
  const Pq = chargeurPaquets();
  const nom = (t) => Pq.codeNom(t);
  const now = () => Math.floor(Number(T.g('maintenant')));
  const n = (v) => Number(T.g(v));
  const pad = (v, k) => String(v).padStart(k, '0').slice(-k);
  const partie = (t, mode = 5, ltm = 0, graine = 42) => '1' + pad((now() - t + 100000) % 100000, 5) + mode + ltm + pad(graine, 2);
  const paquet = (o) => Pq.paquet(Object.assign({ pv: 100, battement: now(), etat: 1, niveau: 7 }, o));
  // fait tourner la VM (temps réel) jusqu'à ce que la condition soit vraie ou que `ms` millisecondes soient écoulées
  const attendre = (cond, ms) => { const t0 = Date.now(); while (!cond() && Date.now() - t0 < ms) T.pas(1); return cond(); };
  const actifs = () => T.L('BotsActifs').map(Number).join('');
  const listeBot = (nomL) => T.sprite('Bots').lookupVariableByNameAndType(nomL, 'list').value;
  const LONG = Pq.contrat.longueurPaquet;

  // artefact de vm_lib.js : chaque chargement ajoute un écouteur « unhandledRejection » au processus ; au 11e scénario
  // Node émet un avertissement MaxListenersExceededWarning sur console.error, capté comme « erreur VM »
  for (let i = T.erreurs.length - 1; i >= 0; i--) if (/MaxListenersExceededWarning/.test(T.erreurs[i])) T.erreurs.splice(i, 1);
  T.pseudo('antoine'); T.souris(0, 0, false); T.drapeau(); T.pas(8);
  verifier('connecté sur l’emplacement 1', n('monSlot') === 1 && n('connecte') === 1, [T.g('monSlot'), T.g('connecte')]);
  verifier('hors partie : aucun bot', n('nbBots') === 0 && actifs() === '000000', [T.g('nbBots'), actifs()]);
  verifier('difficulté par défaut : 2 (normal)', n('bots_difficulte') === 2, T.g('bots_difficulte'));

  // ---- île d'attente : les bots arrivent un par un (≈ 1,5 s + 0,6 s par emplacement) ----
  T.set('enPartie', 1); T.pas(3);
  verifier('île d’attente (etat 8, phase 0), pas encore de bot', n('etat') === 8 && n('phase') === 0 && n('nbBots') === 0, [T.g('etat'), T.g('phase'), T.g('nbBots')]);
  attendre(() => n('nbBots') >= 1, 4000);
  const t1 = Date.now();
  verifier('premier bot arrivé (≈ 1,5-2 s d’attente)', n('nbBots') >= 1, T.g('nbBots'));
  attendre(() => n('nbBots') === 5, 8000);
  verifier('5 bots sur les emplacements libres : nbBots 5, BotsActifs 011111', n('nbBots') === 5 && actifs() === '011111', [T.g('nbBots'), actifs()]);
  verifier('arrivée échelonnée (le dernier ≥ 1 s après le premier)', Date.now() - t1 >= 1000, Date.now() - t1);
  T.pas(6);
  const paquets = T.L('BotsPaquets');
  verifier('les 5 paquets ont ' + LONG + ' chiffres et commencent par 1', [1, 2, 3, 4, 5].every(i => /^1\d+$/.test(String(paquets[i])) && String(paquets[i]).length === LONG), paquets.map(p => String(p).length));
  attendre(() => Number(T.L('E_actif')[1]) === 1 && n('👥 Joueurs') === 6, 1500);
  verifier('bots décodés par Reseau : E_actif[1] = 1, 👥 Joueurs = 6', Number(T.L('E_actif')[1]) === 1 && n('👥 Joueurs') === 6, [T.L('E_actif'), T.g('👥 Joueurs')]);
  const noms = T.L('E_nom').slice(1);
  verifier('pseudos décodés, non vides et distincts', noms.every(x => x && !/^J\d$/.test(x)) && new Set(noms).size === 5, noms);
  verifier('niveau 1-40, skin 1-10, état 8 (île), salon = codeSalon', [1, 2, 3, 4, 5].every(i => Number(T.L('E_niveau')[i]) >= 1 && Number(T.L('E_niveau')[i]) <= 40 && Number(T.L('E_skin')[i]) >= 1 && Number(T.L('E_skin')[i]) <= 10 && Number(T.L('E_etat')[i]) === 8 && Number(T.L('E_salon')[i]) === n('codeSalon')), [T.L('E_niveau'), T.L('E_skin'), T.L('E_etat')]);
  verifier('sur l’île, aucun dégât reçu', n('stat_degatsRecus') === 0 && n('❤ PV') === 100, [T.g('stat_degatsRecus'), T.g('❤ PV')]);

  // ---- ☁ Partie avancée en combat (t = 50 : phase 2 en attente, zone = cercle initial) ----
  T.set('☁ Partie', partie(50, 5)); T.pas(4);
  verifier('phase 2 : je suis replacé en retard (parachute), bots conservés', n('phase') === 2 && n('etat') === 7 && n('nbBots') === 5, [T.g('phase'), T.g('etat'), T.g('nbBots')]);
  T.set('altitude', 1); attendre(() => n('etat') === 1, 2000);
  verifier('atterri : etat 1, ecran jeu', n('etat') === 1 && T.g('ecran') === 'jeu', [T.g('etat'), T.g('ecran')]);
  attendre(() => [1, 2, 3, 4, 5].every(i => Number(T.L('E_etat')[i]) === 1), 1500);
  verifier('les bots sont au sol en combat (E_etat 1, PV 100)', [1, 2, 3, 4, 5].every(i => Number(T.L('E_etat')[i]) === 1 && Number(T.L('E_pv')[i]) === 100), [T.L('E_etat'), T.L('E_pv')]);
  const carte = T.L('Carte');
  const cellule = (x, y) => Number(carte[Math.floor(y) * 32 + Math.floor(x)]);
  verifier('bots placés sur des cases libres de la carte', [1, 2, 3, 4, 5].every(i => cellule(Number(T.L('E_x')[i]), Number(T.L('E_y')[i])) === 0), [T.L('E_x'), T.L('E_y')]);
  verifier('vivants = 6 (moi + 5 bots)', n('vivants') === 6, T.g('vivants'));

  // ---- déplacement ----
  const x0 = T.L('E_x').slice(1).map(Number), y0 = T.L('E_y').slice(1).map(Number);
  attendre(() => T.L('E_x').slice(1).some((x, i) => Math.abs(Number(x) - x0[i]) + Math.abs(Number(T.L('E_y')[i + 1]) - y0[i]) > 0.3), 3000);
  verifier('un bot se déplace (E_x / E_y changent)', T.L('E_x').slice(1).some((x, i) => Math.abs(Number(x) - x0[i]) + Math.abs(Number(T.L('E_y')[i + 1]) - y0[i]) > 0.3), [x0, T.L('E_x')]);

  // ---- un bot en vue me tire dessus : bot 2 placé 3 cases devant moi ----
  T.set('px', 16.5); T.set('py', 4.5); T.set('dir', 90); T.set('surbouclier', 0); T.set('🛡 Bouclier', 0);
  listeBot('bx')[1] = 16.5; listeBot('by')[1] = 7.5; listeBot('bcx')[1] = 16.5; listeBot('bcy')[1] = 7.5; listeBot('bPatience')[1] = 1e9;
  T.pas(2);
  const recus0 = n('stat_degatsRecus');
  attendre(() => Number(T.L('E_cible')[1]) === 1 && Number(T.L('E_seq')[1]) > 0, 9000);
  verifier('le bot 2 me tire dessus : cible = 1 (moi), dégâts 8-17, numéro de tir > 0', Number(T.L('E_cible')[1]) === 1 && Number(T.L('E_degats')[1]) >= 8 && Number(T.L('E_degats')[1]) <= 17 && Number(T.L('E_seq')[1]) > 0, [T.L('E_cible')[1], T.L('E_degats')[1], T.L('E_seq')[1]]);
  attendre(() => n('stat_degatsRecus') > recus0, 1500);
  // (le surbouclier, rechargé vite dans la VM sans rendu, peut absorber le coup : on vérifie les dégâts reçus)
  verifier('dégâts reçus appliqués par Joueur (stat_degatsRecus augmente)', n('stat_degatsRecus') > recus0, [recus0, T.g('stat_degatsRecus'), T.g('❤ PV'), T.g('surbouclier')]);
  verifier('bruit de tir enregistré', T.L('Bruits').length >= 1, T.L('Bruits'));
  verifier('le bot poursuit : il s’est approché et s’arrête à ≈ 2,5 cases', Number(T.L('E_y')[1]) <= 7.6 && Number(T.L('E_y')[1]) >= 6.6, T.L('E_y')[1]);

  // ---- un vrai joueur reprend l'emplacement 3 ----
  T.set('☁ J3', paquet({ x: 10, y: 10, nom: nom('riko') }));
  attendre(() => Number(T.L('BotsActifs')[2]) === 0 && T.L('E_nom')[2] === 'riko', 1500);
  verifier('vrai paquet frais sur ☁ J3 → bot 3 désactivé, nbBots 4, riko décodé', Number(T.L('BotsActifs')[2]) === 0 && n('nbBots') === 4 && T.L('E_nom')[2] === 'riko', [actifs(), T.g('nbBots'), T.L('E_nom')[2]]);

  // ---- mes tirs sur le bot 2 (globales cible / seq / degats = mon dernier tir) : 99 puis 99 dégâts ----
  const elims0 = n('💀 Éliminations');
  T.set('cible', 2); T.set('seq', (n('seq') + 1) % 100); T.set('degats', 99);
  attendre(() => Number(T.L('E_pv')[1]) === 1, 1500);
  verifier('premier tir (99) : bot 2 à 1 PV, toujours vivant', Number(T.L('E_pv')[1]) === 1 && Number(T.L('E_etat')[1]) === 1, [T.L('E_pv')[1], T.L('E_etat')[1]]);
  T.pas(8);
  // un même numéro de tir n'est pas appliqué deux fois (un autre bot peut, lui, l'achever : tueur ≠ 1)
  verifier('même numéro de tir : pas de double application (le bot 2 n’est pas éliminé par moi)', !(Number(T.L('E_etat')[1]) === 2 && Number(T.L('E_tueur')[1]) === 1), [T.L('E_etat')[1], T.L('E_tueur')[1], T.L('E_pv')[1]]);
  T.set('seq', (n('seq') + 1) % 100);
  attendre(() => Number(T.L('E_etat')[1]) === 2, 1500);
  verifier('second tir : bot 2 éliminé (E_etat 2, tueur = 1, morts 1)', Number(T.L('E_etat')[1]) === 2 && Number(T.L('E_tueur')[1]) === 1 && Number(T.L('E_morts')[1]) === 1, [T.L('E_etat')[1], T.L('E_tueur')[1], T.L('E_morts')[1]]);
  verifier('élimination créditée (💀 Éliminations + 1)', n('💀 Éliminations') === elims0 + 1, [elims0, T.g('💀 Éliminations')]);
  verifier('journal : « Tu as éliminé <bot> »', T.L('Journal').some(l => /Tu as éliminé/.test(l)), T.L('Journal'));

  // ---- difficulté réglable ----
  T.set('bots_difficulte', 3); T.pas(2);
  verifier('difficulté 3 : précision 75 %, portée 11', Number(T.l('Bots', 'prec')) === 75 && Number(T.l('Bots', 'portee')) === 11, [T.l('Bots', 'prec'), T.l('Bots', 'portee')]);
  T.set('bots_difficulte', 7); T.pas(2);
  verifier('valeur invalide → remise à 2', n('bots_difficulte') === 2 && Number(T.l('Bots', 'prec')) === 55, [T.g('bots_difficulte'), T.l('Bots', 'prec')]);

  // ---- nouvelle manche : bots réinitialisés (identité conservée) ----
  const nom2 = T.L('E_nom')[1];
  T.diffuser('evt nouvelle manche'); T.pas(2);
  attendre(() => Number(T.L('E_etat')[1]) === 1 && Number(T.L('E_pv')[1]) === 100, 1500);
  verifier('« evt nouvelle manche » : bot 2 de nouveau vivant, PV 100, morts 0, même pseudo', Number(T.L('E_etat')[1]) === 1 && Number(T.L('E_pv')[1]) === 100 && Number(T.L('E_morts')[1]) === 0 && T.L('E_nom')[1] === nom2, [T.L('E_etat')[1], T.L('E_pv')[1], T.L('E_morts')[1], nom2, T.L('E_nom')[1]]);
  verifier('toujours 4 bots (emplacement 3 au vrai joueur)', n('nbBots') === 4 && actifs() === '010111', [T.g('nbBots'), actifs()]);

  // ---- param_bots = 0 ----
  T.set('param_bots', 0); T.pas(3);
  verifier('param_bots = 0 → nbBots 0, BotsActifs 000000', n('nbBots') === 0 && actifs() === '000000' && T.L('BotsPaquets').every(p => Number(p) === 0), [T.g('nbBots'), actifs()]);
  attendre(() => n('👥 Joueurs') === 2, 1500);
  verifier('Reseau ne voit plus que riko (👥 Joueurs 2)', n('👥 Joueurs') === 2, T.g('👥 Joueurs'));
  T.set('param_bots', 1); T.pas(6);
  verifier('en combat, personne ne rejoint (nbBots reste 0)', n('nbBots') === 0, T.g('nbBots'));
  verifier('aucune erreur VM', T.erreurs.length === 0, T.erreurs.slice(0, 3));
};
