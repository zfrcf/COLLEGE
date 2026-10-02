// Scénario de base : le projet démarre, le joueur rejoint un emplacement et le jeu tourne.
module.exports = async (T, verifier) => {
  T.souris(0, 0, false);
  T.drapeau(); T.pas(10);
  verifier('aucun opcode inconnu', T.opcodesInconnus().length === 0, T.opcodesInconnus());
  verifier('un emplacement réseau est pris', Number(T.g('monSlot')) >= 1, T.g('monSlot'));
  verifier('☁ J1 contient un paquet', String(T.g('☁ J1')).length >= 50, String(T.g('☁ J1')).length);
};
