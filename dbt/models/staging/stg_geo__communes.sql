select
    code_insee,
    nom                                         as nom_commune,
    {{ normaliser_commune('nom') }}             as nom_normalise,
    cast(population as integer)                 as population,
    cast(surface_ha as double)                  as surface_ha,
    cast(latitude as double)                    as latitude,
    cast(longitude as double)                   as longitude,
    code_epci,
    coalesce(nom_epci, 'Non renseigné')         as nom_epci
from {{ source('raw', 'communes') }}
