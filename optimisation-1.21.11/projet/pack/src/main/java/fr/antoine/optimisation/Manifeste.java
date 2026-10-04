package fr.antoine.optimisation;

import com.google.gson.Gson;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class Manifeste {
   public String version_pack = "?";
   public String minecraft = "1.21.11";
   public LinkedHashMap<String, String> categories = new LinkedHashMap<>();
   public List<Manifeste.ModEmbarque> mods = new ArrayList<>();

   public static Manifeste charger() {
      try (InputStream in = Manifeste.class.getResourceAsStream("/pack-manifest.json")) {
         if (in == null) {
            OptimisationPack.LOG.warn("pack-manifest.json absent : jar de développement ?");
            return new Manifeste();
         }

         Manifeste m = (Manifeste)new Gson().fromJson(new InputStreamReader(in, StandardCharsets.UTF_8), Manifeste.class);

         for (Manifeste.ModEmbarque mod : m.mods) {
            if (mod.depends == null) {
               mod.depends = new LinkedHashMap<>();
            }

            if (mod.breaks == null) {
               mod.breaks = new LinkedHashMap<>();
            }

            if (mod.fournit == null) {
               mod.fournit = new LinkedHashMap<>();
            }

            if (mod.fichiers == null) {
               mod.fichiers = new ArrayList<>();
            }

            if (mod.fournit.isEmpty()) {
               mod.fournit.put(mod.id, mod.version);
            }
         }

         return m;
      } catch (Exception e) {
         OptimisationPack.LOG.error("Lecture de pack-manifest.json impossible", e);
         return new Manifeste();
      }
   }

   public Manifeste.ModEmbarque parId(String id) {
      for (Manifeste.ModEmbarque m : this.mods) {
         if (m.id.equals(id)) {
            return m;
         }
      }

      return null;
   }

   public List<Manifeste.ModEmbarque> parCategorie(String categorie) {
      List<Manifeste.ModEmbarque> res = new ArrayList<>();

      for (Manifeste.ModEmbarque m : this.mods) {
         if (categorie.equals(m.categorie)) {
            res.add(m);
         }
      }

      return res;
   }

   public String libelleCategorie(String categorie) {
      return this.categories.getOrDefault(categorie, categorie);
   }

   public static final class ModEmbarque {
      public String id;
      public String fichier;
      public String nom;
      public String version = "";
      public String categorie = "autre";
      public String description = "";
      public boolean bibliotheque;
      public boolean par_defaut = true;
      public boolean verrouille;
      public String raison_verrou = "";
      public Map<String, String> depends = new LinkedHashMap<>();
      public Map<String, String> breaks = new LinkedHashMap<>();
      public Map<String, String> fournit = new LinkedHashMap<>();
      public List<String> fichiers = new ArrayList<>();

      public String nomComplet() {
         return this.version != null && !this.version.isEmpty() ? this.nom + " " + this.version : this.nom;
      }
   }
}
