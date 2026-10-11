-- Nettoyage et typage des hébergements classés.
-- Un hébergement = un nom commercial + adresse + code postal + typologie.
-- Les doublons exacts de la source sont dédoublonnés ici mais comptés
-- (nb_occurrences_source) pour être remontés dans le contrôle qualité.

with source as (
    select * from {{ source('raw', 'hebergements_classes') }}
),

nettoye as (
    select
        -- La source publie les dates au format JJ/MM/AAAA ; on accepte aussi l'ISO
        coalesce(
            cast(try_strptime(trim(date_classement), '%d/%m/%Y') as date),
            try_cast(nullif(trim(date_classement), '') as date)
        )                                                              as date_classement,
        upper(trim(typologie))                                         as typologie,
        nullif(nullif(trim(classement), '-'), '')                      as classement,
        try_cast(nullif(regexp_extract(classement, '(\d)', 1), '') as integer) as nb_etoiles,
        nullif(nullif(trim(categorie), '-'), '')                       as categorie,
        nullif(nullif(trim(mention), '-'), '')                         as mention,
        trim(nom_commercial)                                           as nom_commercial,
        nullif(nullif(trim(adresse), '-'), '')                         as adresse,
        lpad(trim(code_postal), 5, '0')                                as code_postal,
        upper(trim(commune))                                           as commune_source,
        {{ normaliser_commune('commune') }}                            as commune_normalisee,
        -- 'www.exemple.fr' -> 'https://www.exemple.fr' (protocole manquant = cas courant, pas une erreur)
        case
            when nullif(nullif(trim(site_internet), '-'), '') is null then null
            when regexp_matches(trim(site_internet), '^https?://', 'i') then trim(site_internet)
            else 'https://' || trim(site_internet)
        end                                                            as site_internet,
        nullif(nullif(trim(type_sejour), '-'), '')                     as type_sejour,
        {{ entier_ou_null('capacite_accueil') }}                       as capacite_accueil,
        {{ entier_ou_null('nb_chambres') }}                            as nb_chambres,
        {{ entier_ou_null('nb_emplacements') }}                        as nb_emplacements,
        {{ entier_ou_null('nb_unites_habitation') }}                   as nb_unites_habitation,
        {{ entier_ou_null('nb_logements') }}                           as nb_logements,
        lower(trim(classement_proroge)) in ('true', '1', 'oui', 'vrai') as classement_proroge,
        _fichier_source                                                as fichier_source,
        try_cast(_ingere_le as timestamp)                              as ingere_le
    from source
),

identifie as (
    select
        md5(concat_ws('|', upper(nom_commercial), coalesce(upper(adresse), ''),
                      code_postal, typologie))                         as hebergement_id,
        *
    from nettoye
)

select
    *,
    count(*) over (partition by hebergement_id)                        as nb_occurrences_source
from identifie
qualify row_number() over (
    partition by hebergement_id order by date_classement desc nulls last
) = 1
