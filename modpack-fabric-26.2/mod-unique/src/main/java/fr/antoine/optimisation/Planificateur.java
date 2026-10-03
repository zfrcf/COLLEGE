package fr.antoine.optimisation;

import net.fabricmc.loader.api.FabricLoader;
import net.fabricmc.loader.api.ModContainer;
import net.fabricmc.loader.api.Version;
import net.fabricmc.loader.api.VersionParsingException;
import net.fabricmc.loader.api.metadata.version.VersionPredicate;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

/**
 * Calcule le jeu de mods cohérent à partir des choix de l'utilisateur :
 * - un mod activé entraîne ses bibliothèques ;
 * - un mod explicitement désactivé entraîne les mods qui en dépendent ;
 * - les contraintes de version (>=, <, ~ ...) sont évaluées par Fabric Loader lui-même.
 */
public final class Planificateur {

    public static final class Plan {
        /** Jeu final de mods actifs. */
        public final LinkedHashSet<String> finaux = new LinkedHashSet<>();
        /** Ajoutés automatiquement (bibliothèques requises). */
        public final List<String> ajoutes = new ArrayList<>();
        /** Retirés automatiquement (dépendaient d'un mod désactivé). */
        public final List<String> retires = new ArrayList<>();
        public final List<String> avertissements = new ArrayList<>();
        /** Non vide = plan impossible (un mod verrouillé devrait être désactivé). */
        public final List<String> refus = new ArrayList<>();

        public boolean valide() {
            return refus.isEmpty();
        }
    }

    private final Manifeste manifeste;

    public Planificateur(Manifeste manifeste) {
        this.manifeste = manifeste;
    }

    public static boolean satisfait(String version, String contrainte) {
        if (contrainte == null || contrainte.isBlank() || contrainte.equals("*")) return true;
        try {
            Version v = Version.parse(version);
            for (String alternative : contrainte.split("\\|\\|")) {
                if (alternative.isBlank() || VersionPredicate.parse(alternative.strip()).test(v)) return true;
            }
            return false;
        } catch (VersionParsingException | IllegalArgumentException e) {
            return true; // syntaxe inconnue : on ne bloque pas
        }
    }

    /** `m` fournit-il `id` dans une version compatible avec `contrainte` ? */
    public static boolean fournit(Manifeste.ModEmbarque m, String id, String contrainte) {
        String v = m.fournit.get(id);
        return v != null && satisfait(v, contrainte);
    }

    /** Un mod chargé par Fabric mais extérieur au pack (déposé dans mods/) fournit-il cet id ? */
    private boolean fourniParExterieur(String id, String contrainte) {
        if (manifeste.parId(id) != null) return false;
        Optional<ModContainer> c = FabricLoader.getInstance().getModContainer(id);
        if (c.isEmpty()) return false;
        // ne pas compter un module imbriqué d'un mod du pack
        for (Manifeste.ModEmbarque m : manifeste.mods) {
            if (m.fournit.containsKey(id)) return false;
        }
        return satisfait(c.get().getMetadata().getVersion().getFriendlyString(), contrainte);
    }

    public List<Manifeste.ModEmbarque> dependants(String id, Set<String> parmi) {
        List<Manifeste.ModEmbarque> res = new ArrayList<>();
        Manifeste.ModEmbarque cible = manifeste.parId(id);
        if (cible == null) return res;
        for (Manifeste.ModEmbarque m : manifeste.mods) {
            if (m.id.equals(id) || !parmi.contains(m.id)) continue;
            for (Map.Entry<String, String> d : m.depends.entrySet()) {
                if (cible.fournit.containsKey(d.getKey())) {
                    res.add(m);
                    break;
                }
            }
        }
        return res;
    }

    /**
     * @param actuels   mods actuellement actifs (chargés ou souhaités auparavant)
     * @param souhaites mods cochés par l'utilisateur
     */
    public Plan calculer(Set<String> actuels, Set<String> souhaites) {
        Plan plan = new Plan();
        LinkedHashSet<String> voulus = new LinkedHashSet<>();
        for (Manifeste.ModEmbarque m : manifeste.mods) {
            if (souhaites.contains(m.id) || m.verrouille) voulus.add(m.id);
        }
        // mods que l'utilisateur vient de décocher : on ne les rajoute jamais automatiquement
        Set<String> interdits = new LinkedHashSet<>();
        for (String id : actuels) {
            Manifeste.ModEmbarque m = manifeste.parId(id);
            if (m != null && !souhaites.contains(id) && !m.verrouille) interdits.add(id);
        }

        boolean change = true;
        int garde = 0;
        while (change && garde++ < 500) {
            change = false;
            for (String id : new ArrayList<>(voulus)) {
                Manifeste.ModEmbarque m = manifeste.parId(id);
                if (m == null) continue;
                for (Map.Entry<String, String> dep : m.depends.entrySet()) {
                    String besoin = dep.getKey();
                    String contrainte = dep.getValue();
                    boolean ok = false;
                    for (String autre : voulus) {
                        Manifeste.ModEmbarque f = manifeste.parId(autre);
                        if (f != null && fournit(f, besoin, contrainte)) {
                            ok = true;
                            break;
                        }
                    }
                    if (!ok) ok = fourniParExterieur(besoin, contrainte);
                    if (ok) continue;

                    List<Manifeste.ModEmbarque> candidats = new ArrayList<>();
                    for (Manifeste.ModEmbarque f : manifeste.mods) {
                        if (!interdits.contains(f.id) && !voulus.contains(f.id) && fournit(f, besoin, contrainte)) {
                            candidats.add(f);
                        }
                    }
                    if (!candidats.isEmpty()) {
                        candidats.sort(Comparator
                                .comparing((Manifeste.ModEmbarque f) -> !actuels.contains(f.id))
                                .thenComparing(f -> !f.bibliotheque)
                                .thenComparing(f -> !f.par_defaut));
                        Manifeste.ModEmbarque choix = candidats.get(0);
                        voulus.add(choix.id);
                        plan.ajoutes.add(choix.nom + " (requis par " + m.nom + ")");
                    } else {
                        if (m.verrouille) {
                            plan.refus.add(m.nom + " est indispensable au gestionnaire et a besoin de « "
                                    + besoin + " » : impossible de désactiver ce dernier.");
                            continue;
                        }
                        voulus.remove(id);
                        String fournisseur = besoin;
                        for (Manifeste.ModEmbarque f : manifeste.mods) {
                            if (f.fournit.containsKey(besoin)) {
                                fournisseur = f.nom;
                                break;
                            }
                        }
                        plan.retires.add(m.nom + " (a besoin de " + fournisseur + ")");
                    }
                    change = true;
                    break;
                }
                if (change) break;
            }
        }

        // incompatibilités déclarées (breaks) entre mods finaux
        for (String a : voulus) {
            Manifeste.ModEmbarque ma = manifeste.parId(a);
            if (ma == null) continue;
            for (Map.Entry<String, String> b : ma.breaks.entrySet()) {
                for (String autre : voulus) {
                    if (autre.equals(a)) continue;
                    Manifeste.ModEmbarque mb = manifeste.parId(autre);
                    if (mb != null && fournit(mb, b.getKey(), b.getValue())) {
                        plan.avertissements.add(ma.nom + " se déclare incompatible avec " + mb.nomComplet());
                    }
                }
            }
        }
        plan.finaux.addAll(voulus);
        return plan;
    }
}
