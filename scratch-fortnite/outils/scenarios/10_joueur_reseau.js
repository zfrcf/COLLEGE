// Scénario : réseau + joueur (sans menus/partie) : on force l'écran « jeu » et l'état « vivant ».
const { chargeurPaquets } = require('../vm_lib');
module.exports = async (T, verifier) => {
  const Pq = chargeurPaquets();
  const nom = (t) => Pq.codeNom(t);
  const now = () => Math.floor(Number(T.g('maintenant')));
  const paquet = (o) => Pq.paquet(Object.assign({ pv: 100, battement: now(), etat: 1, niveau: 7 }, o));
  T.pseudo('antoine'); T.souris(0, 0, false); T.drapeau(); T.set('param_bots', 0); T.pas(8);   // pas de bot sur les emplacements simulés
  // le lama à butin (position selon la graine) est marqué « pris » : un panneau 3D visible demande un redessin à chaque
  // passe du séquenceur, ce qui ralentit le décodage réseau (un emplacement par passe) dans la VM sans rendu
  const cacherLama = () => { Object.values(T.stage.variables).find(x => x.name === 'LamasPris').value = [1]; };
  cacherLama();
  verifier('connecté sur l’emplacement 1', Number(T.g('monSlot')) === 1 && Number(T.g('connecte')) === 1, [T.g('monSlot'), T.g('connecte')]);
  verifier('paquet de ' + Pq.contrat.longueurPaquet + ' chiffres publié', String(T.g('☁ J1')).length === Pq.contrat.longueurPaquet, String(T.g('☁ J1')).length);
  // placer en jeu, position dégagée, regard +y
  T.set('ecran', 'jeu'); T.set('etat', 1); T.set('px', 16.5); T.set('py', 4.5); T.set('dir', 90); T.set('zoneX', 16.5); T.set('zoneY', 10.5); T.set('zoneR', 30); T.set('phase', 2);
  T.pas(3);
  // déplacement
  const y0 = Number(T.g('py'));
  T.touche('z', true); T.pas(5); T.touche('z', false); T.pas(1);
  verifier('avance avec Z', Number(T.g('py')) > y0 + 0.2, [y0, T.g('py')]);
  verifier('distance parcourue comptée', Number(T.g('stat_distance')) > 0.2, T.g('stat_distance'));
  // adversaire devant à 3 cases, nom « riko »
  T.set('☁ J2', paquet({ x: 16.5, y: Number(T.g('py')) + 2, dir: 270, nom: nom('riko'), bouclier: 20 })); T.pas(3);
  verifier('adversaire décodé (nom, niveau, actif)', T.L('E_nom')[1] === 'riko' && Number(T.L('E_niveau')[1]) === 7 && Number(T.L('E_actif')[1]) === 1, [T.L('E_nom')[1], T.L('E_niveau')[1], T.L('E_actif')[1]]);
  for (let i = 0; i < 20 && Number(T.g('👥 Joueurs')) < 2; i++) T.pas(1);
  verifier('2 joueurs comptés', Number(T.g('👥 Joueurs')) === 2, T.g('👥 Joueurs'));
  // tir pistolet
  const mun0 = Number(T.L('Quantites')[0]);
  T.souris(0, 0, true); T.pas(1); T.souris(0, 0, false); T.pas(1);
  verifier('tir : cible 2, dégâts 20, munition consommée', Number(T.g('cible')) === 2 && Number(T.g('degats')) === 20 && Number(T.L('Quantites')[0]) === mun0 - 1, [T.g('cible'), T.g('degats'), T.L('Quantites')[0]]);
  verifier('chiffre de dégâts affiché (18 car.)', T.L('DegatsAffiches').length === 1 && String(T.L('DegatsAffiches')[0]).length === 18, T.L('DegatsAffiches'));
  T.pas(6);
  verifier('paquet mis à jour avec le tir', String(T.g('☁ J1')).slice(Pq.contrat.pos.cible[0] - 1, Pq.contrat.pos.cible[0]) === '2', String(T.g('☁ J1')));
  // l'adversaire me tire dessus : 30 dégâts avec un bouclier de 0 → PV 70
  T.set('☁ J2', paquet({ x: 16.5, y: Number(T.g('py')) + 2, dir: 270, nom: nom('riko'), cible: 1, seq: 1, degats: 30, arme: 1 })); T.pas(3);
  verifier('dégâts reçus appliqués (PV 70)', Number(T.g('❤ PV')) === 70, T.g('❤ PV'));
  verifier('flèche de dégâts : angle relatif ~0 (devant)', Math.abs(((Number(T.g('evt_angle')) + 180) % 360) - 180) < 15, T.g('evt_angle'));
  // bruit de tir enregistré
  verifier('bruit de tir listé', T.L('Bruits').length >= 1, T.L('Bruits'));
  // surbouclier absorbe d'abord
  T.set('surbouclier', 20); T.set('☁ J2', paquet({ x: 16.5, y: Number(T.g('py')) + 2, dir: 270, nom: nom('riko'), cible: 1, seq: 2, degats: 30, arme: 1 })); T.pas(3);
  verifier('surbouclier absorbe 20, PV 60', Number(T.g('surbouclier')) === 0 && Number(T.g('❤ PV')) === 60, [T.g('surbouclier'), T.g('❤ PV')]);
  // l'adversaire meurt tué par moi → élimination + journal
  T.set('☁ J2', paquet({ x: 16.5, y: 8, dir: 270, nom: nom('riko'), pv: 0, tueur: 1, morts: 1, etat: 2, cible: 1, seq: 2, degats: 30, arme: 1 })); T.pas(3);
  verifier('élimination créditée', Number(T.g('💀 Éliminations')) === 1 && Number(T.g('stat_elims')) === 1, T.g('💀 Éliminations'));
  verifier('journal : « Tu as éliminé riko »', T.L('Journal').some(l => /éliminé riko/.test(l)), T.L('Journal'));
  // émote reçue
  T.set('☁ J2', paquet({ x: 16.5, y: 8, dir: 270, nom: nom('riko'), emote: 2, emoteSeq: 1 })); T.pas(3);
  verifier('émote reçue : E_emoteFin dans le futur', Number(T.L('E_emoteFin')[1]) > 0, T.L('E_emoteFin')[1]);
  // chat rapide (mode 5 = Rumble : tout le monde)
  T.set('mode', 5);
  T.set('☁ J2', paquet({ x: 16.5, y: 8, dir: 270, nom: nom('riko'), chat: 2, chatSeq: 1 })); T.pas(3);
  verifier('message rapide reçu « riko : Bien joué ! »', T.L('Chat').some(l => /riko : Bien joué/.test(l)), T.L('Chat'));
  // ping (Rumble : visible)
  T.set('☁ J2', paquet({ x: 16.5, y: 8, dir: 270, nom: nom('riko'), pingX: 12, pingY: 20, pingSeq: 1 }));
  for (let i = 0; i < 30 && T.L('Pings').length === 0; i++) T.pas(1);
  verifier('ping listé (15 car., emplacement 2)', T.L('Pings').length === 1 && String(T.L('Pings')[0]).length === 15 && String(T.L('Pings')[0])[0] === '2', T.L('Pings'));
  // coffre : se placer près du coffre 1 (3.5, 28.5) et tenir E 1,2 s (graine 9 : tirage 2 = médikit + bandages)
  T.set('graine', 9); T.set('px', 3.5); T.set('py', 27.6); T.set('dir', 90); T.pas(1);
  T.touche('e', true); for (let i = 0; i < 200 && T.L('CoffresPris').length === 0; i++) T.pas(1); T.touche('e', false); T.pas(2);
  verifier('coffre ouvert (interaction maintenue)', T.L('CoffresPris').length === 1, T.L('CoffresPris'));
  verifier('butin ramassé (inventaire rempli ou munitions)', T.L('Inventaire').filter(x => Number(x) > 0).length >= 2 || Number(T.g('munitions_legeres')) > 24, T.L('Inventaire'));
  verifier('statistique coffres', Number(T.g('stat_coffres')) === 1, T.g('stat_coffres'));

  // ---- contenu façon Fortnite : nouvelles armes, raretés, lance-grenades, rechargement par type ----------------
  const Lset = (nomL, vals) => { const v = Object.values(T.stage.variables).find(x => x.name === nomL); v.value = vals; };
  const inv = () => T.L('Inventaire').map(Number), rar = () => T.L('Raretes').map(Number), qte = () => T.L('Quantites').map(Number);
  const chrono = () => T.vm.runtime.ioDevices.clock.projectTimer();
  Lset('Inventaire', [1, 0, 0, 0, 0]); Lset('Quantites', [12, 0, 0, 0, 0]); Lset('Raretes', [1, 1, 1, 1, 1]); T.appui('1', 1); T.pas(1);
  // coffres forcés (graine 9) : coffre 4 → tirage 7 (fusil d'assaut + potion), rareté 9 → épique ; coffre 5 → tirage 6
  // (lance-grenades, peu commune) ; coffre 6 → tirage 5 (pistolet-mitrailleur épique + 24 légères)
  const ouvrirCoffre = (x, y, d) => { T.set('px', x); T.set('py', y); T.set('dir', d); T.pas(1); const n0 = T.L('CoffresPris').length; T.touche('e', true); for (let i = 0; i < 200 && T.L('CoffresPris').length === n0; i++) T.pas(1); T.touche('e', false); T.pas(2); };
  ouvrirCoffre(21.4, 21.5, 180);
  verifier('coffre 4 : fusil d’assaut (code 4) épique, chargeur 30, en case 2', inv()[1] === 4 && rar()[1] === 4 && qte()[1] === 30, [inv(), rar(), qte()]);
  verifier('notification « + Fusil d’assaut (Épique) »', T.L('Notifications').some(l => /\+ Fusil d'assaut \(Épique\)/.test(l)), T.L('Notifications'));
  verifier('potion de bouclier (code 10) ramassée, rareté rare (bleue)', inv()[2] === 10 && rar()[2] === 3, [inv(), rar()]);
  const roq0 = Number(T.g('munitions_roquettes'));
  ouvrirCoffre(17.4, 15.5, 180);
  verifier('coffre 5 : lance-grenades (code 6) peu commun, 4 roquettes en réserve en plus', inv()[3] === 6 && rar()[3] === 2 && qte()[3] === 4 && Number(T.g('munitions_roquettes')) === roq0 + 4, [inv(), rar(), T.g('munitions_roquettes')]);
  const leg0 = Number(T.g('munitions_legeres'));
  ouvrirCoffre(5.5, 10.4, 270);
  verifier('coffre 6 : pistolet-mitrailleur (code 5) épique, chargeur 25, +24 légères', inv()[4] === 5 && rar()[4] === 4 && qte()[4] === 25 && Number(T.g('munitions_legeres')) === leg0 + 24, [inv(), rar(), qte(), T.g('munitions_legeres')]);
  // paquet : champ « arme » = code de l'arme tenue (5 pour le PM), 0 pour un consommable
  T.appui('5', 1); T.pas(1); T.touche('e', false);
  verifier('armeTenue = 5 (PM) et champ « arme » du paquet = 5', Number(T.g('armeTenue')) === 5 && Number(T.g('armeNum')) === 5, [T.g('armeTenue'), T.g('armeNum')]);
  T.appui('3', 1); T.pas(1);
  verifier('potion tenue : armeTenue = 0, nom « Potion de bouclier »', Number(T.g('armeTenue')) === 0 && T.g('🎯 Arme') === 'Potion de bouclier', [T.g('armeTenue'), T.g('🎯 Arme')]);
  // fusil d'assaut épique : dégâts 30 × 1,3 = 39, cadence 0,14 s (≥ 3 tirs en 0,6 s) sur riko à 2 cases
  T.set('px', 16.5); T.set('py', 4.5); T.set('dir', 90); T.set('mode', 5); T.set('monEquipe', 0); T.set('ltm', 0); T.pas(1);
  T.set('☁ J2', paquet({ x: 16.5, y: 6.5, dir: 270, nom: nom('riko'), etat: 1, pv: 100 }));
  for (let i = 0; i < 30 && !(Number(T.L('E_actif')[1]) === 1 && Number(T.L('E_etat')[1]) === 1); i++) T.pas(1);
  T.appui('2', 1); T.pas(1);
  const seq0 = Number(T.g('seq'));
  const tA = Date.now(); T.souris(0, 0, true); while (Date.now() - tA < 650) T.pas(1); T.souris(0, 0, false); T.pas(1);
  const tirsFA = 30 - qte()[1];
  verifier('fusil d’assaut : rafale de 3 à 7 tirs en 0,65 s (cadence 0,14 s)', tirsFA >= 3 && tirsFA <= 7, [tirsFA, qte()]);
  verifier('fusil d’assaut épique : dégâts 39 sur la cible 2, seq avancé', Number(T.g('cible')) === 2 && Number(T.g('degats')) === 39 && Number(T.g('seq')) > seq0, [T.g('cible'), T.g('degats'), T.g('seq'), seq0]);
  // lance-grenades : impact sur le mur (16, 8) à ≈ 3,5 cases ; riko (16.5, 6.5) et zed (17.8, 7.2) à moins de 2,5 cases,
  // kai (16.5, 12) hors du rayon → 2 cibles : riko tout de suite, zed 0,15 s plus tard (file locale)
  T.set('☁ J3', paquet({ x: 17.8, y: 7.2, dir: 270, nom: nom('zed'), etat: 1, pv: 100 })); T.pas(2);
  T.set('☁ J4', paquet({ x: 16.5, y: 12, dir: 270, nom: nom('kai'), etat: 1, pv: 100 })); T.pas(2);
  for (let i = 0; i < 30 && !(Number(T.L('E_actif')[2]) === 1 && Number(T.L('E_actif')[3]) === 1); i++) T.pas(1);
  T.appui('4', 1); T.pas(1);
  const prof = Number(T.L('Profondeur')[Math.round(Number(T.g('colonnes')) / 2) - 1]);
  verifier('profondeur au centre ≈ 3,5 (mur en (16, 8))', prof > 3 && prof < 4, prof);
  T.set('seq', 10); T.souris(0, 0, true); T.pas(1); T.souris(0, 0, false); T.pas(1);
  verifier('lance-grenades : 1re cible riko (2), dégâts 99 (100 × 1,1 plafonné), seq 11', Number(T.g('cible')) === 2 && Number(T.g('degats')) === 99 && Number(T.g('seq')) === 11, [T.g('cible'), T.g('degats'), T.g('seq')]);
  verifier('2e cible en file locale (zed), kai hors rayon', T.l('Joueur', 'fileTirs').length === 1 && String(T.l('Joueur', 'fileTirs')[0])[0] === '3', T.l('Joueur', 'fileTirs'));
  verifier('explosion : secousse 10 px et flash', Number(T.g('secousseForce')) === 10 && Number(T.g('flash')) > chrono(), [T.g('secousseForce'), T.g('flash')]);
  const tB = Date.now(); while (Date.now() - tB < 400 && Number(T.g('cible')) !== 3) T.pas(1);
  verifier('0,15 s plus tard : cible zed (3), seq 12, file vide', Number(T.g('cible')) === 3 && Number(T.g('seq')) === 12 && T.l('Joueur', 'fileTirs').length === 0, [T.g('cible'), T.g('seq'), T.l('Joueur', 'fileTirs')]);
  verifier('grenades : chargeur 4 → 3', qte()[3] === 3, qte());
  // rechargement par type de munitions : PM (légères) puis lance-grenades (roquettes)
  T.appui('5', 1); T.pas(1); Lset('Quantites', [qte()[0], qte()[1], qte()[2], qte()[3], 5]);
  const leg1 = Number(T.g('munitions_legeres'));
  T.appui('r', 1); T.pas(1);
  verifier('PM : rechargement lancé (1,8 s)', Number(T.g('rechargeFin')) > chrono() && Math.abs(Number(T.g('rechargeFin')) - Number(T.g('rechargeDebut')) - 1.8) < 0.05, [T.g('rechargeDebut'), T.g('rechargeFin')]);
  T.set('rechargeFin', 0.001); T.pas(2);
  verifier('PM rechargé à 25 avec 20 légères en moins', qte()[4] === 25 && Number(T.g('munitions_legeres')) === leg1 - 20, [qte(), leg1, T.g('munitions_legeres')]);
  T.appui('4', 1); T.pas(1); const roq1 = Number(T.g('munitions_roquettes'));
  T.appui('r', 1); T.pas(1); T.set('rechargeFin', 0.001); T.pas(2);
  verifier('lance-grenades rechargé à 4 avec 1 roquette en moins', qte()[3] === 4 && Number(T.g('munitions_roquettes')) === roq1 - 1, [qte(), roq1, T.g('munitions_roquettes')]);
  // potion de bouclier (code 10) : utilisation 5 s → +50 bouclier
  T.set('🛡 Bouclier', 0); T.appui('3', 1); T.pas(1); T.souris(0, 0, true); T.pas(1); T.souris(0, 0, false); T.pas(1);
  verifier('potion : utilisation lancée (objet 10)', Number(T.g('utilisationObjet')) === 10 && Number(T.g('utilisationFin')) > chrono(), [T.g('utilisationObjet'), T.g('utilisationFin')]);
  T.set('utilisationFin', 0.001); T.pas(2);
  verifier('potion bue : bouclier 50, case 3 vidée (rareté remise à 1)', Number(T.g('🛡 Bouclier')) === 50 && inv()[2] === 0 && rar()[2] === 1, [T.g('🛡 Bouclier'), inv(), rar()]);
  T.appui('1', 1); T.pas(1); T.set('☁ J3', paquet({ x: 17.8, y: 7.2, dir: 270, nom: nom('zed'), etat: 2, pv: 0 })); T.set('☁ J4', paquet({ x: 16.5, y: 12, dir: 270, nom: nom('kai'), etat: 2, pv: 0 })); T.pas(3);
  // pioche : face au mur du fort (x=1..4,y=26..29 : brique « 3 ») → pierre
  T.set('px', 3.5); T.set('py', 27.9); T.set('dir', 90); T.pas(1);   // mur de brique en (3,29)
  T.touche('f', true); T.pas(1); T.touche('f', false);
  const pierre0 = Number(T.g('mat_pierre'));
  T.souris(0, 0, true); T.pas(2); T.souris(0, 0, false); T.pas(1);
  verifier('pioche : pierre récoltée', Number(T.g('mat_pierre')) > pierre0, [pierre0, T.g('mat_pierre'), T.g('armeNum')]);
  // construction : bois insuffisant → notification ; pierre suffisante → mur
  T.set('mat_pierre', 50); T.set('materiauActif', 2); T.set('px', 16.5); T.set('py', 4.5); T.set('dir', 90); T.set('☁ Construction', 0); T.set('☁ Construction2', 0); T.pas(1);
  T.appui('b', 2); T.pas(2);
  verifier('mur de pierre construit devant (16,6)', Number(T.L('Carte')[6 * 32 + 16]) === 1 && Number(T.g('mat_pierre')) === 40, [T.L('Carte')[6 * 32 + 16], T.g('mat_pierre')]);
  verifier('entrée publiée « 2 16 06 »', String(T.g('☁ Construction')) === '121606', T.g('☁ Construction'));
  // édition : retirer le mur
  T.appui('g', 2); T.pas(3);
  verifier('mur retiré et suppression publiée', Number(T.L('Carte')[6 * 32 + 16]) === 0 && String(T.g('☁ Construction')) === '12160601606', T.g('☁ Construction'));
  // synchronisation : un autre joueur construit en (10,10) bois, via Construction2
  T.set('☁ Construction2', '131010');
  for (let i = 0; i < 30 && Number(T.L('Carte')[10 * 32 + 10]) !== 4; i++) T.pas(1);
  verifier('mur distant appliqué depuis ☁ Construction2', Number(T.L('Carte')[10 * 32 + 10]) === 4, T.L('Carte')[10 * 32 + 10]);
  // tempête : hors zone → dégâts par seconde sans bouclier
  T.set('🛡 Bouclier', 50); T.set('zoneX', 60); T.set('zoneR', 10); T.set('zoneDegats', 5); const pv1 = Number(T.g('❤ PV')); T.pas(40);
  verifier('tempête : PV baissent, bouclier intact', Number(T.g('❤ PV')) < pv1 && Number(T.g('🛡 Bouclier')) === 50, [pv1, T.g('❤ PV'), T.g('🛡 Bouclier')]);
  T.set('zoneX', 16.5); T.set('zoneR', 30);
  // mode Duo : mis à terre si un coéquipier est vivant
  // mode Duo imposé via ☁ Partie (Partie recalcule mode et monEquipe à partir de la variable cloud)
  T.set('☁ Partie', '1' + String(now()).padStart(5, '0') + '2' + '0' + '00'); T.pas(3); cacherLama();
  T.set('mode', 2); T.set('monEquipe', 1); T.set('etat', 1); T.set('ecran', 'jeu'); T.set('❤ PV', 30); T.set('🛡 Bouclier', 0); T.set('surbouclier', 0); T.pas(1);
  T.set('☁ J2', paquet({ x: 20, y: 8, dir: 270, nom: nom('riko'), equipe: 1 }));
  T.set('☁ J3', paquet({ x: 16.5, y: 8, dir: 270, nom: nom('zed'), equipe: 2 })); T.pas(3);
  T.set('☁ J3', paquet({ x: 16.5, y: 8, dir: 270, nom: nom('zed'), equipe: 2, cible: 1, seq: 1, degats: 99, arme: 3 }));
  for (let i = 0; i < 40 && Number(T.g('etat')) === 1; i++) T.pas(1);
  verifier('à terre (état 3) au lieu de mourir', Number(T.g('etat')) === 3 && Number(T.g('knockPar')) === 3, [T.g('etat'), T.g('knockPar')]);
  // le coéquipier me réanime (reanime = 1) pendant ~5 s
  T.set('☁ J2', paquet({ x: 16.5, y: 5, dir: 270, nom: nom('riko'), equipe: 1, reanime: 1 }));
  for (let i = 0; i < 400; i++) { T.pas(1); if (Number(T.g('etat')) === 1) break; }
  verifier('réanimé par le coéquipier (PV 30)', Number(T.g('etat')) === 1 && Number(T.g('❤ PV')) === 30, [T.g('etat'), T.g('❤ PV')]);
  // dégâts d'équipe ignorés
  const pv2 = Number(T.g('❤ PV'));
  T.set('☁ J2', paquet({ x: 16.5, y: 5, dir: 270, nom: nom('riko'), equipe: 1, cible: 1, seq: 3, degats: 25, arme: 1 })); T.pas(3);
  verifier('tir allié ignoré', Number(T.g('❤ PV')) === pv2, [pv2, T.g('❤ PV')]);
  // reconnexion : nouveau drapeau avec mon paquet encore frais sur l'emplacement 1
  const monPaquet = String(T.g('☁ J1'));
  T.drapeau(); T.pas(8);
  verifier('reconnexion sur mon emplacement', Number(T.g('monSlot')) === 1 && Number(T.g('reconnexion')) === 1, [T.g('monSlot'), T.g('reconnexion'), monPaquet.slice(0, 20)]);
  // record : proposer 7 éliminations / 2 victoires
  T.set('rec_elims', 7); T.set('rec_victoires', 2); T.diffuser('record proposer'); T.pas(4);
  verifier('☁ Record écrit avec mon entrée', String(T.g('☁ Record')).length === 1 + 23 && T.L('Record_elims')[0] == 7, [T.g('☁ Record'), T.L('Record_nom'), T.L('Record_elims')]);
};
