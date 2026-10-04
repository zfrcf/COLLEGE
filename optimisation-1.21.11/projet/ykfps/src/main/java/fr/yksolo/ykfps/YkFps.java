package fr.yksolo.ykfps;

import net.fabricmc.api.ClientModInitializer;

public final class YkFps implements ClientModInitializer {
   private static final int WINDOW = 90;
   private static final long[] workNs = new long[90];
   private static final long[] fullNs = new long[90];
   private static int index = 0;
   private static int filled = 0;
   private static long frameStart = 0L;
   private static long workEnd = 0L;
   private static volatile double potentialFps = 0.0;
   private static volatile double measuredFps = 0.0;
   private static volatile double waitPercent = 0.0;

   public void onInitializeClient() {
   }

   public static void onFrameStart() {
      frameStart = System.nanoTime();
   }

   public static void onWorkDone() {
      workEnd = System.nanoTime();
   }

   public static void onFrameEnd() {
      long end = System.nanoTime();
      if (frameStart != 0L && workEnd >= frameStart) {
         workNs[index] = workEnd - frameStart;
         fullNs[index] = end - frameStart;
         index = (index + 1) % 90;
         if (filled < 90) {
            filled++;
         }

         long sumWork = 0L;
         long sumFull = 0L;

         for (int i = 0; i < filled; i++) {
            sumWork += workNs[i];
            sumFull += fullNs[i];
         }

         if (sumWork > 0L) {
            potentialFps = filled * 1.0E9 / sumWork;
         }

         if (sumFull > 0L) {
            measuredFps = filled * 1.0E9 / sumFull;
            waitPercent = 100.0 * (sumFull - sumWork) / sumFull;
         }
      }
   }

   public static double potentialFps() {
      return potentialFps;
   }

   public static double measuredFps() {
      return measuredFps;
   }

   public static double waitPercent() {
      return waitPercent;
   }
}
