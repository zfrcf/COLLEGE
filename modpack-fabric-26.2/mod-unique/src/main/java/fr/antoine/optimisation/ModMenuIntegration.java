package fr.antoine.optimisation;

import com.terraformersmc.modmenu.api.ConfigScreenFactory;
import com.terraformersmc.modmenu.api.ModMenuApi;

/** Ajoute le bouton « Configurer » dans Mod Menu pour ouvrir l'écran des mods du pack. */
public final class ModMenuIntegration implements ModMenuApi {
    @Override
    public ConfigScreenFactory<?> getModConfigScreenFactory() {
        return EcranConfig::creer;
    }
}
