// Scénario : sprite Systemes (progression et méta) — XP/niveaux, bonus de session, récapitulatif,
// passe de combat, boutique, casier, quêtes, succès, saison, Arène, code de sauvegarde, record, code créateur.
module.exports = async (T, verifier) => {
  const attendre = (ms) => new Promise((r) => setTimeout(r, ms));
  const STATS = ['stat_elims', 'stat_degats', 'stat_coffres', 'stat_murs', 'stat_recoltes', 'stat_distance', 'stat_tempsSurvie',
    'stat_parties', 'stat_top3', 'stat_victoires', 'stat_reanimations', 'stat_soins', 'stat_pings', 'stat_emotes', 'stat_materiaux', 'stat_touches'];
  const N = (x) => Number(x);
  const notifs = () => T.L('Notifications').join(' | ');
  const actives = () => T.L('QuetesActives').map((e) => String(e).split('|').map(Number));
  const diffuser = (nom, valeur, cible, texte) => {
    if (valeur !== undefined) T.set('evt_valeur', valeur);
    if (cible !== undefined) T.set('evt_cible', cible);
    if (texte !== undefined) T.set('evt_texte', texte);
    T.diffuser(nom); T.pas(2);
  };

  T.pseudo('antoine'); T.souris(0, 0, false); T.drapeau(); T.pas(8);
  // en « jeu », vivant (l'XP de lieu n'est comptée qu'en manche, etat 1 ou 3), hors de tout lieu nommé (sinon Joueur
  // diffuse « evt lieu » au salon / à chaque manche) ; enPartie = 0 : Partie laisse etat et phase tranquilles
  T.set('ecran', 'jeu'); T.set('etat', 1); T.set('px', 10.5); T.set('py', 17.5); T.pas(2);
  // une seule itération du séquenceur par pas (sinon un pas en enchaîne des dizaines)
  const unTick = () => { const seq = T.vm.runtime.sequencer; const orig = seq.stepThread;
    seq.stepThread = function (th) { orig.call(this, th); T.vm.runtime.redrawRequested = true; };
    T.vm.runtime._step(); seq.stepThread = orig; };
  // jetons attendus après un passage de niveau : +100 par niveau + lots de jetons des paliers du passe
  const jetonsPaliers = (nAvant, nApres) => T.L('PasseRecompenses').slice(Math.min(nAvant, 100), Math.min(nApres, 100)).reduce((a, e) => a + (String(e).startsWith('jetons|') ? N(String(e).split('|')[1]) : 0), 0);
  const niveauDe = (x) => Math.min(200, 1 + Math.floor(x / 1000));

  // ---------------------------------------------------------------- listes remplies au démarrage
  verifier('QueteTitres : 32 titres FR + 32 EN', T.L('QueteTitres').length === 64 && T.L('QueteTitres')[0] !== T.L('QueteTitres')[32], T.L('QueteTitres').length);
  const passe = T.L('PasseRecompenses');
  const typesPasse = new Set(passe.map((e) => String(e).split('|')[0]));
  verifier('PasseRecompenses : 100 entrées type|id', passe.length === 100 && passe.every((e) => /^(skin|pioche|planeur|spray|emote|banniere|jetons|style)\|\d+$/.test(e)), passe.slice(0, 12));
  verifier('passe : tous les types présents, skin|2 au palier 1, style|1 au palier 100', typesPasse.size === 8 && passe[0] === 'skin|2' && passe[99] === 'style|1' && passe[9] === 'style|2', [passe[0], passe[9], passe[99]]);
  const boutique = T.L('Boutique').map((e) => String(e).split('|'));
  verifier('Boutique : 6 objets du jour type|id|prix (200-1500), distincts', boutique.length === 6 && boutique.every((b) => b.length === 3 && N(b[2]) >= 200 && N(b[2]) <= 1500 && /^(pioche|planeur|spray|banniere)$/.test(b[0])) && new Set(boutique.map((b) => b[0] + b[1])).size === 6, T.L('Boutique'));
  verifier('Succes : 21 entrées « index|0 »', T.L('Succes').length === 21 && T.L('Succes').every((e, i) => e === (i + 1) + '|0'), T.L('Succes').slice(0, 4));
  verifier('sys_SuccesTitres / Descriptions / DivisionNoms', T.L('sys_SuccesTitres').length === 42 && T.L('sys_SuccesDescriptions').length === 42 && T.L('sys_DivisionNoms').length === 14 && T.L('sys_DivisionNoms')[2] === 'Or', T.L('sys_DivisionNoms'));
  const poss0 = T.L('Possedes');
  verifier('Possedes : défauts + palier 1 du passe (skin|2)', ['skin|1', 'pioche|1', 'planeur|1', 'spray|1', 'banniere|1', 'emote|1', 'emote|6', 'skin|2'].every((p) => poss0.includes(p)), poss0);
  const qa0 = actives();
  verifier('QuetesActives : 11 entrées (3 quotidiennes, 5 hebdo, 3 histoire), 6 champs, état 0', qa0.length === 11 && qa0.every((q) => q.length === 6 && q[4] === 0 && q[2] === 0) && qa0.slice(0, 3).every((q) => q[1] === 1) && qa0.slice(3, 8).every((q) => q[1] === 2) && qa0.slice(8).every((q) => q[1] === 3), T.L('QuetesActives'));
  verifier('quêtes distinctes, histoire = 23, 24, 25', new Set(qa0.map((q) => q[0])).size === 11 && qa0[8][0] === 23 && qa0[9][0] === 24 && qa0[10][0] === 25, qa0.map((q) => q[0]));
  verifier('départ : niveau 1, xp 0, jetons 500, bonusXP 1, passeNiveau 1', N(T.g('niveau')) === 1 && N(T.g('xp')) === 0 && N(T.g('jetons')) === 500 && N(T.g('bonusXP')) === 1 && N(T.g('passeNiveau')) === 1, [T.g('niveau'), T.g('xp'), T.g('jetons'), T.g('bonusXP')]);
  verifier('code de sauvegarde : 76 chiffres dès le départ', /^01\d{74}$/.test(String(T.g('codeSauvegarde'))), T.g('codeSauvegarde'));

  // ---------------------------------------------------------------- XP avec bonus de session (+50 %)
  let xp = 0;
  diffuser('evt elimination', undefined, 2);
  xp += 75;
  verifier('élimination : +50 XP × 1,5 = 75', N(T.g('xp')) === xp && N(T.g('xpGagne')) === xp, [T.g('xp'), T.g('xpGagne')]);
  verifier('RecapLignes « Éliminations ×1 : +75 XP »', T.L('RecapLignes')[0] === 'Éliminations ×1 : +75 XP', T.L('RecapLignes'));
  verifier('succès 1 (première élimination) débloqué, +50 jetons', T.L('Succes')[0] === '1|1' && N(T.g('jetons')) === 550, [T.L('Succes')[0], T.g('jetons')]);
  verifier('notification de succès', /Succès débloqué : Première victime/.test(notifs()), notifs());
  T.pas(2);
  verifier('evt succes différé : evt_valeur = 1', N(T.g('evt_valeur')) === 1, T.g('evt_valeur'));
  diffuser('evt elimination', undefined, 3); xp += 75;
  verifier('regroupement : « Éliminations ×2 : +150 XP »', T.L('RecapLignes')[0] === 'Éliminations ×2 : +150 XP', T.L('RecapLignes'));
  diffuser('evt knock', undefined, 3); xp += 38;          // 25 × 1,5 = 37,5 → 38
  diffuser('evt coffre', 4); xp += 15;
  diffuser('evt reanimation', undefined, 2); xp += 60;
  T.set('ecran', 'salon'); diffuser('evt lieu', 3); T.set('ecran', 'jeu');
  verifier('lieu hors partie (salon) : pas d\'XP', N(T.g('xp')) === xp, T.g('xp'));
  T.set('etat', 8); diffuser('evt lieu', 3); T.set('etat', 1);
  verifier('lieu sur l\'île d\'attente (etat 8) : pas d\'XP', N(T.g('xp')) === xp, T.g('xp'));
  diffuser('evt lieu', 3); xp += 8;                      // 5 × 1,5 = 7,5 → 8
  diffuser('evt lieu', 3);                                // déjà visité : rien
  diffuser('evt lieu', 5); xp += 8;
  diffuser('evt mur', 1); xp += 3; diffuser('evt mur', 2); xp += 3;
  diffuser('evt recolte', 1); xp += 2;                   // 1 × 1,5 = 1,5 → 2
  verifier('cumul XP (knock, coffre, réanimation, lieux, murs, récolte)', N(T.g('xp')) === xp, [T.g('xp'), xp]);
  verifier('récap : 7 types regroupés', T.L('RecapLignes').length === 7 && T.L('RecapLignes').includes('Lieux découverts ×2 : +16 XP') && T.L('RecapLignes').includes('Constructions ×2 : +6 XP'), T.L('RecapLignes'));

  // plafond murs/récolte : 100 XP (hors bonus) par manche
  for (let i = 0; i < 60; i++) { T.diffuser('evt mur'); T.pas(1); }
  const xpAvantPlafond = N(T.g('xp'));
  T.diffuser('evt mur'); T.pas(2); T.diffuser('evt recolte'); T.pas(2);
  verifier('plafond murs/récolte atteint (plus de gain)', N(T.g('xp')) === xpAvantPlafond && N(T.l('Systemes', 'xpMursRecolte')) >= 100, [xpAvantPlafond, T.g('xp'), T.l('Systemes', 'xpMursRecolte')]);
  xp = N(T.g('xp'));

  // ---------------------------------------------------------------- quêtes : progression et réclamation
  const qStat = T.l('Systemes', 'qStat'), qObjectif = T.l('Systemes', 'qObjectif'), qXp = T.l('Systemes', 'qXp'), qJetons = T.l('Systemes', 'qJetons');
  // position 9 = quête d'histoire 23 (ouvrir un coffre : stat_coffres ≥ 1)
  const q9 = qa0[8][0];
  const stat9 = STATS[N(qStat[q9 - 1]) - 1];
  T.set(stat9, N(T.g(stat9)) + N(qObjectif[q9 - 1]) - 1);
  await attendre(1100); T.pas(3);
  verifier('quête 9 : progression objectif−1, état 0', actives()[8][2] === N(qObjectif[q9 - 1]) - 1 && actives()[8][4] === 0, T.L('QuetesActives')[8]);
  T.set(stat9, N(T.g(stat9)) + 1);
  await attendre(1100); T.pas(3);
  verifier('quête 9 terminée (état 1) + notification', actives()[8][4] === 1 && actives()[8][2] === N(qObjectif[q9 - 1]) && /Quête terminée/.test(notifs()), [T.L('QuetesActives')[8], notifs()]);
  verifier('message « quete » affiché (ou en attente derrière une autre bannière)', T.g('message') === 'quete' || T.l('Systemes', 'messageAttente') === 'quete', [T.g('message'), T.l('Systemes', 'messageAttente')]);
  // progression via stat_elims (quête du jour ou hebdo si présente, sinon par position 1)
  const q1 = qa0[0][0]; const stat1 = STATS[N(qStat[q1 - 1]) - 1];
  T.set(stat1, N(T.g(stat1)) + 1); T.diffuser('evt knock'); T.pas(2); xp += 38;
  verifier('quête 1 : progression immédiate après un événement', actives()[0][2] >= 1, T.L('QuetesActives')[0]);
  const jetonsAvant = N(T.g('jetons'));
  const xpAvantReclam = xp;
  diffuser('quete reclamer', 9);
  xp += Math.round(N(qXp[q9 - 1]) * 1.5);
  const jetonsAttendus = jetonsAvant + N(qJetons[q9 - 1]) + 100 * (niveauDe(xp) - niveauDe(xpAvantReclam)) + jetonsPaliers(niveauDe(xpAvantReclam), niveauDe(xp));
  verifier('réclamation : XP (×1,5) et jetons crédités (+ niveau 2 et palier 2)', N(T.g('xp')) === xp && N(T.g('jetons')) === jetonsAttendus, [T.g('xp'), xp, T.g('jetons'), jetonsAttendus]);
  verifier('notification de récompense : XP réellement créditée (bonus compris)', new RegExp('Récompense : \\+' + Math.round(N(qXp[q9 - 1]) * 1.5) + ' XP, \\+' + N(qJetons[q9 - 1]) + ' jetons').test(notifs()), notifs());
  verifier('quête d\'histoire suivante (26) placée en position 9, état 0', actives()[8][0] === 26 && actives()[8][4] === 0, T.L('QuetesActives')[8]);
  verifier('récap « Quêtes ×1 »', T.L('RecapLignes').some((l) => /^Quêtes ×1 : \+\d+ XP$/.test(l)), T.L('RecapLignes'));
  diffuser('quete reclamer', 9);
  verifier('réclamation refusée si non terminée', N(T.g('xp')) === xp, T.g('xp'));
  diffuser('quete partager', 2);
  verifier('partage : chat = 20 + index, chatSeq = 1', N(T.g('chat')) === 20 + qa0[1][0] && N(T.g('chatSeq')) === 1, [T.g('chat'), T.g('chatSeq')]);

  // ---------------------------------------------------------------- fin de manche (victoire) et récapitulatif
  T.set('stat_tempsSurvie', N(T.g('stat_tempsSurvie')) + 120);
  diffuser('evt fin manche', 1);
  xp += 450 + 18 + 300;      // placement 300, survie 12, victoire 200 (× 1,5)
  verifier('fin de manche rang 1 : placement + survie + victoire', N(T.g('xp')) === xp, [T.g('xp'), xp]);
  verifier('récap : Placement, Survie, Victoire Royale', ['Placement : +450 XP', 'Survie : +18 XP', 'Victoire Royale : +300 XP'].every((l) => T.L('RecapLignes').includes(l)), T.L('RecapLignes'));
  verifier('bonus de session terminé (bonusXP 0)', N(T.g('bonusXP')) === 0, T.g('bonusXP'));
  T.pas(8);   // Reseau écrit le ☁ Record dans les images suivantes
  verifier('record proposé : rec_elims 2, rec_victoires 1, ☁ Record écrit', N(T.g('rec_elims')) === 2 && N(T.g('rec_victoires')) === 1 && String(T.g('☁ Record')).length === 24 && N(T.L('Record_victoires')[0]) === 1, [T.g('rec_elims'), T.g('rec_victoires'), T.g('☁ Record')]);
  verifier('succès 4 (première victoire) débloqué', T.L('Succes')[3] === '4|1', T.L('Succes')[3]);
  diffuser('evt victoire');
  verifier('evt victoire après fin de manche : pas de double compte', N(T.g('xp')) === xp, T.g('xp'));
  T.diffuser('evt nouvelle manche'); T.pas(2);
  verifier('nouvelle manche : xpGagne 0, RecapLignes vide', N(T.g('xpGagne')) === 0 && T.L('RecapLignes').length === 0, [T.g('xpGagne'), T.L('RecapLignes')]);
  diffuser('evt victoire'); xp += 200;
  diffuser('evt fin manche', 1); xp += 300;
  verifier('victoire puis fin de manche : victoire comptée une fois (sans bonus)', N(T.g('xp')) === xp && N(T.g('rec_victoires')) === 2, [T.g('xp'), xp, T.g('rec_victoires')]);

  // ---------------------------------------------------------------- niveaux et passe de combat
  T.diffuser('evt nouvelle manche'); T.pas(2);
  const niveauAvant = N(T.g('niveau'));
  verifier('niveau cohérent avec l\'XP', niveauAvant === 1 + Math.floor(xp / 1000) && N(T.g('xpNiveau')) === xp % 1000 && N(T.g('xpSuivant')) === 1000, [niveauAvant, xp]);
  const jetonsN = N(T.g('jetons'));
  T.set('xp', 2990); diffuser('evt knock'); xp = 3015;
  verifier('passage de niveau : niveau 4, +100 jetons par niveau (+ paliers), message « niveau »', N(T.g('niveau')) === 4 && N(T.g('jetons')) === jetonsN + 100 * (4 - niveauAvant) + jetonsPaliers(niveauAvant, 4) && (T.g('message') === 'niveau' || T.l('Systemes', 'messageAttente') === 'niveau'), [T.g('niveau'), T.g('jetons'), T.g('message'), jetonsN]);
  verifier('notification « Niveau 4 atteint ! +' + 100 * (4 - niveauAvant) + ' jetons » (plusieurs niveaux d\'un coup)', new RegExp('Niveau 4 atteint ! \\+' + 100 * (4 - niveauAvant) + ' jetons').test(notifs()), notifs());
  T.pas(2);
  verifier('evt niveau différé : evt_valeur = 4', N(T.g('evt_valeur')) === 4, T.g('evt_valeur'));
  verifier('passeNiveau 4, étoiles 0, récompenses des paliers 2-4 débloquées', N(T.g('passeNiveau')) === 4 && N(T.g('etoiles')) === 0 && passe.slice(0, 4).filter((e) => !e.startsWith('jetons')).every((e) => T.L('Possedes').includes(e)), [T.g('passeNiveau'), passe.slice(0, 4), T.L('Possedes')]);
  verifier('notification de palier du passe', /Passe de combat — palier/.test(notifs()), notifs());
  T.set('xp', 9450); diffuser('evt knock');
  verifier('niveau 10 : étoiles 2 (475/200), style|2 (palier 10) débloqué, succès « Niveau 10 »', N(T.g('niveau')) === 10 && N(T.g('etoiles')) === 2 && T.L('Possedes').includes('style|2') && T.L('Succes')[15] === '16|1', [T.g('niveau'), T.g('etoiles'), T.L('Succes')[15]]);

  // ---------------------------------------------------------------- boutique
  T.set('jetons', 5000);
  const b1 = boutique[0];
  diffuser('boutique acheter', 1);
  verifier('achat : jetons − prix, cosmétique possédé, notification « Achat »', N(T.g('jetons')) === 5000 - N(b1[2]) && T.L('Possedes').includes(b1[0] + '|' + b1[1]) && /Achat :/.test(notifs()), [T.g('jetons'), b1, notifs()]);
  T.pas(2);
  verifier('evt achat différé : evt_valeur = 1', N(T.g('evt_valeur')) === 1, T.g('evt_valeur'));
  const j2 = N(T.g('jetons'));
  diffuser('boutique acheter', 1);
  verifier('rachat refusé « Déjà possédé »', N(T.g('jetons')) === j2 && /Déjà possédé/.test(notifs()), notifs());
  T.set('jetons', 10);
  diffuser('boutique acheter', 2);
  verifier('achat refusé « Pas assez de jetons »', N(T.g('jetons')) === 10 && !T.L('Possedes').includes(boutique[1][0] + '|' + boutique[1][1]) && /Pas assez de jetons/.test(notifs()), notifs());
  T.set('jetons', j2);

  // ---------------------------------------------------------------- casier
  diffuser('casier equiper', 2, 0, 'skin');
  verifier('équiper skin 2 (possédé)', N(T.g('skin')) === 2 && /Équipé/.test(notifs()), [T.g('skin'), notifs()]);
  diffuser('casier equiper', 9, 0, 'skin');
  verifier('skin 9 refusé (non possédé)', N(T.g('skin')) === 2 && /Non possédé/.test(notifs()), [T.g('skin'), notifs()]);
  diffuser('casier equiper', 1, 0, 'style');
  verifier('style du skin 2 équipé (style|2 possédé)', N(T.g('styleSkin')) === 1, T.g('styleSkin'));
  diffuser('casier equiper', 1, 0, 'skin');
  verifier('changer de skin remet le style à 0', N(T.g('skin')) === 1 && N(T.g('styleSkin')) === 0, [T.g('skin'), T.g('styleSkin')]);
  T.set('styleSkin', 1);     // Menus bascule styleSkin avant de demander : Systemes doit trancher
  diffuser('casier equiper', 1, 0, 'style');
  verifier('style refusé pour le skin 1 (style|1 au palier 100), styleSkin remis à 0', N(T.g('styleSkin')) === 0 && /Non possédé/.test(notifs()), [T.g('styleSkin'), notifs()]);
  diffuser('casier equiper', 5, 3, 'emote');
  verifier('émote 5 dans la case 3', N(T.L('EmotesEquipees')[2]) === 5, T.L('EmotesEquipees'));
  if (b1[0] === 'pioche' || b1[0] === 'planeur' || b1[0] === 'spray' || b1[0] === 'banniere') {
    diffuser('casier equiper', N(b1[1]), 0, b1[0]);
    verifier('objet acheté équipable (' + b1[0] + ' ' + b1[1] + ')', N(T.g(b1[0])) === N(b1[1]), T.g(b1[0]));
  }
  diffuser('casier equiper', 7, 0, 'banniere');
  verifier('bannière 7 refusée (non possédée)', N(T.g('banniere')) !== 7, T.g('banniere'));

  // ---------------------------------------------------------------- saison / chapitre
  const jours = Math.floor((Date.now() - Date.UTC(2000, 0, 1)) / 86400000);
  const n = Math.max(0, jours - 9497);
  const saisonGlobale = 1 + Math.floor(n / 70);
  verifier('saison/chapitre/jours restants cohérents avec la date', N(T.g('chapitre')) === 1 + Math.floor((saisonGlobale - 1) / 4) && N(T.g('saison')) === 1 + ((saisonGlobale - 1) % 4) && N(T.g('joursSaison')) === 70 - (n % 70), [T.g('saison'), T.g('chapitre'), T.g('joursSaison'), saisonGlobale]);

  // ---------------------------------------------------------------- Arène (mode 6) : hype et divisions
  T.set('mode', 6); T.diffuser('evt nouvelle manche'); T.pas(2);
  diffuser('evt elimination', undefined, 2); diffuser('evt elimination', undefined, 3);
  diffuser('evt fin manche', 2);
  verifier('Arène : rang 2 + 2 éliminations → hype 60 + 40 = 100, division 1', N(T.g('hype')) === 100 && N(T.g('division')) === 1, [T.g('hype'), T.g('division')]);
  T.set('hype', 1490); T.diffuser('evt nouvelle manche'); T.pas(2);
  diffuser('evt fin manche', 1);
  verifier('rang 1 sans élimination → +100 hype = 1590, division 4 Platine + notification', N(T.g('hype')) === 1590 && N(T.g('division')) === 4 && /Division : Platine/.test(notifs()), [T.g('hype'), T.g('division'), notifs()]);
  T.set('mode', 5); T.diffuser('evt nouvelle manche'); T.pas(2);
  diffuser('evt fin manche', 4);
  verifier('hors Arène : hype inchangée', N(T.g('hype')) === 1590, T.g('hype'));

  // ---------------------------------------------------------------- événements différés : evt_valeur des autres n'est pas écrasée
  // Dans une image, les boucles « toujours » tournent avant les gestionnaires lancés dans cette image. Si Systemes
  // écrivait evt_valeur depuis sa boucle, un « evt lieu » (Joueur) lancé juste avant lirait le numéro de niveau.
  T.pas(2);
  verifier('file d\'événements différés vide avant le test', T.l('Systemes', 'evtCode').length === 0, T.l('Systemes', 'evtCode'));
  const niveauA = N(T.g('niveau'));
  T.set('xp', 1000 * niveauA - 1); T.diffuser('evt knock'); unTick();      // image A : passage de niveau → « evt niveau » en file
  verifier('image A : niveau gagné, « evt niveau » encore en file', N(T.g('niveau')) === niveauA + 1 && T.l('Systemes', 'evtCode').length === 1, [T.g('niveau'), T.l('Systemes', 'evtCode')]);
  const xpA = N(T.g('xp'));
  T.set('evt_valeur', 7); T.diffuser('evt lieu'); unTick();                 // image B : « evt lieu » (7) lancé dans la même image que l'émission
  verifier('image B : lieu 7 compté (+5 XP) — evt_valeur lue avant l\'émission différée', T.l('Systemes', 'lieuxVisites').map(Number).includes(7) && N(T.g('xp')) === xpA + 5, [T.l('Systemes', 'lieuxVisites'), T.g('xp'), xpA]);
  verifier('image B : « evt niveau » émis après coup (evt_valeur = niveau, file vide)', N(T.g('evt_valeur')) === niveauA + 1 && T.l('Systemes', 'evtCode').length === 0, [T.g('evt_valeur'), T.l('Systemes', 'evtCode')]);
  xp = N(T.g('xp'));

  // ---------------------------------------------------------------- code de sauvegarde
  T.diffuser('sauvegarde generer'); T.pas(2);
  const code = String(T.g('codeSauvegarde'));
  const somme = [...code.slice(0, 74)].reduce((a, c) => a + N(c), 0);
  verifier('code : 76 chiffres, version 01, somme de contrôle mod 97', code.length === 76 && code.startsWith('01') && N(code.slice(74)) === somme % 97, code);
  verifier('code : champs xp / jetons / hype / victoires (3) / élims (4) / parties (5) / coffres (1)', N(code.slice(2, 9)) === xp && N(code.slice(9, 14)) === N(T.g('jetons')) && N(code.slice(14, 19)) === 1590 && N(code.slice(19, 23)) === 3 && N(code.slice(23, 29)) === 4 && N(code.slice(29, 34)) === 5 && N(code.slice(34, 39)) === 1, code);
  verifier('code : succès 1 et 4 dans le masque, équipement skin 1', (N(code.slice(39, 46)) & 1) === 1 && (N(code.slice(39, 46)) & 8) === 8 && code.slice(66, 68) === '01', code.slice(39, 46));
  const possAvant = [...T.L('Possedes')].sort().join(',');
  const succesAvant = T.L('Succes').join(',');
  const jetonsCode = N(T.g('jetons'));
  // on casse la progression puis on recharge le code
  T.set('xp', 0); T.set('jetons', 0); T.set('hype', 0); T.diffuser('evt knock'); T.pas(2);
  verifier('progression modifiée avant chargement', N(T.g('xp')) === 25 && N(T.g('niveau')) === 1, [T.g('xp'), T.g('niveau')]);
  T.diffuser('sauvegarde charger'); T.repondre(' ' + code.slice(0, 40) + ' ' + code.slice(40) + ' '); T.pas(3);
  verifier('chargement : xp, niveau, jetons, hype, division restaurés', N(T.g('xp')) === xp && N(T.g('niveau')) === niveauDe(xp) && N(T.g('jetons')) === jetonsCode && N(T.g('hype')) === 1590 && N(T.g('division')) === 4, [T.g('xp'), T.g('niveau'), T.g('jetons'), T.g('hype')]);
  verifier('chargement : possessions et succès restaurés, notification', [...T.L('Possedes')].sort().join(',') === possAvant && T.L('Succes').join(',') === succesAvant && /Sauvegarde chargée/.test(notifs()), [T.L('Possedes'), notifs()]);
  verifier('chargement : totaux (rec) restaurés', N(T.l('Systemes', 'totElims')) === 4 && N(T.l('Systemes', 'totVictoires')) === 3 && N(T.l('Systemes', 'totParties')) === 5 && N(T.l('Systemes', 'totCoffres')) === 1, [T.l('Systemes', 'totElims'), T.l('Systemes', 'totVictoires'), T.l('Systemes', 'totParties')]);
  T.pas(2);
  verifier('le code régénéré est identique', String(T.g('codeSauvegarde')) === code, [T.g('codeSauvegarde'), code]);
  const mauvais = code.slice(0, 5) + ((N(code[5]) + 1) % 10) + code.slice(6);
  T.set('xp', 123);
  T.diffuser('sauvegarde charger'); T.repondre(mauvais); T.pas(3);
  verifier('code altéré refusé (« Code invalide »), xp inchangé', N(T.g('xp')) === 123 && /Code invalide/.test(notifs()), [T.g('xp'), notifs()]);
  T.diffuser('sauvegarde charger'); T.repondre('0123'); T.pas(3);
  verifier('code trop court refusé', N(T.g('xp')) === 123, T.g('xp'));

  // ---------------------------------------------------------------- code créateur
  diffuser('createur definir', undefined, undefined, 'antoine');
  verifier('code créateur défini + notification « Tu soutiens antoine »', T.g('codeCreateur') === 'antoine' && /Tu soutiens antoine/.test(notifs()), [T.g('codeCreateur'), notifs()]);

  // ---------------------------------------------------------------- redémarrage : la progression de la session est conservée
  T.set('xp', xp);
  T.drapeau(); T.pas(8);
  verifier('nouveau drapeau : xp et possessions conservés, bonusXP 1, quêtes réactivées', N(T.g('xp')) === xp && N(T.g('niveau')) === niveauDe(xp) && T.L('Possedes').includes(b1[0] + '|' + b1[1]) && N(T.g('bonusXP')) === 1 && actives().length === 11, [T.g('xp'), T.g('niveau'), T.g('bonusXP')]);
  verifier('aucune liste du contrat en désordre (PasseRecompenses 100, Boutique 6, Succes 21)', T.L('PasseRecompenses').length === 100 && T.L('Boutique').length === 6 && T.L('Succes').length === 21 && T.L('Succes')[0] === '1|1');
};
