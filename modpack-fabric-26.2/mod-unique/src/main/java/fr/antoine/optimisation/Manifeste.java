package fr.antoine.optimisation;

import com.google.gson.Gson;

import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Description des mods embarqués dans le jar (générée par assembler.py dans pack-manifest.json).
 */
public final class Manifeste {
    public String version_pack = "?";
    public String minecraft = "26.2";
    public LinkedHashMap<String, String> categories = new LinkedHashMap<>();
    public List<ModEmbarque> mods = new ArrayList<>();

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
            return version == null || version.isEmpty() ? nom : nom + " " + version;
        }
    }

    public static Manifeste charger() {
        try (InputStream in = Manifeste.class.getResourceAsStream("/pack-manifest.json")) {
            if (in == null) {
                OptimisationPack.LOG.warn("pack-manifest.json absent : jar de développement ?");
                return new Manifeste();
            }
            Manifeste m = new Gson().fromJson(new InputStreamReader(in, StandardCharsets.UTF_8), Manifeste.class);
            for (ModEmbarque mod : m.mods) {
                if (mod.depends == null) mod.depends = new LinkedHashMap<>();
                if (mod.breaks == null) mod.breaks = new LinkedHashMap<>();
                if (mod.fournit == null) mod.fournit = new LinkedHashMap<>();
                if (mod.fichiers == null) mod.fichiers = new ArrayList<>();
                if (mod.fournit.isEmpty()) mod.fournit.put(mod.id, mod.version);
            }
            return m;
        } catch (Exception e) {
            OptimisationPack.LOG.error("Lecture de pack-manifest.json impossible", e);
            return new Manifeste();
        }
    }

    public ModEmbarque parId(String id) {
        for (ModEmbarque m : mods) {
            if (m.id.equals(id)) return m;
        }
        return null;
    }

    public List<ModEmbarque> parCategorie(String categorie) {
        List<ModEmbarque> res = new ArrayList<>();
        for (ModEmbarque m : mods) {
            if (categorie.equals(m.categorie)) res.add(m);
        }
        return res;
    }

    public String libelleCategorie(String categorie) {
        return categories.getOrDefault(categorie, categorie);
    }
}
