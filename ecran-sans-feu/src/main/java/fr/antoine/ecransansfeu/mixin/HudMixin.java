package fr.antoine.ecransansfeu.mixin;

import fr.antoine.ecransansfeu.EcranSansFeuConfig;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.Hud;
import net.minecraft.resources.Identifier;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Retire le givre bleu qui apparaît sur les bords de l'écran quand le joueur gèle
 * (neige poudreuse). Les autres overlays (citrouille, etc.) ne sont pas touchés.
 */
@Mixin(Hud.class)
public abstract class HudMixin {

	@Shadow
	@Final
	private static Identifier POWDER_SNOW_OUTLINE_LOCATION;

	@Inject(method = "extractTextureOverlay", at = @At("HEAD"), cancellable = true)
	private void ecransansfeu$masquerGivre(GuiGraphicsExtractor extracteur, Identifier texture, float opacite, CallbackInfo ci) {
		if (texture.equals(POWDER_SNOW_OUTLINE_LOCATION) && EcranSansFeuConfig.get().givreMasque()) {
			ci.cancel();
		}
	}
}
