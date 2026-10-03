// Capture de débogage du sprite Systemes : sys_debug = 1 → le sprite écrit ses données (niveau, XP,
// jetons, division, saison, quêtes actives, récapitulatif, code de sauvegarde) sur un écran « salon ».
module.exports = async (A) => {
  await A.attendre(800);
  const diffuser = (nom, valeur, cible) => A.evaluer((vm, V, L, arg) => {
    if (arg.valeur !== undefined) V('evt_valeur').value = arg.valeur;
    if (arg.cible !== undefined) V('evt_cible').value = arg.cible;
    vm.runtime.startHats('event_whenbroadcastreceived', { BROADCAST_OPTION: arg.nom.toUpperCase() });
  }, { nom, valeur, cible });
  // hors de tout lieu nommé ; écran « jeu » et vivant le temps de l'événement de lieu (l'XP de lieu n'est comptée qu'en manche)
  await A.evaluer((vm, V) => { V('param_langue').value = 0; V('px').value = 10.5; V('py').value = 17.5; V('ecran').value = 'jeu'; V('etat').value = 1; });
  await A.attendre(200);
  await diffuser('evt elimination', undefined, 2); await A.attendre(120);
  await diffuser('evt elimination', undefined, 3); await A.attendre(120);
  await diffuser('evt coffre', 4); await A.attendre(120);
  await diffuser('evt lieu', 3); await A.attendre(120);
  await diffuser('evt knock', undefined, 3); await A.attendre(120);
  // statistiques simulées : quête d'histoire 23 (ouvrir un coffre) terminée au prochain tick ; Arène proche de l'Or
  await A.evaluer((vm, V) => { V('ecran').value = 'salon'; V('stat_tempsSurvie').value = 95; V('stat_coffres').value = 1; V('mode').value = 6; V('hype').value = 940; V('sys_debug').value = 1; });
  await A.attendre(1300);
  await diffuser('evt fin manche', 2);
  await A.attendre(1200);
  await A.evaluer((vm, V) => { V('message').value = ''; });   // retire la bannière « QUÊTE TERMINÉE » du sprite Message
  await A.attendre(700);
  // dernier rafraîchissement du débogage juste avant la capture (sinon la barre sociale dessinée par Social après un
  // redessin de Menus peut recouvrir la colonne de droite jusqu'au prochain rafraîchissement, 0,5 s plus tard)
  const rafraichir = () => A.evaluer((vm, V) => {
    V('menu_sale').value = 0;
    vm.runtime.getSpriteTargetByName('Systemes').lookupVariableByNameAndType('prochainDebug', '').value = 0;
  });
  await rafraichir(); await A.attendre(120);
  await A.capture('systemes_debug');
  // version anglaise, après réclamation de la quête terminée (position 9) et achat du 1er objet de la boutique
  await A.evaluer((vm, V) => { V('param_langue').value = 1; V('jetons').value = 3000; });
  await diffuser('quete reclamer', 9); await A.attendre(150);
  await diffuser('boutique acheter', 1); await A.attendre(600);
  await A.evaluer((vm, V) => { V('message').value = ''; });
  await A.attendre(700);
  await rafraichir(); await A.attendre(120);
  await A.capture('systemes_debug_en');
};
