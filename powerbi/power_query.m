// =====================================================================
// Requêtes Power Query : une par table (Nouvelle source > Requête vide >
// Éditeur avancé). Prérequis : paramètre texte `DossierExports` se
// terminant par "\". Les types sont appliqués avec la culture "en-US"
// (point décimal) pour être indépendants des paramètres régionaux de Windows.
// =====================================================================

// ---------- Fonction utilitaire : nommer la requête "fnLireCsv" ----------
(nomFichier as text) as table =>
let
    Source = Csv.Document(
        File.Contents(DossierExports & nomFichier),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    AvecEntetes = Table.PromoteHeaders(Source, [PromoteAllScalars = true])
in
    AvecEntetes


// ---------- fct_hebergements_classes ----------
let
    Source = fnLireCsv("fct_hebergements_classes.csv"),
    Types = Table.TransformColumnTypes(Source, {
        {"hebergement_id", type text}, {"code_insee", type text}, {"typologie", type text},
        {"nom_commercial", type text}, {"code_postal", type text}, {"commune_source", type text},
        {"classement", type text}, {"nb_etoiles", Int64.Type}, {"capacite_accueil", Int64.Type},
        {"nb_chambres", Int64.Type}, {"nb_emplacements", Int64.Type},
        {"nb_unites_habitation", Int64.Type}, {"nb_logements", Int64.Type},
        {"date_classement", type date}, {"date_fin_validite", type date},
        {"classement_proroge", type logical}, {"statut_classement", type text},
        {"methode_rapprochement", type text}
    }, "en-US"),
    // Les valeurs vides deviennent null plutôt qu'une erreur
    SansErreurs = Table.ReplaceErrorValues(Types, {
        {"nb_etoiles", null}, {"capacite_accueil", null}, {"nb_chambres", null},
        {"nb_emplacements", null}, {"nb_unites_habitation", null}, {"nb_logements", null},
        {"date_classement", null}, {"date_fin_validite", null}
    })
in
    SansErreurs


// ---------- dim_commune ----------
let
    Source = fnLireCsv("dim_commune.csv"),
    Types = Table.TransformColumnTypes(Source, {
        {"code_insee", type text}, {"nom_commune", type text}, {"population", Int64.Type},
        {"surface_ha", type number}, {"densite_hab_km2", type number},
        {"latitude", type number}, {"longitude", type number},
        {"code_epci", type text}, {"nom_epci", type text}
    }, "en-US"),
    SansErreurs = Table.ReplaceErrorValues(Types, {
        {"population", null}, {"surface_ha", null}, {"densite_hab_km2", null},
        {"latitude", null}, {"longitude", null}
    })
in
    SansErreurs


// ---------- dim_typologie ----------
let
    Source = fnLireCsv("dim_typologie.csv")
in
    Table.TransformColumnTypes(Source, {
        {"typologie", type text}, {"famille", type text}, {"unite_offre", type text}
    })


// ---------- dim_date ----------
let
    Source = fnLireCsv("dim_date.csv")
in
    Table.TransformColumnTypes(Source, {
        {"date_jour", type date}, {"annee", Int64.Type}, {"mois", Int64.Type},
        {"trimestre", Int64.Type}, {"nom_mois", type text}, {"annee_mois", type text},
        {"saison_touristique", type text}
    }, "en-US")


// ---------- mart_qualite_anomalies ----------
let
    Source = fnLireCsv("mart_qualite_anomalies.csv")
in
    Table.TransformColumnTypes(Source, {
        {"anomalie_id", type text}, {"controle", type text}, {"severite", type text},
        {"hebergement_id", type text}, {"nom_commercial", type text}, {"typologie", type text},
        {"code_insee", type text}, {"commune_source", type text}, {"detail", type text},
        {"date_detection", type date}
    }, "en-US")


// ---------- mart_qualite_synthese ----------
let
    Source = fnLireCsv("mart_qualite_synthese.csv")
in
    Table.TransformColumnTypes(Source, {
        {"controle", type text}, {"severite", type text},
        {"nb_etablissements_concernes", Int64.Type}, {"taux_pct", type number}
    }, "en-US")


// ---------- mart_indicateurs_communes ----------
let
    Source = fnLireCsv("mart_indicateurs_communes.csv"),
    Types = Table.TransformColumnTypes(Source, {
        {"code_insee", type text}, {"nom_commune", type text}, {"nom_epci", type text},
        {"population", Int64.Type}, {"nb_etablissements", Int64.Type},
        {"capacite_totale", Int64.Type}, {"taux_fonction_touristique", type number},
        {"part_capacite_departement", type number}
    }, "en-US")
in
    Table.ReplaceErrorValues(Types, {{"population", null}, {"taux_fonction_touristique", null}})


// ---------- mart_suivi_ingestions ----------
let
    Source = fnLireCsv("mart_suivi_ingestions.csv"),
    Types = Table.TransformColumnTypes(Source, {
        {"run_id", type text}, {"table_cible", type text}, {"nb_lignes", Int64.Type},
        {"ingere_le", type datetime}, {"variation", Int64.Type}, {"variation_pct", type number}
    }, "en-US")
in
    Table.ReplaceErrorValues(Types, {{"variation", null}, {"variation_pct", null}})
