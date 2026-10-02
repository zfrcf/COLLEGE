// Script de capture pour outils/capture.js : rendu réel dans Chromium + VRAI moteur audio.
//   node outils/capture.js outils/demos/sons/demo.sb3 outils/demos/sons/capture_sons.js
// 1. injecte scratch-audio dans la page (bundle commonjs2 + ses trois externes : audio-context,
//    startaudiocontext, minilog) via un petit shim `require`, attache un AudioEngine au vm et
//    recharge le projet : Chromium décode alors réellement les 28 WAV (decodeAudioData) ;
// 2. laisse tourner la démo et capture l'écran à des instants clés en consignant l'état du
//    sprite Sons (clones et leur rôle, volumes, PAN, sons en cours de lecture).
const fs = require('fs');
const path = require('path');

module.exports = async (aides) => {
  const { page } = aides;
  const nm = path.join(__dirname, '..', '..', 'node_modules');
  const lire = f => fs.readFileSync(path.join(nm, f), 'utf8');
  const enveloppe = (src, nom) => '(function(){var module={exports:{}};var exports=module.exports;\n' + src
    + '\n;modules[' + JSON.stringify(nom) + ']=module.exports;})();\n';
  const script = '(function(){var modules={};\n'
    + enveloppe(lire('audio-context/index.js'), 'audio-context')
    + enveloppe(lire('startaudiocontext/StartAudioContext.js'), 'startaudiocontext')
    + lire('minilog/dist/minilog.js') + '\nmodules["minilog"]=window.Minilog;\n'
    + 'var require=function(n){if(!(n in modules))throw new Error("module absent : "+n);return modules[n];};\n'
    + 'var module={exports:{}};var exports=module.exports;\n' + lire('scratch-audio/dist.js')
    + '\n;window.AudioEngine=module.exports.default||module.exports;})();';
  await page.addScriptTag({ content: script });
  await page.mouse.click(240, 180);            // geste utilisateur réel : autorise l'AudioContext
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
    // horodatage (horloge audio) de chaque départ de la boucle musicale : mesure l'écart entre deux reprises
    window.departsMusique = [];
    const idMusique = s.sprite.sounds.find(x => x.name === 'musique_salon').soundId;
    s.sprite.soundBank.soundPlayers[idMusique].on('play', () => window.departsMusique.push(moteur.audioContext.currentTime));
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
    const enCours = banque ? Object.values(banque.soundPlayers).filter(p => p.isPlaying).map(p => nomParId[p.id]) : [];
    const clones = vm.runtime.targets.filter(t => t.sprite === s.sprite && !t.isOriginal);
    const locale = (t, n) => Object.values(t.variables).find(v => v.name === n).value;
    const bulle = vm.runtime.getSpriteTargetByName('Demo').getCustomState('Scratch.looks');
    return {
      t: ((performance.now() - window.t0) / 1000).toFixed(1), etapeDemo: bulle ? bulle.text : '',
      audio: moteur.audioContext.state, horlogeAudio: moteur.audioContext.currentTime.toFixed(1), ecran: V('ecran').value,
      musiqueActive: locale(s, 'son_musiqueActive'), clones: clones.map(c => locale(c, 'son_role')),
      volumeOriginal: s.volume, volumesClones: clones.map(c => c.volume),
      pan: s.getCustomState('Scratch.sound').effects.pan, enCours,
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
