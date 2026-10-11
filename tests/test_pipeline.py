"""Test de bout en bout sur les données de démonstration, qui contiennent
des anomalies volontaires : chaque contrôle doit les détecter."""
import subprocess
import sys

import duckdb
import pytest

from src import config


@pytest.fixture(scope="module")
def entrepot(tmp_path_factory):
    resultat = subprocess.run([sys.executable, "run_pipeline.py", "--demo", "--sans-ia"],
                              cwd=config.ROOT, capture_output=True, text=True)
    assert resultat.returncode == 0, resultat.stdout[-3000:] + resultat.stderr[-3000:]
    con = duckdb.connect(str(config.DATA_DIR / "demo" / "warehouse.duckdb"), read_only=True)
    yield con
    con.close()


def test_filtre_departement(entrepot):
    hors_74 = entrepot.sql("select count(*) from marts.fct_hebergements_classes "
                           "where code_postal not like '74%'").fetchone()[0]
    assert hors_74 == 0


def test_doublon_dedoublonne(entrepot):
    n = entrepot.sql("select count(*) from marts.fct_hebergements_classes "
                     "where nom_commercial = 'HÔTEL EN DOUBLE'").fetchone()[0]
    assert n == 1


@pytest.mark.parametrize("etablissement,controle", [
    ("HÔTEL CAPACITÉ ABERRANTE", "Ratio capacité / chambre incohérent"),
    ("HÔTEL SANS CAPACITÉ", "Capacité manquante"),
    ("CAMPING SANS EMPLACEMENTS", "Unité d'offre manquante"),
    ("HÔTEL CLASSEMENT ANCIEN", "Classement expiré"),
    ("RÉSIDENCE DATE FUTURE", "Date de classement future"),
    ("HÔTEL SITE INVALIDE", "Site internet invalide"),
    ("HÔTEL EN DOUBLE", "Doublon dans la source"),
    ("HÔTEL COMMUNE INCONNUE", "Commune non rapprochée"),
])
def test_anomalie_detectee(entrepot, etablissement, controle):
    n = entrepot.execute("select count(*) from marts.mart_qualite_anomalies "
                         "where nom_commercial = ? and controle = ?",
                         [etablissement, controle]).fetchone()[0]
    assert n == 1


def test_classement_proroge_non_expire(entrepot):
    statut = entrepot.sql("select statut_classement from marts.fct_hebergements_classes "
                          "where nom_commercial = 'HÔTEL PROROGÉ'").fetchone()[0]
    assert statut == "Prorogé"


def test_communes_fusionnees_rattachees(entrepot):
    lignes = dict(entrepot.sql("""
        select commune_source, code_insee from marts.fct_hebergements_classes
        where commune_source in ('SEYNOD', 'ANNECY-LE-VIEUX', 'MONTMIN', 'ST GERVAIS LES BAINS')
    """).fetchall())
    assert lignes == {"SEYNOD": "74010", "ANNECY-LE-VIEUX": "74010",
                      "MONTMIN": "74275", "ST GERVAIS LES BAINS": "74236"}


def test_rapport_excel_genere():
    assert list((config.DATA_DIR / "demo" / "exports").glob("Rapport_offre_classee_*.xlsx"))


def test_dates_au_format_francais_converties(entrepot):
    # La source publie les dates en JJ/MM/AAAA : aucune ne doit être perdue au typage
    nulles = entrepot.sql("select count(*) from marts.fct_hebergements_classes "
                          "where date_classement is null").fetchone()[0]
    assert nulles == 0


def test_url_sans_protocole_completee(entrepot):
    sans_protocole = entrepot.sql("select count(*) from marts.fct_hebergements_classes "
                                  "where site_internet not like 'http%'").fetchone()[0]
    assert sans_protocole == 0
