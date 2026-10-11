"""Chargement des données brutes dans DuckDB (schéma `raw`) et journal d'ingestion."""
from __future__ import annotations

import logging
from datetime import datetime

import duckdb
import pandas as pd

from src import config

log = logging.getLogger(__name__)


def connexion() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(config.DUCKDB_PATH))


def charger(tables: dict[str, pd.DataFrame], run_id: str) -> list[str]:
    """Remplace les tables brutes et alimente raw.journal_ingestion.
    Retourne la liste des alertes de volumétrie."""
    alertes: list[str] = []
    with connexion() as con:
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        con.execute("""
            CREATE TABLE IF NOT EXISTS raw.journal_ingestion (
                run_id VARCHAR, table_cible VARCHAR, nb_lignes INTEGER,
                ingere_le TIMESTAMP)
        """)
        for nom, df in tables.items():
            precedent = con.execute(
                "SELECT nb_lignes FROM raw.journal_ingestion WHERE table_cible = ? "
                "ORDER BY ingere_le DESC LIMIT 1", [nom]).fetchone()
            con.register("df_tmp", df)
            con.execute(f"CREATE OR REPLACE TABLE raw.{nom} AS SELECT * FROM df_tmp")
            con.unregister("df_tmp")
            con.execute("INSERT INTO raw.journal_ingestion VALUES (?, ?, ?, ?)",
                        [run_id, nom, len(df), datetime.now()])
            log.info("raw.%s chargée (%d lignes)", nom, len(df))

            # Contrôle de volumétrie : une chute brutale signale souvent un
            # problème de source (fichier tronqué, filtre cassé...)
            if precedent and precedent[0] and len(df) < precedent[0] * (1 - config.SEUIL_BAISSE_VOLUME):
                alerte = (f"Volumétrie anormale sur raw.{nom} : {len(df)} lignes "
                          f"contre {precedent[0]} au run précédent")
                log.warning(alerte)
                alertes.append(alerte)
    return alertes


def charger_correspondances() -> int:
    """(Re)charge la table de correspondance des communes dans raw."""
    if not config.CORRESPONDANCES.exists():
        config.CORRESPONDANCES.write_text(config.ENTETE_CORRESPONDANCES, encoding="utf-8")
    df = pd.read_csv(config.CORRESPONDANCES, dtype=str, keep_default_na=False)
    with connexion() as con:
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        con.register("df_tmp", df)
        con.execute("CREATE OR REPLACE TABLE raw.correspondances_communes AS SELECT * FROM df_tmp")
    return len(df)


def lire(requete: str) -> pd.DataFrame:
    with connexion() as con:
        return con.execute(requete).df()
