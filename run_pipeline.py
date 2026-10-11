"""Orchestration du pipeline de l'observatoire de l'offre touristique.

    python run_pipeline.py            # données réelles (internet requis)
    python run_pipeline.py --demo     # données de démonstration, hors ligne
    python run_pipeline.py --sans-ia  # désactive les appels au modèle de langage
    python run_pipeline.py --archive  # rejoue les derniers fichiers bruts archivés (hors ligne)

Étapes :
  1. Extraction  : hébergements classés (Atout France) + communes (geo.api.gouv.fr)
  2. Chargement  : DuckDB, schéma raw, journal d'ingestion + contrôle de volumétrie
  3. Transformation et tests : dbt build (staging -> intermediate -> marts)
  4. IA          : rapprochement des communes non identifiées, puis dbt build ciblé
  5. Restitution : exports CSV Power BI, note de synthèse, rapport Excel
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime

from src import config


def configurer_logs() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler(config.LOG_DIR / "pipeline.log", encoding="utf-8")],
    )
    for bruyant in ("httpx", "urllib3", "anthropic"):
        logging.getLogger(bruyant).setLevel(logging.WARNING)
    return logging.getLogger("pipeline")


def dbt(*args: str, date_reference: str | None = None) -> bool:
    """Lance une commande dbt via son API Python. Retourne True si tout est passé."""
    from dbt.cli.main import dbtRunner

    os.environ["DUCKDB_PATH"] = str(config.DUCKDB_PATH)
    commande = [*args, "--project-dir", str(config.DBT_DIR),
                "--profiles-dir", str(config.DBT_DIR)]
    if date_reference:
        commande += ["--vars", f"{{date_reference: '{date_reference}'}}"]
    resultat = dbtRunner().invoke(commande)
    if resultat.exception:
        raise resultat.exception
    return bool(resultat.success)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--demo", action="store_true", help="utiliser les données de démonstration")
    parser.add_argument("--sans-ia", action="store_true", help="ne pas appeler le modèle de langage")
    parser.add_argument("--archive", action="store_true",
                        help="rejouer les derniers fichiers bruts de data/raw sans retélécharger")
    parser.add_argument("--date-reference", help="date de calcul des statuts (AAAA-MM-JJ)")
    args = parser.parse_args()

    if args.demo:
        config.activer_mode_demo()
        # Date figée pour que la démo donne toujours les mêmes résultats
        args.date_reference = args.date_reference or "2026-10-11"
    if args.sans_ia:
        config.ANTHROPIC_API_KEY = ""

    log = configurer_logs()
    from src import load
    from src.ai import rapprochement_communes, synthese
    from src.extract import atout_france, geo_api
    from src.reporting import exports

    debut = time.time()
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log.info("=== Run %s | département %s | %s | IA %s ===", run_id, config.DEPARTEMENT,
             "DÉMO" if args.demo else "données réelles",
             "activée" if config.ANTHROPIC_API_KEY else "désactivée (règles de repli)")

    # 1. Extraction
    log.info("--- 1/5 Extraction")
    if args.demo:
        fichier = config.FIXTURES_DIR / "hebergements_classes_demo.csv"
        communes_json, epcis_json = geo_api.lire_fichiers(config.FIXTURES_DIR)
    elif args.archive:
        archives = sorted(config.RAW_DIR.glob("hebergements_classes_*.csv"))
        if not archives:
            log.error("Aucune archive dans %s : lance d'abord le pipeline sans --archive", config.RAW_DIR)
            return 1
        fichier = archives[-1]
        log.info("Rejeu de l'archive %s", fichier.name)
        communes_json, epcis_json = geo_api.lire_fichiers(config.RAW_DIR)
    else:
        fichier = atout_france.telecharger()
        communes_json, epcis_json = geo_api.telecharger()
    hebergements = atout_france.extraire(fichier)
    communes, codes_postaux = geo_api.transformer(communes_json, epcis_json)

    # 2. Chargement
    log.info("--- 2/5 Chargement")
    alertes = load.charger({
        "hebergements_classes": hebergements,
        "communes": communes,
        "communes_codes_postaux": codes_postaux,
    }, run_id)
    load.charger_correspondances()

    # 3. Transformation + tests
    log.info("--- 3/5 Transformation et tests (dbt build)")
    succes = dbt("build", date_reference=args.date_reference)

    # 4. Rapprochement assisté par IA des communes restantes
    log.info("--- 4/5 Rapprochement des communes non identifiées")
    if rapprochement_communes.executer() > 0:
        load.charger_correspondances()
        log.info("Nouvelles correspondances : reconstruction des tables concernées")
        succes = dbt("build", "--select", "int_hebergements__rapproches+",
                     date_reference=args.date_reference)

    # 5. Restitution
    log.info("--- 5/5 Restitution")
    exports.exporter_csv()
    texte = synthese.executer()
    rapport = exports.rapport_excel(texte)

    for alerte in alertes:
        log.warning("ALERTE : %s", alerte)
    qualite = load.lire("select severite, sum(nb_etablissements_concernes) as nb "
                        "from marts.mart_qualite_synthese group by 1")
    log.info("Anomalies détectées : %s",
             ", ".join(f"{r.severite} {int(r.nb)}" for r in qualite.itertuples()) or "aucune")
    log.info("=== Terminé en %.0f s | tests dbt %s | rapport : %s ===",
             time.time() - debut, "OK" if succes else "EN ÉCHEC", rapport)
    return 0 if succes else 1


if __name__ == "__main__":
    sys.exit(main())
