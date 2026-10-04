package fr.antoine.optimisation;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.IOException;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import java.util.zip.ZipOutputStream;

public final class Applicateur {
   private static PrintWriter journal;
   private static final Pattern JARS = Pattern.compile("\"jars\"\\s*:\\s*\\[[^\\]]*\\]");

   public static void main(String[] args) throws Exception {
      if (args.length < 3) {
         System.err.println("Usage : Applicateur <pid> <jar> <en-attente.txt>");
         System.exit(2);
      }

      long pid = Long.parseLong(args[0]);
      Path jar = Paths.get(args[1]).toAbsolutePath();
      Path enAttente = Paths.get(args[2]).toAbsolutePath();
      Path dossier = enAttente.getParent();
      Files.createDirectories(dossier);
      journal = new PrintWriter(
         Files.newBufferedWriter(dossier.resolve("applicateur.log"), StandardCharsets.UTF_8, StandardOpenOption.CREATE, StandardOpenOption.APPEND), true
      );
      dire("=== Applicateur démarré (pid jeu " + pid + ")");

      try {
         ProcessHandle.of(pid).ifPresent(p -> {
            dire("Attente de la fermeture de Minecraft...");
            p.onExit().join();
         });
         Thread.sleep(1500L);
         if (Files.exists(enAttente)) {
            List<String> lignes = Files.readAllLines(enAttente, StandardCharsets.UTF_8);
            List<String> jars = new ArrayList<>();
            List<String[]> deplacements = new ArrayList<>();
            List<String[]> restaurations = new ArrayList<>();

            for (String l : lignes) {
               l = l.strip();
               if (l.startsWith("activer=")) {
                  jars.add(l.substring(8).strip());
               } else if (l.startsWith("deplacer=")) {
                  deplacements.add(l.substring(9).split("\\|", 2));
               } else if (l.startsWith("restaurer=")) {
                  restaurations.add(l.substring(10).split("\\|", 2));
               }
            }

            reecrireJar(jar, jars);

            for (String[] d : deplacements) {
               deplacer(Paths.get(d[0]), Paths.get(d[1]));
            }

            for (String[] r : restaurations) {
               restaurer(Paths.get(r[0]), Paths.get(r[1]));
            }

            Files.deleteIfExists(enAttente);
            Files.writeString(
               dossier.resolve("dernier-resultat.txt"), "OK " + LocalDateTime.now() + " : " + jars.size() + " mods actifs", StandardCharsets.UTF_8
            );
            dire("Terminé avec succès.");
            return;
         }

         dire("Rien en attente, fin.");
      } catch (Exception e) {
         dire("ERREUR : " + e);
         e.printStackTrace(journal);
         Files.writeString(dossier.resolve("dernier-resultat.txt"), "ERREUR " + LocalDateTime.now() + " : " + e, StandardCharsets.UTF_8);
         throw e;
      } finally {
         journal.close();
      }
   }

   static void dire(String msg) {
      String ligne = LocalTime.now().withNano(0) + "  " + msg;
      System.out.println(ligne);
      if (journal != null) {
         journal.println(ligne);
      }
   }

   static void reecrireJar(Path jar, List<String> fichiers) throws IOException, InterruptedException {
      StringBuilder sb = new StringBuilder("\"jars\": [");

      for (int i = 0; i < fichiers.size(); i++) {
         if (i > 0) {
            sb.append(',');
         }

         sb.append("\n    {\"file\": \"META-INF/jars/").append(fichiers.get(i).replace("\"", "")).append("\"}");
      }

      sb.append("\n  ]");
      Path temp = jar.resolveSibling(jar.getFileName() + ".nouveau");
      boolean trouve = false;
      ZipInputStream in = new ZipInputStream(new BufferedInputStream(Files.newInputStream(jar)));

      ZipEntry e;
      try (ZipOutputStream out = new ZipOutputStream(new BufferedOutputStream(Files.newOutputStream(temp)))) {
         for (; (e = in.getNextEntry()) != null; in.closeEntry()) {
            ZipEntry sortie = new ZipEntry(e.getName());
            if (e.getName().equals("fabric.mod.json")) {
               String json = new String(in.readAllBytes(), StandardCharsets.UTF_8);
               Matcher m = JARS.matcher(json);
               if (!m.find()) {
                  throw new IOException("Champ \"jars\" introuvable dans fabric.mod.json");
               }

               json = m.replaceFirst(Matcher.quoteReplacement(sb.toString()));
               out.putNextEntry(sortie);
               out.write(json.getBytes(StandardCharsets.UTF_8));
               out.closeEntry();
               trouve = true;
            } else {
               out.putNextEntry(sortie);
               in.transferTo(out);
               out.closeEntry();
            }
         }
      } catch (Throwable var15) {
         try {
            in.close();
         } catch (Throwable var11) {
            var15.addSuppressed(var11);
         }

         throw var15;
      }

      in.close();
      if (!trouve) {
         Files.deleteIfExists(temp);
         throw new IOException("fabric.mod.json absent du jar " + jar);
      }

      IOException derniere = null;

      for (int essai = 0; essai < 40; essai++) {
         try {
            Files.move(temp, jar, StandardCopyOption.REPLACE_EXISTING);
            dire("Jar réécrit : " + jar.getFileName() + " (" + fichiers.size() + " mods imbriqués actifs)");
            return;
         } catch (IOException ex) {
            derniere = ex;
            Thread.sleep(1500L);
         }
      }

      throw new IOException("Impossible de remplacer " + jar + " : " + derniere, derniere);
   }

   static void deplacer(Path src, Path dst) {
      try {
         if (!Files.exists(src)) {
            dire("Ignoré (absent) : " + src);
            return;
         }

         Files.createDirectories(dst.getParent());
         if (Files.exists(dst)) {
            dst = dst.resolveSibling(dst.getFileName() + ".ancien-" + System.currentTimeMillis());
         }

         Files.move(src, dst);
         dire("Mis de côté : " + src + " -> " + dst);
      } catch (IOException e) {
         dire("Échec du déplacement " + src + " : " + e);
      }
   }

   static void restaurer(Path srcDir, Path dstDir) {
      if (Files.isDirectory(srcDir)) {
         try (Stream<Path> flux = Files.walk(srcDir)) {
            for (Path p : (Iterable<Path>) flux.sorted()::iterator) {
               if (!Files.isDirectory(p)) {
                  Path rel = srcDir.relativize(p);
                  Path cible = dstDir.resolve(rel);
                  Files.createDirectories(cible.getParent());
                  if (Files.exists(cible)) {
                     cible = cible.resolveSibling(cible.getFileName() + ".restaure-" + System.currentTimeMillis());
                  }

                  Files.move(p, cible);
                  dire("Restauré : " + rel + " -> " + cible);
               }
            }
         } catch (IOException e) {
            dire("Échec de la restauration depuis " + srcDir + " : " + e);
            return;
         }

         try (Stream<Path> flux = Files.walk(srcDir)) {
            for (Path p : (Iterable<Path>) flux.sorted((a, b) -> b.getNameCount() - a.getNameCount())::iterator) {
               if (Files.isDirectory(p)) {
                  try (Stream<Path> contenu = Files.list(p)) {
                     if (contenu.findAny().isEmpty()) {
                        Files.delete(p);
                     }
                  }
               }
            }
         } catch (IOException var13) {
         }
      }
   }
}
