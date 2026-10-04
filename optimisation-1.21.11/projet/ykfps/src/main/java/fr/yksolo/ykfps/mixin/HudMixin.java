package fr.yksolo.ykfps.mixin;

import fr.yksolo.ykfps.YkFps;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.Gui;
import net.minecraft.client.gui.GuiGraphics;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Port 1.21.11 : en 26.2 la classe s'appelait Hud et la méthode extractRenderState ; ici Gui.render. */
@Mixin(Gui.class)
public abstract class HudMixin {
   @Inject(method = "render", at = @At("TAIL"))
   private void ykfps$draw(GuiGraphics g, DeltaTracker delta, CallbackInfo ci) {
      Minecraft mc = Minecraft.getInstance();
      if (!mc.options.hideGui) {
         Font font = mc.font;
         int real = mc.getFps();
         int potential = (int)Math.round(YkFps.potentialFps());
         if (potential < real) {
            potential = real;
         }

         String line1 = "FPS : " + real;
         String line2 = "Sans limite : ~" + potential + " FPS";
         String line3 = "Attente VSync/plafond : " + Math.round(YkFps.waitPercent()) + " %";
         int w = Math.max(font.width(line1), Math.max(font.width(line2), font.width(line3)));
         int x = mc.getWindow().getGuiScaledWidth() - w - 6;
         int y = 4;
         int h = 9;
         g.fill(x - 3, y - 2, x + w + 3, y + 3 * h + 3, 1711276032);
         g.drawString(font, line1, x, y, -1, true);
         g.drawString(font, line2, x, y + h + 1, -11141291, true);
         g.drawString(font, line3, x, y + 2 * h + 2, -5592406, true);
      }
   }
}
