package fr.antoine.optimisation;

import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.Map.Entry;
import me.shedaniel.clothconfig2.api.ConfigBuilder;
import me.shedaniel.clothconfig2.api.ConfigCategory;
import me.shedaniel.clothconfig2.api.ConfigEntryBuilder;
import net.minecraft.ChatFormatting;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.AlertScreen;
import net.minecraft.client.gui.screens.ConfirmScreen;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

public final class EcranConfig {
   private EcranConfig() {
   }

   public static Screen creer(Screen parent) {
      Manifeste manifeste = OptimisationPack.manifeste();
      Etat etat = OptimisationPack.etat();
      Set<String> charges = OptimisationPack.charges();
      Planificateur planificateur = new Planificateur(manifeste);
      Map<String, Boolean> choix = new LinkedHashMap<>();
      boolean[] mettreDeCote = new boolean[]{etat.mettre_de_cote};
      ConfigBuilder builder = ConfigBuilder.create()
         .setParentScreen(parent)
         .setTitle(Component.literal("Optimisation 1.21.11 — mods du pack"))
         .setTransparentBackground(true)
         .setDoesConfirmSave(false);
      ConfigEntryBuilder eb = builder.entryBuilder();
      ConfigCategory resume = builder.getOrCreateCategory(Component.literal("Résumé"));
      int nbActifs = 0;

      for (Manifeste.ModEmbarque m : manifeste.mods) {
         if (etat.actifs.contains(m.id)) {
            nbActifs++;
         }
      }

      resume.addEntry(
         eb.startTextDescription(
               Component.literal(
                  manifeste.mods.size()
                     + " mods embarqués dans ce fichier · "
                     + charges.size()
                     + " chargés actuellement · "
                     + nbActifs
                     + " prévus au prochain lancement"
               )
            )
            .build()
      );
      if (OptimisationPack.changementsEnAttente()) {
         resume.addEntry(
            eb.startTextDescription(
                  Component.literal(
                        "⚠ Des changements sont en attente : ils seront appliqués automatiquement à la fermeture du jeu, puis pris en compte au lancement suivant."
                     )
                     .withStyle(ChatFormatting.GOLD)
               )
               .build()
         );
      }

      resume.addEntry(
         eb.startTextDescription(
               Component.literal(
                     "Coche ou décoche les mods dans les onglets, puis « Enregistrer ». Les bibliothèques nécessaires sont ajoutées toutes seules ; désactiver une bibliothèque désactive les mods qui en dépendent. Les changements s'appliquent à la fermeture du jeu (le pack se réécrit lui-même)."
                  )
                  .withStyle(ChatFormatting.GRAY)
            )
            .build()
      );
      resume.addEntry(
         eb.startBooleanToggle(Component.literal("Mettre de côté les fichiers des mods désactivés"), etat.mettre_de_cote)
            .setDefaultValue(false)
            .setTooltip(
               new Component[]{
                  Component.literal("Schematics, shaderpacks, resourcepacks, config/... d'un mod désactivé"),
                  Component.literal("sont déplacés dans config/optimisation_pack/mis-de-cote/<mod>/"),
                  Component.literal("et remis en place automatiquement quand le mod est réactivé."),
                  Component.literal("Un dossier partagé avec un mod encore actif n'est jamais déplacé.")
               }
            )
            .setYesNoTextSupplier(b -> Component.literal(b ? "Oui" : "Non"))
            .setSaveConsumer(v -> mettreDeCote[0] = v)
            .build()
      );

      for (Entry<String, String> cat : manifeste.categories.entrySet()) {
         List<Manifeste.ModEmbarque> mods = manifeste.parCategorie(cat.getKey());
         if (!mods.isEmpty()) {
            ConfigCategory categorie = builder.getOrCreateCategory(Component.literal(cat.getValue()));

            for (Manifeste.ModEmbarque m : mods) {
               boolean prevu = etat.actifs.contains(m.id);
               boolean charge = charges.contains(m.id);
               List<Component> infobulle = infobulle(manifeste, planificateur, m, prevu, charge);
               if (m.verrouille) {
                  choix.put(m.id, true);
                  categorie.addEntry(
                     eb.startTextDescription(
                           Component.literal(
                                 "\ud83d\udd12 "
                                    + m.nomComplet()
                                    + " — toujours actif ("
                                    + (m.raison_verrou.isEmpty() ? "requis par le gestionnaire" : m.raison_verrou)
                                    + ")"
                              )
                              .withStyle(ChatFormatting.DARK_GREEN)
                        )
                        .setTooltip(infobulle.toArray(new Component[0]))
                        .build()
                  );
               } else {
                  choix.put(m.id, prevu);
                  String titre = m.nomComplet() + (m.bibliotheque ? "  [bibliothèque]" : "") + (prevu != charge ? "  (redémarrage requis)" : "");
                  categorie.addEntry(
                     eb.startBooleanToggle(Component.literal(titre), prevu)
                        .setDefaultValue(m.par_defaut)
                        .setTooltip(infobulle.toArray(new Component[0]))
                        .setYesNoTextSupplier(
                           b -> b ? Component.literal("Activé").withStyle(ChatFormatting.GREEN) : Component.literal("Désactivé").withStyle(ChatFormatting.RED)
                        )
                        .setSaveConsumer(v -> choix.put(m.id, v))
                        .build()
                  );
               }
            }
         }
      }

      builder.setSavingRunnable(() -> enregistrer(manifeste, planificateur, etat, charges, choix, mettreDeCote[0], parent));
      return builder.build();
   }

