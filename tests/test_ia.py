"""L'IA est encadrée : on simule ses réponses pour vérifier les garde-fous."""
import json

import pandas as pd
import pytest

from src import config
from src.ai import client, rapprochement_communes


@pytest.fixture
def contexte(monkeypatch, tmp_path):
    corresp = tmp_path / "correspondances.csv"
    corresp.write_text(config.ENTETE_CORRESPONDANCES, encoding="utf-8")
    monkeypatch.setattr(config, "CORRESPONDANCES", corresp)
    monkeypatch.setattr(config, "EXPORT_DIR", tmp_path)
    monkeypatch.setattr(client, "disponible", lambda: True)
    monkeypatch.setattr(rapprochement_communes, "cas_a_resoudre", lambda: pd.DataFrame(
        {"code_postal": ["74600", "74290", "74999"],
         "commune_source": ["SEYNOD", "TALLOIRES", "VILLAGE IMAGINAIRE"]}))
    monkeypatch.setattr(rapprochement_communes, "candidats", lambda: pd.DataFrame(
        {"code_insee": ["74010", "74275"], "nom_commune": ["Annecy", "Talloires-Montmin"],
         "codes_postaux": ["74000,74600", "74290"]}))
    return corresp


def test_garde_fous_ia(monkeypatch, contexte):
    reponse = [
        {"code_postal": "74600", "commune_source": "SEYNOD", "code_insee": "74010",
         "confiance": 0.97, "justification": "Seynod a fusionné dans Annecy en 2017"},
        # Proposition peu sûre : tracée mais non appliquée
        {"code_postal": "74290", "commune_source": "TALLOIRES", "code_insee": "74275",
         "confiance": 0.6, "justification": "hésitation"},
        # Hallucination : code INSEE hors référentiel -> rejeté
        {"code_postal": "74999", "commune_source": "VILLAGE IMAGINAIRE", "code_insee": "74888",
         "confiance": 0.99, "justification": "inventé"},
    ]
    monkeypatch.setattr(client, "generer", lambda *a, **k: "```json\n" + json.dumps(reponse) + "\n```")

    assert rapprochement_communes.executer() == 1
    table = pd.read_csv(contexte, dtype=str, keep_default_na=False).set_index("commune_source")
    assert table.loc["SEYNOD", "code_insee"] == "74010"
    assert table.loc["SEYNOD", "methode"] == "ia"
    assert table.loc["TALLOIRES", "code_insee"] == ""
    assert table.loc["VILLAGE IMAGINAIRE", "code_insee"] == ""


def test_repli_si_ia_en_panne(monkeypatch, contexte):
    def panne(*a, **k):
        raise ConnectionError("API indisponible")
    monkeypatch.setattr(client, "generer", panne)
    rapprochement_communes.executer()  # ne doit pas lever d'exception
    table = pd.read_csv(contexte, dtype=str, keep_default_na=False).set_index("commune_source")
    assert table.loc["TALLOIRES", "methode"] == "similarite"
    assert table.loc["TALLOIRES", "code_insee"] == "74275"
