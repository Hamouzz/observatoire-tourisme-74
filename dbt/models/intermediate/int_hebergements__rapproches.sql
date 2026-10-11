-- Rattache chaque hébergement à une commune INSEE.
-- La source ne fournit qu'un code postal et un libellé de commune saisi
-- librement (anciennes communes fusionnées, abréviations "ST", tirets...).
-- On applique des règles par ordre de fiabilité décroissante :
--   1. table de correspondance (validée par un humain ou proposée par l'IA)
--   2. code postal + nom de commune normalisé
--   3. nom de commune normalisé, s'il est unique dans le département
--   4. code postal ne desservant qu'une seule commune
-- Ce qui reste est "non rapproché" et part en contrôle qualité / traitement IA.

with hebergements as (
    select * from {{ ref('stg_atout_france__hebergements') }}
),

communes as (
    select code_insee, nom_normalise from {{ ref('stg_geo__communes') }}
),

codes_postaux as (
    select * from {{ ref('stg_geo__codes_postaux') }}
),

correspondances as (
    select
        code_postal,
        {{ normaliser_commune('commune_source') }} as commune_normalisee,
        any_value(code_insee)                     as code_insee,
        any_value(methode)                        as methode
    from {{ source('raw', 'correspondances_communes') }}
    where nullif(code_insee, '') is not null
    group by all
),

regle_cp_nom as (
    select h.hebergement_id, c.code_insee
    from hebergements h
    join codes_postaux cp on cp.code_postal = h.code_postal
    join communes c on c.code_insee = cp.code_insee
                   and c.nom_normalise = h.commune_normalisee
),

noms_uniques as (
    select nom_normalise, min(code_insee) as code_insee
    from communes group by 1 having count(*) = 1
),

regle_nom as (
    select h.hebergement_id, n.code_insee
    from hebergements h
    join noms_uniques n on n.nom_normalise = h.commune_normalisee
),

cp_uniques as (
    select code_postal, min(code_insee) as code_insee
    from codes_postaux group by 1 having count(*) = 1
),

regle_cp as (
    select h.hebergement_id, u.code_insee
    from hebergements h
    join cp_uniques u on u.code_postal = h.code_postal
)

select
    h.*,
    coalesce(k.code_insee, r1.code_insee, r2.code_insee, r3.code_insee) as code_insee,
    case
        when k.code_insee  is not null then 'table de correspondance (' || k.methode || ')'
        when r1.code_insee is not null then 'code postal + nom'
        when r2.code_insee is not null then 'nom de commune'
        when r3.code_insee is not null then 'code postal unique'
        else 'non rapproché'
    end as methode_rapprochement
from hebergements h
left join correspondances k
       on k.code_postal = h.code_postal and k.commune_normalisee = h.commune_normalisee
left join regle_cp_nom r1 on r1.hebergement_id = h.hebergement_id
left join regle_nom    r2 on r2.hebergement_id = h.hebergement_id
left join regle_cp     r3 on r3.hebergement_id = h.hebergement_id
