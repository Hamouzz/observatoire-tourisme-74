"""Référentiel géographique : communes et intercommunalités (geo.api.gouv.fr)."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd
import requests

from src import config

log = logging.getLogger(__name__)

CHAMPS = "nom,code,codesPostaux,population,surface,centre,codeEpci"


def telecharger(departement: str = config.DEPARTEMENT) -> tuple[list, list]:
    url = f"{config.GEO_API_URL}/communes"
    params = {"codeDepartement": departement, "fields": CHAMPS, "format": "json"}
    communes = requests.get(url, params=params, timeout=config.HTTP_TIMEOUT).json()
    log.info("%d communes récupérées pour le département %s", len(communes), departement)

    epcis = []
    for code in sorted({c.get("codeEpci") for c in communes if c.get("codeEpci")}):
        r = requests.get(f"{config.GEO_API_URL}/epcis/{code}",
                         params={"fields": "nom,code"}, timeout=config.HTTP_TIMEOUT)
        if r.ok:
            epcis.append(r.json())
    log.info("%d intercommunalités récupérées", len(epcis))

    (config.RAW_DIR / "communes.json").write_text(json.dumps(communes, ensure_ascii=False), encoding="utf-8")
    (config.RAW_DIR / "epcis.json").write_text(json.dumps(epcis, ensure_ascii=False), encoding="utf-8")
    return communes, epcis


def _lire_json(chemin: Path):
    # UTF-8 attendu ; cp1252 accepté pour les fichiers écrits par une ancienne version sous Windows
    for encodage in ("utf-8", "cp1252"):
        try:
            return json.loads(chemin.read_text(encoding=encodage))
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Encodage non reconnu : {chemin}")


def lire_fichiers(dossier: Path) -> tuple[list, list]:
    return _lire_json(dossier / "communes.json"), _lire_json(dossier / "epcis.json")


def transformer(communes: list, epcis: list) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aplati le JSON en deux tables : communes et (commune, code postal)."""
    noms_epci = {e["code"]: e["nom"] for e in epcis}
    lignes, codes_postaux = [], []
    for c in communes:
        lon, lat = (c.get("centre") or {}).get("coordinates", [None, None])
        lignes.append({
            "code_insee": c["code"],
            "nom": c["nom"],
            "population": c.get("population"),
            "surface_ha": c.get("surface"),
            "latitude": lat,
            "longitude": lon,
            "code_epci": c.get("codeEpci"),
            "nom_epci": noms_epci.get(c.get("codeEpci")),
        })
        for cp in c.get("codesPostaux", []):
            codes_postaux.append({"code_insee": c["code"], "code_postal": cp})
    return pd.DataFrame(lignes), pd.DataFrame(codes_postaux)
