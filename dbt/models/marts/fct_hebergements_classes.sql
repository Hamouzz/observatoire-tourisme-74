-- Table de faits : un établissement classé (grain = hebergement_id).
with h as (
    select * from {{ ref('int_hebergements__rapproches') }}
)

select
    hebergement_id,
    coalesce(code_insee, '99999')                                        as code_insee,
    typologie,
    nom_commercial,
    adresse,
    code_postal,
    commune_source,
    classement,
    nb_etoiles,
    categorie,
    capacite_accueil,
    nb_chambres,
    nb_emplacements,
    nb_unites_habitation,
    nb_logements,
    date_classement,
    cast(date_classement + to_years({{ var('duree_validite_classement') }}) as date) as date_fin_validite,
    classement_proroge,
    case
        when date_classement is null then 'Date inconnue'
        when classement_proroge then 'Prorogé'
        when date_classement + to_years({{ var('duree_validite_classement') }}) < {{ date_reference() }}
            then 'Expiré'
        when date_classement + to_years({{ var('duree_validite_classement') }})
             < {{ date_reference() }} + interval 6 month
            then 'Expire sous 6 mois'
        else 'Valide'
    end                                                                  as statut_classement,
    site_internet,
    methode_rapprochement,
    fichier_source
from h
