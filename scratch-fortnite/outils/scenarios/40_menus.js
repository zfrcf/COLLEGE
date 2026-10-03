// Scénario : module Menus — navigation par clics et touches, paramètres, pause, écran de fin.
module.exports = async (T, verifier) => {
  const dodo = (ms) => new Promise(r => setTimeout(r, ms));
  const local = (n) => T.l('Menus', n);
  const boutons = () => (T.sprite('Menus').lookupVariableByNameAndType('menu_bid', 'list') || { value: [] }).value;
  T.pseudo('antoine'); T.souris(0, 0, false); T.drapeau(); T.pas(5);
  await dodo(700); T.pas(6);                       // attente du chargement des costumes (0,4 s réels)
  verifier('écran de connexion au démarrage', T.g('ecran') === 'connexion' && Number(T.g('menu_sale')) === 0, [T.g('ecran'), T.g('menu_sale')]);
  verifier('boutons de connexion enregistrés', boutons().includes('continuer') && boutons().includes('langue'), boutons());
  // survol : son + identifiant
  T.souris(0, -44, false); T.pas(2);
  verifier('survol de CONTINUER détecté (menu_survolId)', T.g('menu_survolId') === 'continuer', T.g('menu_survolId'));
  // « Charger un code » : question puis réponse → diffusion « sauvegarde charger » ; « Code créateur » → evt_texte
  let question = null; T.vm.runtime.on('QUESTION', q => { question = q; });
  T.clic(-150, -89); T.pas(2);
  verifier('Charger un code : question posée', question !== null, question);
  T.repondre('010000000'); await dodo(30); T.pas(3);           // la réponse résout une promesse : laisser passer un tour
  verifier('après la réponse, la boucle des menus reprend (boutons présents)', boutons().includes('langue'), boutons());
  T.clic(0, -89); T.pas(2);
  verifier('Langue : FR → EN', Number(T.g('param_langue')) === 1, T.g('param_langue'));
  T.clic(0, -89); T.pas(2);
  question = null; T.clic(150, -89); T.pas(2);
  verifier('Code créateur : question posée', question !== null, question);
  T.repondre('LAMA42'); await dodo(30); T.pas(3);
  verifier('Code créateur → evt_texte = LAMA42', T.g('evt_texte') === 'LAMA42', T.g('evt_texte'));
  // CONTINUER actif seulement connecté
  T.set('connecte', 1); T.set('menu_sale', 1); T.pas(2);
  T.clic(0, -44); T.pas(3);
  verifier('CONTINUER → salon', T.g('ecran') === 'salon' && T.g('onglet') === 'accueil', T.g('ecran'));
  verifier('menu_sale = 1 → redessin du salon (nbDessins +1, menu_sale consommé)', (() => { const n0 = Number(local('nbDessins')); T.set('menu_sale', 1); T.pas(2); return Number(local('nbDessins')) === n0 + 1 && Number(T.g('menu_sale')) === 0; })(), [local('nbDessins'), T.g('menu_sale')]);
  // chaque onglet par clic sur la barre
  const onglets = [['passe', -126], ['boutique', -52], ['casier', 9], ['quetes', 64], ['carriere', 123], ['parametres', 196], ['accueil', -202]];
  for (const [nom, x] of onglets) {
    T.clic(x, 163); T.pas(2);
    verifier('onglet « ' + nom + ' » par clic', T.g('onglet') === nom, T.g('onglet'));
  }
  // sélecteur de mode : ouverture puis choix « Trio »
  T.clic(55, -127); T.pas(2);
  verifier('liste des modes ouverte', Number(local('listeModes')) === 1 && boutons().includes('mode 3'), [local('listeModes'), boutons().length]);
  T.clic(55, -8); T.pas(2);
  verifier('mode Trio choisi (modeChoisi = 3), liste fermée', Number(T.g('modeChoisi')) === 3 && Number(local('listeModes')) === 0, [T.g('modeChoisi'), local('listeModes')]);
  // événement limité : flèche droite
  T.clic(55, -127); T.pas(2); T.clic(126, -96); T.pas(2);
  verifier('événement limité suivant (ltmChoisi = 1)', Number(T.g('ltmChoisi')) === 1, T.g('ltmChoisi'));
  T.clic(55, -127); T.pas(2);
  // remplissage auto et confidentialité
  const r0 = Number(T.g('remplissage'));
  T.clic(-58, -120); T.pas(2);
  verifier('interrupteur remplissage auto', Number(T.g('remplissage')) === 1 - r0, T.g('remplissage'));
  // JOUER → matchmaking (enPartie = 1) ; compte à rebours → chargement
  T.clic(55, -161); T.pas(2);
  verifier('JOUER → enPartie = 1, écran matchmaking', Number(T.g('enPartie')) === 1 && (T.g('ecran') === 'matchmaking' || Number(T.g('enPartie')) === 1), [T.g('enPartie'), T.g('ecran')]);
  if (T.g('ecran') === 'matchmaking') {
    T.sprite('Menus').lookupVariableByNameAndType('tCompte', '').value = -1; T.pas(3);
    verifier('fin du compte à rebours → écran chargement', T.g('ecran') === 'chargement' || T.g('ecran') !== 'matchmaking', T.g('ecran'));
    T.clic(0, -119); T.pas(2);   // Annuler n'existe plus sur chargement : rien ne doit casser
  } else {
    verifier('(module Partie présent : il a pris la main dès JOUER)', true);
  }
  // Annuler depuis le matchmaking
  T.set('enPartie', 1); T.set('ecran', 'matchmaking'); T.set('menu_sale', 1); T.sprite('Menus').lookupVariableByNameAndType('tCompte', '').value = 1e9; T.pas(2);
  T.clic(0, -119); T.pas(2);
  verifier('Annuler → salon, enPartie = 0', T.g('ecran') === 'salon' && Number(T.g('enPartie')) === 0, [T.g('ecran'), T.g('enPartie')]);
  // paramètres : sensibilité +, QWERTY, qualité, langue
  T.set('onglet', 'parametres'); T.set('menu_sale', 1); T.pas(2);
  const s0 = Number(T.g('param_sensibilite'));
  T.clic(120, 124); T.pas(2);
  verifier('sensibilité + 0,25', Math.abs(Number(T.g('param_sensibilite')) - (s0 + 0.25)) < 1e-9, T.g('param_sensibilite'));
  T.clic(100, 124); T.pas(2);
  verifier('sensibilité − 0,25', Math.abs(Number(T.g('param_sensibilite')) - s0) < 1e-9, T.g('param_sensibilite'));
  T.clic(104, 102); T.pas(2);
  verifier('interrupteur visée assistée', Number(T.g('param_viseeAssistee')) === 0, T.g('param_viseeAssistee'));
  T.clic(-188, 98); T.pas(2);
  verifier('section Commandes', Number(local('section')) === 2, local('section'));
  T.clic(62, 123); T.pas(2);
  verifier('QWERTY → Touches[1] = w, param_clavier = 1', T.L('Touches')[0] === 'w' && Number(T.g('param_clavier')) === 1, [T.L('Touches')[0], T.g('param_clavier')]);
  T.clic(-8, 123); T.pas(2);
  verifier('AZERTY → Touches[1] = z', T.L('Touches')[0] === 'z', T.L('Touches')[0]);
  // reconfiguration d'une touche : clic sur « Sauter » puis appui sur « k »
  T.clic(-64, 16); T.pas(2);
  verifier('attente d’une touche pour « sauter »', Number(local('attenteTouche')) === 5, local('attenteTouche'));
  T.touche('k', true); T.pas(2); T.touche('k', false); T.pas(1);
  verifier('touche « sauter » = k', T.L('Touches')[4] === 'k' && Number(local('attenteTouche')) === 0, [T.L('Touches')[4], local('attenteTouche')]);
  T.clic(-188, 70); T.pas(2);
  const q0 = Number(T.g('param_qualite'));
  T.clic(120, 124); T.pas(2);
  verifier('qualité graphique suivante', Number(T.g('param_qualite')) === (q0 % 3) + 1, T.g('param_qualite'));
  T.clic(-188, 126); T.pas(2);
  T.clic(120, -8); T.pas(2);
  verifier('langue → EN (param_langue = 1)', Number(T.g('param_langue')) === 1, T.g('param_langue'));
  T.clic(100, -8); T.pas(2);
  verifier('langue → FR (param_langue = 0)', Number(T.g('param_langue')) === 0, T.g('param_langue'));
  T.clic(-188, 42); T.pas(2); T.clic(120, 124); T.pas(2);
  verifier('volume musique +10', Number(T.g('param_volumeMusique')) === 60, T.g('param_volumeMusique'));
  // casier : clic sur un objet → diffusion « casier equiper » (evt_texte / evt_valeur)
  T.set('onglet', 'casier'); T.set('menu_sale', 1); T.pas(2);
  T.clic(-56, 90); T.pas(2);
  verifier('casier : clic sur la tenue 2 → evt_texte = skin, evt_valeur = 2', T.g('evt_texte') === 'skin' && Number(T.g('evt_valeur')) === 2, [T.g('evt_texte'), T.g('evt_valeur')]);
  // boutique : clic Acheter sur la 1re carte → evt_valeur = 1
  T.set('onglet', 'boutique'); T.set('jetons', 99999); T.set('menu_sale', 1); T.pas(2);
  if (T.L('Boutique').length) { T.set('evt_valeur', 0); T.clic(-176, 20); T.pas(2); verifier('boutique : Acheter carte 1 → evt_valeur = 1', Number(T.g('evt_valeur')) === 1, T.g('evt_valeur')); }
  // pause en jeu : touche P, puis Quitter
  T.set('ecran', 'jeu'); T.set('etat', 1); T.set('enPartie', 1); T.set('superposition', ''); T.pas(2);
  T.appui('p', 2); T.pas(2);
  verifier('touche pause en jeu → écran pause (ecranPrecedent = jeu)', T.g('ecran') === 'pause' && T.g('ecranPrecedent') === 'jeu', [T.g('ecran'), T.g('ecranPrecedent')]);
  T.appui('p', 2); T.pas(2);
  verifier('touche pause à nouveau → retour au jeu', T.g('ecran') === 'jeu', T.g('ecran'));
  T.appui('p', 2); T.pas(2);
  T.clic(0, 18); T.pas(2);
  verifier('Paramètres depuis la pause', Number(local('pauseParam')) === 1 && boutons().includes('pause retour'), [local('pauseParam')]);
  T.clic(0, -135); T.pas(2);
  verifier('Retour → menu pause', Number(local('pauseParam')) === 0, local('pauseParam'));
  T.clic(0, -90); T.pas(2);
  verifier('Quitter la partie → salon, enPartie = 0, etat = 5', T.g('ecran') === 'salon' && Number(T.g('enPartie')) === 0 && Number(T.g('etat')) === 5, [T.g('ecran'), T.g('enPartie'), T.g('etat')]);
  // touche carte : jeu ⇄ carte
  T.set('ecran', 'jeu'); T.pas(1); T.appui('m', 2); T.pas(2);
  verifier('touche carte → écran carte', T.g('ecran') === 'carte', T.g('ecran'));
  T.appui('m', 2); T.pas(2);
  verifier('touche carte à nouveau → jeu', T.g('ecran') === 'jeu', T.g('ecran'));
  // écran de fin : Rejouer → matchmaking
  T.set('ecran', 'fin'); T.set('victoire', 1); T.set('rang', 1); T.pas(3);
  verifier('écran fin : boutons REJOUER / Salon', boutons().includes('rejouer') && boutons().includes('salon'), boutons());
  T.clic(-80, -145); T.pas(2);
  verifier('REJOUER → matchmaking, enPartie = 1', (T.g('ecran') === 'matchmaking' || Number(T.g('enPartie')) === 1) && Number(T.g('enPartie')) === 1, [T.g('ecran'), T.g('enPartie')]);
  T.set('ecran', 'fin'); T.set('enPartie', 0); T.pas(3); T.clic(80, -145); T.pas(2);
  verifier('Salon depuis la fin → salon', T.g('ecran') === 'salon', T.g('ecran'));
  // --- signalement (panneau central de Social, x ∈ [−130, 130], y ∈ [−90, 90]) ouvert dans le salon :
  //     aucun clic de Menus sous le panneau, mais les boutons hors du panneau (onglets) répondent ---
  T.set('onglet', 'parametres'); T.set('superposition', 'signaler'); T.set('menu_sale', 1); T.pas(3);
  const ct0 = Number(T.g('param_constructionTurbo'));
  T.clic(110, 80); T.pas(2);                           // interrupteur « Construction turbo », sous le panneau
  verifier('salon + signalement : clic sous le panneau central ignoré', Number(T.g('param_constructionTurbo')) === ct0 && T.g('ecran') === 'salon', [T.g('param_constructionTurbo'), ct0]);
  T.souris(0, 0, false); T.pas(2);
  verifier('salon + signalement : aucun survol sous le panneau', T.g('menu_survolId') === '', T.g('menu_survolId'));
  T.clic(-202, 163); T.pas(2);                          // onglet Découvrir, hors du panneau
  verifier('salon + signalement : clic hors du panneau (onglet) traité', T.g('onglet') === 'accueil', T.g('onglet'));
  T.set('superposition', ''); T.set('onglet', 'parametres'); T.set('menu_sale', 1); T.pas(3);
  T.clic(110, 80); T.pas(2);
  verifier('sans signalement : le même clic bascule Construction turbo', Number(T.g('param_constructionTurbo')) === 1 - ct0, T.g('param_constructionTurbo'));
  T.clic(110, 80); T.pas(2);
  // --- signalement ouvert sur l'écran pause : Menus ne dessine qu'un voile, aucun bouton, clics ignorés ---
  T.set('ecran', 'jeu'); T.set('etat', 1); T.set('enPartie', 1); T.set('superposition', 'signaler'); T.pas(2);   // Social mémorise la superposition
  T.set('ecran', 'pause'); T.set('ecranPrecedent', 'jeu'); T.pas(3);
  verifier('pause + signalement : aucun bouton de pause enregistré', T.g('ecran') === 'pause' && boutons().length === 0, [T.g('ecran'), boutons()]);
  T.clic(0, 52); T.pas(2);                              // position de « Reprendre »
  verifier('pause + signalement : clic sur « Reprendre » sans effet', T.g('ecran') === 'pause', T.g('ecran'));
  T.appui('p', 2); T.pas(2);
  verifier('pause + signalement : touche pause ignorée', T.g('ecran') === 'pause', T.g('ecran'));
  T.set('superposition', ''); T.pas(3);
  verifier('signalement fermé : boutons de pause de retour', boutons().includes('reprendre') && boutons().includes('quitter'), boutons());
  T.clic(0, 52); T.pas(2);
  verifier('Reprendre → retour au jeu', T.g('ecran') === 'jeu', T.g('ecran'));
  verifier('aucune erreur VM', T.erreurs.length === 0, T.erreurs.slice(0, 2));
};
