#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestionnaire du pack « Optimisation Fabric 26.2 »
==================================================

Un seul fichier, aucune dépendance externe (Python 3.9+).

- Installe / met à jour tous les mods du catalogue (Modrinth + mods personnels).
- Active / désactive les mods en tenant compte des bibliothèques :
    * désactiver une bibliothèque propose de désactiver les mods qui en dépendent ;
    * activer un mod réactive (ou installe) les bibliothèques qu'il requiert.
- Gère les fichiers associés (schematics, shaderpacks, config/...) :
    * ils sont listés pour chaque mod ;
    * option « mettre de côté » : déplacés dans gestionnaire-mods/mis-de-cote/<mod>/
      à la désactivation, restaurés automatiquement à la réactivation.
- Profils (jeux de mods actifs) sauvegardables / rechargeables.
- Export du pack au format .mrpack (Modrinth App, Prism Launcher...).

Lancement :  python gestionnaire.py            -> interface graphique (si tkinter)
             python gestionnaire.py --aide     -> ligne de commande
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import platform
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Set

VERSION_OUTIL = "1.0.0"
RACINE = Path(__file__).resolve().parent
CHEMIN_CATALOGUE = RACINE / "catalogue.json"
CHEMIN_VERROU = RACINE / "verrou.json"
DOSSIER_MODS_PERSO = RACINE / "mods-perso"
CHEMIN_CONFIG_UTILISATEUR = Path.home() / ".gestionnaire-mods-26.2.json"

API_MODRINTH = "https://api.modrinth.com/v2"
META_FABRIC = "https://meta.fabricmc.net/v2"
USER_AGENT = f"gestionnaire-optimisation-fabric/{VERSION_OUTIL} (github.com/zfrcf/college)"

SUFFIXE_ACTIF = ".jar"
SUFFIXE_INACTIF = ".jar.disabled"
IDS_IGNORES = {"minecraft", "java", "fabricloader", "fabric-loader"}

Progression = Optional[Callable[[str], None]]


class ErreurGestion(Exception):
    """Erreur attendue, affichée proprement à l'utilisateur."""


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def normaliser_id(texte: str) -> str:
    return re.sub(r"[^a-z0-9]", "", texte.lower())


def charger_json(chemin: Path, defaut=None):
    try:
        with open(chemin, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return defaut
    except json.JSONDecodeError as e:
        raise ErreurGestion(f"Fichier JSON invalide : {chemin} ({e})")


def ecrire_json(chemin: Path, donnees) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2)
        f.write("\n")


def requete_json(url: str, tentatives: int = 3):
    derniere = None
    for essai in range(tentatives):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=40) as rep:
                return json.load(rep)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise ErreurGestion(f"Introuvable sur Modrinth : {url}")
            derniere = e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            derniere = e
        time.sleep(1.5 * (essai + 1))
    raise ErreurGestion(f"Connexion impossible ({derniere}) : {url}")


def telecharger(url: str, destination: Path, sha512: Optional[str] = None,
                tentatives: int = 3) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    derniere = None
    for essai in range(tentatives):
        tmp = destination.with_suffix(destination.suffix + ".part")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            h = hashlib.sha512()
            with urllib.request.urlopen(req, timeout=60) as rep, open(tmp, "wb") as f:
                while True:
                    bloc = rep.read(1 << 16)
                    if not bloc:
                        break
                    f.write(bloc)
                    h.update(bloc)
            if sha512 and h.hexdigest() != sha512:
                raise ErreurGestion("empreinte SHA-512 incorrecte")
            os.replace(tmp, destination)
            return
        except Exception as e:  # noqa: BLE001
            derniere = e
            if tmp.exists():
                tmp.unlink()
            time.sleep(1.5 * (essai + 1))
    raise ErreurGestion(f"Téléchargement échoué ({derniere}) : {url}")


def empreintes(chemin: Path) -> Dict[str, str]:
    h1, h512 = hashlib.sha1(), hashlib.sha512()
    with open(chemin, "rb") as f:
        while True:
            bloc = f.read(1 << 16)
            if not bloc:
                break
            h1.update(bloc)
            h512.update(bloc)
    return {"sha1": h1.hexdigest(), "sha512": h512.hexdigest()}


def ouvrir_dans_explorateur(chemin: Path) -> None:
    systeme = platform.system()
    try:
        if systeme == "Windows":
            os.startfile(str(chemin))  # type: ignore[attr-defined]
        elif systeme == "Darwin":
            subprocess.Popen(["open", str(chemin)])
        else:
            subprocess.Popen(["xdg-open", str(chemin)])
    except Exception as e:  # noqa: BLE001
        raise ErreurGestion(f"Impossible d'ouvrir le dossier : {e}")


def detecter_dossier_minecraft() -> Optional[Path]:
    systeme = platform.system()
    candidats: List[Path] = []
    if systeme == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            candidats.append(Path(appdata) / ".minecraft")
    elif systeme == "Darwin":
        candidats.append(Path.home() / "Library" / "Application Support" / "minecraft")
    else:
        candidats.append(Path.home() / ".minecraft")
        candidats.append(Path.home() / ".var/app/com.mojang.Minecraft/.minecraft")
    for c in candidats:
        if c.is_dir():
            return c
    return None


# ---------------------------------------------------------------------------
# Versions sémantiques (sous-ensemble de ce que comprend Fabric Loader)
# ---------------------------------------------------------------------------

class VersionSem:
    """Version du type 1.2.3-beta.4+meta ; comparaison façon semver / Fabric."""

    def __init__(self, texte: str):
        self.texte = texte
        corps = texte.split("+", 1)[0]
        if "-" in corps:
            corps, pre = corps.split("-", 1)
            self.prerelease: Optional[str] = pre  # "" = plus petite pré-version possible
        else:
            self.prerelease = None
        self.composants: List[int] = []
        self.joker = False
        for c in corps.split("."):
            if c in ("x", "X", "*"):
                self.joker = True
                break
            if not c.isdigit():
                raise ValueError(texte)
            self.composants.append(int(c))
        if not self.composants:
            raise ValueError(texte)

    def _cle_pre(self):
        if self.prerelease is None:
            return (1,)
        parties = []
        for p in self.prerelease.split("."):
            parties.append((0, int(p), "") if p.isdigit() else (1, 0, p))
        return (0, tuple(parties))

    def comparer(self, autre: "VersionSem") -> int:
        n = max(len(self.composants), len(autre.composants))
        a = self.composants + [0] * (n - len(self.composants))
        b = autre.composants + [0] * (n - len(autre.composants))
        if a != b:
            return -1 if a < b else 1
        pa, pb = self._cle_pre(), autre._cle_pre()
        if pa == pb:
            return 0
        return -1 if pa < pb else 1

    def borne_sup(self, niveau: int) -> "VersionSem":
        """Version juste au-dessus en incrémentant le composant `niveau` (0 = majeur)."""
        comp = self.composants[: niveau + 1] + [0] * max(0, niveau + 1 - len(self.composants))
        comp[niveau] += 1
        v = VersionSem(".".join(map(str, comp)) + "-")
        return v


def _predicat_ok(version: VersionSem, pred: str) -> bool:
    pred = pred.strip()
    if pred in ("*", ""):
        return True
    m = re.match(r"^(>=|<=|>|<|=|~|\^)?\s*(.+)$", pred)
    op, cible_txt = m.group(1) or "=", m.group(2).strip()
    cible = VersionSem(cible_txt)
    if cible.joker:  # 26.2.* / 26.2.x  →  ~26.2
        op, cible = "~", VersionSem(".".join(map(str, cible.composants)))
    c = version.comparer(cible)
    if op == ">=":
        return c >= 0
    if op == "<=":
        return c <= 0
    if op == ">":
        return c > 0
    if op == "<":
        return c < 0
    if op == "=":
        return c == 0
    if op == "~":
        niveau = 1 if len(cible.composants) >= 2 else 0
        return c >= 0 and version.comparer(cible.borne_sup(niveau)) < 0
    if op == "^":
        niveau = 0
        if cible.composants[0] == 0 and len(cible.composants) > 1:
            niveau = 1
        return c >= 0 and version.comparer(cible.borne_sup(niveau)) < 0
    return True


def contrainte_satisfaite(version_txt: str, contrainte) -> bool:
    """Vrai si `version_txt` respecte `contrainte` ("*", ">=1.2", "<0.9.0-", "~26.2", liste = OU).
    En cas de syntaxe inconnue, on considère la contrainte satisfaite (prudence)."""
    if contrainte is None:
        return True
    if isinstance(contrainte, list):
        return any(contrainte_satisfaite(version_txt, c) for c in contrainte) if contrainte else True
    contrainte = str(contrainte).strip()
    if contrainte in ("*", ""):
        return True
    try:
        version = VersionSem(version_txt)
        for alternative in contrainte.split("||"):
            preds = alternative.split()
            if all(_predicat_ok(version, p) for p in preds):
                return True
        return False
    except (ValueError, AttributeError):
        return True


# ---------------------------------------------------------------------------
# Lecture des jars Fabric
# ---------------------------------------------------------------------------

@dataclass
class MetaJar:
    id: str
    nom: str
    version: str
    depends: Dict[str, object]
    breaks: Dict[str, object]
    fournit: Dict[str, str]   # id fourni -> version (modules imbriqués inclus)
    environnement: str
    description: str = ""


