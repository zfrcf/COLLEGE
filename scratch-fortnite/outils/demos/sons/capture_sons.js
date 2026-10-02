// Script de capture pour outils/capture.js : rendu réel dans Chromium + VRAI moteur audio.
//   node outils/capture.js outils/demos/sons/demo.sb3 outils/demos/sons/capture_sons.js
// 1. injecte scratch-audio dans la page (voir moteur_audio.js) : Chromium décode réellement les 28 WAV ;
// 2. laisse tourner la démo et capture l'écran à des instants clés en consignant l'état du
//    sprite Sons (clones et leur rôle, volumes, PAN, sons en cours de lecture).
const injecterAudio = require('./moteur_audio');

module.exports = async (aides) => {
  const { page } = aides;
  const charge = await injecterAudio(page);
  const depart0 = await page.evaluate(() => {
    vm.greenFlag();
    window.t0 = performance.now();
    const s = vm.runtime.getSpriteTargetByName('Sons');
    // horodatage (horloge audio) de chaque départ de la boucle musicale : mesure l'écart entre deux reprises
    window.departsMusique = [];
    const idMusique = s.sprite.sounds.find(x => x.name === 'musique_salon').soundId;
    s.sprite.soundBank.soundPlayers[idMusique].on('play', () => window.departsMusique.push(moteur.audioContext.currentTime));
    return { nbSons: s.sprite.sounds.length, lecteurs: s.sprite.soundBank ? Object.keys(s.sprite.soundBank.soundPlayers).length : -1 };
  });
  console.log('chargement avec moteur audio :', JSON.stringify({
    etatAudio: charge.etatAudio, nbSons: depart0.nbSons, decodes: charge.sons.filter(x => x.decode).length, lecteurs: depart0.lecteurs,
    sons: charge.sons.map(x => x.nom + ':' + x.rate + 'Hz/' + x.sampleCount + '→' + x.dureeDecodee.toFixed(2) + 's'),
  }));

  const etat = () => aides.evaluer((vm, V) => {
    const s = vm.runtime.getSpriteTargetByName('Sons');
    const banque = s.sprite.soundBank;
    const nomParId = {};
    for (const x of s.sprite.sounds) nomParId[x.soundId] = x.name;
    const enCours = banque ? Object.values(banque.soundPlayers).filter(p => p.isPlaying).map(p => nomParId[p.id]) : [];
    const clones = vm.runtime.targets.filter(t => t.sprite === s.sprite && !t.isOriginal);
    const locale = (t, n) => Object.values(t.variables).find(v => v.name === n).value;
    const bulle = vm.runtime.getSpriteTargetByName('Demo').getCustomState('Scratch.looks');
    return {
      t: ((performance.now() - window.t0) / 1000).toFixed(1), etapeDemo: bulle ? bulle.text : '',
      audio: moteur.audioContext.state, horlogeAudio: moteur.audioContext.currentTime.toFixed(1), ecran: V('ecran').value,
      musiqueActive: locale(s, 'son_musiqueActive'), clones: clones.map(c => locale(c, 'son_role')),
      volumeOriginal: s.volume, volumesClones: clones.map(c => c.volume),
      pan: s.getCustomState('Scratch.sound').effects.pan, pansClones: clones.map(c => c.getCustomState('Scratch.sound').effects.pan), enCours,
    };
  });

  // instants nominaux (la démo dérive d'environ 25 ms par étape : le champ etapeDemo dit où elle en est)
  const etapes = [[2.9, 'sons_t03_effet'], [9.9, 'sons_t10_voix'], [17.6, 'sons_t18_musique_fin'],
    [19.2, 'sons_t19_ecran_jeu'], [20.7, 'sons_t21_salon_reprise'], [22.2, 'sons_t22_stop_tout'], [24.5, 'sons_t24_stop_musique']];
  const depart = Date.now();
  for (const [t, nom] of etapes) {
    const reste = t * 1000 - (Date.now() - depart);
    if (reste > 0) await aides.attendre(reste);
    console.log(nom, JSON.stringify(await etat()));
    await aides.capture(nom);
  }
  const departs = await page.evaluate(() => window.departsMusique);
  const ecarts = departs.slice(1).map((t, i) => (t - departs[i] - 8.7273).toFixed(3));
  console.log('départs de musique_salon (horloge audio) :', departs.map(t => t.toFixed(2)).join(' '),
    '→ écarts au-delà des 8,727 s de la boucle :', ecarts.join(' '), 's');
};