   private static List<Component> infobulle(Manifeste manifeste, Planificateur planificateur, Manifeste.ModEmbarque m, boolean prevu, boolean charge) {
      List<Component> lignes = new ArrayList<>();
      if (!m.description.isEmpty()) {
         for (String morceau : decouper(m.description, 60)) {
            lignes.add(Component.literal(morceau));
         }
      }

      lignes.add(
         Component.literal(
               "État actuel : "
                  + (charge ? "chargé" : "non chargé")
                  + (prevu != charge ? " → " + (prevu ? "sera activé" : "sera désactivé") + " au prochain lancement" : "")
            )
            .withStyle(ChatFormatting.GRAY)
      );
      if (!m.depends.isEmpty()) {
         List<String> noms = new ArrayList<>();

         for (String d : m.depends.keySet()) {
            String nom = d;

            for (Manifeste.ModEmbarque f : manifeste.mods) {
               if (f.fournit.containsKey(d)) {
                  nom = f.nom;
                  break;
               }
            }

            if (!noms.contains(nom)) {
               noms.add(nom);
            }
         }

         lignes.add(Component.literal("Dépend de : " + String.join(", ", noms)).withStyle(ChatFormatting.AQUA));
      }

      Set<String> tous = new LinkedHashSet<>();

      for (Manifeste.ModEmbarque x : manifeste.mods) {
         tous.add(x.id);
      }

      List<Manifeste.ModEmbarque> dependants = planificateur.dependants(m.id, tous);
      if (!dependants.isEmpty()) {
         List<String> noms = new ArrayList<>();

         for (Manifeste.ModEmbarque d : dependants) {
            noms.add(d.nom);
         }

         for (String morceau : decouper("Requis par : " + String.join(", ", noms), 60)) {
            lignes.add(Component.literal(morceau).withStyle(ChatFormatting.YELLOW));
         }
      }

      List<Path> fichiers = OptimisationPack.fichiersAssocies(m);
      if (!fichiers.isEmpty()) {
         List<String> noms = new ArrayList<>();

         for (Path p : fichiers) {
            noms.add(p.toString().replace('\\', '/'));
         }

         lignes.add(Component.literal("Fichiers associés : " + String.join(", ", noms)).withStyle(ChatFormatting.LIGHT_PURPLE));
      }

      if (OptimisationPack.aDesFichiersMisDeCote(m)) {
         lignes.add(Component.literal("Des fichiers de ce mod sont mis de côté (restaurés à la réactivation).").withStyle(ChatFormatting.LIGHT_PURPLE));
      }

      return lignes;
   }

   private static List<String> decouper(String texte, int largeur) {
      List<String> res = new ArrayList<>();
      StringBuilder ligne = new StringBuilder();

      for (String mot : texte.split(" ")) {
         if (ligne.length() + mot.length() + 1 > largeur && ligne.length() > 0) {
            res.add(ligne.toString());
            ligne.setLength(0);
         }

         if (ligne.length() > 0) {
            ligne.append(' ');
         }

         ligne.append(mot);
      }

      if (ligne.length() > 0) {
         res.add(ligne.toString());
      }

      return res;
   }

