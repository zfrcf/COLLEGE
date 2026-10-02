// Scénario 2 : joueur non-admin, réponses vides / QWERTY, et décodage d'un adversaire (chat + couleur)
const fs = require('fs');
const VirtualMachine = require('scratch-vm');
const SS = require('scratch-storage');
const log = [], fails = [];
const expect = (c, m) => (c ? log : fails).push((c ? 'OK   ' : 'FAIL ') + m);

(async () => {
  const vm = new VirtualMachine();
  vm.attachStorage(new SS.ScratchStorage());
  console.warn = () => {};
  await vm.loadProject(fs.readFileSync(process.argv[2]));
  vm.runtime.currentStepTime = 1000 / 30;
  const stage = vm.runtime.getTargetForStage();
  const gv = n => stage.lookupVariableByNameAndType(n, '').value;
  const sv = (n, v) => { stage.lookupVariableByNameAndType(n, '').value = v; };
  const questions = [];
  vm.runtime.on('QUESTION', q => { if (q !== null) questions.push(q); });
  const says = [];
  vm.runtime.on('SAY', (t, type, text) => { if (text) says.push(t.getName() + '#' + (t.isOriginal ? 'orig' : 'clone') + ': ' + text); });
  const step = async n => { for (let i = 0; i < n; i++) { vm.runtime._step(); await new Promise(r => setImmediate(r)); } };
  const key = (k, d) => vm.postIOData('keyboard', { key: k, isDown: d });
  const tap = async k => { key(k, true); await step(6); key(k, false); await step(6); };

  vm.greenFlag(); await step(5);
  for (const a of ['', '2', '', '']) {           // pseudo vide, QWERTY, couleur vide, pas de code
    let n = 0; while (!questions.length && n++ < 300) await step(1);
    questions.shift(); vm.runtime.emit('ANSWER', a); await step(3);
  }
  await step(10);
  expect(gv('*setup done') == 1, 'setup terminé');
  expect(/^joueur\d{1,3}$/.test(gv('___username')), 'pseudo par défaut généré : ' + gv('___username'));
  expect(gv('Clavier') === 'QWERTY', 'QWERTY choisi');
  expect(String(gv('Couleur')) === '0', 'couleur normale (0)');
  expect(String(gv('___owner')) === '0', 'pas admin');
  expect(String(gv('*chat')) === '7', 'message de bienvenue');
  await step(30);
  await tap('i'); expect(String(gv('God Mode')) === '0', 'I sans effet pour un non-admin');
  await tap('f'); expect(String(gv('Fly Mode')) === '0', 'F sans effet pour un non-admin');
  await tap('u'); expect(String(gv('Checkpoint')) === '1', 'U sans effet pour un non-admin');
  await tap('c'); expect(String(gv('Aide visible')) === '1', 'C (aide) fonctionne pour tous');
  key('q', true); await step(4); expect(!(gv('-left') === true), 'Q inactif en QWERTY'); key('q', false);
  key('a', true); await step(4); expect(gv('-left') === true, 'A actif en QWERTY'); key('a', false);

  // ---- simuler un adversaire (joueur 2) : "bob★", chat 2 (GG !), couleur 120, à l'écran
  await new Promise(r => setTimeout(r, 3500)); await step(40);
  expect(Number(gv('MY PLAYER #')) === 1, 'je suis le joueur 1');
  const CODE = stage.lookupVariableByNameAndType('CODE', 'list').value;
  const enc = vals => vals.map(v => String(v).split('').map(ch => {
    const i = CODE.findIndex(c => c.toLowerCase() === ch.toLowerCase()) + 1;
    if (i < 10) throw new Error('caractère non encodable ' + ch);
    return String(i);
  }).join('') + '00').join('');
  const mk = (timer, chat) => enc([2, 'bob★', timer, Math.round(gv('SCROLL X')) + 10, Math.round(gv('SCROLL Y')) + 10, 90, 99999, chat, 120]);
  sv('☁ P2', mk(1000, 2)); await step(3);
  sv('☁ P2', mk(1001, 2)); await step(3);
  sv('☁ P2', mk(1002, 2)); await step(3);
  const opp = vm.runtime.targets.filter(t => t.getName() === 'Opponents' && !t.isOriginal);
  const bob = opp.find(t => t.lookupVariableByNameAndType('oname', '') && t.lookupVariableByNameAndType('oname', '').value === 'bob★');
  expect(!!bob, 'clone adversaire décodé avec pseudo bob★');
  if (bob) {
    expect(says.some(s => s.includes('bob★ : GG !')), 'bulle "bob★ : GG !" affichée (' + says.filter(s => s.includes('bob')).slice(-1) + ')');
    expect(Math.round(bob.effects.color) === 120, 'couleur 120 appliquée (' + bob.effects.color + ')');
    expect(bob.visible, 'adversaire visible');
  }
  // sans chat : bulle = pseudo seul
  sv('☁ P2', mk(1003, 0)); await step(3); sv('☁ P2', mk(1004, 0)); await step(3);
  expect(says.slice(-3).some(s => /Opponents#clone: bob★$/.test(s)), 'sans chat, la bulle redevient le pseudo (' + says.slice(-1) + ')');

  console.log(log.join('\n')); if (fails.length) console.log(fails.join('\n'));
  console.log(fails.length ? `\n${fails.length} ECHEC(S)` : '\nTOUT EST OK');
  process.exit(fails.length ? 1 : 0);
})().catch(e => { console.error('CRASH', e); process.exit(2); });
