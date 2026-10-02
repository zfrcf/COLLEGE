// Capture du rendu 3D de base (sans menus) : on force l'écran « jeu ».
module.exports = async (A) => {
  await A.attendre(800);
  await A.evaluer((vm, V) => { V('ecran').value = 'jeu'; V('etat').value = 1; V('connecte').value = 1; V('px').value = 16.5; V('py').value = 4.5; V('dir').value = 90; V('zoneX').value = 16.5; V('zoneY').value = 10.5; V('zoneR').value = 9; V('phase').value = 2; V('monEquipe').value = 1; V('mode').value = 2; });
  // deux adversaires et un coéquipier via paquets (format du contrat)
  const contrat = require('../contrat.json');
  const pad = (v, n) => String(Math.max(0, Math.round(Number(v) || 0))).padStart(n, '0').slice(-n);
  const paquet = (o, now) => { let s = '1'; for (const [nom, l] of contrat.champs) { let v = o[nom] || 0; if (nom === 'x' || nom === 'y') v = v * 100; if (nom === 'nom') { s += String(v || '').padEnd(l, '0').slice(0, l); continue; } s += pad(v, l); } return s; };
  const now = await A.evaluer((vm, V) => Math.floor(Number(V('maintenant').value)));
  const p2 = paquet({ x: 15.5, y: 7.2, dir: 270, pv: 75, bouclier: 20, battement: now, etat: 1, nom: '1809111500000000', niveau: 12, skin: 3, equipe: 2 }, now);
  const p3 = paquet({ x: 18.2, y: 6.5, dir: 270, pv: 100, battement: now, etat: 3, nom: '2605040000000000', niveau: 4, skin: 5, equipe: 1, knockPar: 2 }, now);
  await A.evaluer((vm, V, L, arg) => { V('☁ J2').value = arg[0]; V('☁ J3').value = arg[1]; V('Pings').value = ['3' + '1650' + '0900' + '999999']; }, [p2, p3]);
  await A.attendre(900);
  await A.capture('jeu_base');
  // zoom sniper + hors zone
  await A.evaluer((vm, V) => { V('plan').value = 0.22; V('zoneX').value = 40; V('zoneR').value = 15; });
  await A.attendre(500);
  await A.capture('jeu_lunette_tempete');
  await A.evaluer((vm, V) => { V('plan').value = 0.66; V('zoneX').value = 16.5; V('zoneR').value = 9; V('param_qualite').value = 3; V('dir').value = 150; });
  await A.attendre(600);
  await A.capture('jeu_epique');
};
