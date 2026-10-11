# Mesures DAX

À créer dans une table **Mesures** dédiée. Les formats conseillés sont indiqués en commentaire.

## Offre

```dax
Établissements = COUNTROWS ( fct_hebergements_classes )
-- Format : nombre entier, séparateur de milliers

Capacité totale = SUM ( fct_hebergements_classes[capacite_accueil] )
-- Format : nombre entier, séparateur de milliers

Population =
-- La population est portée par la dimension : elle n'est pas filtrée par la typologie,
-- ce qui est voulu (le dénominateur reste la population de la commune).
SUM ( dim_commune[population] )

Taux de fonction touristique =
-- Lits touristiques classés pour 100 habitants.
-- > 100 : la commune peut accueillir plus de touristes qu'elle ne compte d'habitants (station).
DIVIDE ( [Capacité totale], [Population] ) * 100
-- Format : décimal, 1 décimale

Part de la capacité départementale =
DIVIDE (
    [Capacité totale],
    CALCULATE ( [Capacité totale], REMOVEFILTERS ( dim_commune ) )
)
-- Format : pourcentage, 1 décimale

Capacité moyenne par établissement = DIVIDE ( [Capacité totale], [Établissements] )

Étoiles moyennes (hôtels) =
CALCULATE (
    AVERAGE ( fct_hebergements_classes[nb_etoiles] ),
    dim_typologie[famille] = "Hôtellerie"
)
-- Format : décimal, 1 décimale
```

## Classements

```dax
Classements à renouveler =
CALCULATE (
    [Établissements],
    fct_hebergements_classes[statut_classement] IN { "Expiré", "Expire sous 6 mois" }
)

Classements expirant dans 6 mois =
CALCULATE ( [Établissements], fct_hebergements_classes[statut_classement] = "Expire sous 6 mois" )

% classements à renouveler = DIVIDE ( [Classements à renouveler], [Établissements] )
-- Format : pourcentage

Classements sur 12 mois glissants =
-- Nombre d'établissements (re)classés sur les 12 mois précédant la dernière date du contexte
CALCULATE (
    [Établissements],
    DATESINPERIOD ( dim_date[date_jour], MAX ( dim_date[date_jour] ), -12, MONTH )
)

Classements N-1 =
CALCULATE ( [Établissements], SAMEPERIODLASTYEAR ( dim_date[date_jour] ) )

Évolution classements vs N-1 =
DIVIDE ( [Établissements] - [Classements N-1], [Classements N-1] )
-- Format : pourcentage
```

## Qualité des données

```dax
Anomalies = COUNTROWS ( mart_qualite_anomalies )

Anomalies bloquantes =
CALCULATE ( [Anomalies], mart_qualite_anomalies[severite] = "Bloquante" )

Établissements avec anomalie bloquante =
CALCULATE (
    DISTINCTCOUNT ( mart_qualite_anomalies[hebergement_id] ),
    mart_qualite_anomalies[severite] = "Bloquante"
)

Taux de fiabilité =
-- Part des établissements sans anomalie bloquante
1 - DIVIDE ( [Établissements avec anomalie bloquante], [Établissements] )
-- Format : pourcentage, 1 décimale

Contrôle de réconciliation =
-- Compare le total calculé par Power BI à celui calculé par dbt.
-- Deux chemins de calcul indépendants : s'ils divergent, une jointure ou un filtre a perdu des lignes.
VAR TotalPowerBI = CALCULATE ( [Capacité totale], REMOVEFILTERS () )
VAR TotalDbt = SUM ( mart_indicateurs_communes[capacite_totale] )
RETURN
    IF ( TotalPowerBI = TotalDbt, "✔ Totaux réconciliés", "✖ Écart : " & FORMAT ( TotalPowerBI - TotalDbt, "# ##0" ) )
```

## Libellés dynamiques

```dax
Titre dynamique =
VAR Territoire =
    SELECTEDVALUE ( dim_commune[nom_commune],
        SELECTEDVALUE ( dim_commune[nom_epci], "Haute-Savoie" ) )
RETURN
    "Offre d'hébergement classée - " & Territoire

Date des données =
"Données Atout France au " & FORMAT ( MAX ( mart_suivi_ingestions[ingere_le] ), "dd/mm/yyyy" )
```
