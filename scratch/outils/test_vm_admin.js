// Test headless du projet patché dans scratch-vm
const fs = require('fs');
const VirtualMachine = require('scratch-vm');
const SS = require('scratch-storage'); const ScratchStorage = SS.ScratchStorage || SS.default || SS;

const file = process.argv[2];
const answers = ['Antoine!!', '1', '50', 'ANTOINE33'];   // pseudo, clavier, couleur, code admin
const log = [];
const fails = [];
function expect(cond, msg) { (cond ? log : fails).push((cond ? 'OK   ' : 'FAIL ') + msg); }

(async () => {
  const vm = new VirtualMachine();
  const storage = new ScratchStorage();
  vm.attachStorage(storage);
  vm.setCompatibilityMode(false);
  vm.setTurboMode(false);
  const warnings = [];
  const origWarn = console.warn; console.warn = (...a) => warnings.push(a.join(' '));
  const origErr = console.error; console.error = (...a) => warnings.push('ERR ' + a.join(' '));

  await vm.loadProject(fs.readFileSync(file));
  expect(vm.runtime.targets.length === 18, 'projet chargé, 18 cibles (' + vm.runtime.targets.length + ')');

  const stage = vm.runtime.getTargetForStage();
  const gv = name => { const v = stage.lookupVariableByNameAndType(name, ''); return v ? v.value : undefined; };
  const player = vm.runtime.getSpriteTargetByName('Player');
  const pv = name => { const v = player.lookupVariableByNameAndType(name, ''); return v ? v.value : undefined; };

  const says = [];
  vm.runtime.on('SAY', (target, type, text) => { if (text) says.push(target.getName() + ': ' + text); });
  const questions = [];
  vm.runtime.on('QUESTION', q => { if (q !== null) questions.push(q); });

  const step = async n => { for (let i = 0; i < n; i++) { vm.runtime._step(); await new Promise(r => setImmediate(r)); } };
  const key = (k, down) => vm.postIOData('keyboard', { key: k, isDown: down });
  const tap = async (k, frames = 6) => { key(k, true); await step(frames); key(k, false); await step(frames); };

  vm.runtime.currentStepTime = 1000 / 30;
  vm.greenFlag();
  await step(5);
  // répondre aux 4 questions
  for (const a of answers) {
    let tries = 0;
    while (questions.length === 0 && tries++ < 300) await step(1);
    expect(questions.length > 0, 'question posée : ' + (questions[0] || '(aucune)'));
    questions.shift();
    vm.runtime.emit('ANSWER', a);
    await step(3);
    log.push('     après réponse "' + a + '" : Couleur=' + gv('Couleur') + ' user=' + gv('___username'));
  }
  await step(10);
  expect(gv('*setup done') == 1, '*setup done = 1');
  expect(gv('___username') === 'antoine★', '___username = "antoine★" (obtenu : ' + gv('___username') + ')');
  expect(gv('Clavier') === 'AZERTY', 'Clavier = AZERTY');
  expect(String(gv('Couleur')) === '50', 'Couleur = 50 (obtenu : ' + gv('Couleur') + ')');
  expect(String(gv('___owner')) === '1', '___owner = 1 (admin)');
  expect(String(gv('*chat')) === '10', 'message admin connecté (*chat = 10, obtenu ' + gv('*chat') + ')');

  // la boucle de jeu tourne : touches AZERTY
  await step(30);
  key('z', true); await step(4);
  expect(gv('-up') === true || gv('-up') == 1, 'Z = haut en AZERTY (-up = ' + gv('-up') + ')');
  key('z', false);
  key('q', true); await step(4);
  expect(gv('-left') === true || gv('-left') == 1, 'Q = gauche en AZERTY (-left = ' + gv('-left') + ')');
  key('q', false); await step(2);
  key('a', true); await step(4);
  expect(!(gv('-left') === true || gv('-left') == 1), 'A inactif en AZERTY');
  key('a', false); await step(2);

  await tap('p');
  expect(gv('Clavier') === 'QWERTY', 'P bascule vers QWERTY (' + gv('Clavier') + ')');
  key('a', true); await step(4);
  expect(gv('-left') === true || gv('-left') == 1, 'A = gauche en QWERTY');
  key('a', false);
  key('w', true); await step(4);
  expect(gv('-up') === true || gv('-up') == 1, 'W = haut en QWERTY');
  key('w', false); await step(2);

  // chat
  says.length = 0;
  await tap('4');
  await step(5);
  expect(String(gv('*chat')) === '1', 'touche 4 -> *chat = 1');
  expect(says.some(s => s.includes('Salut !')), 'le joueur dit "Salut !" (' + says.slice(-1) + ')');

  // pouvoirs admin
  await tap('i'); expect(String(gv('God Mode')) === '1', 'I -> God Mode = 1');
  await tap('j'); expect(String(gv('Vitesse')) === '1', 'J -> Vitesse = 1');
  await tap('h'); expect(String(gv('Super Saut')) === '1', 'H -> Super Saut = 1');
  await tap('b'); expect(String(gv('Disco Mode')) === '1', 'B -> Disco Mode = 1');
  await tap('f'); expect(String(gv('Fly Mode')) === '1', 'F -> Fly Mode = 1');
  await step(5);
  expect(String(gv('Triche')) === '1', 'Triche = 1 après usage des pouvoirs');
  await tap('c'); expect(String(gv('Aide visible')) === '1', 'C -> Aide visible');
  await tap('m'); expect(String(gv('Panneau')) === '0', 'M -> Panneau admin masqué (était affiché)');
  await tap('v'); expect(String(gv('Musique')) === '0', 'V -> Musique coupée');
  await tap('i'); await tap('j'); await tap('h'); await tap('b'); await tap('f');

  // téléportation checkpoint
  const cp0 = Number(gv('Checkpoint'));
  await tap('u', 8); await step(20);
  expect(Number(gv('Checkpoint')) === cp0 + 1, 'U -> checkpoint ' + cp0 + ' -> ' + gv('Checkpoint'));
  await tap('y', 8); await step(20);
  expect(Number(gv('Checkpoint')) === cp0, 'Y -> retour checkpoint ' + gv('Checkpoint'));
  expect(String(gv('_deaths')) === '0', 'téléportation ne compte pas comme une mort (' + gv('_deaths') + ')');

  // connexion cloud (join game attend 3 s réelles)
  await new Promise(r => setTimeout(r, 3500));
  await step(60);
  expect(Number(gv('MY PLAYER #')) > 0, 'MY PLAYER # = ' + gv('MY PLAYER #'));
  const p1 = String(gv('☁ P' + gv('MY PLAYER #')));
  expect(/^\d+$/.test(p1), 'variable cloud numérique (' + p1.length + ' chiffres)');
  // décodage
  const CODE = stage.lookupVariableByNameAndType('CODE', 'list').value;
  const vals = []; let cur = '';
  for (let i = 0; i < p1.length; i += 2) {
    const idx = parseInt(p1.substr(i, 2), 10);
    if (idx < 1) { vals.push(cur); cur = ''; } else cur += CODE[idx - 1];
  }
  log.push('     décodé : ' + JSON.stringify(vals));
  expect(vals[1] === 'antoine★', 'pseudo transmis avec badge ★');
  expect(vals[7] === String(gv('*chat')), 'chat transmis (' + vals[7] + ')');
  expect(vals[8] === '50', 'couleur transmise (' + vals[8] + ')');
  expect(p1.length <= 256, 'taille cloud <= 256');

  console.warn = origWarn; console.error = origErr;
  console.log(log.join('\n'));
  if (fails.length) { console.log(fails.join('\n')); }
  const w = warnings.filter(x => !/Unknown opcode|audio|Audio|font|Font|No renderer/i.test(x));
  if (w.length) console.log('WARNINGS:\n' + w.slice(0, 20).join('\n'));
  console.log(fails.length ? `\n${fails.length} ECHEC(S)` : '\nTOUT EST OK');
  process.exit(fails.length ? 1 : 0);
})().catch(e => { console.error('CRASH', e); process.exit(2); });
