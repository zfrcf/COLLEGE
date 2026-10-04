package fr.antoine.optimisation;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.Iterator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.Map.Entry;
import net.fabricmc.loader.api.FabricLoader;
import net.fabricmc.loader.api.ModContainer;
import net.fabricmc.loader.api.Version;
import net.fabricmc.loader.api.VersionParsingException;
import net.fabricmc.loader.api.metadata.version.VersionPredicate;

public final class Planificateur {
   private final Manifeste manifeste;

   public Planificateur(Manifeste manifeste) {
      this.manifeste = manifeste;
   }

   public static boolean satisfait(String version, String contrainte) {
      if (contrainte != null && !contrainte.isBlank() && !contrainte.equals("*")) {
         try {
            Version v = Version.parse(version);

            for (String alternative : contrainte.split("\\|\\|")) {
               if (alternative.isBlank() || VersionPredicate.parse(alternative.strip()).test(v)) {
                  return true;
               }
            }

            return false;
         } catch (VersionParsingException | IllegalArgumentException e) {
            return true;
         }
      } else {
         return true;
      }
   }

   public static boolean fournit(Manifeste.ModEmbarque m, String id, String contrainte) {
      String v = m.fournit.get(id);
      return v != null && satisfait(v, contrainte);
   }

   private boolean fourniParExterieur(String id, String contrainte) {
      if (this.manifeste.parId(id) != null) {
         return false;
      }

      Optional<ModContainer> c = FabricLoader.getInstance().getModContainer(id);
      if (c.isEmpty()) {
         return false;
      }

      for (Manifeste.ModEmbarque m : this.manifeste.mods) {
         if (m.fournit.containsKey(id)) {
            return false;
         }
      }

      return satisfait(c.get().getMetadata().getVersion().getFriendlyString(), contrainte);
   }

   public List<Manifeste.ModEmbarque> dependants(String id, Set<String> parmi) {
      List<Manifeste.ModEmbarque> res = new ArrayList<>();
      Manifeste.ModEmbarque cible = this.manifeste.parId(id);
      if (cible == null) {
         return res;
      }

      for (Manifeste.ModEmbarque m : this.manifeste.mods) {
         if (!m.id.equals(id) && parmi.contains(m.id)) {
            for (Entry<String, String> d : m.depends.entrySet()) {
               if (cible.fournit.containsKey(d.getKey())) {
                  res.add(m);
                  break;
               }
            }
         }
      }

      return res;
   }

   public Planificateur.Plan calculer(Set<String> actuels, Set<String> souhaites) {
      Planificateur.Plan plan = new Planificateur.Plan();
      LinkedHashSet<String> voulus = new LinkedHashSet<>();

      for (Manifeste.ModEmbarque m : this.manifeste.mods) {
         if (souhaites.contains(m.id) || m.verrouille) {
            voulus.add(m.id);
         }
      }

      Set<String> interdits = new LinkedHashSet<>();

      for (String id : actuels) {
         Manifeste.ModEmbarque m = this.manifeste.parId(id);
         if (m != null && !souhaites.contains(id) && !m.verrouille) {
            interdits.add(id);
         }
      }

      boolean change = true;
      int garde = 0;

      while (change && garde++ < 500) {
         change = false;

         for (String id : new ArrayList<>(voulus)) {
            Manifeste.ModEmbarque m = this.manifeste.parId(id);
            if (m != null) {
               Iterator var11 = m.depends.entrySet().iterator();

               label150: {
                  while (true) {
                     if (!var11.hasNext()) {
                        break label150;
                     }

                     Entry<String, String> dep = (Entry<String, String>)var11.next();
                     String besoin = dep.getKey();
                     String contrainte = dep.getValue();
                     boolean ok = false;

                     for (String autre : voulus) {
                        Manifeste.ModEmbarque f = this.manifeste.parId(autre);
                        if (f != null && fournit(f, besoin, contrainte)) {
                           ok = true;
                           break;
                        }
                     }

                     if (!ok) {
                        ok = this.fourniParExterieur(besoin, contrainte);
                     }

                     if (!ok) {
                        List<Manifeste.ModEmbarque> candidats = new ArrayList<>();

                        for (Manifeste.ModEmbarque f : this.manifeste.mods) {
                           if (!interdits.contains(f.id) && !voulus.contains(f.id) && fournit(f, besoin, contrainte)) {
                              candidats.add(f);
                           }
                        }

                        if (!candidats.isEmpty()) {
                           candidats.sort(
                              Comparator.<Manifeste.ModEmbarque, Boolean>comparing(fx -> !actuels.contains(fx.id))
                                 .thenComparing(fx -> !fx.bibliotheque)
                                 .thenComparing(fx -> !fx.par_defaut)
                           );
                           Manifeste.ModEmbarque choix = candidats.get(0);
                           voulus.add(choix.id);
                           plan.ajoutes.add(choix.nom + " (requis par " + m.nom + ")");
                           break;
                        }

                        if (!m.verrouille) {
                           voulus.remove(id);
                           String fournisseur = besoin;

                           for (Manifeste.ModEmbarque f : this.manifeste.mods) {
                              if (f.fournit.containsKey(besoin)) {
                                 fournisseur = f.nom;
                                 break;
                              }
                           }

                           plan.retires.add(m.nom + " (a besoin de " + fournisseur + ")");
                           break;
                        }

                        plan.refus.add(m.nom + " est indispensable au gestionnaire et a besoin de « " + besoin + " » : impossible de désactiver ce dernier.");
                     }
                  }

                  change = true;
               }

               if (change) {
                  break;
               }
            }
         }
      }

      for (String a : voulus) {
         Manifeste.ModEmbarque ma = this.manifeste.parId(a);
         if (ma != null) {
            for (Entry<String, String> b : ma.breaks.entrySet()) {
               for (String autre : voulus) {
                  if (!autre.equals(a)) {
                     Manifeste.ModEmbarque mb = this.manifeste.parId(autre);
                     if (mb != null && fournit(mb, b.getKey(), b.getValue())) {
                        plan.avertissements.add(ma.nom + " se déclare incompatible avec " + mb.nomComplet());
                     }
                  }
               }
            }
         }
      }

      plan.finaux.addAll(voulus);
      return plan;
   }

   public static final class Plan {
      public final LinkedHashSet<String> finaux = new LinkedHashSet<>();
      public final List<String> ajoutes = new ArrayList<>();
      public final List<String> retires = new ArrayList<>();
      public final List<String> avertissements = new ArrayList<>();
      public final List<String> refus = new ArrayList<>();

      public boolean valide() {
         return this.refus.isEmpty();
      }
   }
}
