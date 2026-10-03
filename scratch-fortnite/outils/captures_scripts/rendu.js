// Captures du rendu 3D « spectaculaire » (moteur3d.py / overlays.py) : murs texturés, cycle jour/nuit, soleil,
// nuages, tempête et éclairs, secousse, traceur, ennemi touché / mort, arme (recul, rechargement, pompe), qualités.
// Affiche aussi le temps moyen d'une image (ms, vm.runtime._step) pour plusieurs scènes, mesuré dans Chromium.
//   node capture.js captures_scripts/rendu.js
module.exports = async (A) => {
  const contrat = require('../contrat.json');
  const pad = (v, n) => String(Math.max(0, Math.round(Number(v) || 0))).padStart(n, '0').slice(-n);
  const paquet = (o) => { let s = '1'; for (const [nom, l] of contrat.champs) { let v = o[nom] || 0; if (nom === 'x' || nom === 'y') v = v * 100; if (nom === 'nom') { s += String(v || '').padEnd(l, '0').slice(0, l); continue; } s += pad(v, l); } return s; };
  const regler = (valeurs) => A.evaluer((vm, V, L, arg) => { for (const [k, v] of Object.entries(arg)) V(k).value = v; }, valeurs);
  const chrono = () => A.evaluer((vm) => vm.runtime.ioDevices.clock.projectTimer());
  const maintenant = () => A.evaluer((vm, V) => Math.floor(Number(V('maintenant').value)));
  // heure de la manche : ☁ Partie est réécrit avec un début « il y a T secondes » (Partie recalcule tempsManche à
  // chaque image ; un nouveau début déclenche « nouvelle manche », d'où l'attente avant de régler la scène)
  const heure = async (T) => { const now = await maintenant(); await regler({ '☁ Partie': '1' + pad((now - T + 100000) % 100000, 5) + '2' + '0' + '07' }); await A.attendre(250); };
  // adversaire (emplacement 2) et coéquipier à terre (emplacement 3) : battement rafraîchi (périmé après 15 s)
  const pousser = async (o2 = {}, o3 = {}) => {
    const now = await maintenant();
    const p2 = paquet(Object.assign({ x: 15.5, y: 7.2, dir: 270, pv: 75, bouclier: 20, battement: now, etat: 1, nom: '1809111500000000', niveau: 12, skin: 3, equipe: 2 }, o2));
    const p3 = paquet(Object.assign({ x: 18.2, y: 6.5, dir: 270, pv: 100, battement: now, etat: 3, nom: '2605040000000000', niveau: 4, skin: 5, equipe: 1, knockPar: 2 }, o3));
    await A.evaluer((vm, V, L, arg) => { V('☁ J2').value = arg[0]; V('☁ J3').value = arg[1]; }, [p2, p3]);
  };
  const scene = async (nom, { T, j2, j3, attente = 700, ...valeurs }) => {
    if (T !== undefined) await heure(T);
    await pousser(j2 || {}, j3 || {});
    await regler(valeurs); await A.attendre(attente); await A.capture(nom);
  };
  // mesure du temps d'une image (tous les scripts, stylo compris, hors GPU)
  await A.evaluer((vm) => {
    const o = vm.runtime._step.bind(vm.runtime); window._perf = [];
    vm.runtime._step = () => { const t0 = performance.now(); o(); window._perf.push(performance.now() - t0); };
  });
  const mesurer = async (libelle, ms = 1500) => {
    await A.evaluer(() => { window._perf.length = 0; }); await A.attendre(ms);
    const r = await A.evaluer(() => { const a = window._perf.slice(3); a.sort((x, y) => x - y); return { moy: a.reduce((s, x) => s + x, 0) / a.length, med: a[Math.floor(a.length / 2)], p90: a[Math.floor(a.length * 0.9)], n: a.length }; });
    console.log('image %s : moyenne %s ms, médiane %s ms, p90 %s ms (%d images)', libelle.padEnd(28), r.moy.toFixed(1), r.med.toFixed(1), r.p90.toFixed(1), r.n);
    return r;
  };

  await A.attendre(800);
  const base = { ecran: 'jeu', etat: 1, connecte: 1, px: 16.5, py: 4.5, dir: 90, zoneX: 16.5, zoneY: 10.5, zoneR: 9, phase: 3,
    monEquipe: 1, mode: 2, param_qualite: 2, param_performance: 0, horsZone: 0, plan: 0.66, m3d_prochainEclair: 1e9 };
  await regler({ ecran: 'jeu', etat: 1, connecte: 1 });
  await A.evaluer((vm, V) => { V('Pings').value = ['3' + '1650' + '0900' + '999999']; });
  await A.attendre(400);

  // 1. jour : béton (vue de base), soleil en haut à droite, nuages
  await scene('rendu_01_jour_beton', { T: 100, ...base, attente: 900 });
  await mesurer('jour qualité 2 (béton)');
  // 2. bois : cabane (19..22, 20..23), vue en biais, dans la zone
  await scene('rendu_02_jour_bois', { T: 120, px: 20.5, py: 17.5, dir: 60, zoneX: 16.5, zoneY: 16.5, zoneR: 14 });
  // 3. brique : place brique (15..19, 14..17)
  await scene('rendu_03_jour_brique', { T: 140, px: 17.5, py: 11.6, dir: 112, zoneX: 16.5, zoneY: 16.5, zoneR: 14 });
  // 4. crépuscule : hangar métal (15..19, 26..29) avec sa porte, soleil bas orangé à gauche
  await scene('rendu_04_crepuscule_metal', { T: 232, px: 17.5, py: 23.4, dir: 104, phase: 4, zoneX: 16.5, zoneY: 20.5, zoneR: 9, m3d_prochainEclair: 1e9 });
  await mesurer('crépuscule qualité 2 (métal)');
  // 5. aube : île d'attente (prépartie)
  await scene('rendu_05_aube', { T: 8, px: 10.5, py: 18.5, dir: 40, phase: 0, invulnerable: 1, zoneX: 16.5, zoneY: 16.5, zoneR: 30 });
  // 6. nuit : dernière zone (phase 6), mur de tempête tout proche, lune, adversaire derrière le mur
  await scene('rendu_06_nuit_derniere_zone', { T: 285, j2: { x: 14.9, y: 23.3, dir: 330 }, px: 17.5, py: 21.8, dir: 150, phase: 6,
    zoneX: 17.5, zoneY: 21.0, zoneR: 1.5, invulnerable: 0 });
  await mesurer('nuit + mur de tempête');
  // 6b. nuit sans le mur devant : hangar éclairé par la lune
  await scene('rendu_06b_nuit_hangar', { px: 17.5, py: 22.6, dir: 125, zoneX: 17.5, zoneY: 23.0, zoneR: 8 });
  // 7. tempête : éclair forcé (phase 5), zone devant
  const t0 = await chrono();
  await scene('rendu_07_tempete_eclair', { T: 200, px: 16.5, py: 4.5, dir: 90, phase: 5, zoneX: 16.5, zoneY: 10.5, zoneR: 4.2,
    m3d_eclairFin: t0 + 60, m3d_eclairX: -70, m3d_prochainEclair: 1e9, attente: 500 });
  // 8. flash blanc du ciel (1 image normalement ; forcé ici)
  const t1 = await chrono();
  await scene('rendu_08_flash_ciel', { m3d_eclairFin: 0, m3d_flashFin: t1 + 60, attente: 400 });
  await regler({ m3d_flashFin: 0 });
  // 9. hors zone : teinte violette + vignette
  await scene('rendu_09_hors_zone', { zoneX: 40, zoneR: 9, phase: 4, horsZone: 1 });
  await mesurer('hors zone (vignette)');
  // 10. secousse d'écran (amplitude forcée 10 px)
  const t2 = await chrono();
  await scene('rendu_10_secousse', { zoneX: 16.5, zoneR: 9, horsZone: 0, secousse: t2 + 60, secousseForce: 10, attente: 500 });
  await mesurer('secousse');
  await regler({ secousse: 0 });
  // 11. traceur + étincelles + ennemi touché (cible 2) + viseur de touche
  const t3 = await chrono();
  await scene('rendu_11_traceur_touche', { traceFin: t3 + 60, traceX: -52, traceY: 2, toucheFin: t3 + 60, cible: 2, attente: 400 });
  await regler({ traceFin: 0, toucheFin: 0 });
  // 12. mort de l'adversaire 2 : disparition (0,6 s) — on attend que le clone démarre son animation (mortAnim > 0)
  await A.attendre(300);
  await pousser({ pv: 0, etat: 2, tueur: 1, morts: 1 });
  const cloneAnime = () => A.evaluer((vm) => { const c = vm.runtime.targets.find(t => t.getName() === 'Ennemi' && !t.isOriginal && Object.values(t.variables).find(v => v.name === 'monIndex').value == 2); return c ? Number(Object.values(c.variables).find(v => v.name === 'mortAnim').value) : -1; });
  for (let i = 0; i < 40 && (await cloneAnime()) <= 0; i++) await A.attendre(25);
  await A.attendre(60);
  await A.capture('rendu_12_mort_disparition');
  await A.attendre(700);
  await pousser();
  // 13. rechargement (arme descendue, inclinée)
  const t4 = await chrono();
  await scene('rendu_13_rechargement', { rechargeDebut: t4 - 0.75, rechargeFin: t4 + 60, attente: 300 });
  await regler({ rechargeFin: 0, rechargeDebut: 0 });
  // 14. fusil à pompe : recul + grand flash de bouche (tirAnim forcé)
  await A.evaluer((vm, V) => { const inv = V('Inventaire').value.slice(); inv[0] = 2; V('Inventaire').value = inv; V('slotActif').value = 1; V('armeNum').value = 2; V('tirAnim').value = 100; });
  await A.attendre(250);
  await A.capture('rendu_14_pompe_flash');
  await A.evaluer((vm, V) => { const inv = V('Inventaire').value.slice(); inv[0] = 1; V('Inventaire').value = inv; V('armeNum').value = 1; V('tirAnim').value = 0; });
  // 15. marche : balancement de l'arme (touche avancer maintenue)
  await A.touche('z', true); await A.attendre(450); await A.capture('rendu_15_marche_a'); await A.attendre(120); await A.capture('rendu_15_marche_b'); await A.touche('z', false);
  await regler({ px: 16.5, py: 4.5, dir: 90 });
  // 16. qualités 1 / 3 et mode performance
  await scene('rendu_16_qualite1', { param_qualite: 1 });
  await mesurer('qualité 1');
  await scene('rendu_17_qualite3', { param_qualite: 3, dir: 100 });
  await mesurer('qualité 3');
  await scene('rendu_18_performance', { param_qualite: 2, param_performance: 1, dir: 90 });
  await mesurer('mode performance');
  await regler({ param_performance: 0 });
  // 19. lunette de sniper au crépuscule
  await scene('rendu_19_lunette_crepuscule', { T: 240, plan: 0.22, dir: 96 });
  await regler({ plan: 0.66 });
};
