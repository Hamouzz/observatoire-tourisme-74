"""Configuration centrale du pipeline."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Territoire analysé (code département INSEE)
DEPARTEMENT = os.getenv("DEPARTEMENT", "74")

# Sources ouvertes
# Hébergements collectifs classés (Atout France), ressource stable sur data.gouv.fr
ATOUT_FRANCE_URL = os.getenv(
    "ATOUT_FRANCE_URL",
    "https://www.data.gouv.fr/api/1/datasets/r/3ce290bf-07ec-4d63-b12b-d0496193a535",
)
GEO_API_URL = "https://geo.api.gouv.fr"

# Arborescence
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
EXPORT_DIR = DATA_DIR / "exports"
LOG_DIR = DATA_DIR / "logs"
DUCKDB_PATH = Path(os.getenv("DUCKDB_PATH", DATA_DIR / "warehouse.duckdb"))
DBT_DIR = ROOT / "dbt"
# Table de correspondance libellé -> code INSEE, versionnée dans Git et relue par un humain
CORRESPONDANCES = ROOT / "referentiels" / "correspondances_communes.csv"
FIXTURES_DIR = ROOT / "tests" / "fixtures"
MODE_DEMO = False

# IA (optionnelle) : sans clé, le pipeline bascule sur des règles déterministes
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5")
# Seuil de confiance au-delà duquel une proposition de l'IA est appliquée automatiquement
SEUIL_CONFIANCE_IA = float(os.getenv("SEUIL_CONFIANCE_IA", "0.85"))

# Contrôle de volumétrie : alerte si le nombre de lignes chute de plus de X % d'un run à l'autre
SEUIL_BAISSE_VOLUME = 0.20

HTTP_TIMEOUT = 60



def activer_mode_demo() -> None:
    """Isole le mode démo dans data/demo/ pour ne jamais mélanger avec les vraies données."""
    global MODE_DEMO, RAW_DIR, EXPORT_DIR, DUCKDB_PATH, CORRESPONDANCES
    MODE_DEMO = True
    base = DATA_DIR / "demo"
    RAW_DIR, EXPORT_DIR = base / "raw", base / "exports"
    DUCKDB_PATH = base / "warehouse.duckdb"
    CORRESPONDANCES = base / "correspondances_communes.csv"
    creer_dossiers()
    if not CORRESPONDANCES.exists():
        CORRESPONDANCES.write_text(ENTETE_CORRESPONDANCES, encoding="utf-8")


ENTETE_CORRESPONDANCES = "code_postal,commune_source,code_insee,methode,confiance,justification\n"


def creer_dossiers() -> None:
    for d in (RAW_DIR, EXPORT_DIR, LOG_DIR, CORRESPONDANCES.parent):
        d.mkdir(parents=True, exist_ok=True)


creer_dossiers()
