package fr.antoine.optimisation;

import java.io.IOException;
import java.lang.ProcessBuilder.Redirect;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.stream.Stream;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.loader.api.FabricLoader;
import net.fabricmc.loader.api.ModContainer;
import net.fabricmc.loader.api.metadata.ModOrigin;
import net.fabricmc.loader.api.metadata.ModOrigin.Kind;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public final class OptimisationPack implements ClientModInitializer {
   public static final String ID = "optimisation_pack";
   public static final Logger LOG = LoggerFactory.getLogger("Optimisation 1.21.11");
   private static Manifeste manifeste = new Manifeste();
   private static Etat etat = new Etat();
   private static Set<String> charges = new LinkedHashSet<>();
   private static final AtomicBoolean applicateurLance = new AtomicBoolean(false);

   public static Manifeste manifeste() {
      return manifeste;
   }

   public static Etat etat() {
      return etat;
   }

   public static Set<String> charges() {
      return charges;
   }

   public static Path fichierEnAttente() {
      return Etat.dossierConfig().resolve("en-attente.txt");
   }

   public static Path dossierMisDeCote() {
      return Etat.dossierConfig().resolve("mis-de-cote");
   }

   public static boolean changementsEnAttente() {
      return Files.exists(fichierEnAttente());
   }

   public void onInitializeClient() {
      manifeste = Manifeste.charger();
      charges = Etat.charges(manifeste);
      etat = Etat.charger(manifeste);
      LOG.info("Pack {} : {} mods embarqués, {} chargés dans cette session.", new Object[]{manifeste.version_pack, manifeste.mods.size(), charges.size()});
      if (changementsEnAttente()) {
         LOG.warn("Des changements de mods n'ont pas été appliqués au dernier arrêt : ils le seront à la fermeture du jeu.");
         lancerApplicateur();
      }

      Runtime.getRuntime().addShutdownHook(new Thread(() -> {
         if (changementsEnAttente()) {
            lancerApplicateur();
         }
      }, "optimisation-pack-arret"));
      modeTest();
   }

   private static void modeTest() {
      String test = System.getProperty("optimisation_pack.test");
      if (test != null && !test.isBlank()) {
         Set<String> souhaites = new LinkedHashSet<>(charges);

         for (String ordre : test.split(";")) {
            String[] kv = ordre.split(":", 2);
            if (kv.length == 2) {
               for (String id : kv[1].split(",")) {
                  if (kv[0].equals("desactiver")) {
                     souhaites.remove(id.strip());
                  } else if (kv[0].equals("activer")) {
                     souhaites.add(id.strip());
                  }
               }
            }
         }

         Planificateur.Plan plan = new Planificateur(manifeste).calculer(charges, souhaites);
         LOG.info(
            "[TEST] finaux={} ajoutés={} retirés={} avertissements={} refus={}",
            new Object[]{plan.finaux, plan.ajoutes, plan.retires, plan.avertissements, plan.refus}
         );
         if (plan.valide()) {
            try {
               programmer(plan, true);
               LOG.info("[TEST] en-attente écrit : {}", fichierEnAttente());
            } catch (IOException e) {
               LOG.error("[TEST] échec", e);
            }
         }
      }
   }

   static String normaliser(String s) {
      return s.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]", "");
   }

   public static List<Path> fichiersAssocies(Manifeste.ModEmbarque m) {
      Path jeu = FabricLoader.getInstance().getGameDir();
      LinkedHashSet<Path> res = new LinkedHashSet<>();

      for (String f : m.fichiers) {
         Path p = Path.of(f);
         if (Files.exists(jeu.resolve(p))) {
            res.add(p);
         }
      }

      Path config = jeu.resolve("config");
      if (Files.isDirectory(config)) {
         String cible = normaliser(m.id);

         try (Stream<Path> flux = Files.list(config)) {
            for (Path p : (Iterable<Path>) flux::iterator) {
               String base = p.getFileName().toString();
               int point = base.indexOf(46);
               if (point > 0) {
                  base = base.substring(0, point);
               }

               base = base.replaceAll("[-_](client|common|server)$", "");
               if (normaliser(base).equals(cible)) {
                  res.add(jeu.relativize(p));
               }
            }
         } catch (IOException var12) {
         }
      }

      return new ArrayList<>(res);
   }

   public static boolean aDesFichiersMisDeCote(Manifeste.ModEmbarque m) {
      return Files.isDirectory(dossierMisDeCote().resolve(m.id));
   }

   public static void programmer(Planificateur.Plan plan, boolean mettreDeCote) throws IOException {
      Path jeu = FabricLoader.getInstance().getGameDir().toAbsolutePath();
      Set<String> finaux = plan.finaux;
      List<String> lignes = new ArrayList<>();
      Optional<Path> jar = cheminJar();
      lignes.add("# Fichier généré par Optimisation 1.21.11 — appliqué à la fermeture du jeu");
      lignes.add("jar=" + jar.map(Path::toString).orElse("?"));

      for (Manifeste.ModEmbarque m : manifeste.mods) {
         if (finaux.contains(m.id)) {
            lignes.add("activer=" + m.fichier);
         }
      }

      Set<String> avant = new LinkedHashSet<>(charges);
      avant.addAll(etat.actifs);

      for (Manifeste.ModEmbarque m : manifeste.mods) {
         boolean actif = finaux.contains(m.id);
         if (actif) {
            Path cote = dossierMisDeCote().resolve(m.id);
            if (Files.isDirectory(cote)) {
               lignes.add("restaurer=" + cote.toAbsolutePath() + "|" + jeu);
            }
         } else if (mettreDeCote && avant.contains(m.id)) {
            for (Path rel : fichiersAssocies(m)) {
               if (!reclamePar(rel, finaux)) {
                  lignes.add("deplacer=" + jeu.resolve(rel) + "|" + dossierMisDeCote().resolve(m.id).resolve(rel).toAbsolutePath());
               }
            }
         }
      }

      etat.actifs.clear();
      etat.actifs.addAll(finaux);
      etat.mettre_de_cote = mettreDeCote;
      etat.sauver();
      Files.createDirectories(Etat.dossierConfig());
      Files.write(fichierEnAttente(), lignes, StandardCharsets.UTF_8);
      LOG.info("Changements programmés : {} mods actifs au prochain lancement.", finaux.size());
   }

   private static boolean reclamePar(Path rel, Set<String> actifs) {
      for (Manifeste.ModEmbarque autre : manifeste.mods) {
         if (actifs.contains(autre.id)) {
            for (String f : autre.fichiers) {
               if (Path.of(f).equals(rel)) {
                  return true;
               }
            }
         }
      }

      return false;
   }

   public static void annuler() throws IOException {
      Files.deleteIfExists(fichierEnAttente());
      etat.actifs.clear();
      etat.actifs.addAll(charges);
      etat.sauver();
   }

   public static Optional<Path> cheminJar() {
      Optional<ModContainer> c = FabricLoader.getInstance().getModContainer("optimisation_pack");
      if (c.isEmpty()) {
         return Optional.empty();
      }

      ModOrigin origine = c.get().getOrigin();
      if (origine.getKind() != Kind.PATH) {
         return Optional.empty();
      }

      for (Path p : origine.getPaths()) {
         if (p.toString().toLowerCase(Locale.ROOT).endsWith(".jar") && Files.isRegularFile(p)) {
            return Optional.of(p.toAbsolutePath());
         }
      }

      return Optional.empty();
   }

   public static synchronized void lancerApplicateur() {
      if (applicateurLance.compareAndSet(false, true)) {
         Optional<Path> jar = cheminJar();
         if (jar.isEmpty()) {
            LOG.error("Jar du pack introuvable (environnement de développement ?) : changements non appliqués.");
            applicateurLance.set(false);
         } else {
            String java = ProcessHandle.current().info().command().orElse(Path.of(System.getProperty("java.home"), "bin", "java").toString());

            try {
               Files.createDirectories(Etat.dossierConfig());
               Path journal = Etat.dossierConfig().resolve("applicateur-console.log");
               ProcessBuilder pb = new ProcessBuilder(
                  java,
                  "-cp",
                  jar.get().toString(),
                  "fr.antoine.optimisation.Applicateur",
                  Long.toString(ProcessHandle.current().pid()),
                  jar.get().toString(),
                  fichierEnAttente().toAbsolutePath().toString()
               );
               pb.redirectErrorStream(true);
               pb.redirectOutput(Redirect.appendTo(journal.toFile()));
               pb.environment().remove("JAVA_TOOL_OPTIONS");
               pb.start();
               LOG.info("Applicateur lancé : les changements seront appliqués à la fermeture du jeu.");
            } catch (IOException e) {
               LOG.error("Impossible de lancer l'Applicateur", e);
               applicateurLance.set(false);
            }
         }
      }
   }
}
