// Script de capture pour outils/capture.js : rendu réel dans Chromium + VRAI moteur audio.
//   node outils/capture.js outils/demos/sons/demo.sb3 outils/demos/sons/capture_sons.js
// 1. injecte scratch-audio (bundle commonjs2) dans la page, attache un AudioEngine au vm et
//    recharge le projet : Chromium décode alors réellement les 28 WAV (decodeAudioData) ;
// 2. laisse tourner la démo et capture l'écran à des instants clés en consignant l'état du
//    sprite Sons (clones et leur rôle, volumes, PAN, sons en cours de lecture).
const fs = require('fs');
const path = require('path');

module.exports = async (aides) => {
  const { page } = aides;
  const src = fs.readFileSync(path.join(__dirname, '..', '..', 'node_modules', 'scratch-audio', 'dist.js'), 'utf8');
  await page.addScriptTag({ content: '(function(){var module={exports:{}};var exports=module.exports;\n' + src
    + '\n;window.AudioEngine=module.exports.default||module.exports;})();' });
  const charge = await page.evaluate(async () => {
    const moteur = new window.AudioEngine();
    window.moteur = moteur;
    vm.attachAudioEngine(moteur);
    const buf = await (await fetch('projet.sb3')).arrayBuffer();
    await vm.loadProject(buf);
    try { moteur.audioContext.resume().catch(() => {}); } catch (e) { /* politique de lecture automatique */ }
    vm.greenFlag();
    window.t0 = performance.now();
    const s = vm.runtime.getSpriteTargetByName('Sons');
    return {
      etatAudio: moteur.audioContext.state, nbSons: s.sprite.sounds.length,
      decodes: s.sprite.sounds.filter(x => x.soundId).length,
      lecteurs: s.sprite.soundBank ? Object.keys(s.sprite.soundBank.soundPlayers).length : -1,
      sons: s.sprite.sounds.map(x => x.name + ':' + x.rate + 'Hz/' + x.sampleCount),
    };
  });
  console.log('chargement avec moteur audio :', JSON.stringify(charge));

  const etat = () => aides.evaluer((vm, V) => {
    const s = vm.runtime.getSpriteTargetByName('Sons');
    const banque = s.sprite.soundBank;
    const nomParId = {};
    for (const x of s.sprite.sounds) nomParId[x.soundId] = x.name;
    const enCours = Object.values(banque.soundPlayers).filter(p => p.isPlaying).map(p => nomParId[p.id]);
    const clones = vm.runtime.targets.filter(t => t.sprite === s.sprite && !t.isOriginal);
    const locale = (t, n) => Object.values(t.variables).find(v => v.name === n).value;
    return {
      t: ((performance.now() - window.t0) / 1000).toFixed(1), audio: moteur.audioContext.state,
      horlogeAudio: moteur.audioContext.currentTime.toFixed(1), ecran: V('ecran').value,
      musiqueActive: locale(s, 'son_musiqueActive'), clones: clones.map(c => locale(c, 'son_role')),
      volumeOriginal: s.volume, volumesClones: clones.map(c => c.volume),
      pan: s.getCustomState('Scratch.sound').effects.pan, enCours,
    };
  });

  const etapes = [[2.9, 'sons_03_touche'], [9.5, 'sons_14_tempete'], [17.3, 'sons_27_musique_fin'],
    [18.4, 'sons_ecran_jeu'], [19.9, 'sons_salon_reprise'], [21.4, 'sons_stop_tout'], [22.9, 'sons_stop_musique']];
  const depart = Date.now();
  for (const [t, nom] of etapes) {
    const reste = t * 1000 - (Date.now() - depart);
    if (reste > 0) await aides.attendre(reste);
    console.log(nom, JSON.stringify(await etat()));
    await aides.capture(nom);
  }
};
