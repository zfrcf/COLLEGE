// Moteur audio RÉEL pour le banc de capture (outils/capture.js) : la page du banc n'attache pas
// scratch-audio. Ce module l'injecte dans la page (bundle commonjs2 + ses trois externes :
// audio-context, startaudiocontext, minilog) via un petit shim `require`, attache un AudioEngine
// au vm et recharge le projet : Chromium décode alors réellement les WAV (decodeAudioData).
//
//   const injecterAudio = require('./moteur_audio');
//   const infos = await injecterAudio(aides.page);
//   // infos = { etatAudio, sons: [{ nom, rate, sampleCount, decode, dureeDecodee, tauxDecode, pic }] }
//
// Après l'appel, le projet est rechargé et ARRÊTÉ : l'appelant lance vm.greenFlag() lui-même.
// `window.moteur` est l'AudioEngine (horloge audio : moteur.audioContext.currentTime).
const fs = require('fs');
const path = require('path');

module.exports = async function injecterAudio(page, nomSprite = 'Sons') {
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
  return page.evaluate(async (nomSprite) => {
    const moteur = new window.AudioEngine();
    window.moteur = moteur;
    vm.attachAudioEngine(moteur);
    const buf = await (await fetch('projet.sb3')).arrayBuffer();
    await vm.loadProject(buf);
    try { await moteur.audioContext.resume(); } catch (e) { /* politique de lecture automatique */ }
    const s = vm.runtime.getSpriteTargetByName(nomSprite);
    const sons = s.sprite.sounds.map(x => {
      const lecteur = x.soundId && s.sprite.soundBank ? s.sprite.soundBank.soundPlayers[x.soundId] : null;
      let dureeDecodee = -1, tauxDecode = -1, pic = -1;
      if (lecteur && lecteur.buffer) {
        dureeDecodee = lecteur.buffer.duration;
        tauxDecode = lecteur.buffer.sampleRate;
        const d = lecteur.buffer.getChannelData(0);
        let m = 0;
        for (let i = 0; i < d.length; i++) { const a = Math.abs(d[i]); if (a > m) m = a; }
        pic = m;
      }
      return { nom: x.name, rate: x.rate, sampleCount: x.sampleCount, decode: !!x.soundId, dureeDecodee, tauxDecode, pic };
    });
    return { etatAudio: moteur.audioContext.state, sons };
  }, nomSprite);
};
