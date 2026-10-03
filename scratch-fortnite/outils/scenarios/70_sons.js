// Module Sons dans le PROJET COMPLET (scratch-vm, sans moteur audio) :
//   node test_vm.js ../"Royale 3D.sb3" scenarios/70_sons.js
// Vérifie : les 28 sons de contrat.SONS attachés (WAV, taux, échantillons), aucun opcode inconnu, un script
// « quand je reçois son <nom> » par son + « son stop musique » / « son stop tout », la musique du salon
// (clone « musique ») présente sur connexion/salon/matchmaking/chargement et supprimée ailleurs, le volume
// des effets = param_volumeEffets × son_volume / 100 et l'effet PAN = son_pan, les voix et musiques jouées
// par un clone au volume de leur catégorie, les arrêts, et qu'une diffusion « son clic » ne provoque aucune erreur.
// Un faux « soundBank » journalise chaque départ de son avec le volume et le PAN de la cible à cet instant.
const fs = require('fs');
const path = require('path');

module.exports = async (T, verifier) => {
  const contrat = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'contrat.json'), 'utf8'));
  const S = T.sprite('Sons');
  const sons = S.sprite.sounds;
  verifier('28 sons attachés au sprite Sons', sons.length === 28 && contrat.sons.length === 28, sons.length);
  verifier('noms des sons = contrat.SONS (même ordre)', JSON.stringify(sons.map(s => s.name)) === JSON.stringify(contrat.sons), sons.map(s => s.name));
  verifier('tous en WAV à 22050 ou 11025 Hz avec des échantillons et un md5',
    sons.every(s => s.dataFormat === 'wav' && (s.rate === 22050 || s.rate === 11025) && s.sampleCount > 0 && /^[0-9a-f]{32}\.wav$/.test(s.md5)), sons[0]);
  verifier('sprite Sons invisible', !S.visible);
  verifier('aucun opcode inconnu', T.opcodesInconnus().length === 0, T.opcodesInconnus());

  // un chapeau « quand je reçois » par son + les deux arrêts
  const chapeaux = Object.values(S.blocks._blocks).filter(b => b.opcode === 'event_whenbroadcastreceived' && b.topLevel)
    .map(b => String(b.fields.BROADCAST_OPTION.value).toLowerCase());
  const manquants = contrat.sons.filter(n => !chapeaux.includes('son ' + n));
  verifier('un script « quand je reçois son <nom> » par son', manquants.length === 0, manquants);
  verifier('scripts « son stop musique » et « son stop tout »', chapeaux.includes('son stop musique') && chapeaux.includes('son stop tout'), chapeaux);
  const parametre = nom => nom.startsWith('musique_') ? 'param_volumeMusique'
    : ['victoire', 'defaite', 'niveau', 'elimination', 'notification', 'compte'].includes(nom) ? 'param_volumeVoix' : 'param_volumeEffets';
  // chaque script lit bien la variable de volume de sa catégorie
  const mauvaiseCategorie = [];
  for (const b of Object.values(S.blocks._blocks)) {
    if (b.opcode !== 'event_whenbroadcastreceived' || !b.topLevel) continue;
    const nom = String(b.fields.BROADCAST_OPTION.value).toLowerCase().replace(/^son /, '');
    if (!contrat.sons.includes(nom)) continue;
    const vars = new Set(); let id = b.next; const pile = [];
    while (id) { pile.push(id); id = S.blocks._blocks[id].next; }
    const visiter = (bid) => { const bl = S.blocks._blocks[bid]; if (!bl) return; if (bl.opcode === 'data_variable') vars.add(bl.fields.VARIABLE.value);
      for (const k in bl.inputs) { const inp = bl.inputs[k]; if (inp.block) visiter(inp.block); }
      if (bl.inputs.SUBSTACK && bl.inputs.SUBSTACK.block) { let s = bl.inputs.SUBSTACK.block; while (s) { visiter(s); s = S.blocks._blocks[s].next; } }
      if (bl.inputs.SUBSTACK2 && bl.inputs.SUBSTACK2.block) { let s = bl.inputs.SUBSTACK2.block; while (s) { visiter(s); s = S.blocks._blocks[s].next; } } };
    pile.forEach(visiter);
    const attendu = parametre(nom);
    const autres = ['param_volumeMusique', 'param_volumeVoix', 'param_volumeEffets'].filter(p => p !== attendu);
    if (!vars.has(attendu) || autres.some(p => vars.has(p))) mauvaiseCategorie.push(nom + ' → ' + [...vars].filter(v => v.startsWith('param_')).join(','));
  }
  verifier('chaque script lit la variable de volume de sa catégorie (musique/voix/effets)', mauvaiseCategorie.length === 0, mauvaiseCategorie);

  // --- faux moteur audio : journal des départs (volume / PAN appliqués à cet instant) ---
  const clones = () => T.vm.runtime.targets.filter(t => t.sprite === S.sprite && !t.isOriginal);
  const locale = (t, n) => Object.values(t.variables).find(v => v.name === n).value;
  const roles = () => clones().map(c => locale(c, 'son_role'));
  const panDe = t => t.getCustomState('Scratch.sound').effects.pan;
  // les blocs son rendent une promesse résolue à l'image suivante : laisser tourner les micro-tâches entre deux images
  const pas = async n => { for (let i = 0; i < n; i++) { T.vm.runtime._step(); await new Promise(r => setImmediate(r)); } };
  sons.forEach(x => { x.soundId = x.name; });
  const journal = [];
  S.sprite.soundBank = {
    playSound(cible, soundId) {
      journal.push({ son: soundId, cible: cible.isOriginal ? 'original' : 'clone ' + locale(cible, 'son_role'), volume: cible.volume, pan: panDe(cible) });
      return new Promise(r => setImmediate(r));     // « jusqu'au bout » dure une image
    },
    setEffects() {}, stop() {}, stopAllSounds() {}, dispose() {},
  };
  // la boucle du salon (jouée « jusqu'au bout » en une image par le faux moteur) redémarre à chaque image : on l'écarte des comparaisons
  const depuis = n => journal.slice(n).filter(d => d.son !== 'musique_salon');

  T.souris(0, 0, false);
  T.drapeau(); await pas(6);
  verifier('écran de départ « connexion »', T.g('ecran') === 'connexion', T.g('ecran'));
  verifier('musique du salon : un clone « musique » dès l\'écran connexion', roles().length === 1 && roles()[0] === 'musique' && Number(T.l('Sons', 'son_musiqueActive')) === 1, roles());
  verifier('musique_salon jouée par le clone au volume param_volumeMusique (50), PAN 0',
    journal.some(d => d.son === 'musique_salon' && d.cible === 'clone musique' && d.volume === Number(T.g('param_volumeMusique')) && d.pan === 0), journal.slice(0, 3));
  verifier('l\'original : son_estClone = 0, volume 100', Number(T.l('Sons', 'son_estClone')) === 0 && Number(S.volume) === 100, [T.l('Sons', 'son_estClone'), S.volume]);

  // --- « son clic » ne provoque aucune erreur, volume effets × son_volume / 100, PAN = son_pan ---
  let n0 = journal.length; const nbErreurs = T.erreurs.length;
  T.set('son_volume', 100); T.set('son_pan', 0); T.diffuser('son clic'); await pas(4);
  verifier('« son clic » : joué par l\'original au volume param_volumeEffets (80), PAN 0, sans erreur',
    JSON.stringify(depuis(n0)) === JSON.stringify([{ son: 'clic', cible: 'original', volume: 80, pan: 0 }]) && T.erreurs.length === nbErreurs, [depuis(n0), T.erreurs.slice(nbErreurs)]);
  verifier('… et la musique continue (clone toujours là)', roles().length === 1 && roles()[0] === 'musique', roles());
  n0 = journal.length;
  T.set('son_volume', 50); T.set('son_pan', 30); T.diffuser('son tir_pistolet'); await pas(4);
  verifier('effet : volume = 80 × 50 / 100 = 40, PAN = son_pan (30)', JSON.stringify(depuis(n0)) === JSON.stringify([{ son: 'tir_pistolet', cible: 'original', volume: 40, pan: 30 }]), depuis(n0));
  verifier('PAN mémorisé (son_dernierPan = 30)', Number(T.l('Sons', 'son_dernierPan')) === 30, T.l('Sons', 'son_dernierPan'));
  T.set('param_volumeEffets', 20); n0 = journal.length;
  T.set('son_pan', -15); T.diffuser('son coffre'); await pas(4);
  verifier('param_volumeEffets 20 : volume = 20 × 50 / 100 = 10, PAN -15', JSON.stringify(depuis(n0)) === JSON.stringify([{ son: 'coffre', cible: 'original', volume: 10, pan: -15 }]), depuis(n0));
  T.set('param_volumeEffets', 80);

  // --- voix : clone éphémère au volume param_volumeVoix × son_volume / 100, PAN propre ---
  n0 = journal.length;
  T.set('son_volume', 100); T.set('son_pan', 0); T.diffuser('son elimination'); await pas(1);
  verifier('voix « elimination » : clone dédié créé', roles().includes('elimination'), roles());
  await pas(6);
  verifier('… jouée par le clone au volume param_volumeVoix (80), PAN 0 (pas le -15 hérité de l\'original)',
    JSON.stringify(depuis(n0)) === JSON.stringify([{ son: 'elimination', cible: 'clone elimination', volume: 80, pan: 0 }]), depuis(n0));
  verifier('… puis clone supprimé ; l\'original garde volume 10 et PAN -15', !roles().includes('elimination') && Number(S.volume) === 10 && panDe(S) === -15, [roles(), S.volume, panDe(S)]);
  T.set('param_volumeVoix', 30); n0 = journal.length;
  T.set('son_volume', 50); T.diffuser('son compte'); await pas(7);
  verifier('param_volumeVoix 30, son_volume 50 : voix à 15', JSON.stringify(depuis(n0)) === JSON.stringify([{ son: 'compte', cible: 'clone compte', volume: 15, pan: 0 }]), depuis(n0));
  T.set('param_volumeVoix', 80); T.set('son_volume', 100);

  // --- écrans : musique sur connexion/salon/matchmaking/chargement, arrêtée ailleurs sans couper les effets ---
  for (const e of ['salon', 'matchmaking', 'chargement']) {
    T.set('ecran', e); await pas(3);
    verifier('écran « ' + e + ' » : la musique reste (un seul clone musique)', roles().length === 1 && roles()[0] === 'musique', roles());
  }
  n0 = journal.length;
  T.set('ecran', 'jeu'); await pas(4);
  verifier('écran « jeu » : clone musique supprimé, son_musiqueActive = 0', roles().length === 0 && Number(T.l('Sons', 'son_musiqueActive')) === 0, [roles(), T.l('Sons', 'son_musiqueActive')]);
  n0 = journal.length;
  T.set('son_pan', 60); T.diffuser('son tir_pompe'); await pas(4);
  verifier('en jeu, les effets jouent toujours (tir_pompe, PAN 60)', depuis(n0).some(d => d.son === 'tir_pompe' && d.cible === 'original' && d.pan === 60), depuis(n0));
  for (const e of ['pause', 'carte', 'spectateur', 'fin', 'prepartie', 'bus', 'parachute', 'cinema']) {
    T.set('ecran', e); await pas(3);
    verifier('écran « ' + e + ' » : pas de musique du salon', !roles().includes('musique'), roles());
  }
  n0 = journal.length; T.set('son_pan', 0);
  T.diffuser('son musique_fin'); await pas(1);
  verifier('« son musique_fin » : clone dédié au volume param_volumeMusique', roles().includes('musique_fin') , roles());
  await pas(6);
  verifier('… joué au volume param_volumeMusique (50), PAN 0, puis clone supprimé', JSON.stringify(depuis(n0)) === JSON.stringify([{ son: 'musique_fin', cible: 'clone musique_fin', volume: 50, pan: 0 }]) && !roles().includes('musique_fin'), [depuis(n0), roles()]);

  // --- retour au salon : la musique reprend au centre malgré le PAN 60 des effets ---
  n0 = journal.length;
  T.set('ecran', 'salon'); await pas(5);
  const dm = journal.slice(n0).find(d => d.son === 'musique_salon');
  verifier('retour au salon : musique relancée par un clone, PAN 0, volume 50', !!dm && dm.cible === 'clone musique' && dm.pan === 0 && dm.volume === 50, journal.slice(n0, n0 + 3));
  T.set('son_pan', 60); T.diffuser('son touche'); await pas(3);
  verifier('l\'original garde son PAN d\'effets (60)', panDe(S) === 60, panDe(S));
  T.set('param_volumeMusique', 20); await pas(6);
  verifier('param_volumeMusique suivi en direct par le clone musique (20)', clones().some(c => locale(c, 'son_role') === 'musique' && Number(c.volume) === 20), clones().map(c => c.volume));
  T.set('param_volumeMusique', 50);
  n0 = journal.length;
  T.diffuser('son musique_salon'); await pas(4);
  verifier('« son musique_salon » pendant la boucle : pas de second lecteur', roles().length === 1 && journal.slice(n0).every(d => d.cible === 'clone musique'), [roles(), journal.slice(n0)]);

  // --- arrêts ---
  T.diffuser('son stop musique'); await pas(4);
  verifier('« son stop musique » : clone supprimé, silence maintenu sur l\'écran courant', roles().length === 0 && Number(T.l('Sons', 'son_musiqueActive')) === 1, [roles(), T.l('Sons', 'son_musiqueActive')]);
  n0 = journal.length;
  T.diffuser('son saut'); await pas(4);
  verifier('… les effets jouent toujours', depuis(n0).some(d => d.son === 'saut' && d.cible === 'original'), depuis(n0));
  T.set('ecran', 'jeu'); await pas(3); T.set('ecran', 'salon'); await pas(4);
  verifier('… la musique reprend après un passage par un écran non musical', roles().length === 1 && roles()[0] === 'musique', roles());
  const idAvant = clones()[0].id; const stops = []; S.sprite.soundBank.stopAllSounds = (c) => stops.push(c ? (c.isOriginal ? 'original' : 'clone') : 'tous');
  T.diffuser('son stop tout'); await pas(5);
  verifier('« son stop tout » : « arrêter tous les sons » exécuté par l\'original, ancien clone supprimé', stops.includes('original') && !clones().some(c => c.id === idAvant), [stops, roles()]);
  verifier('… puis la musique reprend d\'elle-même sur un écran musical (un nouveau clone)', roles().length === 1 && roles()[0] === 'musique', roles());

  // --- second drapeau vert (vrai redémarrage) : un seul clone musique, aucun clone pris pour l'original ---
  T.drapeau(); await pas(8);
  verifier('second drapeau vert : écran connexion, exactement un clone musique, son_estClone = 1 sur les clones',
    T.g('ecran') === 'connexion' && roles().length === 1 && roles()[0] === 'musique' && clones().every(c => Number(locale(c, 'son_estClone')) === 1), roles());
  verifier('original : son_estClone 0, PAN remis à 0, volume 100', Number(T.l('Sons', 'son_estClone')) === 0 && panDe(S) === 0 && Number(S.volume) === 100, [panDe(S), S.volume]);
  // --- clone musique impossible (limite de 300 clones atteinte par d'autres sprites) : l'original doit réessayer
  //     dès que des clones se libèrent (globale son_musiqueLecteur). La saturation est simulée sur le compteur du VM. ---
  T.set('ecran', 'salon'); await pas(4);
  T.diffuser('son stop musique'); await pas(3);                       // plus de clone musique (son_musiqueLecteur reste à 1)
  const reels = () => T.vm.runtime.targets.filter(t => !t.isOriginal).length;
  T.vm.runtime._cloneCounter = 300;
  T.set('ecran', 'jeu'); await pas(3); T.set('ecran', 'salon'); await pas(4);  // nouvelle tentative de clonage : refusée
  verifier('saturation : clone musique impossible → son_musiqueLecteur = 0, son_musiqueActive = 1, aucune erreur VM',
    roles().length === 0 && Number(T.g('son_musiqueLecteur')) === 0 && Number(T.l('Sons', 'son_musiqueActive')) === 1 && T.erreurs.length === 0, [roles(), T.g('son_musiqueLecteur')]);
  T.vm.runtime._cloneCounter = reels();                               // des clones se libèrent
  const t0 = Date.now(); while (Date.now() - t0 < 700) await pas(1);
  verifier('clones libérés : la musique repart d\'elle-même en moins de 0,7 s (un seul clone musique, son_musiqueLecteur = 1)',
    roles().length === 1 && roles()[0] === 'musique' && Number(T.g('son_musiqueLecteur')) === 1 && Number(T.l('Sons', 'son_musiqueActive')) === 1, [roles(), T.g('son_musiqueLecteur')]);
  T.diffuser('son stop musique'); const t1 = Date.now(); while (Date.now() - t1 < 700) await pas(1);
  verifier('« son stop musique » volontaire : pas de reprise automatique après 0,7 s', roles().length === 0, roles());

  // --- valeurs hors bornes et nom inconnu : pas d'erreur ---
  n0 = journal.length;
  T.set('son_volume', -50); T.set('son_pan', 250); T.diffuser('son clic'); await pas(4);
  verifier('son_volume négatif / son_pan 250 : volume 0, PAN borné à 100', depuis(n0).some(d => d.son === 'clic' && d.volume === 0 && d.pan === 100), depuis(n0));
  T.set('son_volume', 100); T.set('son_pan', 0);
  n0 = journal.length;
  T.diffuser('son inexistant'); await pas(3);
  verifier('nom inconnu : aucun départ, aucune erreur', depuis(n0).length === 0 && T.erreurs.length === 0, [depuis(n0), T.erreurs.slice(0, 2)]);
  verifier('aucune erreur VM', T.erreurs.length === 0, T.erreurs.slice(0, 3));
};
