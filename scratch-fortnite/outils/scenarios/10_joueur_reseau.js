// Scénario : réseau + joueur (sans menus/partie) : on force l'écran « jeu » et l'état « vivant ».
const { chargeurPaquets } = require('../vm_lib');
module.exports = async (T, verifier) => {
  const Pq = chargeurPaquets();
  const nom = (t) => Pq.codeNom(t);
  const now = () => Math.floor(Number(T.g('maintenant')));
  const paquet = (o) => Pq.paquet(Object.assign({ pv: 100, battement: now(), etat: 1, niveau: 7 }, o));
  T.pseudo('antoine'); T.souris(0, 0, false); T.drapeau(); T.pas(8);
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
  T.set('☁ J2', paquet({ x: 16.5, y: 8, dir: 270, nom: nom('riko'), pingX: 12, pingY: 20, pingSeq: 1 })); T.pas(3);
  verifier('ping listé (15 car., emplacement 2)', T.L('Pings').length === 1 && String(T.L('Pings')[0]).length === 15 && String(T.L('Pings')[0])[0] === '2', T.L('Pings'));
  // coffre : se placer près du coffre 1 (3.5, 28.5) et tenir E 1,2 s
  T.set('px', 3.5); T.set('py', 27.6); T.set('dir', 90); T.pas(1);
  T.touche('e', true); for (let i = 0; i < 200 && T.L('CoffresPris').length === 0; i++) T.pas(1); T.touche('e', false); T.pas(2);
  verifier('coffre ouvert (interaction maintenue)', T.L('CoffresPris').length === 1, T.L('CoffresPris'));
  verifier('butin ramassé (inventaire rempli ou munitions)', T.L('Inventaire').filter(x => Number(x) > 0).length >= 2 || Number(T.g('munitions_legeres')) > 24, T.L('Inventaire'));
  verifier('statistique coffres', Number(T.g('stat_coffres')) === 1, T.g('stat_coffres'));
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
  T.set('☁ Construction2', '131010'); T.pas(3);
  verifier('mur distant appliqué depuis ☁ Construction2', Number(T.L('Carte')[10 * 32 + 10]) === 4, T.L('Carte')[10 * 32 + 10]);
  // tempête : hors zone → dégâts par seconde sans bouclier
  T.set('🛡 Bouclier', 50); T.set('zoneX', 60); T.set('zoneR', 10); T.set('zoneDegats', 5); const pv1 = Number(T.g('❤ PV')); T.pas(40);
  verifier('tempête : PV baissent, bouclier intact', Number(T.g('❤ PV')) < pv1 && Number(T.g('🛡 Bouclier')) === 50, [pv1, T.g('❤ PV'), T.g('🛡 Bouclier')]);
  T.set('zoneX', 16.5); T.set('zoneR', 30);
  // mode Duo : mis à terre si un coéquipier est vivant
  T.set('mode', 2); T.set('monEquipe', 1); T.set('❤ PV', 30); T.set('🛡 Bouclier', 0); T.set('surbouclier', 0);
  T.set('☁ J2', paquet({ x: 20, y: 8, dir: 270, nom: nom('riko'), equipe: 1 }));
  T.set('☁ J3', paquet({ x: 16.5, y: 8, dir: 270, nom: nom('zed'), equipe: 2 })); T.pas(3);
  T.set('☁ J3', paquet({ x: 16.5, y: 8, dir: 270, nom: nom('zed'), equipe: 2, cible: 1, seq: 1, degats: 99, arme: 3 })); T.pas(4);
  verifier('à terre (état 3) au lieu de mourir', Number(T.g('etat')) === 3 && Number(T.g('knockPar')) === 3, [T.g('etat'), T.g('knockPar')]);
  // le coéquipier me réanime (reanime = 1) pendant ~5 s
  T.set('☁ J2', paquet({ x: 16.5, y: 5, dir: 270, nom: nom('riko'), equipe: 1, reanime: 1 }));
  for (let i = 0; i < 60; i++) { T.pas(1); if (Number(T.g('etat')) === 1) break; }
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
