-- Test de réconciliation : la capacité totale agrégée par commune doit être
-- égale à la capacité totale de la table de faits (aucune perte en jointure).
select *
from (
    select
        (select coalesce(sum(capacite_accueil), 0) from {{ ref('fct_hebergements_classes') }}) as total_faits,
        (select sum(capacite_totale) from {{ ref('mart_indicateurs_communes') }})               as total_communes
)
where total_faits <> total_communes
