// capture unique après 2,5 s ; NOM = nom du fichier (défaut verif)
module.exports = async (A) => {
  await A.attendre(2500);
  const n = await A.evaluer(vm => vm.runtime.targets.filter(t => !t.isOriginal).length);
  console.log('clones :', n);
  await A.capture(process.env.NOM || 'verif');
};
