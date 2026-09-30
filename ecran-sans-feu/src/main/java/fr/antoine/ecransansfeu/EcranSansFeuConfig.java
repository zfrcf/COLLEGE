package fr.antoine.ecransansfeu;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonParseException;
import net.fabricmc.loader.api.FabricLoader;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * Configuration du mod, enregistrée dans {@code config/ecransansfeu.json}.
 * Chaque champ correspond à un effet visuel que le mod peut retirer.
 */
public final class EcranSansFeuConfig {
	private static final Logger LOGGER = LoggerFactory.getLogger("ecransansfeu");
	private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
	private static final String NOM_FICHIER = "ecransansfeu.json";

	private static EcranSansFeuConfig instance;

	/** Interrupteur général : si faux, le mod ne modifie plus rien. */
	public boolean modActive = true;

	/** Retire les flammes dessinées en bas de l'écran quand le joueur brûle. */
	public boolean masquerFeuEcran = true;

	/** Retire le brouillard orange qui bouche la vue quand la tête est dans la lave. */
	public boolean voirDansLaLave = true;

	/** Retire le brouillard bleuté de la neige poudreuse. */
	public boolean voirDansLaPoudreuse = true;

	/** Retire le givre bleu qui se forme sur les bords de l'écran quand le joueur gèle. */
	public boolean masquerGivreEcran = true;

	/** Retire l'overlay d'eau (texture bleutée) quand la tête est sous l'eau. Désactivé par défaut. */
	public boolean masquerOverlayEau = false;

	/** Retire la texture de bloc affichée quand la tête est dans un bloc solide. Désactivé par défaut. */
	public boolean masquerOverlayBloc = false;

	private EcranSansFeuConfig() {
	}

	public static EcranSansFeuConfig get() {
		if (instance == null) {
			instance = charger();
		}
		return instance;
	}

	public boolean feuMasque() {
		return modActive && masquerFeuEcran;
	}

	public boolean laveClaire() {
		return modActive && voirDansLaLave;
	}

	public boolean poudreuseClaire() {
		return modActive && voirDansLaPoudreuse;
	}

	public boolean givreMasque() {
		return modActive && masquerGivreEcran;
	}

	public boolean eauMasquee() {
		return modActive && masquerOverlayEau;
	}

	public boolean blocMasque() {
		return modActive && masquerOverlayBloc;
	}

	private static Path chemin() {
		return FabricLoader.getInstance().getConfigDir().resolve(NOM_FICHIER);
	}

	private static EcranSansFeuConfig charger() {
		Path fichier = chemin();
		if (Files.exists(fichier)) {
			try {
				String json = Files.readString(fichier, StandardCharsets.UTF_8);
				EcranSansFeuConfig lue = GSON.fromJson(json, EcranSansFeuConfig.class);
				if (lue != null) {
					// On réécrit le fichier pour ajouter les éventuelles nouvelles options.
					lue.sauvegarder();
					return lue;
				}
			} catch (IOException | JsonParseException e) {
				LOGGER.warn("Impossible de lire {}, utilisation des valeurs par défaut", fichier, e);
			}
		}
		EcranSansFeuConfig defaut = new EcranSansFeuConfig();
		defaut.sauvegarder();
		return defaut;
	}

	public void sauvegarder() {
		Path fichier = chemin();
		try {
			Files.createDirectories(fichier.getParent());
			Files.writeString(fichier, GSON.toJson(this), StandardCharsets.UTF_8);
		} catch (IOException e) {
			LOGGER.warn("Impossible d'écrire {}", fichier, e);
		}
	}
}
