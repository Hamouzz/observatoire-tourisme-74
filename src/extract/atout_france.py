"""Extraction des hébergements collectifs classés (Atout France, via data.gouv.fr).

Principes :
- on archive le fichier brut tel quel (traçabilité, rejouabilité) ;
- on ne type rien ici : tout reste en texte, le typage se fait dans dbt (ELT) ;
- on contrôle le schéma : si Atout France renomme une colonne, le pipeline
  s'arrête avec un message clair plutôt que de produire des chiffres faux.
"""
from __future__ import annotations

import csv
import io
import logging
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

from src import config

log = logging.getLogger(__name__)

# Colonnes cibles -> préfixe attendu du nom de colonne normalisé dans la source.
# La correspondance par préfixe rend l'ingestion robuste aux petites variations
# d'intitulé (accents, parenthèses, majuscules).
COLONNES = {
    "date_classement": "date_de_classement",
    "typologie": "typologie",
    "classement": "classement",
    "categorie": "categorie",
    "mention": "mention",
    "nom_commercial": "nom_commercial",
    "adresse": "adresse",
    "code_postal": "code_postal",
    "commune": "commune",
    "site_internet": "site_internet",
    "type_sejour": "type_de_sejour",
    "capacite_accueil": "capacite_d_accueil",
    "nb_chambres": "nombre_de_chambres",
    "nb_emplacements": "nombre_d_emplacements",
    "nb_unites_habitation": "nombre_d_unites",
    "nb_logements": "nombre_de_logements",
    "classement_proroge": "classement_proroge",
}
OBLIGATOIRES = {"date_classement", "typologie", "classement", "nom_commercial",
                "code_postal", "commune", "capacite_accueil"}


def normaliser_nom(nom: str) -> str:
    """'CAPACITÉ D'ACCUEIL (PERSONNES)' -> 'capacite_d_accueil_personnes'."""
    nom = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode()
    nom = re.sub(r"[^a-z0-9]+", "_", nom.lower())
    return nom.strip("_")


def mapper_colonnes(colonnes: list[str]) -> dict[str, str]:
    """Associe chaque colonne source à son nom cible. Lève une erreur si une
    colonne obligatoire est introuvable (contrôle de schéma)."""
    mapping: dict[str, str] = {}
    normalisees = {c: normaliser_nom(c) for c in colonnes}
    for cible, prefixe in COLONNES.items():
        for source, norm in normalisees.items():
            if source in mapping:
                continue
            # 'classement' ne doit pas capturer 'classement_proroge'
            if norm == prefixe or (norm.startswith(prefixe) and cible != "classement"):
                mapping[source] = cible
                break
    manquantes = OBLIGATOIRES - set(mapping.values())
    if manquantes:
        raise ValueError(
            f"Schéma source modifié : colonnes introuvables {sorted(manquantes)}. "
            f"Colonnes reçues : {colonnes}"
        )
    return mapping


def lire_csv(contenu: bytes) -> pd.DataFrame:
    """Lecture robuste : détection de l'encodage et du séparateur."""
    for encodage in ("utf-8-sig", "cp1252"):
        try:
            texte = contenu.decode(encodage)
            break
        except UnicodeDecodeError:
            continue
    else:  # pragma: no cover
        raise ValueError("Encodage du fichier non reconnu")
    premiere_ligne = texte.splitlines()[0]
    separateur = csv.Sniffer().sniff(premiere_ligne, delimiters=";,\t").delimiter
    return pd.read_csv(io.StringIO(texte), sep=separateur, dtype=str,
                       keep_default_na=False)


def telecharger(url: str = config.ATOUT_FRANCE_URL) -> Path:
    log.info("Téléchargement des hébergements classés : %s", url)
    reponse = requests.get(url, timeout=config.HTTP_TIMEOUT)
    reponse.raise_for_status()
    chemin = config.RAW_DIR / f"hebergements_classes_{datetime.now():%Y%m%d}.csv"
    chemin.write_bytes(reponse.content)
    log.info("Fichier brut archivé : %s (%.1f Mo)", chemin.name, len(reponse.content) / 1e6)
    return chemin


def extraire(chemin: Path, departement: str = config.DEPARTEMENT) -> pd.DataFrame:
    """Lit le fichier brut, renomme les colonnes et filtre le département."""
    brut = lire_csv(chemin.read_bytes())
    mapping = mapper_colonnes(list(brut.columns))
    df = brut.rename(columns=mapping)[list(mapping.values())]
    for cible in COLONNES:  # colonnes optionnelles absentes -> vides
        if cible not in df.columns:
            df[cible] = ""
    df["code_postal"] = df["code_postal"].str.strip().str.zfill(5)
    total = len(df)
    df = df[df["code_postal"].str.startswith(departement)].copy()
    df["_fichier_source"] = chemin.name
    df["_ingere_le"] = datetime.now().isoformat(timespec="seconds")
    log.info("%d établissements classés en France, dont %d dans le %s",
             total, len(df), departement)
    return df[list(COLONNES) + ["_fichier_source", "_ingere_le"]]
