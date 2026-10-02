// Captures du sprite Partie : île d'attente (vue 3D), bus (carte + trajectoire), parachute (altitude 50),
// carte plein écran (écran « carte » en pleine tempête, avec coéquipier, joueur en l'air, ping).
module.exports = async (A) => {
  await A.attendre(1200);
  const contrat = require('../contrat.json');
  const pad = (v, n) => String(Math.max(0, Math.round(Number(v) || 0))).padStart(n, '0').slice(-n);
  const paquet = (o) => { let s = '1'; for (const [nom, l] of contrat.champs) { let v = o[nom] || 0; if (nom === 'x' || nom === 'y') v = v * 100; if (nom === 'nom') { s += String(v || '').padEnd(l, '0').slice(0, l); continue; } s += pad(v, l); } return s; };
  const now = async () => A.evaluer((vm, V) => Math.floor(Number(V('maintenant').value)));
  const partie = async (t, mode = 5, ltm = 0, graine = 42) => '1' + pad(((await now()) - t + 100000) % 100000, 5) + mode + ltm + pad(graine, 2);

  // 1) île d'attente : vue 3D (ciel doré = invulnérable), zone initiale
  await A.evaluer((vm, V, L, arg) => { V('enPartie').value = 1; V('☁ Partie').value = arg; }, await partie(3));
  await A.attendre(900);
  await A.evaluer((vm, V) => { V('px').value = 16.5; V('py').value = 4.5; V('dir').value = 90; });
  await A.attendre(400);
  await A.capture('partie_prepartie');

  // 2) bus : t = 32 (progression ≈ 35 %), carte avec trajectoire pointillée et icône du bus
  await A.evaluer((vm, V, L, arg) => { V('☁ Partie').value = arg; }, await partie(32));
  await A.attendre(900);
  await A.capture('partie_bus');

  // 3) parachute à l'altitude 50 (planeur fermé), un coéquipier en l'air et un autre au sol
  const n0 = await now();
  const p2 = paquet({ x: 12.5, y: 20.5, dir: 90, pv: 100, battement: n0, etat: 7, nom: '1809111500000000', niveau: 12, skin: 3, equipe: 1, altitude: 40 });
  const p3 = paquet({ x: 24.5, y: 9.5, dir: 270, pv: 80, battement: n0, etat: 1, nom: '2605040000000000', niveau: 4, skin: 5, equipe: 1 });
  await A.evaluer((vm, V, L, arg) => {
    V('☁ Partie').value = arg[0]; V('mode').value = 2; V('remplissage').value = 1;
    V('☁ J2').value = arg[1]; V('☁ J3').value = arg[2];
  }, [await partie(60, 2, 0, 42), p2, p3]);
  await A.attendre(700);
  await A.evaluer((vm, V) => { V('etat').value = 7; V('ecran').value = 'parachute'; V('altitude').value = 50; V('px').value = 14.5; V('py').value = 18.5; V('dir').value = 45; V('message').value = ''; });
  await A.attendre(500);
  await A.capture('partie_parachute');

  // 4) carte plein écran pendant le rétrécissement de la zone 2 (t = 140), ping d'un coéquipier, coffre ouvert
  await A.evaluer((vm, V, L, arg) => { V('☁ Partie').value = arg; }, await partie(140, 2, 0, 42));
  await A.attendre(700);
  await A.evaluer((vm, V) => {
    V('etat').value = 1; V('altitude').value = 0; V('invulnerable').value = 0; V('ecran').value = 'carte';
    V('px').value = 18.5; V('py').value = 14.5; V('dir').value = 120;
    const t = vm.runtime.ioDevices.clock.projectTimer();
    V('Pings').value = ['3' + '2200' + '1200' + String(Math.round((t + 60) * 10)).padStart(6, '0')];
    V('CoffresPris').value = ['5', '7'];
  });
  await A.attendre(600);
  await A.capture('partie_carte');

  // 5) carte en anglais, dernière zone en mouvement (t = 225)
  await A.evaluer((vm, V, L, arg) => { V('☁ Partie').value = arg; V('param_langue').value = 1; }, await partie(225, 2, 0, 42));
  await A.attendre(700);
  await A.evaluer((vm, V) => { V('etat').value = 1; V('altitude').value = 0; V('ecran').value = 'carte'; V('px').value = 18.5; V('py').value = 14.5; });
  await A.attendre(500);
  await A.capture('partie_carte_en');
};
