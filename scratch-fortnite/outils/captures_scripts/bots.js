// Captures du sprite Bots : vue 3D en combat avec deux bots en vue (ils me poursuivent et me tirent dessus),
// puis l'île d'attente où les bots viennent d'arriver.
module.exports = async (A) => {
  await A.attendre(1200);
  const pad = (v, n) => String(v).padStart(n, '0').slice(-n);
  const now = async () => A.evaluer((vm, V) => Math.floor(Number(V('maintenant').value)));
  const partie = async (t, mode = 5, ltm = 0, graine = 42) => '1' + pad(((await now()) - t + 100000) % 100000, 5) + mode + ltm + pad(graine, 2);
  const g = (nom) => A.evaluer((vm, V, L, arg) => V(arg).value, nom);
  const attendre = async (cond, ms) => { const t0 = Date.now(); while (!(await cond()) && Date.now() - t0 < ms) await A.attendre(100); };

  // 1) île d'attente : les bots rejoignent un par un pendant l'attente (≈ 5 s)
  await A.evaluer((vm, V) => { V('enPartie').value = 1; });
  await attendre(async () => Number(await g('nbBots')) >= 5, 12000);
  console.log('bots arrivés :', await g('nbBots'), 'BotsActifs', await A.evaluer((vm, V, L) => L('BotsActifs').join('')));
  await A.evaluer((vm, V) => { V('px').value = 16.5; V('py').value = 4.5; V('dir').value = 90; V('message').value = ''; });
  await A.attendre(400);
  await A.capture('bots_ile');

  // 2) combat : ☁ Partie avancée (t = 50, zone = cercle initial), atterrissage, deux bots placés devant moi
  await A.evaluer((vm, V, L, arg) => { V('☁ Partie').value = arg; }, await partie(50));
  await A.attendre(600);
  await A.evaluer((vm, V) => { V('altitude').value = 1; });
  await attendre(async () => Number(await g('etat')) === 1, 3000);
  await A.evaluer((vm, V) => {
    V('px').value = 16.5; V('py').value = 4.5; V('dir').value = 90; V('message').value = ''; V('surbouclier').value = 0;
    const B = vm.runtime.getSpriteTargetByName('Bots');
    const l = (n) => B.lookupVariableByNameAndType(n, 'list').value;
    // bot 2 à 3 cases devant à gauche, bot 3 à 3,2 cases devant à droite (cases libres, en ligne de vue)
    l('bx')[1] = 15.7; l('by')[1] = 7.4; l('bcx')[1] = 15.7; l('bcy')[1] = 7.4; l('bPatience')[1] = 1e9; l('bProchainTir')[1] = 0;
    l('bx')[2] = 17.6; l('by')[2] = 7.8; l('bcx')[2] = 17.6; l('bcy')[2] = 7.8; l('bPatience')[2] = 1e9; l('bProchainTir')[2] = 0;
  });
  await A.attendre(700);
  console.log('E_x', await A.evaluer((vm, V, L) => L('E_x').join(',')), 'E_y', await A.evaluer((vm, V, L) => L('E_y').join(',')),
              'E_etat', await A.evaluer((vm, V, L) => L('E_etat').join(',')), 'PV', await g('❤ PV'), 'vivants', await g('vivants'));
  await A.capture('bots_jeu');
};
