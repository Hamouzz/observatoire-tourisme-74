import pytest

from src.extract import atout_france


def test_normaliser_nom():
    assert atout_france.normaliser_nom("CAPACITÉ D'ACCUEIL (PERSONNES)") == "capacite_d_accueil_personnes"


def test_mapper_colonnes_reelles():
    colonnes = ["DATE DE CLASSEMENT", "TYPOLOGIE ÉTABLISSEMENT", "CLASSEMENT", "NOM COMMERCIAL",
                "CODE POSTAL", "COMMUNE", "CAPACITÉ D'ACCUEIL (PERSONNES)", "classement prorogé"]
    mapping = atout_france.mapper_colonnes(colonnes)
    assert mapping["CLASSEMENT"] == "classement"
    assert mapping["classement prorogé"] == "classement_proroge"
    assert mapping["CAPACITÉ D'ACCUEIL (PERSONNES)"] == "capacite_accueil"


def test_schema_modifie_detecte():
    with pytest.raises(ValueError, match="Schéma source modifié"):
        atout_france.mapper_colonnes(["NOM COMMERCIAL", "COMMUNE"])


@pytest.mark.parametrize("sep", [";", ","])
def test_lecture_separateur(sep):
    contenu = f"NOM COMMERCIAL{sep}COMMUNE\nHÔTEL A{sep}ANNECY\n".encode("utf-8")
    df = atout_france.lire_csv(contenu)
    assert list(df.columns) == ["NOM COMMERCIAL", "COMMUNE"]
    assert df.iloc[0]["COMMUNE"] == "ANNECY"


def test_lecture_encodage_windows():
    contenu = "NOM COMMERCIAL;COMMUNE\nHÔTEL A;MEGÈVE\n".encode("cp1252")
    assert atout_france.lire_csv(contenu).iloc[0]["COMMUNE"] == "MEGÈVE"


def test_json_ecrit_sous_windows_relu(tmp_path):
    """Un communes.json écrit en cp1252 par une ancienne version doit rester lisible."""
    from src.extract import geo_api
    (tmp_path / "communes.json").write_text('[{"nom": "Arâches-la-Frasse"}]', encoding="cp1252")
    (tmp_path / "epcis.json").write_text("[]", encoding="utf-8")
    communes, _ = geo_api.lire_fichiers(tmp_path)
    assert communes[0]["nom"] == "Arâches-la-Frasse"
