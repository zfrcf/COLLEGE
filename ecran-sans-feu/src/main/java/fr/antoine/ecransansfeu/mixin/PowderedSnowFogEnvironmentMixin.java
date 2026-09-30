package fr.antoine.ecransansfeu.mixin;

import fr.antoine.ecransansfeu.EcranSansFeuConfig;
import net.minecraft.client.Camera;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.renderer.fog.FogData;
import net.minecraft.client.renderer.fog.environment.PowderedSnowFogEnvironment;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Repousse le brouillard bleuté de la neige poudreuse jusqu'à la distance de rendu.
 */
@Mixin(PowderedSnowFogEnvironment.class)
public abstract class PowderedSnowFogEnvironmentMixin {

	@Inject(method = "setupFog", at = @At("TAIL"))
	private void ecransansfeu$poudreuseClaire(FogData data, Camera camera, ClientLevel level, float distanceRendu, DeltaTracker deltaTracker, CallbackInfo ci) {
		if (EcranSansFeuConfig.get().poudreuseClaire()) {
			FogUtil.degager(data, distanceRendu);
		}
	}
}
