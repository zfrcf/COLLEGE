// Bibliothèque de test : charge un .sb3 dans scratch-vm (sans rendu) et expose
// des aides pour piloter le jeu image par image.
//
//   const { charger } = require('./vm_lib');
//   const T = await charger('../Royale 3D.sb3');
//   T.drapeau(); T.pas(5); T.touche('z', true); T.pas(10); console.log(T.g('px'));
//
// Remarque : sans moteur de rendu, le séquenceur exécute plusieurs itérations de
// « répéter indéfiniment » par pas (pas de demande de redessin). Les tests de
// logique restent valides ; les tests de vitesse exacte ne le sont pas.
const fs = require('fs');
const path = require('path');
const VM = require('scratch-vm');

async function charger(chemin, options = {}) {
  const vm = new VM();
  const erreurs = [];
  const origErr = console.error;
  console.error = (...a) => { const s = a.join(' '); if (!/No storage module|Translation for/.test(s)) erreurs.push(s); };
  process.on('unhandledRejection', e => erreurs.push('rejection: ' + e));
  await vm.loadProject(fs.readFileSync(chemin));
  vm.runtime.currentStepTime = 1000 / 30;
  vm.setTurboMode(!!options.turbo);
  const stage = vm.runtime.getTargetForStage();
  const trouverVar = (cible, nom) => Object.values(cible.variables).find(v => v.name === nom);
  const T = {
    vm, stage, erreurs,
    // --- cycle de vie ---
    drapeau() { vm.greenFlag(); },
    pas(n = 1) { for (let i = 0; i < n; i++) vm.runtime._step(); },
    // --- entrées ---
    touche(k, enfonce) { vm.postIOData('keyboard', { key: k, isDown: !!enfonce }); },
    appui(k, pasApres = 1) { T.touche(k, true); T.pas(pasApres); T.touche(k, false); T.pas(1); },
    // x, y en coordonnées Scratch (centre = 0,0)
    souris(x, y, enfonce) { vm.postIOData('mouse', { x: 240 + x, y: 180 - y, isDown: !!enfonce, canvasWidth: 480, canvasHeight: 360 }); },
    clic(x, y, pasApres = 2) { T.souris(x, y, true); T.pas(pasApres); T.souris(x, y, false); T.pas(1); },
    repondre(texte) { vm.runtime.emit('ANSWER', texte); },
    pseudo(nom) { vm.postIOData('userData', { username: nom }); },
    diffuser(nom) { vm.runtime.startHats('event_whenbroadcastreceived', { BROADCAST_OPTION: String(nom).toUpperCase() }); },
    // --- état ---
    g(nom) { const v = trouverVar(stage, nom); if (!v) throw new Error('variable globale inconnue : ' + nom); return v.value; },
    set(nom, valeur) { const v = trouverVar(stage, nom); if (!v) throw new Error('variable globale inconnue : ' + nom); v.value = valeur; },
    L(nom) { const v = trouverVar(stage, nom); if (!v) throw new Error('liste globale inconnue : ' + nom); return v.value; },
    sprite(nom) { const s = vm.runtime.getSpriteTargetByName(nom); if (!s) throw new Error('sprite inconnu : ' + nom); return s; },
    l(sprite, nom) { const v = trouverVar(T.sprite(sprite), nom); if (!v) throw new Error('variable locale inconnue : ' + sprite + '.' + nom); return v.value; },
    clones(nom) { return vm.runtime.targets.filter(t => t.getName() === nom && !t.isOriginal).length; },
    visible(nom) { return T.sprite(nom).visible; },
    costume(nom) { const s = T.sprite(nom); return s.getCostumes()[s.currentCostume].name; },
    // --- diagnostics ---
    opcodesInconnus() {
      const connus = new Set(['procedures_definition', 'procedures_prototype', 'argument_reporter_string_number', 'argument_reporter_boolean',
        'control_forever', 'control_repeat', 'control_if', 'control_if_else', 'control_repeat_until', 'control_stop', 'procedures_call',
        'data_variable', 'data_listcontents', 'control_wait_until', 'control_wait']);
      const inconnus = new Set();
      for (const t of vm.runtime.targets) for (const id in t.blocks._blocks) {
        const b = t.blocks._blocks[id];
        if (b.shadow || connus.has(b.opcode)) continue;
        if (!vm.runtime.getOpcodeFunction(b.opcode) && !vm.runtime._hats[b.opcode]) inconnus.add(b.opcode);
      }
      return [...inconnus];
    },
    nbBlocs() { return vm.runtime.targets.filter(t => t.isOriginal).reduce((n, t) => n + Object.keys(t.blocks._blocks).length, 0); },
    fin() { console.error = origErr; },
  };
  return T;
}

// Construit un paquet réseau à partir de outils/contrat.json (généré par `python3 -m royale.contrat`).
function chargeurPaquets() {
  const contrat = JSON.parse(fs.readFileSync(path.join(__dirname, 'contrat.json'), 'utf8'));
  const pad = (v, n) => String(Math.max(0, Math.round(Number(v) || 0))).padStart(n, '0').slice(-n);
  return {
    contrat,
    // champs : objet {x, y, dir, pv, ...} (x, y en cases ; les champs absents valent 0 ; nom : chaîne de 16 chiffres)
    paquet(champs) {
      let s = '1';
      for (const [nom, longueur] of contrat.champs) {
        let v = champs[nom];
        if (nom === 'x' || nom === 'y') v = (v || 0) * 100;
        if (nom === 'nom') { s += String(v || '').padEnd(longueur, '0').slice(0, longueur); continue; }
        s += pad(v, longueur);
      }
      return s;
    },
    codeNom(texte) {
      const alpha = contrat.alphabet;
      let s = '';
      for (let i = 0; i < 8; i++) { const c = (texte[i] || '').toLowerCase(); const k = alpha.indexOf(c); s += pad(k >= 0 ? k + 1 : 0, 2); }
      return s;
    },
  };
}

module.exports = { charger, chargeurPaquets };
