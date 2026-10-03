// Scénario : moteur de rendu 3D (sensations) — cycle jour/nuit, secousse, éclairs, texture selon la qualité,
// disparition d'un adversaire mort. Les globales privées m3d_* sont écrites par Moteur3D à chaque image rendue.
const { chargeurPaquets } = require('../vm_lib');
module.exports = async (T, verifier) => {
  const Pq = chargeurPaquets();
  const now = () => Math.floor(Number(T.g('maintenant')));
  const paquet = (o) => Pq.paquet(Object.assign({ x: 15.5, y: 7.2, dir: 270, pv: 75, battement: now(), etat: 1, nom: Pq.codeNom('riko'), equipe: 2, niveau: 7 }, o));
  const chrono = () => T.vm.runtime.ioDevices.clock.projectTimer();
  T.pseudo('antoine'); T.souris(0, 0, false); T.drapeau(); T.pas(8);
  T.set('ecran', 'jeu'); T.set('etat', 1); T.set('px', 16.5); T.set('py', 4.5); T.set('dir', 90);
  T.set('zoneX', 16.5); T.set('zoneY', 10.5); T.set('zoneR', 9); T.set('phase', 3); T.set('param_performance', 0); T.set('param_qualite', 2);
  T.set('☁ J2', paquet({})); T.pas(4);
  // tempsManche est recalculé par Partie à partir de ☁ Partie : on fixe un début « il y a T secondes »
  const heure = (secondes) => { T.set('☁ Partie', '1' + String((now() - secondes + 100000) % 100000).padStart(5, '0') + '2' + '0' + '07'); T.pas(4); };
  heure(100); T.pas(2);
  verifier('tempsManche imposé (~100 s)', Math.abs(Number(T.g('tempsManche')) - 100) <= 2, T.g('tempsManche'));
  const lumJour = Number(T.g('m3d_lumiere'));
  verifier('plein jour : lumière 1', Math.abs(lumJour - 1) < 0.02 && Math.abs(Number(T.g('m3d_heure')) - 0.333) < 0.02, [lumJour, T.g('m3d_heure')]);
  heure(232); T.pas(2);
  const lumCrep = Number(T.g('m3d_lumiere'));
  verifier('crépuscule : lumière réduite (0,72..0,9)', lumCrep < 0.9 && lumCrep > 0.7, lumCrep);
  T.set('m3d_prochainEclair', 1e9); T.set('phase', 6); T.pas(3);    // pas d'éclair (flash blanc) pendant la mesure
  verifier('dernière zone : nuit (heure 1, lumière 0,4)', Number(T.g('m3d_heure')) === 1 && Math.abs(Number(T.g('m3d_lumiere')) - 0.4) < 0.01 && Number(T.g('m3d_nuit')) > 0.99, [T.g('m3d_heure'), T.g('m3d_lumiere'), T.g('m3d_nuit')]);
  T.set('phase', 3); heure(100); T.pas(2);
  // hors zone (Joueur recalcule horsZone d'après la zone ; « nouvelle manche » a remis zoneR à 30) : lumière × 0,7
  T.set('zoneX', 40); T.set('zoneR', 9); T.pas(3);
  verifier('hors zone : lumière × 0,7', Number(T.g('horsZone')) === 1 && Math.abs(Number(T.g('m3d_lumiere')) - 0.7) < 0.02, [T.g('horsZone'), T.g('m3d_lumiere')]);
  T.set('zoneX', 16.5); T.set('zoneR', 9); T.pas(2);
  // secousse : décalage aléatoire non nul borné par secousseForce, puis retour à 0
  T.set('secousse', chrono() + 100); T.set('secousseForce', 8);
  let maxSec = 0, nonNul = 0;
  for (let i = 0; i < 6; i++) { T.pas(1); const sx = Math.abs(Number(T.g('m3d_secX'))); maxSec = Math.max(maxSec, sx); if (sx > 0) nonNul++; }
  verifier('secousse : décalage non nul et ≤ secousseForce', nonNul >= 3 && maxSec <= 8, [nonNul, maxSec]);
  T.set('secousse', 0); T.pas(2);
  verifier('fin de secousse : décalage nul', Number(T.g('m3d_secX')) === 0 && Number(T.g('m3d_secY')) === 0, [T.g('m3d_secX'), T.g('m3d_secY')]);
  // éclairs : programmés seulement à partir de la phase 4
  T.set('m3d_prochainEclair', 0); T.set('m3d_eclairFin', 0); T.set('phase', 3); T.pas(2);
  verifier('phase 3 : pas d’éclair', Number(T.g('m3d_eclairFin')) === 0, T.g('m3d_eclairFin'));
  T.set('phase', 4); T.pas(2);
  const prochain = Number(T.g('m3d_prochainEclair')) - chrono();
  verifier('phase 4 : éclair déclenché, prochain dans 4 à 9 s', Number(T.g('m3d_eclairFin')) > chrono() - 0.5 && prochain > 3 && prochain < 9.5, [T.g('m3d_eclairFin'), prochain]);
  T.set('param_performance', 1); T.set('m3d_prochainEclair', 0); T.set('m3d_eclairFin', 0); T.pas(2);
  verifier('mode performance : pas d’éclair', Number(T.g('m3d_eclairFin')) === 0, T.g('m3d_eclairFin'));
  T.set('param_performance', 0); T.set('phase', 3);
  // texture : activée de près en qualité 2, jamais en qualité 1
  T.set('px', 17.5); T.set('py', 11.6); T.set('dir', 90); T.set('param_qualite', 2); T.pas(2);
  verifier('qualité 2, mur proche : texture active', Number(T.l('Moteur3D', 'tex')) === 1, T.l('Moteur3D', 'tex'));
  T.set('param_qualite', 1); T.pas(2);
  verifier('qualité 1 : une seule ligne par colonne (tex = 0)', Number(T.l('Moteur3D', 'tex')) === 0 && Number(T.g('colonnes')) === 40, [T.l('Moteur3D', 'tex'), T.g('colonnes')]);
  T.set('param_qualite', 2);
  // disparition : l'adversaire 2 visible meurt → mortAnim programmé 0,6 s
  T.set('px', 16.5); T.set('py', 4.5); T.set('dir', 90); T.set('☁ J2', paquet({})); T.pas(4);
  const clone = () => T.vm.runtime.targets.find(t => t.getName() === 'Ennemi' && !t.isOriginal && Object.values(t.variables).find(v => v.name === 'monIndex').value == 2);
  const lv = (n) => Number(Object.values(clone().variables).find(v => v.name === n).value);
  verifier('adversaire 2 affiché (vu = 1)', clone() && clone().visible && lv('vu') === 1, clone() && [clone().visible, lv('vu')]);
  T.set('☁ J2', paquet({ pv: 0, etat: 2, tueur: 1, morts: 1 }));
  for (let i = 0; i < 10 && lv('mortAnim') === 0; i++) T.pas(1);
  verifier('mort : disparition programmée (0,6 s), clone encore visible', lv('mortAnim') > chrono() && lv('mortAnim') < chrono() + 0.7 && clone().visible, [lv('mortAnim'), chrono(), clone().visible]);
  for (let i = 0; i < 40 && clone().visible; i++) T.pas(1);
  verifier('fin de disparition : clone caché, effets remis à 0', !clone().visible && lv('mortAnim') === 0 && clone().effects.ghost === 0, [clone().visible, lv('mortAnim'), clone().effects.ghost]);
};
