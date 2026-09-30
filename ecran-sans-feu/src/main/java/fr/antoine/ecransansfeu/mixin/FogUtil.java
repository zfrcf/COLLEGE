package fr.antoine.ecransansfeu.mixin;

import net.minecraft.client.renderer.fog.FogData;

/**
 * Petit utilitaire partagé par les mixins de brouillard.
 */
final class FogUtil {
	private FogUtil() {
	}

	/**
	 * Applique les mêmes valeurs que le mode spectateur : le brouillard commence
	 * derrière la caméra et se termine à la distance de rendu, donc il ne gêne plus.
	 */
	static void degager(FogData data, float distanceRendu) {
		data.environmentalStart = -8.0F;
		data.environmentalEnd = Math.max(distanceRendu, 16.0F);
		data.skyEnd = data.environmentalEnd;
		data.cloudEnd = data.environmentalEnd;
	}
}
