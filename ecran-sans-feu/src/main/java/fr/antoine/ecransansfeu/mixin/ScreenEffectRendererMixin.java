package fr.antoine.ecransansfeu.mixin;

import com.mojang.blaze3d.vertex.PoseStack;
import fr.antoine.ecransansfeu.EcranSansFeuConfig;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.ScreenEffectRenderer;
import net.minecraft.client.renderer.SubmitNodeCollector;
import net.minecraft.client.renderer.texture.TextureAtlasSprite;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Empêche le dessin des overlays plein écran (feu, eau, bloc) selon la configuration.
 */
@Mixin(ScreenEffectRenderer.class)
public abstract class ScreenEffectRendererMixin {

	@Inject(method = "submitFire", at = @At("HEAD"), cancellable = true)
	private static void ecransansfeu$masquerFeu(PoseStack poseStack, SubmitNodeCollector collector, TextureAtlasSprite sprite, CallbackInfo ci) {
		if (EcranSansFeuConfig.get().feuMasque()) {
			ci.cancel();
		}
	}

	@Inject(method = "submitWater", at = @At("HEAD"), cancellable = true)
	private static void ecransansfeu$masquerEau(Minecraft minecraft, PoseStack poseStack, SubmitNodeCollector collector, CallbackInfo ci) {
		if (EcranSansFeuConfig.get().eauMasquee()) {
			ci.cancel();
		}
	}

	@Inject(method = "submitBlockSprite", at = @At("HEAD"), cancellable = true)
	private static void ecransansfeu$masquerBloc(TextureAtlasSprite sprite, PoseStack poseStack, SubmitNodeCollector collector, int couleur, CallbackInfo ci) {
		if (EcranSansFeuConfig.get().blocMasque()) {
			ci.cancel();
		}
	}
}