def _fournit(valeur, ident: str, version: str) -> Dict[str, str]:
    if isinstance(valeur, dict):
        return {str(k): str(v) for k, v in valeur.items()}
    if isinstance(valeur, list):
        return {str(k): version for k in valeur}
    return {ident: version}


def _contraintes(valeur) -> Dict[str, object]:
    if isinstance(valeur, dict):
        return {str(k): v for k, v in valeur.items()}
    if isinstance(valeur, list):
        return {str(v): "*" for v in valeur}
    return {}


def _lire_zip(z: zipfile.ZipFile) -> Optional[MetaJar]:
    try:
        brut = z.read("fabric.mod.json").decode("utf-8", errors="replace")
    except KeyError:
        return None
    meta = json.loads(brut, strict=False)
    if isinstance(meta, list):  # ancien format (liste)
        meta = meta[0]
    version = str(meta.get("version", "?"))
    fournit: Dict[str, str] = {meta["id"]: version}
    for p in meta.get("provides", []) or []:
        fournit.setdefault(str(p), version)
    depends = _contraintes(meta.get("depends"))
    breaks = _contraintes(meta.get("breaks"))
    for imbrique in meta.get("jars", []) or []:
        try:
            with zipfile.ZipFile(io.BytesIO(z.read(imbrique["file"]))) as nz:
                sous = _lire_zip(nz)
        except (KeyError, zipfile.BadZipFile):
            sous = None
        if sous:
            for ident, ver in sous.fournit.items():
                fournit.setdefault(ident, ver)
    return MetaJar(
        id=meta["id"],
        nom=meta.get("name") or meta["id"],
        version=version,
        depends={d: c for d, c in depends.items() if d not in IDS_IGNORES},
        breaks=breaks,
        fournit=fournit,
        environnement=str(meta.get("environment", "*")),
        description=str(meta.get("description", "") or ""),
    )


def lire_meta_jar(chemin: Path) -> Optional[MetaJar]:
    try:
        with zipfile.ZipFile(chemin) as z:
            return _lire_zip(z)
    except (zipfile.BadZipFile, OSError, KeyError, json.JSONDecodeError):
        return None


# ---------------------------------------------------------------------------
# Modèle
# ---------------------------------------------------------------------------

@dataclass
class EntreeCatalogue:
    id: str
    nom: str
    categorie: str
    description: str = ""
    modrinth: Optional[str] = None
    fichier: Optional[str] = None
    bibliotheque: bool = False
    par_defaut: bool = True
    prerelease: bool = False
    fichiers: List[str] = field(default_factory=list)

    @staticmethod
    def depuis(d: dict) -> "EntreeCatalogue":
        return EntreeCatalogue(
            id=d["id"], nom=d.get("nom", d["id"]), categorie=d.get("categorie", "autre"),
            description=d.get("description", ""), modrinth=d.get("modrinth"),
            fichier=d.get("fichier"), bibliotheque=bool(d.get("bibliotheque", False)),
            par_defaut=bool(d.get("par_defaut", True)), prerelease=bool(d.get("prerelease", False)),
            fichiers=list(d.get("fichiers", [])),
        )


@dataclass
class Mod:
    """Un mod tel que vu par le gestionnaire : installé (jar) et/ou connu du catalogue."""
    id: str
    nom: str
    version: str = ""
    chemin: Optional[Path] = None          # jar présent dans mods/ (actif ou non)
    actif: bool = False
    depends: Dict[str, object] = field(default_factory=dict)
    breaks: Dict[str, object] = field(default_factory=dict)
    fournit: Dict[str, str] = field(default_factory=dict)
    environnement: str = "*"
    catalogue: Optional[EntreeCatalogue] = None
    verrou: Optional[dict] = None

    @property
    def installe(self) -> bool:
        return self.chemin is not None

    @property
    def categorie(self) -> str:
        return self.catalogue.categorie if self.catalogue else "autre"

    @property
    def bibliotheque(self) -> bool:
        if self.catalogue:
            return self.catalogue.bibliotheque
        return bool(self.verrou and self.verrou.get("auto"))

    @property
    def description(self) -> str:
        if self.catalogue and self.catalogue.description:
            return self.catalogue.description
        return (self.verrou or {}).get("description", "")

    @property
    def etat(self) -> str:
        if not self.installe:
            return "Non installé"
        return "Actif" if self.actif else "Désactivé"


@dataclass
class Plan:
    activer: List[Mod] = field(default_factory=list)
    desactiver: List[Mod] = field(default_factory=list)
    installer: List[str] = field(default_factory=list)   # ids à installer (catalogue/verrou)
    manquants: List[str] = field(default_factory=list)   # ids requis mais inconnus
    avertissements: List[str] = field(default_factory=list)

    @property
    def vide(self) -> bool:
        return not (self.activer or self.desactiver or self.installer)

    def resume(self) -> str:
        lignes = []
        if self.activer:
            lignes.append("À activer : " + ", ".join(m.nom for m in self.activer))
        if self.desactiver:
            lignes.append("À désactiver : " + ", ".join(m.nom for m in self.desactiver))
        if self.installer:
            lignes.append("À installer (téléchargement) : " + ", ".join(self.installer))
        if self.manquants:
            lignes.append("Dépendances introuvables : " + ", ".join(self.manquants))
        lignes.extend(self.avertissements)
        return "\n".join(lignes) if lignes else "Rien à faire."


# ---------------------------------------------------------------------------
# Gestionnaire
# ---------------------------------------------------------------------------

