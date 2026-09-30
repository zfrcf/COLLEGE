package fr.antoine.ecransansfeu.mixin;

import fr.antoine.ecransansfeu.EcranSansFeuConfig;
import net.minecraft.client.Camera;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.renderer.fog.FogData;
import net.minecraft.client.renderer.fog.environment.LavaFogEnvironment;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Repousse le brouillard de lave jusqu'à la distance de rendu :
 * la vue reste dégagée quand la tête du joueur est dans la lave.
 */
@Mixin(LavaFogEnvironment.class)
public abstract class LavaFogEnvironmentMixin {

	@Inject(method = "setupFog", at = @At("TAIL"))
	private void ecransansfeu$laveClaire(FogData data, Camera camera, ClientLevel level, float distanceRendu, DeltaTracker deltaTracker, CallbackInfo ci) {
		if (EcranSansFeuConfig.get().laveClaire()) {
			FogUtil.degager(data, distanceRendu);
		}
	}
}
