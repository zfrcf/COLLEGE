package fr.antoine.ecransansfeu;

import com.mojang.blaze3d.platform.InputConstants;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.keymapping.v1.KeyMappingHelper;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Point d'entrée client du mod « Écran Sans Feu ».
 * Enregistre les touches et charge la configuration.
 */
public final class EcranSansFeuClient implements ClientModInitializer {
	public static final String MOD_ID = "ecransansfeu";
	private static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

	private static final KeyMapping.Category CATEGORIE =
			KeyMapping.Category.register(Identifier.fromNamespaceAndPath(MOD_ID, "touches"));

	private KeyMapping toucheBasculerMod;
	private KeyMapping toucheBasculerFeu;
	private KeyMapping toucheBasculerLave;

	@Override
	public void onInitializeClient() {
		EcranSansFeuConfig config = EcranSansFeuConfig.get();
		LOGGER.info("Écran Sans Feu chargé (feu masqué : {}, lave claire : {})", config.masquerFeuEcran, config.voirDansLaLave);

		toucheBasculerMod = KeyMappingHelper.registerKeyMapping(new KeyMapping(
				"key.ecransansfeu.basculer", InputConstants.Type.KEYSYM, InputConstants.KEY_F8, CATEGORIE));
		toucheBasculerFeu = KeyMappingHelper.registerKeyMapping(new KeyMapping(
				"key.ecransansfeu.basculer_feu", InputConstants.Type.KEYSYM, InputConstants.UNKNOWN.getValue(), CATEGORIE));
		toucheBasculerLave = KeyMappingHelper.registerKeyMapping(new KeyMapping(
				"key.ecransansfeu.basculer_lave", InputConstants.Type.KEYSYM, InputConstants.UNKNOWN.getValue(), CATEGORIE));

		ClientTickEvents.END_CLIENT_TICK.register(this::gererTouches);
	}

	private void gererTouches(Minecraft minecraft) {
		EcranSansFeuConfig config = EcranSansFeuConfig.get();

		while (toucheBasculerMod.consumeClick()) {
			config.modActive = !config.modActive;
			config.sauvegarder();
			afficher(minecraft, config.modActive ? "message.ecransansfeu.mod_active" : "message.ecransansfeu.mod_inactif");
		}

		while (toucheBasculerFeu.consumeClick()) {
			config.masquerFeuEcran = !config.masquerFeuEcran;
			config.sauvegarder();
			afficher(minecraft, config.masquerFeuEcran ? "message.ecransansfeu.feu_masque" : "message.ecransansfeu.feu_visible");
		}

		while (toucheBasculerLave.consumeClick()) {
			config.voirDansLaLave = !config.voirDansLaLave;
			config.sauvegarder();
			afficher(minecraft, config.voirDansLaLave ? "message.ecransansfeu.lave_claire" : "message.ecransansfeu.lave_normale");
		}
	}

	private static void afficher(Minecraft minecraft, String cle) {
		if (minecraft.gui != null && minecraft.player != null) {
			minecraft.gui.hud.setOverlayMessage(Component.translatable(cle), false);
		}
	}
}