class Gestionnaire:
    def __init__(self, dossier_minecraft: Path):
        self.dossier = Path(dossier_minecraft)
        self.dossier_mods = self.dossier / "mods"
        self.dossier_gestion = self.dossier / "gestionnaire-mods"
        self.dossier_mis_de_cote = self.dossier_gestion / "mis-de-cote"
        self.dossier_profils = self.dossier_gestion / "profils"
        self.journal_chemin = self.dossier_gestion / "journal.log"
        brut = charger_json(CHEMIN_CATALOGUE)
        if not brut:
            raise ErreurGestion(f"Catalogue introuvable : {CHEMIN_CATALOGUE}")
        self.catalogue_brut = brut
        self.catalogue: Dict[str, EntreeCatalogue] = {
            e["id"]: EntreeCatalogue.depuis(e) for e in brut["mods"]
        }
        self.categories: Dict[str, str] = brut.get("categories", {})
        self.verrou: dict = charger_json(CHEMIN_VERROU, {"mods": {}}) or {"mods": {}}
        self.mods: Dict[str, Mod] = {}
        self.scanner()

    # -- journal -----------------------------------------------------------
    def journal(self, message: str) -> None:
        try:
            self.dossier_gestion.mkdir(parents=True, exist_ok=True)
            with open(self.journal_chemin, "a", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S") + "  " + message + "\n")
        except OSError:
            pass

    # -- analyse du dossier mods ------------------------------------------
    def scanner(self) -> Dict[str, Mod]:
        mods: Dict[str, Mod] = {}
        alias: Dict[str, str] = {}  # id normalisé -> id catalogue
        for ident, e in self.catalogue.items():
            alias[normaliser_id(ident)] = ident
            if e.modrinth:
                alias.setdefault(normaliser_id(e.modrinth), ident)
        for ident, v in self.verrou.get("mods", {}).items():
            alias.setdefault(normaliser_id(ident), ident)
            if v.get("id_mod"):
                alias.setdefault(normaliser_id(v["id_mod"]), ident)

        if self.dossier_mods.is_dir():
            for chemin in sorted(self.dossier_mods.iterdir()):
                nom = chemin.name
                if nom.endswith(SUFFIXE_INACTIF):
                    actif = False
                elif nom.endswith(SUFFIXE_ACTIF):
                    actif = True
                else:
                    continue
                meta = lire_meta_jar(chemin)
                if meta is None:
                    ident = "fichier:" + nom
                    mod = Mod(id=ident, nom=nom, version="?", chemin=chemin, actif=actif)
                    mods[ident] = mod
                    continue
                ident_cat = alias.get(normaliser_id(meta.id), meta.id)
                mod = Mod(
                    id=ident_cat, nom=meta.nom, version=meta.version, chemin=chemin,
                    actif=actif, depends=meta.depends, breaks=meta.breaks,
                    fournit=meta.fournit, environnement=meta.environnement,
                    catalogue=self.catalogue.get(ident_cat),
                    verrou=self.verrou.get("mods", {}).get(ident_cat),
                )
                if not mod.catalogue and not mod.description:
                    mod.verrou = dict(mod.verrou or {}, description=meta.description)
                if ident_cat in mods:  # doublon (deux versions du même mod)
                    ancien = mods[ident_cat]
                    # on garde l'actif en priorité ; l'autre est signalé en doublon
                    if not ancien.actif and actif:
                        mods["doublon:" + ancien.chemin.name] = ancien
                        mods[ident_cat] = mod
                    else:
                        mods["doublon:" + nom] = mod
                    continue
                mods[ident_cat] = mod

        # entrées du catalogue / verrou non installées
        for ident, e in self.catalogue.items():
            if ident not in mods:
                v = self.verrou.get("mods", {}).get(ident, {})
                mods[ident] = Mod(
                    id=ident, nom=e.nom, version=v.get("version_mod", ""), catalogue=e, verrou=v or None,
                    depends=_contraintes(v.get("depends")), breaks=_contraintes(v.get("breaks")),
                    fournit=_fournit(v.get("fournit"), ident, v.get("version_mod", "")),
                )
        for ident, v in self.verrou.get("mods", {}).items():
            if ident not in mods and v.get("auto"):
                mods[ident] = Mod(
                    id=ident, nom=v.get("nom", ident), version=v.get("version_mod", ""), verrou=v,
                    depends=_contraintes(v.get("depends")), breaks=_contraintes(v.get("breaks")),
                    fournit=_fournit(v.get("fournit"), ident, v.get("version_mod", "")),
                )
        self.mods = mods
        return mods

    # -- graphe de dépendances --------------------------------------------
    def fournisseurs(self, uniquement_actifs: bool = True) -> Dict[str, List[Mod]]:
        table: Dict[str, List[Mod]] = {}
        for m in self.mods.values():
            if not m.installe:
                continue
            if uniquement_actifs and not m.actif:
                continue
            for f in m.fournit:
                table.setdefault(f, []).append(m)
        return table

    def fournisseurs_connus(self) -> Dict[str, List[Mod]]:
        """Tous les mods (installés ou catalogue) capables de fournir un id."""
        table: Dict[str, List[Mod]] = {}
        for m in self.mods.values():
            for f in (m.fournit or {m.id: m.version}):
                table.setdefault(f, []).append(m)
        return table

    @staticmethod
    def satisfait(fournisseur: Mod, ident: str, contrainte) -> bool:
        """`fournisseur` fournit-il `ident` dans une version qui respecte `contrainte` ?"""
        version = fournisseur.fournit.get(ident, fournisseur.version)
        return contrainte_satisfaite(version, contrainte)

    def dependances_manquantes(self, mod: Mod) -> List[str]:
        actifs = self.fournisseurs(True)
        return [d for d, c in mod.depends.items()
                if not any(self.satisfait(f, d, c) for f in actifs.get(d, []))]

    def casse(self, a: Mod, b: Mod) -> bool:
        """Vrai si `a` déclare une incompatibilité (breaks) effective avec la version de `b`."""
        return any(ident in b.fournit and contrainte_satisfaite(b.fournit[ident], c)
                   for ident, c in a.breaks.items())

    def dependants(self, mod: Mod, parmi_actifs: bool = True) -> List[Mod]:
        """Mods (actifs) qui ont besoin de `mod` et pour qui aucun autre actif ne fournit l'id."""
        actifs = self.fournisseurs(True)
        resultat = []
        for autre in self.mods.values():
            if autre is mod or not autre.installe or (parmi_actifs and not autre.actif):
                continue
            for d, c in autre.depends.items():
                if d in mod.fournit:
                    autres = [m for m in actifs.get(d, []) if m is not mod and self.satisfait(m, d, c)]
                    if not autres:
                        resultat.append(autre)
                        break
        return resultat

    def requis_par(self, mod: Mod) -> List[Mod]:
        """Tous les mods installés qui déclarent une dépendance vers `mod` (info)."""
        return [a for a in self.mods.values()
                if a is not mod and a.installe and any(d in mod.fournit for d in a.depends)]

    def plan_desactivation(self, ids: Iterable[str]) -> Plan:
        plan = Plan()
        a_traiter = [self.mods[i] for i in ids if i in self.mods and self.mods[i].installe and self.mods[i].actif]
        vus: Set[str] = set()
        # simulation : on retire progressivement
        etat_actif = {m.id: m.actif for m in self.mods.values() if m.installe}
        file_ = list(a_traiter)
        while file_:
            m = file_.pop(0)
            if m.id in vus:
                continue
            vus.add(m.id)
            plan.desactiver.append(m)
            etat_actif[m.id] = False
            # qui dépendait de lui sans alternative ?
            for autre in self.mods.values():
                if not autre.installe or not etat_actif.get(autre.id) or autre.id in vus:
                    continue
                for d, c in autre.depends.items():
                    if d in m.fournit:
                        alternatives = [x for x in self.mods.values()
                                        if x.installe and etat_actif.get(x.id) and x is not m
                                        and d in x.fournit and self.satisfait(x, d, c)]
                        if not alternatives:
                            file_.append(autre)
                            break
        return plan

    def plan_activation(self, ids: Iterable[str]) -> Plan:
        plan = Plan()
        connus = self.fournisseurs_connus()
        etat_actif = {m.id: m.actif for m in self.mods.values() if m.installe}
        vus: Set[str] = set()
        file_ = [i for i in ids]
        while file_:
            ident = file_.pop(0)
            if ident in vus:
                continue
            vus.add(ident)
            m = self.mods.get(ident)
            if m is None:
                plan.manquants.append(ident)
                continue
            if m.installe:
                if not etat_actif.get(m.id):
                    plan.activer.append(m)
                    etat_actif[m.id] = True
            else:
                if m.catalogue or m.verrou:
                    plan.installer.append(m.id)
                    etat_actif[m.id] = True
                else:
                    plan.manquants.append(m.id)
                    continue
            for d, c in m.depends.items():
                if any(etat_actif.get(x.id) and self.satisfait(x, d, c) for x in connus.get(d, [])):
                    continue
                candidats = [x for x in connus.get(d, []) if self.satisfait(x, d, c)]
                if not candidats:
                    if connus.get(d):
                        plan.avertissements.append(
                            f"Attention : {m.nom} demande « {d} » {c}, version présente trop ancienne.")
                        continue
                    plan.manquants.append(d)
                    continue
                # préférer un mod installé mais désactivé, sinon le catalogue
                candidats.sort(key=lambda x: (not x.installe, not bool(x.catalogue)))
                file_.append(candidats[0].id)
            for b in m.breaks:
                for x in connus.get(b, []):
                    if etat_actif.get(x.id) and self.casse(m, x):
                        plan.avertissements.append(
                            f"Attention : {m.nom} est déclaré incompatible avec {x.nom} {x.version} (actif).")
        return plan

    def verifier(self) -> List[str]:
        """Liste de problèmes dans l'état courant (dépendances manquantes, incompatibilités, doublons)."""
        problemes = []
        actifs = self.fournisseurs(True)
        for m in self.mods.values():
            if not m.installe or not m.actif:
                continue
            for d, c in m.depends.items():
                fournisseurs = actifs.get(d, [])
                if not fournisseurs:
                    inactif = [x for x in self.mods.values() if x.installe and not x.actif and d in x.fournit]
                    if inactif:
                        problemes.append(f"{m.nom} a besoin de « {d} » qui est désactivé ({inactif[0].nom}).")
                    else:
                        problemes.append(f"{m.nom} a besoin de « {d} » qui n'est pas installé.")
                elif not any(self.satisfait(f, d, c) for f in fournisseurs):
                    problemes.append(f"{m.nom} demande « {d} » {c}, mais la version installée est "
                                     f"{fournisseurs[0].fournit.get(d, fournisseurs[0].version)} ({fournisseurs[0].nom}).")
            for b in m.breaks:
                for x in actifs.get(b, []):
                    if self.casse(m, x):
                        problemes.append(f"{m.nom} est incompatible avec {x.nom} {x.version} (tous deux actifs).")
            if m.environnement == "server":
                problemes.append(f"{m.nom} est un mod serveur uniquement.")
        for ident, m in self.mods.items():
            if ident.startswith("doublon:"):
                problemes.append(f"Doublon : {m.chemin.name} (une autre version du même mod est présente).")
            if ident.startswith("fichier:"):
                problemes.append(f"{m.nom} n'est pas un mod Fabric lisible (fabric.mod.json absent).")
        return problemes

    # -- fichiers associés ---------------------------------------------------
    def fichiers_associes(self, mod: Mod) -> List[Path]:
        """Chemins (relatifs au dossier Minecraft) existants liés au mod."""
        rel: List[str] = []
        if mod.catalogue:
            rel.extend(mod.catalogue.fichiers)
        ids = {normaliser_id(mod.id)} | {normaliser_id(f) for f in mod.fournit}
        ids.discard("")
        dossier_config = self.dossier / "config"
        if dossier_config.is_dir():
            for enfant in dossier_config.iterdir():
                base = enfant.name.split(".")[0]
                base = re.sub(r"(-|_)?(client|common|server)$", "", base)
                if normaliser_id(base) in ids:
                    rel.append("config/" + enfant.name)
        racine_mod = self.dossier / mod.id
        if racine_mod.is_dir() and mod.id not in ("mods", "config", "saves"):
            rel.append(mod.id)
        resultat: List[Path] = []
        vus = set()
        for r in rel:
            p = Path(r)
            if str(p) in vus:
                continue
            vus.add(str(p))
            if (self.dossier / p).exists():
                resultat.append(p)
        return resultat

    def fichiers_mis_de_cote(self, mod: Mod) -> List[Path]:
        d = self.dossier_mis_de_cote / mod.id
        if not d.is_dir():
            return []
        return [p.relative_to(d) for p in sorted(d.iterdir())]

    def _fichiers_partages(self, mod: Mod, exclus: Set[str]) -> Set[str]:
        """Fichiers associés à `mod` également réclamés par un autre mod actif (non désactivé)."""
        partages = set()
        for autre in self.mods.values():
            if autre is mod or not autre.installe or not autre.actif or autre.id in exclus:
                continue
            for p in self.fichiers_associes(autre):
                partages.add(str(p))
        return partages

    def mettre_de_cote(self, mod: Mod, exclus: Set[str]) -> List[str]:
        deplaces = []
        partages = self._fichiers_partages(mod, exclus)
        for rel in self.fichiers_associes(mod):
            if str(rel) in partages:
                continue
            src = self.dossier / rel
            dst = self.dossier_mis_de_cote / mod.id / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                # fusion : on déplace le contenu
                if src.is_dir() and dst.is_dir():
                    for enfant in src.iterdir():
                        cible = dst / enfant.name
                        if cible.exists():
                            cible = dst / f"{enfant.name}.ancien-{int(time.time())}"
                        shutil.move(str(enfant), str(cible))
                    shutil.rmtree(src, ignore_errors=True)
                else:
                    dst = dst.with_name(f"{dst.name}.ancien-{int(time.time())}")
                    shutil.move(str(src), str(dst))
            else:
                shutil.move(str(src), str(dst))
            deplaces.append(str(rel))
        return deplaces

    def restaurer(self, mod: Mod) -> List[str]:
        base = self.dossier_mis_de_cote / mod.id
        if not base.is_dir():
            return []
        restaures = []
        for src in sorted(base.rglob("*")):
            if src.is_dir():
                continue
            rel = src.relative_to(base)
            dst = self.dossier / rel
            if dst.exists():
                dst = dst.with_name(f"{dst.name}.restaure-{int(time.time())}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            restaures.append(str(rel))
        shutil.rmtree(base, ignore_errors=True)
        return restaures

    # -- application d'un plan -----------------------------------------------
    def appliquer(self, plan: Plan, mettre_de_cote: bool = False,
                  progression: Progression = None) -> List[str]:
        def dire(msg: str) -> None:
            self.journal(msg)
            if progression:
                progression(msg)

        messages: List[str] = []
        if plan.installer:
            self.installer(plan.installer, progression=progression)
            self.scanner()
            # les mods fraîchement installés sont actifs ; on recalcule ce qui reste à activer
            plan.activer = [self.mods[m.id] for m in plan.activer if m.id in self.mods]
        exclus = {m.id for m in plan.desactiver}
        for m in plan.desactiver:
            if not m.chemin or not m.actif:
                continue
            nouveau = m.chemin.with_name(m.chemin.name[: -len(SUFFIXE_ACTIF)] + SUFFIXE_INACTIF)
            os.replace(m.chemin, nouveau)
            m.chemin, m.actif = nouveau, False
            msg = f"Désactivé : {m.nom}"
            if mettre_de_cote:
                deplaces = self.mettre_de_cote(m, exclus)
                if deplaces:
                    msg += " (mis de côté : " + ", ".join(deplaces) + ")"
            dire(msg)
            messages.append(msg)
        for m in plan.activer:
            if not m.chemin or m.actif:
                continue
            nouveau = m.chemin.with_name(m.chemin.name[: -len(SUFFIXE_INACTIF)] + SUFFIXE_ACTIF)
            os.replace(m.chemin, nouveau)
            m.chemin, m.actif = nouveau, True
            msg = f"Activé : {m.nom}"
            restaures = self.restaurer(m)
            if restaures:
                msg += " (fichiers restaurés : " + ", ".join(restaures) + ")"
            dire(msg)
            messages.append(msg)
        for ident in plan.installer:
            m = self.mods.get(ident)
            if m and m.installe:
                restaures = self.restaurer(m)
                if restaures:
                    messages.append(f"Fichiers restaurés pour {m.nom} : " + ", ".join(restaures))
        self.scanner()
        return messages

    # -- Modrinth ---------------------------------------------------------------
    def _version_minecraft(self) -> str:
        return self.catalogue_brut.get("minecraft", "26.2")

    def resoudre_modrinth(self, slug: str, prerelease: bool = False) -> dict:
        q = urllib.parse.urlencode({
            "loaders": '["fabric"]',
            "game_versions": json.dumps([self._version_minecraft()]),
        })
        versions = requete_json(f"{API_MODRINTH}/project/{slug}/version?{q}")
        if not versions:
            raise ErreurGestion(f"Aucune version Fabric {self._version_minecraft()} pour « {slug} ».")
        stables = [v for v in versions if v["version_type"] == "release"]
        if stables:
            v = stables[0]
        elif prerelease:
            v = versions[0]
        else:
            v = versions[0]
        fichier = next((f for f in v["files"] if f.get("primary")), v["files"][0])
        return {
            "slug": slug,
            "projet_id": v["project_id"],
            "version_id": v["id"],
            "version": v["version_number"],
            "type": v["version_type"],
            "date": v["date_published"],
            "fichier": fichier["filename"],
            "url": fichier["url"],
            "sha1": fichier["hashes"].get("sha1"),
            "sha512": fichier["hashes"].get("sha512"),
            "taille": fichier.get("size"),
            "dependances_requises": [d["project_id"] for d in v.get("dependencies", [])
                                     if d.get("dependency_type") == "required" and d.get("project_id")],
        }

    def _enrichir_depuis_jar(self, entree: dict, chemin: Path) -> None:
        meta = lire_meta_jar(chemin)
        if meta:
            entree.update({
                "id_mod": meta.id, "nom": meta.nom, "version_mod": meta.version,
                "depends": meta.depends, "breaks": meta.breaks,
                "fournit": dict(sorted(meta.fournit.items())), "environnement": meta.environnement,
                "description": meta.description,
            })

    def generer_verrou(self, progression: Progression = None, cache: Optional[Path] = None) -> dict:
        """Résout toutes les versions du catalogue (+ dépendances requises) et écrit verrou.json."""
        def dire(msg: str) -> None:
            if progression:
                progression(msg)

        cache = cache or (RACINE / ".cache")
        cache.mkdir(parents=True, exist_ok=True)
        verrou: dict = {
            "genere_le": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "minecraft": self._version_minecraft(),
            "fabric_loader": None,
            "mods": {},
        }
        try:
            chargeurs = requete_json(f"{META_FABRIC}/versions/loader/{self._version_minecraft()}")
            stables = [c for c in chargeurs if c["loader"].get("stable", True)]
            verrou["fabric_loader"] = (stables or chargeurs)[0]["loader"]["version"]
        except Exception as e:  # noqa: BLE001
            dire(f"Avertissement : version Fabric Loader non résolue ({e})")

        projets_vus: Dict[str, str] = {}  # projet_id -> id d'entrée
        a_resoudre: List[tuple] = []
        for ident, e in self.catalogue.items():
            if e.modrinth:
                a_resoudre.append((ident, e.modrinth, e.prerelease, False))
        while a_resoudre:
            ident, slug, prerelease, auto = a_resoudre.pop(0)
            dire(f"Résolution : {slug}")
            entree = self.resoudre_modrinth(slug, prerelease)
            entree["auto"] = auto
            projet = requete_json(f"{API_MODRINTH}/project/{entree['projet_id']}")
            entree["client"] = projet.get("client_side", "required")
            entree["serveur"] = projet.get("server_side", "optional")
            entree["titre"] = projet.get("title", slug)
            local = cache / entree["fichier"]
            if not local.exists() or empreintes(local)["sha512"] != entree["sha512"]:
                dire(f"Téléchargement : {entree['fichier']}")
                telecharger(entree["url"], local, entree["sha512"])
            self._enrichir_depuis_jar(entree, local)
            verrou["mods"][ident] = entree
            projets_vus[entree["projet_id"]] = ident
            for pid in entree["dependances_requises"]:
                if pid in projets_vus or any(x[1] == pid for x in a_resoudre):
                    continue
                # cette dépendance est-elle déjà dans le catalogue ?
                deja = next((i for i, c in self.catalogue.items() if c.modrinth and
                             normaliser_id(c.modrinth) == normaliser_id(pid)), None)
                if deja:
                    continue
                proj = requete_json(f"{API_MODRINTH}/project/{pid}")
                slug_dep = proj["slug"]
                if any(c.modrinth == slug_dep for c in self.catalogue.values()):
                    continue
                a_resoudre.append((slug_dep, slug_dep, False, True))
        ecrire_json(CHEMIN_VERROU, verrou)
        self.verrou = verrou
        self.scanner()
        return verrou

    # -- installation -----------------------------------------------------------
    def ids_par_defaut(self) -> List[str]:
        return [i for i, e in self.catalogue.items() if e.par_defaut]

    def _retirer_anciennes_versions(self, id_mod: str, garder: Path) -> List[str]:
        retires = []
        for chemin in list(self.dossier_mods.iterdir()):
            if chemin == garder or not (chemin.name.endswith(SUFFIXE_ACTIF) or chemin.name.endswith(SUFFIXE_INACTIF)):
                continue
            meta = lire_meta_jar(chemin)
            if meta and normaliser_id(meta.id) == normaliser_id(id_mod):
                chemin.unlink()
                retires.append(chemin.name)
        return retires

    def installer(self, ids: Optional[Iterable[str]] = None, mise_a_jour: bool = False,
                  progression: Progression = None) -> List[str]:
        """Installe (ou met à jour) les mods demandés. Retourne les messages."""
        def dire(msg: str) -> None:
            self.journal(msg)
            if progression:
                progression(msg)

        self.dossier_mods.mkdir(parents=True, exist_ok=True)
        ids = list(ids) if ids is not None else self.ids_par_defaut()
        # inclure les dépendances requises connues (catalogue / verrou)
        connus = self.fournisseurs_connus()
        file_ = list(ids)
        vus: Set[str] = set()
        ordre: List[str] = []
        while file_:
            i = file_.pop(0)
            if i in vus:
                continue
            vus.add(i)
            ordre.append(i)
            m = self.mods.get(i)
            deps = dict(m.depends) if m else _contraintes(self.verrou.get("mods", {}).get(i, {}).get("depends"))
            for d, contrainte in deps.items():
                candidats = [c for c in connus.get(d, []) if (c.catalogue or c.verrou) and self.satisfait(c, d, contrainte)]
                if not candidats or any(c.id in vus or c.id in file_ for c in candidats):
                    continue
                # préférer un mod déjà installé, puis une entrée du catalogue
                candidats.sort(key=lambda c: (not c.installe, not bool(c.catalogue)))
                file_.append(candidats[0].id)

        messages: List[str] = []
        verrou_modifie = False
        for ident in ordre:
            e = self.catalogue.get(ident)
            v = self.verrou.get("mods", {}).get(ident)
            existant = self.mods.get(ident)
            etait_inactif = bool(existant and existant.installe and not existant.actif)
            if e and e.fichier:  # mod personnel fourni dans mods-perso/
                src = DOSSIER_MODS_PERSO / e.fichier
                if not src.exists():
                    messages.append(f"Fichier personnel introuvable : {src}")
                    continue
                dst = self.dossier_mods / (e.fichier + ("" if not etait_inactif else ".disabled"))
                if existant and existant.installe and existant.chemin.name.startswith(e.fichier):
                    if empreintes(existant.chemin)["sha512"] == empreintes(src)["sha512"]:
                        continue
                shutil.copy2(src, dst)
                meta = lire_meta_jar(src)
                if meta:
                    self._retirer_anciennes_versions(meta.id, dst)
                dire(f"Installé (perso) : {e.nom}")
                messages.append(f"Installé : {e.nom}")
                continue
            slug = (e.modrinth if e else None) or (v or {}).get("slug")
            if not slug:
                messages.append(f"Aucune source connue pour « {ident} ».")
                continue
            if mise_a_jour or not v:
                dire(f"Recherche de la dernière version : {slug}")
                try:
                    nv = self.resoudre_modrinth(slug, e.prerelease if e else False)
                except ErreurGestion as err:
                    messages.append(str(err))
                    continue
                if v:
                    nv.update({k: v[k] for k in ("auto", "client", "serveur", "titre") if k in v})
                v = nv
                verrou_modifie = True
            if existant and existant.installe and existant.chemin.name.startswith(v["fichier"]):
                if v.get("sha512") and empreintes(existant.chemin)["sha512"] == v["sha512"]:
                    continue
            dst = self.dossier_mods / (v["fichier"] + ("" if not etait_inactif else ".disabled"))
            dire(f"Téléchargement : {v['fichier']}")
            telecharger(v["url"], dst, v.get("sha512"))
            if verrou_modifie:
                self._enrichir_depuis_jar(v, dst)
                self.verrou.setdefault("mods", {})[ident] = v
            meta = lire_meta_jar(dst)
            if meta:
                retires = self._retirer_anciennes_versions(meta.id, dst)
                if retires:
                    messages.append("Ancienne version retirée : " + ", ".join(retires))
            messages.append(f"Installé : {v.get('nom') or v.get('titre') or slug} {v.get('version_mod') or v['version']}")
            dire(messages[-1])
        if verrou_modifie:
            try:
                ecrire_json(CHEMIN_VERROU, self.verrou)
            except OSError:
                pass
        self.scanner()
        return messages

    # -- profils ---------------------------------------------------------------------
    def liste_profils(self) -> List[str]:
        if not self.dossier_profils.is_dir():
            return []
        return sorted(p.stem for p in self.dossier_profils.glob("*.json"))

    def sauver_profil(self, nom: str) -> Path:
        nom = re.sub(r"[^\w\- ]", "", nom).strip() or "profil"
        chemin = self.dossier_profils / f"{nom}.json"
        ecrire_json(chemin, {
            "nom": nom,
            "date": time.strftime("%Y-%m-%d %H:%M"),
            "actifs": sorted(m.id for m in self.mods.values() if m.installe and m.actif),
            "inactifs": sorted(m.id for m in self.mods.values() if m.installe and not m.actif),
        })
        self.journal(f"Profil sauvegardé : {nom}")
        return chemin

    def plan_profil(self, nom: str) -> Plan:
        chemin = self.dossier_profils / f"{nom}.json"
        donnees = charger_json(chemin)
        if not donnees:
            raise ErreurGestion(f"Profil introuvable : {nom}")
        actifs = set(donnees.get("actifs", []))
        plan = Plan()
        plan_act = self.plan_activation([i for i in actifs if i in self.mods])
        plan.activer, plan.installer, plan.manquants = plan_act.activer, plan_act.installer, plan_act.manquants
        plan.avertissements = plan_act.avertissements
        a_desactiver = [m.id for m in self.mods.values() if m.installe and m.actif and m.id not in actifs
                        and not m.id.startswith(("doublon:", "fichier:"))]
        plan_des = self.plan_desactivation(a_desactiver)
        ids_act = {m.id for m in plan.activer} | set(plan.installer)
        plan.desactiver = [m for m in plan_des.desactiver if m.id not in ids_act]
        return plan

    # -- export .mrpack -------------------------------------------------------------------
    def exporter_mrpack(self, destination: Path, inclure_optionnels: bool = False,
                        progression: Progression = None) -> Path:
        if not self.verrou.get("mods"):
            raise ErreurGestion("verrou.json absent : lance d'abord « python gestionnaire.py verrou ».")
        inclus = {}
        for ident, v in self.verrou["mods"].items():
            e = self.catalogue.get(ident)
            if e and not e.par_defaut and not inclure_optionnels:
                continue
            if not e and not v.get("auto"):
                continue
            inclus[ident] = v
        # dépendances automatiques : seulement si un mod inclus en a besoin
        besoins = set()
        for v in inclus.values():
            besoins |= set(_contraintes(v.get("depends")).keys())
        for ident in [i for i, v in inclus.items() if v.get("auto")]:
            if not (set(_fournit(inclus[ident].get("fournit"), ident, "").keys()) & besoins):
                del inclus[ident]
        fichiers = []
        for ident, v in inclus.items():
            e = self.catalogue.get(ident)
            if e and e.fichier:
                continue
            serveur = v.get("serveur", "optional")
            fichiers.append({
                "path": f"mods/{v['fichier']}",
                "hashes": {"sha1": v["sha1"], "sha512": v["sha512"]},
                "env": {"client": "required",
                        "server": "unsupported" if serveur == "unsupported" else "optional"},
                "downloads": [v["url"]],
                "fileSize": v.get("taille") or 0,
            })
        index = {
            "formatVersion": 1,
            "game": "minecraft",
            "versionId": self.catalogue_brut.get("version_pack", "1.0.0"),
            "name": self.catalogue_brut.get("nom", "Optimisation Fabric 26.2"),
            "summary": self.catalogue_brut.get("description", ""),
            "files": fichiers,
            "dependencies": {
                "minecraft": self._version_minecraft(),
                "fabric-loader": self.verrou.get("fabric_loader") or "0.19.5",
            },
        }
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("modrinth.index.json", json.dumps(index, ensure_ascii=False, indent=2))
            for ident, e in self.catalogue.items():
                if not e.fichier or (not e.par_defaut and not inclure_optionnels):
                    continue
                src = DOSSIER_MODS_PERSO / e.fichier
                if src.exists():
                    z.write(src, f"overrides/mods/{e.fichier}")
                    if progression:
                        progression(f"Ajouté au pack : {e.fichier}")
            lisez = RACINE / "README.md"
            if lisez.exists():
                z.write(lisez, "overrides/LISEZMOI-pack.md")
        self.journal(f"Export .mrpack : {destination}")
        return destination


# ---------------------------------------------------------------------------
# Configuration utilisateur (dossier Minecraft mémorisé)
# ---------------------------------------------------------------------------

def lire_config_utilisateur() -> dict:
    return charger_json(CHEMIN_CONFIG_UTILISATEUR, {}) or {}


def ecrire_config_utilisateur(donnees: dict) -> None:
    ecrire_json(CHEMIN_CONFIG_UTILISATEUR, donnees)


def dossier_minecraft_courant(explicite: Optional[str] = None) -> Path:
    if explicite:
        return Path(explicite).expanduser()
    conf = lire_config_utilisateur()
    if conf.get("dossier_minecraft") and Path(conf["dossier_minecraft"]).is_dir():
        return Path(conf["dossier_minecraft"])
    detecte = detecter_dossier_minecraft()
    if detecte:
        return detecte
    raise ErreurGestion(
        "Dossier Minecraft introuvable. Indique-le : python gestionnaire.py dossier <chemin>")


# ---------------------------------------------------------------------------
# Ligne de commande
# ---------------------------------------------------------------------------

def _tableau(lignes: List[List[str]], entetes: List[str]) -> str:
    largeurs = [len(h) for h in entetes]
    for l in lignes:
        for i, c in enumerate(l):
            largeurs[i] = max(largeurs[i], len(c))
    fmt = "  ".join("{:<" + str(w) + "}" for w in largeurs)
    out = [fmt.format(*entetes), fmt.format(*["-" * w for w in largeurs])]
    out += [fmt.format(*l) for l in lignes]
    return "\n".join(out)


def _confirmer(question: str, oui: bool) -> bool:
    if oui:
        return True
    rep = input(question + " [o/N] ").strip().lower()
    return rep in ("o", "oui", "y", "yes")


def cli(argv: List[str]) -> int:
    p = argparse.ArgumentParser(
        prog="gestionnaire.py", add_help=False,
        description="Gestionnaire du pack Optimisation Fabric 26.2")
    p.add_argument("--aide", "-h", action="help", help="Afficher cette aide")
    p.add_argument("--minecraft", "-m", help="Dossier .minecraft (ou instance Prism/Modrinth) à utiliser")
    sp = p.add_subparsers(dest="commande")

    sp.add_parser("gui", help="Interface graphique")
    s = sp.add_parser("liste", help="Lister les mods (installés + catalogue)")
    s.add_argument("--tout", action="store_true", help="Inclure les bibliothèques et les non installés")
    s = sp.add_parser("installer", help="Installer / mettre à jour le pack")
    s.add_argument("ids", nargs="*", help="Mods précis (défaut : tout le pack par défaut)")
    s.add_argument("--mise-a-jour", action="store_true", help="Chercher les dernières versions sur Modrinth")
    s.add_argument("--avec-optionnels", action="store_true", help="Installer aussi les mods optionnels")
    s = sp.add_parser("activer", help="Activer des mods (et leurs bibliothèques)")
    s.add_argument("ids", nargs="+")
    s.add_argument("--oui", "-o", action="store_true", help="Ne pas demander confirmation")
    s = sp.add_parser("desactiver", help="Désactiver des mods (et ceux qui en dépendent)")
    s.add_argument("ids", nargs="+")
    s.add_argument("--oui", "-o", action="store_true")
    s.add_argument("--mettre-de-cote", action="store_true",
                   help="Déplacer aussi les fichiers associés (schematics, config...) hors du jeu")
    sp.add_parser("verifier", help="Vérifier dépendances, incompatibilités et doublons")
    s = sp.add_parser("fichiers", help="Afficher les fichiers associés à un mod")
    s.add_argument("id")
    s = sp.add_parser("profil", help="Gérer les profils")
    s.add_argument("action", choices=["liste", "sauver", "charger"])
    s.add_argument("nom", nargs="?")
    s.add_argument("--oui", "-o", action="store_true")
    s = sp.add_parser("dossier", help="Afficher / définir le dossier Minecraft")
    s.add_argument("chemin", nargs="?")
    sp.add_parser("verrou", help="(Mainteneur) régénérer verrou.json depuis Modrinth")
    s = sp.add_parser("mrpack", help="Exporter le pack au format .mrpack")
    s.add_argument("sortie", nargs="?")
    s.add_argument("--avec-optionnels", action="store_true")

    args = p.parse_args(argv)
    if args.commande is None or args.commande == "gui":
        return lancer_gui(args.minecraft)

    if args.commande == "dossier":
        if args.chemin:
            chemin = Path(args.chemin).expanduser()
            if not chemin.is_dir():
                raise ErreurGestion(f"Dossier inexistant : {chemin}")
            conf = lire_config_utilisateur()
            conf["dossier_minecraft"] = str(chemin.resolve())
            ecrire_config_utilisateur(conf)
            print(f"Dossier Minecraft enregistré : {chemin.resolve()}")
        else:
            print(dossier_minecraft_courant())
        return 0

    if args.commande == "verrou":
        g = Gestionnaire(Path(tempfile.mkdtemp(prefix="verrou-")))
        g.generer_verrou(progression=print)
        print(f"verrou.json écrit ({len(g.verrou['mods'])} mods, Fabric Loader {g.verrou.get('fabric_loader')}).")
        return 0

    dossier = dossier_minecraft_courant(args.minecraft)
    g = Gestionnaire(dossier)
    print(f"Dossier Minecraft : {dossier}")

    if args.commande == "liste":
        lignes = []
        for m in sorted(g.mods.values(), key=lambda x: (x.categorie, x.nom.lower())):
            if not args.tout and (m.bibliotheque or not m.installe):
                continue
            lignes.append([m.etat, m.id, m.nom, m.version, g.categories.get(m.categorie, m.categorie),
                           ", ".join(m.depends) or "-"])
        print(_tableau(lignes, ["État", "Identifiant", "Nom", "Version", "Catégorie", "Dépend de"]))
        return 0

    if args.commande == "installer":
        ids = args.ids or None
        if ids is None and args.avec_optionnels:
            ids = list(g.catalogue.keys())
        msgs = g.installer(ids, mise_a_jour=args.mise_a_jour, progression=lambda m: print("  " + m))
        print(f"{len(msgs)} opération(s) effectuée(s)." if msgs else "Tout est déjà à jour.")
        problemes = g.verifier()
        if problemes:
            print("\nProblèmes détectés :\n  - " + "\n  - ".join(problemes))
        return 0

    if args.commande in ("activer", "desactiver"):
        inconnus = [i for i in args.ids if i not in g.mods]
        if inconnus:
            raise ErreurGestion("Identifiant(s) inconnu(s) : " + ", ".join(inconnus)
                                + "\nUtilise « liste --tout » pour voir les identifiants.")
        plan = g.plan_activation(args.ids) if args.commande == "activer" else g.plan_desactivation(args.ids)
        print(plan.resume())
        if plan.vide:
            return 0
        if not _confirmer("Appliquer ?", args.oui):
            print("Annulé.")
            return 1
        msgs = g.appliquer(plan, mettre_de_cote=getattr(args, "mettre_de_cote", False),
                           progression=lambda m: None)
        print("\n".join(msgs))
        return 0

    if args.commande == "verifier":
        problemes = g.verifier()
        print("Aucun problème détecté." if not problemes else "- " + "\n- ".join(problemes))
        return 0 if not problemes else 2

    if args.commande == "fichiers":
        m = g.mods.get(args.id)
        if not m:
            raise ErreurGestion(f"Identifiant inconnu : {args.id}")
        assoc = g.fichiers_associes(m)
        cote = g.fichiers_mis_de_cote(m)
        print("Fichiers associés présents : " + (", ".join(map(str, assoc)) or "aucun"))
        print("Fichiers mis de côté : " + (", ".join(map(str, cote)) or "aucun"))
        return 0

    if args.commande == "profil":
        if args.action == "liste":
            print("\n".join(g.liste_profils()) or "Aucun profil.")
        elif args.action == "sauver":
            if not args.nom:
                raise ErreurGestion("Nom du profil manquant.")
            print(f"Profil enregistré : {g.sauver_profil(args.nom)}")
        else:
            if not args.nom:
                raise ErreurGestion("Nom du profil manquant.")
            plan = g.plan_profil(args.nom)
            print(plan.resume())
            if not plan.vide and _confirmer("Appliquer ?", args.oui):
                print("\n".join(g.appliquer(plan)))
        return 0

    if args.commande == "mrpack":
        sortie = Path(args.sortie) if args.sortie else RACINE / f"Optimisation-Fabric-{g._version_minecraft()}.mrpack"
        g.exporter_mrpack(sortie, inclure_optionnels=args.avec_optionnels, progression=print)
        print(f"Pack exporté : {sortie}")
        return 0
    return 0


# ---------------------------------------------------------------------------
# Interface graphique (tkinter)
# ---------------------------------------------------------------------------

def lancer_gui(dossier_explicite: Optional[str] = None) -> int:
    try:
        import tkinter as tk  # noqa: F401
        from tkinter import ttk, messagebox, filedialog, simpledialog  # noqa: F401
    except ImportError:
        print("tkinter n'est pas disponible : utilisation en ligne de commande.\n")
        cli(["--aide"])
        return 1

    class Application(tk.Tk):
        def __init__(self) -> None:
            super().__init__()
            self.title("Gestionnaire — Optimisation Fabric 26.2")
            self.geometry("1180x700")
            self.minsize(900, 560)
            self.file_messages: "queue.Queue[tuple]" = queue.Queue()
            self.gestion: Optional[Gestionnaire] = None
            self.occupe = False
            self._construire()
            try:
                dossier = dossier_minecraft_courant(dossier_explicite)
            except ErreurGestion:
                dossier = None
            if dossier:
                self.var_dossier.set(str(dossier))
                self.charger_dossier()
            else:
                self.statut("Choisis ton dossier Minecraft (bouton « Parcourir… »).")
            self.after(150, self._pomper)

        # -- construction -------------------------------------------------
        def _construire(self) -> None:
            style = ttk.Style(self)
            try:
                style.theme_use("clam")
            except tk.TclError:
                pass
            style.configure("Treeview", rowheight=24)

            haut = ttk.Frame(self, padding=8)
            haut.pack(fill="x")
            ttk.Label(haut, text="Dossier Minecraft :").pack(side="left")
            self.var_dossier = tk.StringVar()
            ttk.Entry(haut, textvariable=self.var_dossier, width=70).pack(side="left", padx=6, fill="x", expand=True)
            ttk.Button(haut, text="Parcourir…", command=self.parcourir).pack(side="left")
            ttk.Button(haut, text="Rafraîchir", command=self.rafraichir).pack(side="left", padx=4)
            ttk.Button(haut, text="Ouvrir le dossier mods", command=self.ouvrir_mods).pack(side="left")

            filtres = ttk.Frame(self, padding=(8, 0, 8, 6))
            filtres.pack(fill="x")
            ttk.Label(filtres, text="Catégorie :").pack(side="left")
            self.var_categorie = tk.StringVar(value="Toutes")
            self.combo_cat = ttk.Combobox(filtres, textvariable=self.var_categorie, state="readonly", width=38)
            self.combo_cat.pack(side="left", padx=6)
            self.combo_cat.bind("<<ComboboxSelected>>", lambda e: self.remplir())
            ttk.Label(filtres, text="Recherche :").pack(side="left", padx=(12, 0))
            self.var_recherche = tk.StringVar()
            self.var_recherche.trace_add("write", lambda *a: self.remplir())
            ttk.Entry(filtres, textvariable=self.var_recherche, width=28).pack(side="left", padx=6)
            self.var_biblios = tk.BooleanVar(value=True)
            ttk.Checkbutton(filtres, text="Afficher les bibliothèques", variable=self.var_biblios,
                            command=self.remplir).pack(side="left", padx=12)
            self.var_non_installes = tk.BooleanVar(value=True)
            ttk.Checkbutton(filtres, text="Afficher les non installés", variable=self.var_non_installes,
                            command=self.remplir).pack(side="left")

            centre = ttk.Frame(self, padding=(8, 0))
            centre.pack(fill="both", expand=True)
            colonnes = ("etat", "nom", "version", "categorie", "depend", "requis", "fichiers")
            self.arbre = ttk.Treeview(centre, columns=colonnes, show="headings", selectmode="extended")
            entetes = {"etat": ("État", 95), "nom": ("Mod", 210), "version": ("Version", 150),
                       "categorie": ("Catégorie", 190), "depend": ("Dépend de", 180),
                       "requis": ("Requis par", 180), "fichiers": ("Fichiers associés", 170)}
            for c in colonnes:
                self.arbre.heading(c, text=entetes[c][0], command=lambda col=c: self.trier(col))
                self.arbre.column(c, width=entetes[c][1], anchor="w", stretch=(c in ("nom", "depend", "requis", "fichiers")))
            defil = ttk.Scrollbar(centre, orient="vertical", command=self.arbre.yview)
            self.arbre.configure(yscrollcommand=defil.set)
            self.arbre.pack(side="left", fill="both", expand=True)
            defil.pack(side="left", fill="y")
            self.arbre.tag_configure("actif", foreground="#1b7f3b")
            self.arbre.tag_configure("inactif", foreground="#8a8a8a")
            self.arbre.tag_configure("absent", foreground="#b36b00")
            self.arbre.tag_configure("probleme", background="#ffe9e9")
            self.arbre.bind("<<TreeviewSelect>>", self.selection_changee)
            self.arbre.bind("<Double-1>", lambda e: self.basculer())
            self.tri_courant = ("categorie", False)

            self.var_description = tk.StringVar(value="Sélectionne un mod pour voir sa description.")
            ttk.Label(self, textvariable=self.var_description, wraplength=1120, padding=(10, 6),
                      justify="left").pack(fill="x")

            boutons = ttk.Frame(self, padding=8)
            boutons.pack(fill="x")
            self.btn_activer = ttk.Button(boutons, text="Activer", command=lambda: self.basculer(True))
            self.btn_activer.pack(side="left")
            self.btn_desactiver = ttk.Button(boutons, text="Désactiver", command=lambda: self.basculer(False))
            self.btn_desactiver.pack(side="left", padx=4)
            self.var_mettre_de_cote = tk.BooleanVar(value=False)
            ttk.Checkbutton(boutons, text="Mettre de côté les fichiers associés à la désactivation",
                            variable=self.var_mettre_de_cote).pack(side="left", padx=8)
            ttk.Separator(boutons, orient="vertical").pack(side="left", fill="y", padx=8)
            ttk.Button(boutons, text="Installer / mettre à jour le pack", command=self.installer_pack).pack(side="left")
            ttk.Button(boutons, text="Installer la sélection", command=self.installer_selection).pack(side="left", padx=4)
            ttk.Button(boutons, text="Vérifier", command=self.verifier).pack(side="left")
            self.menu_profils = tk.Menu(self, tearoff=0)
            self.menu_profils.add_command(label="Sauvegarder le profil actuel…", command=self.sauver_profil)
            self.menu_profils.add_command(label="Charger un profil…", command=self.charger_profil)
            self.menu_profils.add_separator()
            self.menu_profils.add_command(label="Tout activer", command=lambda: self.tout(True))
            self.menu_profils.add_command(label="Tout désactiver (sauf bibliothèques)", command=lambda: self.tout(False))
            ttk.Button(boutons, text="Profils ▾", command=self.ouvrir_menu_profils).pack(side="left", padx=4)
            ttk.Button(boutons, text="Exporter .mrpack", command=self.exporter).pack(side="left")

            bas = ttk.Frame(self, padding=(8, 0, 8, 8))
            bas.pack(fill="x")
            self.var_statut = tk.StringVar(value="Prêt.")
            ttk.Label(bas, textvariable=self.var_statut, anchor="w").pack(side="left", fill="x", expand=True)
            self.barre = ttk.Progressbar(bas, mode="indeterminate", length=180)
            self.barre.pack(side="right")

        # -- aides --------------------------------------------------------
        def statut(self, texte: str) -> None:
            self.var_statut.set(texte)

        def erreur(self, e: Exception) -> None:
            messagebox.showerror("Erreur", str(e))
            self.statut("Erreur : " + str(e)[:120])

        def _pomper(self) -> None:
            try:
                while True:
                    genre, contenu = self.file_messages.get_nowait()
                    if genre == "statut":
                        self.statut(contenu)
                    elif genre == "fin":
                        self.occupe = False
                        self.barre.stop()
                        self.rafraichir()
                        if contenu:
                            messagebox.showinfo("Terminé", contenu)
                    elif genre == "erreur":
                        self.occupe = False
                        self.barre.stop()
                        self.rafraichir()
                        self.erreur(contenu)
            except queue.Empty:
                pass
            self.after(150, self._pomper)

        def tache(self, fonction: Callable[[], str]) -> None:
            if self.occupe:
                messagebox.showwarning("Patiente", "Une opération est déjà en cours.")
                return
            self.occupe = True
            self.barre.start(12)

            def courir() -> None:
                try:
                    resultat = fonction()
                    self.file_messages.put(("fin", resultat))
                except Exception as e:  # noqa: BLE001
                    self.file_messages.put(("erreur", e))

            threading.Thread(target=courir, daemon=True).start()

        def progression(self, msg: str) -> None:
            self.file_messages.put(("statut", msg))

        def selection(self) -> List[Mod]:
            if not self.gestion:
                return []
            return [self.gestion.mods[i] for i in self.arbre.selection() if i in self.gestion.mods]

        # -- actions ------------------------------------------------------
        def parcourir(self) -> None:
            chemin = filedialog.askdirectory(title="Choisis le dossier .minecraft (ou l'instance Prism / Modrinth)")
            if chemin:
                self.var_dossier.set(chemin)
                conf = lire_config_utilisateur()
                conf["dossier_minecraft"] = chemin
                ecrire_config_utilisateur(conf)
                self.charger_dossier()

        def charger_dossier(self) -> None:
            try:
                self.gestion = Gestionnaire(Path(self.var_dossier.get()))
            except Exception as e:  # noqa: BLE001
                self.erreur(e)
                return
            cats = ["Toutes"] + [self.gestion.categories.get(c, c) for c in self.gestion.categories]
            self.combo_cat["values"] = cats
            self.remplir()
            nb = sum(1 for m in self.gestion.mods.values() if m.installe)
            actifs = sum(1 for m in self.gestion.mods.values() if m.installe and m.actif)
            self.statut(f"{nb} mods installés, {actifs} actifs — dossier : {self.gestion.dossier_mods}")

        def rafraichir(self) -> None:
            if self.gestion:
                self.gestion.scanner()
                self.remplir()
                nb = sum(1 for m in self.gestion.mods.values() if m.installe)
                actifs = sum(1 for m in self.gestion.mods.values() if m.installe and m.actif)
                self.statut(f"{nb} mods installés, {actifs} actifs.")
            elif self.var_dossier.get():
                self.charger_dossier()

        def remplir(self) -> None:
            if not self.gestion:
                return
            selection = set(self.arbre.selection())
            self.arbre.delete(*self.arbre.get_children())
            g = self.gestion
            cat_filtre = self.var_categorie.get()
            recherche = self.var_recherche.get().strip().lower()
            problemes_ids = set()
            for m in g.mods.values():
                if m.installe and m.actif and g.dependances_manquantes(m):
                    problemes_ids.add(m.id)
            lignes = []
            for m in g.mods.values():
                if not self.var_biblios.get() and m.bibliotheque:
                    continue
                if not self.var_non_installes.get() and not m.installe:
                    continue
                cat_nom = g.categories.get(m.categorie, m.categorie)
                if cat_filtre != "Toutes" and cat_nom != cat_filtre:
                    continue
                if recherche and recherche not in (m.nom + " " + m.id + " " + m.description).lower():
                    continue
                fichiers = [str(p) for p in g.fichiers_associes(m)]
                cote = g.fichiers_mis_de_cote(m)
                if cote:
                    fichiers.append(f"[{len(cote)} mis de côté]")
                requis = ", ".join(a.nom for a in g.requis_par(m))
                lignes.append((m, [m.etat, m.nom, m.version, cat_nom, ", ".join(m.depends) or "-",
                                    requis or "-", ", ".join(fichiers) or "-"]))
            col, inverse = self.tri_courant
            index = ("etat", "nom", "version", "categorie", "depend", "requis", "fichiers").index(col)
            lignes.sort(key=lambda x: (x[1][index].lower(), x[1][1].lower()), reverse=inverse)
            for m, valeurs in lignes:
                tags = ["actif" if m.actif else ("inactif" if m.installe else "absent")]
                if m.id in problemes_ids:
                    tags.append("probleme")
                self.arbre.insert("", "end", iid=m.id, values=valeurs, tags=tags)
                if m.id in selection:
                    self.arbre.selection_add(m.id)

        def trier(self, colonne: str) -> None:
            col, inverse = self.tri_courant
            self.tri_courant = (colonne, not inverse if col == colonne else False)
            self.remplir()

        def selection_changee(self, _evt=None) -> None:
            mods = self.selection()
            if len(mods) == 1:
                m = mods[0]
                g = self.gestion
                morceaux = [f"{m.nom} ({m.id}) — {m.description or 'Pas de description.'}"]
                if m.installe:
                    morceaux.append(f"Fichier : {m.chemin.name}")
                    manquantes = g.dependances_manquantes(m) if m.actif else []
                    if manquantes:
                        morceaux.append("Dépendances manquantes : " + ", ".join(manquantes))
                    dependants = g.dependants(m)
                    if dependants:
                        morceaux.append("Désactiver ce mod désactiverait aussi : " + ", ".join(d.nom for d in dependants))
                elif m.catalogue and not m.catalogue.par_defaut:
                    morceaux.append("Mod optionnel : non installé par défaut.")
                self.var_description.set("\n".join(morceaux))
            elif mods:
                self.var_description.set(f"{len(mods)} mods sélectionnés.")

        def basculer(self, activer: Optional[bool] = None) -> None:
            if not self.gestion:
                return
            mods = self.selection()
            if not mods:
                messagebox.showinfo("Sélection", "Sélectionne au moins un mod dans la liste.")
                return
            if activer is None:
                activer = not mods[0].actif
            g = self.gestion
            ids = [m.id for m in mods]
            plan = g.plan_activation(ids) if activer else g.plan_desactivation(ids)
            if plan.vide:
                if plan.manquants:
                    messagebox.showwarning("Dépendances", plan.resume())
                else:
                    self.statut("Rien à changer.")
                return
            if not messagebox.askyesno("Confirmer", plan.resume() + "\n\nAppliquer ?"):
                return
            mettre = self.var_mettre_de_cote.get() and not activer

            def travail() -> str:
                msgs = g.appliquer(plan, mettre_de_cote=mettre, progression=self.progression)
                return "\n".join(msgs) if plan.installer else ""

            if plan.installer:
                self.tache(travail)
            else:
                try:
                    msgs = travail()
                    self.rafraichir()
                    self.statut(" | ".join(msgs)[:200] if msgs else "Terminé.")
                except Exception as e:  # noqa: BLE001
                    self.erreur(e)

        def tout(self, activer: bool) -> None:
            if not self.gestion:
                return
            g = self.gestion
            if activer:
                ids = [m.id for m in g.mods.values() if m.installe and not m.actif]
                plan = g.plan_activation(ids)
            else:
                ids = [m.id for m in g.mods.values() if m.installe and m.actif and not m.bibliotheque]
                plan = g.plan_desactivation(ids)
            if plan.vide:
                self.statut("Rien à changer.")
                return
            if messagebox.askyesno("Confirmer", plan.resume() + "\n\nAppliquer ?"):
                try:
                    g.appliquer(plan, mettre_de_cote=self.var_mettre_de_cote.get() and not activer)
                    self.rafraichir()
                except Exception as e:  # noqa: BLE001
                    self.erreur(e)

        def installer_pack(self) -> None:
            if not self.gestion:
                return
            g = self.gestion
            reponse = messagebox.askyesnocancel(
                "Installer / mettre à jour",
                "Installer tous les mods du pack dans :\n" + str(g.dossier_mods) +
                "\n\nOui = chercher les dernières versions sur Modrinth\n"
                "Non = utiliser les versions vérifiées du pack (recommandé)\nAnnuler = ne rien faire")
            if reponse is None:
                return
            mise_a_jour = bool(reponse)

            def travail() -> str:
                msgs = g.installer(None, mise_a_jour=mise_a_jour, progression=self.progression)
                problemes = g.verifier()
                texte = "\n".join(msgs) if msgs else "Tout était déjà à jour."
                if problemes:
                    texte += "\n\nProblèmes détectés :\n- " + "\n- ".join(problemes)
                return texte

            self.tache(travail)

        def installer_selection(self) -> None:
            if not self.gestion:
                return
            mods = [m for m in self.selection() if not m.installe]
            if not mods:
                messagebox.showinfo("Sélection", "Sélectionne des mods « Non installé » dans la liste.")
                return
            g = self.gestion
            plan = g.plan_activation([m.id for m in mods])
            if not messagebox.askyesno("Installer", plan.resume() + "\n\nContinuer ?"):
                return
            self.tache(lambda: "\n".join(g.appliquer(plan, progression=self.progression)) or "Installation terminée.")

        def verifier(self) -> None:
            if not self.gestion:
                return
            problemes = self.gestion.verifier()
            if problemes:
                messagebox.showwarning("Vérification", "- " + "\n- ".join(problemes))
            else:
                messagebox.showinfo("Vérification", "Aucun problème : dépendances satisfaites, pas d'incompatibilité.")

        def ouvrir_menu_profils(self) -> None:
            self.menu_profils.tk_popup(self.winfo_pointerx(), self.winfo_pointery())

        def sauver_profil(self) -> None:
            if not self.gestion:
                return
            nom = simpledialog.askstring("Profil", "Nom du profil :", parent=self)
            if nom:
                chemin = self.gestion.sauver_profil(nom)
                self.statut(f"Profil enregistré : {chemin}")

        def charger_profil(self) -> None:
            if not self.gestion:
                return
            profils = self.gestion.liste_profils()
            if not profils:
                messagebox.showinfo("Profils", "Aucun profil enregistré.")
                return
            fen = tk.Toplevel(self)
            fen.title("Charger un profil")
            fen.transient(self)
            liste = tk.Listbox(fen, height=min(12, len(profils) + 1), width=40)
            for p in profils:
                liste.insert("end", p)
            liste.pack(padx=10, pady=10)
            liste.selection_set(0)

            def valider() -> None:
                sel = liste.curselection()
                if not sel:
                    return
                nom = profils[sel[0]]
                fen.destroy()
                try:
                    plan = self.gestion.plan_profil(nom)
                except ErreurGestion as e:
                    self.erreur(e)
                    return
                if plan.vide:
                    self.statut("Profil déjà appliqué.")
                    return
                if messagebox.askyesno("Profil " + nom, plan.resume() + "\n\nAppliquer ?"):
                    g = self.gestion
                    self.tache(lambda: "\n".join(g.appliquer(plan, progression=self.progression)))

            ttk.Button(fen, text="Charger", command=valider).pack(pady=(0, 10))

        def ouvrir_mods(self) -> None:
            if self.gestion:
                try:
                    self.gestion.dossier_mods.mkdir(parents=True, exist_ok=True)
                    ouvrir_dans_explorateur(self.gestion.dossier_mods)
                except ErreurGestion as e:
                    self.erreur(e)

        def exporter(self) -> None:
            if not self.gestion:
                return
            chemin = filedialog.asksaveasfilename(
                title="Exporter le pack", defaultextension=".mrpack",
                initialfile=f"Optimisation-Fabric-{self.gestion._version_minecraft()}.mrpack",
                filetypes=[("Pack Modrinth", "*.mrpack")])
            if chemin:
                try:
                    self.gestion.exporter_mrpack(Path(chemin))
                    messagebox.showinfo("Export", f"Pack exporté :\n{chemin}\n\nImporte-le dans Modrinth App ou Prism Launcher.")
                except ErreurGestion as e:
                    self.erreur(e)

    Application().mainloop()
    return 0


def main() -> int:
    try:
        return cli(sys.argv[1:])
    except ErreurGestion as e:
        print("Erreur : " + str(e), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrompu.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
