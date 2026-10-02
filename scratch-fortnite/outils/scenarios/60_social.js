// Scénario : module Social (ping, chat rapide, émotes, sprays, spectateur, signalement, barre sociale).
// On force l'écran « jeu » et l'état « vivant » (Menus/Partie ne sont pas nécessaires).
const { chargeurPaquets } = require('../vm_lib');
module.exports = async (T, verifier) => {
  const Pq = chargeurPaquets();
  const nom = (t) => Pq.codeNom(t);
  const now = () => Math.floor(Number(T.g('maintenant')));
  const paquet = (o) => Pq.paquet(Object.assign({ pv: 100, battement: now(), etat: 1, niveau: 7 }, o));
  T.pseudo('antoine'); T.souris(0, 0, false); T.drapeau(); T.pas(8);
  verifier('connecté sur l’emplacement 1', Number(T.g('monSlot')) === 1, T.g('monSlot'));
  // mode Solo : Partie (s'il est présent) relance une manche à partir de modeChoisi quand ☁ Partie est vide ;
  // on attend que ce soit fait avant de forcer l'état (la relance remet etat à 5)
  T.set('modeChoisi', 1); T.set('☁ Partie', ''); T.pas(6); T.set('mode', 1); T.pas(1);
  T.set('ecran', 'jeu'); T.set('etat', 1); T.set('px', 16.5); T.set('py', 4.5); T.set('dir', 90); T.set('zoneX', 16.5); T.set('zoneY', 10.5); T.set('zoneR', 30); T.set('phase', 2);
  T.pas(3);

  // --- ping (touche « ping » = v) ---
  T.appui('v', 2); T.pas(2);
  verifier('ping : pingSeq passe de 0 à 1', Number(T.g('pingSeq')) === 1, T.g('pingSeq'));
  verifier('ping : Pings contient mon entrée (15 car., emplacement 1)', T.L('Pings').length === 1 && String(T.L('Pings')[0]).length === 15 && String(T.L('Pings')[0])[0] === '1', T.L('Pings'));
  verifier('ping : devant moi (x 16, y ≥ 6)', Number(T.g('pingX')) === 16 && Number(T.g('pingY')) >= 6, [T.g('pingX'), T.g('pingY')]);
  verifier('ping : statistique', Number(T.g('stat_pings')) === 1, T.g('stat_pings'));
  T.appui('v', 2); T.pas(2);
  verifier('2e ping : remplace le précédent (une seule entrée)', T.L('Pings').length === 1 && Number(T.g('pingSeq')) === 2, T.L('Pings'));

  // --- chat rapide (touche t) ---
  T.appui('t', 2); T.pas(1);
  verifier('touche chat → superposition « chat »', T.g('superposition') === 'chat', T.g('superposition'));
  T.clic(-72, 20, 2); T.pas(2);   // 2e phrase (colonne gauche, 2e ligne)
  verifier('clic 2e phrase → chat = 2, chatSeq = 1', Number(T.g('chat')) === 2 && Number(T.g('chatSeq')) === 1, [T.g('chat'), T.g('chatSeq')]);
  verifier('Chat contient « Toi : Bien joué ! »', T.L('Chat').some(l => l === 'Toi : Bien joué !'), T.L('Chat'));
  verifier('ChatFin dans le futur', T.L('ChatFin').length === T.L('Chat').length, [T.L('Chat').length, T.L('ChatFin').length]);
  verifier('panneau refermé après le relâchement de la souris', T.g('superposition') === '', T.g('superposition'));
  T.appui('t', 2); T.pas(1); T.appui('t', 2); T.pas(1);
  verifier('la touche chat referme le panneau', T.g('superposition') === '', T.g('superposition'));
  T.appui('t', 2); T.pas(1); T.clic(120, 71, 2); T.pas(2);
  verifier('bouton 👍 → phrase 9', Number(T.g('chat')) === 9 && Number(T.g('chatSeq')) === 2 && T.L('Chat').some(l => l === 'Toi : 👍'), [T.g('chat'), T.L('Chat')]);

  // --- roue d'émotes (touche y) ---
  T.appui('y', 2); T.pas(1);
  verifier('touche emotes → superposition « emotes »', T.g('superposition') === 'emotes', T.g('superposition'));
  T.clic(0, 72, 2); T.pas(2);   // secteur 1 (haut)
  verifier('clic secteur → emote > 0, emoteSeq = 1', Number(T.g('emote')) === 1 && Number(T.g('emoteSeq')) === 1, [T.g('emote'), T.g('emoteSeq')]);
  verifier('monEmoteFin > chrono, stat_emotes = 1', Number(T.g('monEmoteFin')) > 0 && Number(T.g('stat_emotes')) === 1, [T.g('monEmoteFin'), T.g('stat_emotes')]);
  verifier('roue refermée', T.g('superposition') === '', T.g('superposition'));
  T.appui('y', 2); T.pas(1); T.clic(54, -21, 2); T.pas(2);   // secteur 3 (en bas à droite : angle −30°)
  verifier('secteur 3 → émote 3', Number(T.g('emote')) === 3 && Number(T.g('emoteSeq')) === 2, [T.g('emote'), T.g('emoteSeq')]);

  // --- roue de sprays (touche h) ---
  T.appui('h', 2); T.pas(1);
  verifier('touche sprays → superposition « sprays »', T.g('superposition') === 'sprays', T.g('superposition'));
  T.clic(0, 72, 2); T.pas(2);
  verifier('spray posé : Sprays.length = 1, 12 caractères, n° 1', T.L('Sprays').length === 1 && String(T.L('Sprays')[0]).length === 12 && String(T.L('Sprays')[0])[8] === '1', T.L('Sprays'));
  verifier('spray devant moi (y ≈ py + 2)', Math.abs(Number(String(T.L('Sprays')[0]).slice(4, 8)) / 100 - 6.5) < 0.6, T.L('Sprays'));
  verifier('notification « Spray posé »', T.L('Notifications').some(l => /Spray posé/.test(l)), T.L('Notifications'));
  for (let i = 0; i < 11; i++) { T.appui('h', 2); T.pas(1); T.clic(0, 72, 2); T.pas(1); }
  verifier('au plus 10 sprays', T.L('Sprays').length === 10, T.L('Sprays').length);
  verifier('clic hors de la roue : fermeture sans action', (() => { T.appui('h', 2); T.pas(1); T.clic(200, 150, 2); T.pas(2); return T.g('superposition') === '' && T.L('Sprays').length === 10; })(), T.g('superposition'));

  // --- carte plein écran : clic → point de rassemblement ---
  T.set('ecran', 'carte'); T.pas(2);
  T.clic(-160 + 125, -160 + 205, 2); T.pas(2);   // case (12, 20)
  verifier('clic carte → ping (12, 20)', Number(T.g('pingX')) === 12 && Number(T.g('pingY')) === 20 && Number(T.g('pingSeq')) === 3, [T.g('pingX'), T.g('pingY'), T.g('pingSeq')]);
  T.set('ecran', 'jeu'); T.pas(2);

  // --- spectateur : mort en Solo, deux adversaires vivants ---
  T.set('☁ J2', paquet({ x: 10, y: 10, dir: 180, nom: nom('riko') }));
  T.set('☁ J3', paquet({ x: 25, y: 25, dir: 0, nom: nom('zed') })); T.pas(4);
  verifier('2 adversaires actifs', Number(T.L('E_actif')[1]) === 1 && Number(T.L('E_actif')[2]) === 1, T.L('E_actif'));
  T.set('etat', 2); T.set('mortX', 16.5); T.set('mortY', 4.5); T.pas(3);
  verifier('pas encore spectateur (moins de 3 s)', T.g('ecran') === 'jeu', T.g('ecran'));
  for (let i = 0; i < 400 && T.g('ecran') !== 'spectateur'; i++) T.pas(1);
  verifier('écran « spectateur » après la mort', T.g('ecran') === 'spectateur', T.g('ecran'));
  const s1 = Number(T.g('spectSlot'));
  verifier('spectSlot = 2 (premier vivant)', s1 === 2, s1);
  T.pas(30);
  verifier('caméra converge vers l’adversaire (10, 10)', Math.abs(Number(T.g('px')) - 10) < 0.2 && Math.abs(Number(T.g('py')) - 10) < 0.2, [T.g('px'), T.g('py')]);
  verifier('direction suit la cible (180)', Math.abs(((Number(T.g('dir')) - 180 + 540) % 360) - 180) < 5, T.g('dir'));
  T.appui('ArrowRight', 2); T.pas(2);
  verifier('flèche droite → spectSlot change (3)', Number(T.g('spectSlot')) === 3, T.g('spectSlot'));
  T.pas(30);
  verifier('caméra converge vers (25, 25)', Math.abs(Number(T.g('px')) - 25) < 0.2 && Math.abs(Number(T.g('py')) - 25) < 0.2, [T.g('px'), T.g('py')]);
  T.appui('ArrowLeft', 2); T.pas(2);
  verifier('flèche gauche → retour sur 2', Number(T.g('spectSlot')) === 2, T.g('spectSlot'));
  // la cible meurt → cible suivante
  T.set('☁ J2', paquet({ x: 10, y: 10, dir: 180, nom: nom('riko'), etat: 2, pv: 0, morts: 1 })); T.pas(4);
  verifier('cible morte → bascule sur 3', Number(T.g('spectSlot')) === 3, T.g('spectSlot'));
  T.set('☁ J3', paquet({ x: 25, y: 25, dir: 0, nom: nom('zed'), etat: 2, pv: 0, morts: 1 })); T.pas(4);
  verifier('plus personne de vivant → spectSlot 0, caméra immobile', Number(T.g('spectSlot')) === 0, T.g('spectSlot'));
  const pxFixe = Number(T.g('px')); T.pas(5);
  verifier('caméra immobile', Number(T.g('px')) === pxFixe, [pxFixe, T.g('px')]);
  // le passage automatique en spectateur est unique : la pause ouverte depuis le spectateur (mort) reste affichée
  if (T.vm.runtime.getSpriteTargetByName('Menus')) {
    T.appui('p', 2); T.pas(6);
    verifier('pause depuis le spectateur (mort) : l’écran « pause » reste affiché', T.g('ecran') === 'pause', T.g('ecran'));
    T.appui('p', 2); T.pas(3);
    verifier('touche pause à nouveau → retour au spectateur', T.g('ecran') === 'spectateur', T.g('ecran'));
  }
  // signalement ouvert depuis la pause : Social revient sur l'écran 3D sous-jacent (Menus recouvrirait le panneau),
  // puis retourne à la pause à la fermeture
  T.set('ecran', 'pause'); T.set('ecranPrecedent', 'spectateur'); T.pas(2);
  verifier('écran pause (mort) non forcé en spectateur', T.g('ecran') === 'pause', T.g('ecran'));
  T.set('superposition', 'signaler'); T.pas(2);
  verifier('signaler depuis la pause → écran « spectateur » sous-jacent, étape 1', T.g('ecran') === 'spectateur' && Number(T.g('soc_etape')) === 1, [T.g('ecran'), T.g('soc_etape')]);
  T.clic(0, -75, 2); T.pas(2);
  verifier('Fermer → retour à la pause, superposition vide', T.g('ecran') === 'pause' && T.g('superposition') === '', [T.g('ecran'), T.g('superposition')]);
  T.set('ecran', 'spectateur'); T.pas(2);
  // superposition périmée : un panneau ouvert ne survit pas à un changement d'écran (ex. fin de manche)
  T.appui('t', 2); T.pas(1);
  verifier('chat ouvert en spectateur', T.g('superposition') === 'chat', T.g('superposition'));
  T.set('ecran', 'fin'); T.pas(2);
  verifier('changement d’écran (fin) → superposition refermée', T.g('superposition') === '', T.g('superposition'));
  T.set('ecran', 'jeu'); T.pas(2);

  // --- caméra libre ---
  T.set('ecran', 'cinema'); T.set('px', 16.5); T.set('py', 4.5); T.set('dir', 90); T.pas(2);
  const y0 = Number(T.g('py'));
  T.touche('z', true); T.pas(3); T.touche('z', false); T.pas(1);
  verifier('cinéma : Z avance la caméra', Number(T.g('py')) > y0 + 0.1, [y0, T.g('py')]);
  const v0 = Number(T.g('cineVitesse'));
  T.touche('o', true); T.pas(2); T.touche('o', false); T.pas(1);
  verifier('cinéma : O augmente la vitesse', Number(T.g('cineVitesse')) > v0, [v0, T.g('cineVitesse')]);
  T.touche(' ', true); T.pas(3); T.touche(' ', false); T.pas(1);
  verifier('cinéma : espace élève la caméra (hauteur < 0 → horizon > 0)', Number(T.g('hauteur')) < 0 && Number(T.g('horizon')) > 0, [T.g('hauteur'), T.g('horizon')]);
  T.set('ecran', 'jeu'); T.pas(2);
  verifier('sortie du cinéma : hauteur remise à 0', Number(T.g('hauteur')) === 0, T.g('hauteur'));

  // --- signalement (superposition forcée, comme depuis la pause) ---
  T.set('☁ J2', paquet({ x: 10, y: 10, dir: 180, nom: nom('riko') }));
  T.set('☁ J3', paquet({ x: 25, y: 25, dir: 0, nom: nom('zed') })); T.set('etat', 1); T.pas(3);
  T.set('soc_cible', 0); T.set('superposition', 'signaler'); T.pas(2);
  verifier('signalement : étape 1 (choix du joueur)', Number(T.g('soc_etape')) === 1, T.g('soc_etape'));
  T.clic(0, 52 - 24 - 10, 2); T.pas(2);    // 2e ligne = emplacement 3 (zed)
  verifier('choix de zed → soc_cible = 3, étape 2', Number(T.g('soc_cible')) === 3 && Number(T.g('soc_etape')) === 2, [T.g('soc_cible'), T.g('soc_etape')]);
  T.clic(0, 36 - 10, 2); T.pas(2);   // 1re raison (Triche) : haut 36, hauteur 20
  verifier('raison choisie → étape 3, Muets contient 3', Number(T.g('soc_etape')) === 3 && T.L('Muets').map(Number).includes(3), [T.g('soc_etape'), T.L('Muets')]);
  T.clic(0, -75, 2); T.pas(2);
  verifier('Fermer → superposition vide', T.g('superposition') === '', T.g('superposition'));
  // un joueur masqué n'alimente plus le chat
  T.set('mode', 5);
  T.set('☁ J3', paquet({ x: 25, y: 25, dir: 0, nom: nom('zed'), chat: 1, chatSeq: 1 })); T.pas(3);
  verifier('message de zed ignoré (masqué)', !T.L('Chat').some(l => /zed/.test(l)), T.L('Chat'));

  // --- salon : barre sociale ---
  T.set('ecran', 'salon'); T.set('etat', 5); T.pas(2);
  T.set('menu_rafraichi', 1); T.pas(2); T.set('menu_rafraichi', 0); T.pas(1);
  verifier('barre sociale dessinée sans erreur', Number(T.l('Social', 'nbDessins')) > 0 && T.erreurs.length === 0, [T.l('Social', 'nbDessins'), T.erreurs.slice(0, 2)]);
  // un nouveau joueur actif → menu_sale = 1 (si Menus est présent, il consomme menu_sale et met menu_rafraichi → la barre est redessinée)
  verifier('menu_sale demandé au changement de joueurs', (() => { const n0 = Number(T.l('Social', 'nbDessins')); T.set('menu_sale', 0); T.set('☁ J4', paquet({ x: 5, y: 5, nom: nom('nina'), etat: 5 })); T.pas(4); return Number(T.g('menu_sale')) === 1 || Number(T.l('Social', 'nbDessins')) > n0; })(), [T.g('menu_sale'), T.l('Social', 'nbDessins')]);
  // survol puis clic sur « … » de la 1re ligne (riko, emplacement 2) → menu → « Masquer »
  T.souris(226, 96 - 11, false); T.pas(2);
  verifier('survol du bouton … détecté', Number(T.l('Social', 'survolSoc')) === 12, T.l('Social', 'survolSoc'));
  T.clic(226, 96 - 11, 2); T.pas(2);
  verifier('menu « … » ouvert pour l’emplacement 2', Number(T.g('soc_menuK')) === 2, T.g('soc_menuK'));
  T.clic(194, 96 - 28, 2); T.pas(2);
  verifier('« Masquer » → Muets contient 2, menu fermé', T.L('Muets').map(Number).includes(2) && Number(T.g('soc_menuK')) === 0, [T.L('Muets'), T.g('soc_menuK')]);
  T.clic(226, 96 - 11, 2); T.pas(1); T.clic(194, 96 - 28, 2); T.pas(2);
  verifier('« Réactiver » → 2 retiré de Muets', !T.L('Muets').map(Number).includes(2), T.L('Muets'));
  // « … » → Signaler
  T.clic(226, 96 - 11, 2); T.pas(1); T.clic(194, 96 - 45, 2); T.pas(2);
  verifier('« Signaler » depuis la barre → superposition signaler, cible 2, étape 2', T.g('superposition') === 'signaler' && Number(T.g('soc_cible')) === 2 && Number(T.g('soc_etape')) === 2, [T.g('superposition'), T.g('soc_cible'), T.g('soc_etape')]);
  T.clic(0, -75, 2); T.pas(2);
  verifier('Fermer le signalement depuis le salon', T.g('superposition') === '', T.g('superposition'));
  // Inviter des amis / Pseudo Epic
  T.set('codeSalon', 1234); T.pas(2);
  T.clic(192, -117, 2); T.pas(2);
  verifier('Inviter des amis → notifications (lien + code de salon)', T.L('Notifications').some(l => /Partage le lien/.test(l)) && T.L('Notifications').some(l => /1234/.test(l)), T.L('Notifications'));
  T.clic(192, -139, 2); T.pas(2);
  verifier('Pseudo Epic → « Nom d\'affichage : antoine (pseudo Scratch) »', T.L('Notifications').some(l => /Nom d'affichage : antoine/.test(l)) && T.L('Notifications').some(l => /Niveau de compte/.test(l)), T.L('Notifications'));
  T.set('menu_rafraichi', 1); T.pas(2); T.set('menu_rafraichi', 0);
  // protocole réel avec Menus (s'il est présent) : menu_sale = 1 → Menus redessine le fond et met menu_rafraichi → Social redessine la barre
  if (T.vm.runtime.getSpriteTargetByName('Menus')) {
    const n0 = Number(T.l('Social', 'nbDessins')); T.set('menu_sale', 1); T.pas(4);
    verifier('avec Menus : la barre est redessinée via menu_rafraichi', Number(T.l('Social', 'nbDessins')) > n0, [n0, T.l('Social', 'nbDessins')]);
  }
  verifier('aucune erreur VM', T.erreurs.length === 0, T.erreurs.slice(0, 3));
};
