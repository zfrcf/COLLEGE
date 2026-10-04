package fr.antoine.optimisation;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import java.io.IOException;
import java.io.Reader;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.TreeSet;
import net.fabricmc.loader.api.FabricLoader;

public final class Etat {
   public Set<String> actifs = new TreeSet<>();
   public boolean mettre_de_cote = false;
   private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();

   public static Path dossierConfig() {
      return FabricLoader.getInstance().getConfigDir().resolve("optimisation_pack");
   }

   public static Path fichier() {
      return dossierConfig().resolve("etat.json");
   }

   public static Set<String> charges(Manifeste manifeste) {
      Set<String> res = new LinkedHashSet<>();

      for (Manifeste.ModEmbarque m : manifeste.mods) {
         if (FabricLoader.getInstance().isModLoaded(m.id)) {
            res.add(m.id);
         }
      }

      return res;
   }

   public static Etat charger(Manifeste manifeste) {
      Path f = fichier();
      if (Files.exists(f)) {
         try (Reader r = Files.newBufferedReader(f, StandardCharsets.UTF_8)) {
            Etat e = (Etat)GSON.fromJson(r, Etat.class);
            if (e != null) {
               if (e.actifs == null) {
                  e.actifs = new TreeSet<>();
               }

               e.actifs = new TreeSet<>(e.actifs);
               return e;
            }
         } catch (Exception ex) {
            OptimisationPack.LOG.warn("etat.json illisible, état reconstruit depuis les mods chargés", ex);
         }
      }

      Etat e = new Etat();
      e.actifs = new TreeSet<>(charges(manifeste));
      return e;
   }

   public void sauver() throws IOException {
      Files.createDirectories(dossierConfig());

      try (Writer w = Files.newBufferedWriter(fichier(), StandardCharsets.UTF_8)) {
         GSON.toJson(this, w);
      }
   }
}
