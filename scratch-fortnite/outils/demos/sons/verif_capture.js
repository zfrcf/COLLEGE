// VÉRIFICATION ADVERSARIALE avec le VRAI moteur audio (Chromium + scratch-audio) :
//   node outils/capture.js outils/demos/sons/demo.sb3 outils/demos/sons/verif_capture.js
// - les 28 WAV sont décodés par decodeAudioData : durée décodée = sampleCount / rate, pic <= 0,8 ;
// - chaque DÉPART de son (soundBank.playSound) est journalisé avec la cible (original / rôle du clone)
//   et le volume et le PAN effectivement appliqués au lecteur à cet instant ;
// - scénario piloté directement (le sprite Demo est arrêté dès le drapeau) : musique au centre après des
//   effets panoramiqués, voix au centre, second « demarrer », volume de la musique suivi en direct,
//   arrêts, écart entre deux reprises de la boucle ;
// - captures PNG annotées (carte du son + bulle d'état) : outils/captures/sons_verif_*.png.
const injecterAudio = require('./moteur_audio');

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
  verifier('durée décodée = sampleCount / rate (± 2 ms) pour les 28', dureesFausses.length === 0,
    dureesFausses.map(s => [s.nom, s.dureeDecodee, s.sampleCount / s.rate]));
  verifier('pic décodé entre 0,35 et 0,81 partout', charge.sons.every(s => s.pic <= 0.81 && s.pic >= 0.35), charge.sons.map(s => s.nom + ':' + s.pic.toFixed(2)));
  console.log('  taux décodé :', [...new Set(charge.sons.map(s => s.tauxDecode))].join(', '), 'Hz ; durées :',
    charge.sons.map(s => s.nom + ' ' + s.dureeDecodee.toFixed(2)).join(', '));

  // journal des départs (volume / PAN appliqués au lecteur) et pilotage direct
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
      window.departs.push({ t: moteur.audioContext.currentTime, son: nomParId[soundId],
        cible: cible.isOriginal ? 'original' : 'clone ' + locale(cible, 'son_role'), volume: val('volume'), pan: val('pan') });
      return r;
    };
    window.demo = vm.runtime.getSpriteTargetByName('Demo');
    vm.greenFlag();
    vm.runtime.stopForTarget(window.demo);     // la démo ne tourne pas : on pilote nous-mêmes
  });

  const faire = (fn, arg) => aides.evaluer(fn, arg);
  const etat = () => faire((vm, V) => {
    const s = vm.runtime.getSpriteTargetByName('Sons');
    const locale = (t, n) => Object.values(t.variables).find(v => v.name === n).value;
    const panDe = t => t.getCustomState('Scratch.sound').effects.pan;
    const clones = vm.runtime.targets.filter(t => t.sprite === s.sprite && !t.isOriginal);
    const enCours = Object.values(s.sprite.soundBank.soundPlayers).filter(p => p.isPlaying).map(p => window.nomParId[p.id]);
    return { ecran: V('ecran').value, musiqueActive: locale(s, 'son_musiqueActive'), volumeOriginal: s.volume, panOriginal: panDe(s),
      clones: clones.map(c => ({ role: locale(c, 'son_role'), estClone: locale(c, 'son_estClone'), volume: c.volume, pan: panDe(c) })), enCours };
  });
  const set = (nom, valeur) => faire((vm, V, L, a) => { V(a.nom).value = a.valeur; }, { nom, valeur });
  const diffuser = nom => faire((vm, V, L, n) => vm.runtime.startHats('event_whenbroadcastreceived', { BROADCAST_OPTION: n.toUpperCase() }), nom);
  const annoter = async (costume, texte) => {
    await faire((vm, V, L, a) => {
      const d = window.demo;
      d.setVisible(true); d.setXY(0, 8);
      const idx = d.getCostumes().findIndex(c => c.name === a.costume);
      if (idx >= 0) d.setCostume(idx);
      vm.runtime.emit('SAY', d, 'say', a.texte);
    }, { costume, texte });
    await aides.attendre(150);
  };
  const departs = () => page.evaluate(() => window.departs);
  const departsDepuis = async n => (await departs()).slice(n);
  const nbDeparts = async () => (await departs()).length;
  let e, d, n0;

  // --- 1. salon : la musique part par un clone, au centre, au volume param_volumeMusique ---
  await set('ecran', 'salon'); await diffuser('demarrer'); await aides.attendre(700);
  e = await etat(); d = await departsDepuis(0);
  console.log('1. salon :', JSON.stringify(e), JSON.stringify(d));
  verifier('salon : un clone musique, musique_salon en cours', e.clones.length === 1 && e.clones[0].role === 'musique' && e.enCours.includes('musique_salon'), e);
  verifier('départ musique : clone, volume 50 (param_volumeMusique), PAN 0',
    d.length === 1 && d[0].son === 'musique_salon' && d[0].cible === 'clone musique' && d[0].volume === 50 && d[0].pan === 0, d);
  await annoter('musique_salon', 'salon : musique_salon jouée par le clone (volume 50, PAN 0)');
  await aides.capture('sons_verif_01_salon');

  // --- 2. jeu : effet panoramiqué à -70 puis voix émise avec son_pan = 0 → au centre ---
  await set('ecran', 'jeu'); await aides.attendre(300);
  e = await etat();
  verifier('jeu : musique arrêtée, plus de clone', e.clones.length === 0 && !e.enCours.includes('musique_salon'), e);
  n0 = await nbDeparts();
  await set('son_volume', 100); await set('son_pan', -70); await diffuser('son tir_pompe'); await aides.attendre(250);
  d = await departsDepuis(n0);
  verifier('effet tir_pompe : original, volume 80 (param_volumeEffets), PAN -70', d.length === 1 && d[0].cible === 'original' && d[0].volume === 80 && d[0].pan === -70, d);
  n0 = await nbDeparts();
  await set('son_pan', 0); await diffuser('son victoire'); await aides.attendre(250);
  d = await departsDepuis(n0); e = await etat();
  console.log('2. voix :', JSON.stringify(e), JSON.stringify(d));
  verifier('voix victoire (son_pan 0) après un effet à -70 : clone, volume 80, PAN 0',
    d.length === 1 && d[0].son === 'victoire' && d[0].cible === 'clone victoire' && d[0].volume === 80 && d[0].pan === 0, d);
  verifier('l\'original garde PAN -70 et volume 80 pendant la voix', e.panOriginal === -70 && e.volumeOriginal === 80, e);
  await annoter('victoire', 'jeu : « victoire » par un clone au centre (PAN 0) ; original resté à PAN -70');
  await aides.capture('sons_verif_02_voix_centre');
  await aides.attendre(1900);
  e = await etat();
  verifier('clone victoire supprimé après ses 2 s', e.clones.length === 0 && !e.enCours.includes('victoire'), e);

  // --- 3. musique recréée après un effet à PAN 70 : au centre ---
  n0 = await nbDeparts();
  await set('son_pan', 70); await diffuser('son tir_pistolet'); await aides.attendre(200);
  await set('ecran', 'salon'); await aides.attendre(700);
  d = await departsDepuis(n0); e = await etat();
  console.log('3. retour salon :', JSON.stringify(e), JSON.stringify(d));
  const dm = d.find(x => x.son === 'musique_salon');
  verifier('retour salon après un effet à PAN 70 : musique par le clone au centre (PAN 0), volume 50', !!dm && dm.cible === 'clone musique' && dm.pan === 0 && dm.volume === 50, d);
  verifier('l\'original garde PAN 70', e.panOriginal === 70, e.panOriginal);
  await annoter('musique_salon', 'retour salon : musique au centre (PAN 0) malgré l\'original à PAN 70');
  await aides.capture('sons_verif_03_musique_centre');

  // --- 4. second « demarrer » pendant la musique ---
  n0 = await nbDeparts();
  await diffuser('demarrer'); await aides.attendre(700);
  d = await departsDepuis(n0); e = await etat();
  console.log('4. second demarrer :', JSON.stringify(e), JSON.stringify(d));
  verifier('second demarrer : un seul clone (musique, son_estClone 1), musique en cours',
    e.clones.length === 1 && e.clones[0].role === 'musique' && Number(e.clones[0].estClone) === 1 && e.enCours.includes('musique_salon'), e);
  verifier('second demarrer : un seul nouveau départ de musique_salon, PAN 0', d.filter(x => x.son === 'musique_salon').length === 1 && d[0].pan === 0, d);
  verifier('second demarrer : original remis à PAN 0, volume 100', e.panOriginal === 0 && e.volumeOriginal === 100, e);
  await aides.attendre(400);
  e = await etat();
  verifier('… toujours un seul clone 1 s plus tard (pas de cascade)', e.clones.length === 1, e.clones);
  await annoter('musique_salon', 'second « demarrer » : un seul clone musique, relance propre');
  await aides.capture('sons_verif_04_redemarrer');

  // --- 5. volume de la musique suivi en direct ---
  await set('param_volumeMusique', 20); await aides.attendre(350);
  const volLecteur = await faire(vm => {
    const s = vm.runtime.getSpriteTargetByName('Sons');
    const id = s.sprite.sounds.find(x => x.name === 'musique_salon').soundId;
    return s.sprite.soundBank.getSoundEffects(id)._effects.find(e => e.name === 'volume').value;
  });
  e = await etat();
  verifier('param_volumeMusique → 20 : volume du clone et du lecteur suivis en direct', Number(e.clones[0].volume) === 20 && volLecteur === 20, [e.clones, volLecteur]);
  await set('param_volumeMusique', 50);

  // --- 6. arrêts ---
  await diffuser('son stop musique'); await aides.attendre(300);
  e = await etat();
  verifier('son stop musique : aucun clone, rien en cours, son_musiqueActive reste 1 (silence)', e.clones.length === 0 && e.enCours.length === 0 && Number(e.musiqueActive) === 1, e);
  n0 = await nbDeparts();
  await set('son_pan', 0); await diffuser('son compte'); await diffuser('son stop tout'); await aides.attendre(500);
  e = await etat(); d = await departsDepuis(n0);
  console.log('6. arrêts :', JSON.stringify(e), JSON.stringify(d));
  verifier('son stop tout sur le salon : la musique repart (un clone musique, musique_salon en cours)',
    e.clones.length === 1 && e.clones[0].role === 'musique' && e.enCours.includes('musique_salon'), e);
  await annoter('compte', '« son stop musique » → silence ; « son stop tout » → la musique repart');
  await aides.capture('sons_verif_05_arrets');

  // --- 7. la boucle reprend d'elle-même : écart entre deux départs de musique_salon ---
  const reprisesAvant = (await departs()).filter(x => x.son === 'musique_salon').map(x => x.t);
  await aides.attendre(9300);
  const reprises = (await departs()).filter(x => x.son === 'musique_salon').map(x => x.t);
  const dernier = reprises[reprises.length - 1], avant = reprises[reprises.length - 2];
  const ecart = dernier - avant - 8.7273;
  console.log('7. reprises de musique_salon (horloge audio) :', reprises.map(t => t.toFixed(3)).join(' '), '→ trou au-delà de la boucle :', ecart.toFixed(3), 's');
  verifier('la boucle reprend d\'elle-même après 8,73 s (trou < 0,08 s)',
    reprises.length === reprisesAvant.length + 1 && ecart >= -0.01 && ecart < 0.08, [avant, dernier, ecart]);
  await set('ecran', 'jeu'); await aides.attendre(300);
  e = await etat();
  verifier('fin : écran jeu → plus rien', e.clones.length === 0 && e.enCours.length === 0, e);

  console.log(echecs ? echecs + ' ÉCHEC(S) audio réel' : 'Toutes les vérifications audio réelles passent.');
  if (echecs) process.exitCode = 1;
};
