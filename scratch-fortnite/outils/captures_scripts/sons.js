// Module Sons dans le PROJET COMPLET avec le VRAI moteur audio (Chromium + scratch-audio injecté, voir
// outils/demos/sons/moteur_audio.js) :
//   node capture.js captures_scripts/sons.js
// - les 28 WAV sont décodés par decodeAudioData : durée décodée = sampleCount / rate, pic décodé ≤ 0,81 ;
// - chaque DÉPART de son (soundBank.playSound) est journalisé avec la cible (original / rôle du clone) et le
//   volume / PAN effectivement appliqués au lecteur ;
// - musique du salon en cours sur connexion, arrêtée en jeu (effets toujours joués, panoramiqués), voix au centre
//   par un clone, retour au salon → musique au centre, « son stop tout » puis reprise, « son stop musique » ;
// - captures : outils/captures/sons_connexion_musique.png, sons_jeu_effets.png, sons_salon_reprise.png.
const injecterAudio = require('../demos/sons/moteur_audio');

module.exports = async (aides) => {
  const { page } = aides;
  const charge = await injecterAudio(page);
  let echecs = 0;
  const verifier = (libelle, ok, detail) => {
    if (!ok) echecs++;
    console.log((ok ? '  ✔ ' : '  ✘ ') + libelle + (ok || detail === undefined ? '' : '  → ' + JSON.stringify(detail)));
  };
  verifier('AudioContext en marche', charge.etatAudio === 'running', charge.etatAudio);
  verifier('28 sons décodés par Chromium', charge.sons.length === 28 && charge.sons.every(s => s.decode), charge.sons.filter(s => !s.decode).map(s => s.nom));
  const dureesFausses = charge.sons.filter(s => Math.abs(s.dureeDecodee - s.sampleCount / s.rate) > 0.002);
  verifier('durée décodée = sampleCount / rate (± 2 ms) pour les 28', dureesFausses.length === 0, dureesFausses.map(s => [s.nom, s.dureeDecodee, s.sampleCount / s.rate]));
  verifier('pic décodé entre 0,35 et 0,81 partout', charge.sons.every(s => s.pic <= 0.81 && s.pic >= 0.35), charge.sons.map(s => s.nom + ':' + s.pic.toFixed(2)));
  console.log('  taux décodé :', [...new Set(charge.sons.map(s => s.tauxDecode))].join(', '), 'Hz ; durées :', charge.sons.map(s => s.nom + ' ' + s.dureeDecodee.toFixed(2)).join(', '));

  await page.evaluate(() => {
    const s = vm.runtime.getSpriteTargetByName('Sons');
    const banque = s.sprite.soundBank;
    const nomParId = {};
    for (const x of s.sprite.sounds) nomParId[x.soundId] = x.name;
    window.nomParId = nomParId;
    window.departs = [];
    const locale = (t, n) => { const v = Object.values(t.variables).find(v => v.name === n); return v ? v.value : undefined; };
    const orig = banque.playSound.bind(banque);
    banque.playSound = (cible, soundId) => {
      const r = orig(cible, soundId);
      const eff = banque.getSoundEffects(soundId);
      const val = n => { const e = eff._effects.find(e => e.name === n); return e ? e.value : null; };
      window.departs.push({ t: +moteur.audioContext.currentTime.toFixed(2), son: nomParId[soundId],
        cible: cible.isOriginal ? 'original' : 'clone ' + locale(cible, 'son_role'), volume: val('volume'), pan: val('pan') });
      return r;
    };
    vm.postIOData('mouse', { x: 240, y: 180, isDown: false, canvasWidth: 480, canvasHeight: 360 });
    vm.greenFlag();
  });
  const faire = (fn, arg) => aides.evaluer(fn, arg);
  const etat = () => faire((vm, V) => {
    const s = vm.runtime.getSpriteTargetByName('Sons');
    const locale = (t, n) => Object.values(t.variables).find(v => v.name === n).value;
    const panDe = t => t.getCustomState('Scratch.sound').effects.pan;
    const clones = vm.runtime.targets.filter(t => t.sprite === s.sprite && !t.isOriginal);
    const enCours = Object.values(s.sprite.soundBank.soundPlayers).filter(p => p.isPlaying).map(p => window.nomParId[p.id]);
    return { ecran: V('ecran').value, musiqueActive: locale(s, 'son_musiqueActive'), lecteur: V('son_musiqueLecteur').value, volumeOriginal: s.volume, panOriginal: panDe(s),
      clones: clones.map(c => ({ role: locale(c, 'son_role'), estClone: locale(c, 'son_estClone'), volume: c.volume, pan: panDe(c) })), enCours, nbClones: vm.runtime._cloneCounter };
  });
  const set = (nom, valeur) => faire((vm, V, L, a) => { V(a.nom).value = a.valeur; }, { nom, valeur });
  const diffuser = nom => faire((vm, V, L, n) => vm.runtime.startHats('event_whenbroadcastreceived', { BROADCAST_OPTION: n.toUpperCase() }), nom);
  const departs = () => page.evaluate(() => window.departs);
  const nbDeparts = async () => (await departs()).length;
  // la page est lente (rendu 3D en OpenGL logiciel) : état et journal sont lus dans le MÊME evaluate, et l'on attend
  // (au plus `ms`) que la condition soit vraie plutôt qu'un délai fixe
  const instantane = async n0 => { const [e, j] = await Promise.all([etat(), departs()]); return { e, d: j.slice(n0) }; };
  const jusqua = async (n0, cond, ms = 3000) => {
    const t0 = Date.now(); let x = await instantane(n0);
    while (!cond(x) && Date.now() - t0 < ms) { await aides.attendre(100); x = await instantane(n0); }
    return x;
  };
  let e, d, n0, x;

  // --- 1. connexion : la musique part d'elle-même, par un clone, au centre, au volume param_volumeMusique ---
  x = await jusqua(0, x => x.e.enCours.includes('musique_salon'), 4000); e = x.e; d = x.d;
  console.log('1. connexion :', JSON.stringify(e), JSON.stringify(d));
  verifier('connexion : un clone musique, musique_salon en cours', e.ecran === 'connexion' && e.clones.length === 1 && e.clones[0].role === 'musique' && e.enCours.includes('musique_salon'), e);
  verifier('départ musique : clone, volume 50 (param_volumeMusique), PAN 0', d.some(x => x.son === 'musique_salon' && x.cible === 'clone musique' && x.volume === 50 && x.pan === 0), d);
  verifier('aucun effet parti tout seul au démarrage (hors musique)', d.every(x => x.son === 'musique_salon'), d);
  await set('menu_sale', 1); await aides.attendre(800);      // le projet a été rechargé avec le moteur audio : on redessine l'écran
  await aides.capture('sons_connexion_musique');

  // --- 2. jeu : musique arrêtée sans couper les effets ; effet panoramiqué ; voix au centre par un clone ---
  await set('ecran', 'jeu');
  x = await jusqua(0, x => x.e.clones.length === 0 && !x.e.enCours.includes('musique_salon')); e = x.e;
  verifier('jeu : musique arrêtée (lecteur stoppé), plus de clone', e.clones.length === 0 && !e.enCours.includes('musique_salon'), e);
  n0 = await nbDeparts();
  await set('son_volume', 100); await set('son_pan', -70); await diffuser('son tir_pompe');
  x = await jusqua(n0, x => x.d.length >= 1); d = x.d;
  verifier('effet tir_pompe en jeu : original, volume 80 (param_volumeEffets), PAN -70', d.length === 1 && d[0].cible === 'original' && d[0].volume === 80 && d[0].pan === -70, d);
  n0 = await nbDeparts();
  await set('son_pan', 0); await diffuser('son elimination');
  x = await jusqua(n0, x => x.d.length >= 1); d = x.d; e = x.e;
  console.log('2. jeu :', JSON.stringify(e), JSON.stringify(d));
  verifier('voix elimination (son_pan 0) après un effet à -70 : clone, volume 80 (param_volumeVoix), PAN 0',
    d.length === 1 && d[0].son === 'elimination' && d[0].cible === 'clone elimination' && d[0].volume === 80 && d[0].pan === 0, d);
  verifier('l\'original garde PAN -70 et volume 80 pendant la voix', e.panOriginal === -70 && e.volumeOriginal === 80, e);
  await aides.capture('sons_jeu_effets');
  x = await jusqua(0, x => x.e.clones.length === 0 && !x.e.enCours.includes('elimination')); e = x.e;
  verifier('clone elimination supprimé après ses 0,6 s', e.clones.length === 0 && !e.enCours.includes('elimination'), e);

  // --- 3. retour au salon : musique relancée au centre malgré l'original à PAN 70 ; volume suivi en direct ---
  n0 = await nbDeparts();
  await set('son_pan', 70); await diffuser('son tir_pistolet');
  await jusqua(n0, x => x.d.length >= 1);
  await set('ecran', 'salon');
  x = await jusqua(n0, x => x.d.some(y => y.son === 'musique_salon') && x.e.enCours.includes('musique_salon')); d = x.d; e = x.e;
  console.log('3. retour salon :', JSON.stringify(e), JSON.stringify(d));
  const dm = d.find(x => x.son === 'musique_salon');
  verifier('retour salon après un effet à PAN 70 : musique par le clone au centre (PAN 0), volume 50, en cours', !!dm && dm.cible === 'clone musique' && dm.pan === 0 && dm.volume === 50 && e.enCours.includes('musique_salon'), [d, e.enCours]);
  verifier('l\'original garde PAN 70', e.panOriginal === 70, e.panOriginal);
  await set('param_volumeMusique', 20); await aides.attendre(400);
  const volLecteur = await faire(vm => {
    const s = vm.runtime.getSpriteTargetByName('Sons');
    const eff = s.sprite.soundBank.getSoundEffects(s.sprite.sounds.find(x => x.name === 'musique_salon').soundId);
    return eff._effects.find(e => e.name === 'volume').value;
  });
  verifier('param_volumeMusique 20 : volume du lecteur de musique suivi en direct (20)', volLecteur === 20, volLecteur);
  await set('param_volumeMusique', 50); await aides.attendre(200);
  await aides.capture('sons_salon_reprise');

  // --- 4. arrêts ---
  n0 = await nbDeparts();
  const idAvant = e.clones.length ? await faire(vm => vm.runtime.targets.find(t => t.getName() === 'Sons' && !t.isOriginal).id) : null;
  await diffuser('son stop tout');
  x = await jusqua(n0, x => x.d.some(y => y.son === 'musique_salon') && x.e.enCours.includes('musique_salon')); d = x.d; e = x.e;
  const idApres = await faire(vm => (vm.runtime.targets.find(t => t.getName() === 'Sons' && !t.isOriginal) || {}).id);
  console.log('4. stop tout :', JSON.stringify(e), JSON.stringify(d));
  // (si la page est très lente, l'ancien clone peut relancer la boucle une fois avant sa suppression : 1 ou 2 départs rapprochés,
  //  tous au centre ; les départs suivants sont les reprises normales de la boucle toutes les 8,73 s)
  verifier('« son stop tout » sur un écran musical : ancien clone supprimé, la musique repart d\'elle-même par un NOUVEAU clone, au centre',
    e.clones.length === 1 && e.clones[0].role === 'musique' && e.enCours.includes('musique_salon') && idApres !== idAvant
    && d.length >= 1 && d.filter(y => y.t - d[0].t < 2).length <= 2 && d.every(y => y.son === 'musique_salon' && y.cible === 'clone musique' && y.pan === 0 && y.volume === 50), [e.clones, d, idAvant, idApres]);
  await diffuser('son stop musique');
  x = await jusqua(0, x => x.e.clones.length === 0 && !x.e.enCours.includes('musique_salon')); e = x.e;
  verifier('« son stop musique » : plus de clone, lecteur de musique arrêté, silence maintenu', e.clones.length === 0 && !e.enCours.includes('musique_salon') && Number(e.musiqueActive) === 1, e);
  n0 = await nbDeparts();
  await set('son_pan', 0); await diffuser('son clic');
  x = await jusqua(n0, x => x.d.length >= 1); d = x.d;
  verifier('… les effets jouent toujours (clic par l\'original, PAN 0)', d.length === 1 && d[0].son === 'clic' && d[0].cible === 'original' && d[0].pan === 0, d);
  await set('ecran', 'jeu'); await jusqua(0, x => Number(x.e.musiqueActive) === 0); await set('ecran', 'connexion');
  x = await jusqua(0, x => x.e.clones.length === 1 && x.e.enCours.includes('musique_salon'), 4000); e = x.e;
  verifier('… et la musique reprend après un passage par un écran non musical', e.clones.length === 1 && e.enCours.includes('musique_salon'), e);
  const log = await aides.log();
  verifier('aucune erreur de page', !log.some(l => /ERREUR/.test(l)), log.filter(l => /ERREUR/.test(l)));
  console.log(echecs ? 'SONS : ' + echecs + ' échec(s)' : 'SONS : tout est vert');
};
