-- Indicateurs d'offre par commune, prêts pour Excel et pour contrôle croisé Power BI.
-- Taux de fonction touristique = lits marchands classés / population x 100
-- (indicateur classique des observatoires ; ici limité à l'offre classée,
--  hors résidences secondaires et meublés).
with offre as (
    select
        f.code_insee,
        count(*)                                                          as nb_etablissements,
        sum(f.capacite_accueil)                                           as capacite_totale,
        sum(case when t.famille = 'Hôtellerie' then f.capacite_accueil end)              as capacite_hotellerie,
        sum(case when t.famille = 'Hôtellerie de plein air' then f.capacite_accueil end) as capacite_plein_air,
        sum(case when t.famille = 'Résidences et villages' then f.capacite_accueil end)  as capacite_residences,
        sum(case when t.famille = 'Hébergement collectif' then f.capacite_accueil end)   as capacite_collectif,
        sum(f.nb_chambres)                                                as nb_chambres_hotel,
        round(avg(case when t.famille = 'Hôtellerie' then f.nb_etoiles end), 1) as etoiles_moyennes_hotels,
        count(*) filter (where f.statut_classement in ('Expiré', 'Expire sous 6 mois'))  as nb_classements_a_renouveler
    from {{ ref('fct_hebergements_classes') }} f
    join {{ ref('dim_typologie') }} t using (typologie)
    group by 1
)

select
    c.code_insee,
    c.nom_commune,
    c.nom_epci,
    c.population,
    coalesce(o.nb_etablissements, 0)   as nb_etablissements,
    coalesce(o.capacite_totale, 0)     as capacite_totale,
    coalesce(o.capacite_hotellerie, 0) as capacite_hotellerie,
    coalesce(o.capacite_plein_air, 0)  as capacite_plein_air,
    coalesce(o.capacite_residences, 0) as capacite_residences,
    coalesce(o.capacite_collectif, 0)  as capacite_collectif,
    coalesce(o.nb_chambres_hotel, 0)   as nb_chambres_hotel,
    o.etoiles_moyennes_hotels,
    coalesce(o.nb_classements_a_renouveler, 0) as nb_classements_a_renouveler,
    round(100.0 * coalesce(o.capacite_totale, 0) / nullif(c.population, 0), 1) as taux_fonction_touristique,
    round(100.0 * coalesce(o.capacite_totale, 0)
          / nullif(sum(coalesce(o.capacite_totale, 0)) over (), 0), 2)          as part_capacite_departement
from {{ ref('dim_commune') }} c
left join offre o using (code_insee)