   private static void enregistrer(
      Manifeste manifeste, Planificateur planificateur, Etat etat, Set<String> charges, Map<String, Boolean> choix, boolean mettreDeCote, Screen parent
   ) {
      Set<String> souhaites = new LinkedHashSet<>();

      for (Entry<String, Boolean> e : choix.entrySet()) {
         if (e.getValue()) {
            souhaites.add(e.getKey());
         }
      }

      Set<String> actuels = new LinkedHashSet<>(charges);
      actuels.addAll(etat.actifs);
      Planificateur.Plan plan = planificateur.calculer(actuels, souhaites);
      Minecraft mc = Minecraft.getInstance();
      if (!plan.valide()) {
         afficherPlusTard(
            mc,
            new AlertScreen(
               () -> mc.setScreenAndShow(parent), Component.literal("Impossible d'appliquer ces choix"), Component.literal(String.join("\n", plan.refus))
            )
         );
      } else {
         boolean identique = plan.finaux.equals(new LinkedHashSet<>(charges)) && !OptimisationPack.changementsEnAttente();
         if (!identique || mettreDeCote != etat.mettre_de_cote) {
            if (plan.ajoutes.isEmpty() && plan.retires.isEmpty() && plan.avertissements.isEmpty()) {
               appliquer(mc, plan, mettreDeCote, parent, charges);
            } else {
               StringBuilder msg = new StringBuilder();
               if (!plan.ajoutes.isEmpty()) {
                  msg.append("Activés automatiquement :\n");

                  for (String s : limiter(plan.ajoutes)) {
                     msg.append("  + ").append(s).append('\n');
                  }
               }

               if (!plan.retires.isEmpty()) {
                  msg.append("Désactivés automatiquement :\n");

                  for (String s : limiter(plan.retires)) {
                     msg.append("  − ").append(s).append('\n');
                  }
               }

               if (!plan.avertissements.isEmpty()) {
                  msg.append("Avertissements :\n");

                  for (String s : limiter(plan.avertissements)) {
                     msg.append("  ! ").append(s).append('\n');
                  }
               }

               msg.append("\nAppliquer ces changements ?");
               afficherPlusTard(mc, new ConfirmScreen(oui -> {
                  if (oui) {
                     appliquer(mc, plan, mettreDeCote, parent, charges);
                  } else {
                     mc.setScreenAndShow(creer(parent));
                  }
               }, Component.literal("Dépendances ajustées"), Component.literal(msg.toString())));
            }
         }
      }
   }

   private static List<String> limiter(List<String> liste) {
      if (liste.size() <= 6) {
         return liste;
      }

      List<String> res = new ArrayList<>(liste.subList(0, 5));
      res.add("… et " + (liste.size() - 5) + " autre(s)");
      return res;
   }

   private static void appliquer(Minecraft mc, Planificateur.Plan plan, boolean mettreDeCote, Screen parent, Set<String> charges) {
      try {
         if (plan.finaux.equals(new LinkedHashSet<>(charges))) {
            OptimisationPack.annuler();
            OptimisationPack.etat().mettre_de_cote = mettreDeCote;
            OptimisationPack.etat().sauver();
            afficherPlusTard(
               mc,
               new AlertScreen(
                  () -> mc.setScreenAndShow(parent),
                  Component.literal("Aucun changement"),
                  Component.literal("Les mods sélectionnés correspondent à ceux déjà chargés.")
               )
            );
            return;
         }

         OptimisationPack.programmer(plan, mettreDeCote);
         int plus = 0;
         int moins = 0;

         for (String id : plan.finaux) {
            if (!charges.contains(id)) {
               plus++;
            }
         }

         for (String id : charges) {
            if (!plan.finaux.contains(id)) {
               moins++;
            }
         }

         afficherPlusTard(
            mc,
            new AlertScreen(
               () -> mc.setScreenAndShow(parent),
               Component.literal("Changements enregistrés"),
               Component.literal(
                  plus
                     + " mod(s) à activer, "
                     + moins
                     + " mod(s) à désactiver.\n\nIls seront appliqués automatiquement quand tu fermeras Minecraft, puis pris en compte au lancement suivant."
               )
            )
         );
      } catch (IOException e) {
         OptimisationPack.LOG.error("Enregistrement impossible", e);
         afficherPlusTard(
            mc,
            new AlertScreen(() -> mc.setScreenAndShow(parent), Component.literal("Erreur"), Component.literal("Enregistrement impossible : " + e.getMessage()))
         );
      }
   }

   private static void afficherPlusTard(Minecraft mc, Screen ecran) {
      mc.execute(() -> mc.setScreenAndShow(ecran));
   }
}
