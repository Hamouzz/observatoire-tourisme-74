-- Dimension commune, avec un membre "inconnu" pour les hébergements non rapprochés
-- (bonne pratique : aucune ligne de fait ne doit pointer dans le vide).
select
    code_insee, nom_commune, population, surface_ha,
    round(population / nullif(surface_ha / 100, 0), 1) as densite_hab_km2,
    latitude, longitude, code_epci, nom_epci
from {{ ref('stg_geo__communes') }}

union all

select '99999', 'Commune non identifiée', null, null, null, null, null, null, 'Non renseigné'
