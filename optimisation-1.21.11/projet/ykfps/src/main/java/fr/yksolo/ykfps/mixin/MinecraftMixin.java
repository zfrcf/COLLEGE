package fr.yksolo.ykfps.mixin;

import fr.yksolo.ykfps.YkFps;
import net.minecraft.client.Minecraft;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.At.Shift;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Port 1.21.11 : renderFrame(Z)V s'appelle runTick(Z)V, la présentation passe par Window.updateDisplay et la limite par RenderSystem.limitDisplayFPS. */
@Mixin(Minecraft.class)
public abstract class MinecraftMixin {
   @Inject(method = "runTick(Z)V", at = @At("HEAD"))
   private void ykfps$frameStart(boolean tick, CallbackInfo ci) {
      YkFps.onFrameStart();
   }

   @Inject(method = "runTick(Z)V", at = @At(value = "INVOKE", target = "Lcom/mojang/blaze3d/platform/Window;updateDisplay(Lcom/mojang/blaze3d/TracyFrameCapture;)V"))
   private void ykfps$beforePresent(boolean tick, CallbackInfo ci) {
      YkFps.onWorkDone();
   }

   @Inject(method = "runTick(Z)V", at = @At(value = "INVOKE", target = "Lcom/mojang/blaze3d/systems/RenderSystem;limitDisplayFPS(I)V", shift = Shift.AFTER))
   private void ykfps$frameEnd(boolean tick, CallbackInfo ci) {
      YkFps.onFrameEnd();
   }
}
