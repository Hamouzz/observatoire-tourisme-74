-- Contrôles automatisés de cohérence : une ligne par anomalie détectée.
-- Contrairement aux tests dbt (qui bloquent ou alertent le run), cette table
-- est exploitée dans Power BI (page "Qualité des données") et dans Excel
-- pour que l'équipe puisse traiter les anomalies une par une.
--
-- Sévérités : 'Bloquante' (chiffre faux), 'Avertissement' (à vérifier), 'Info'.

{% set ref_date = date_reference() %}

with f as (
    select * from {{ ref('fct_hebergements_classes') }}
),
s as (
    select hebergement_id, commune_normalisee, nb_occurrences_source
    from {{ ref('stg_atout_france__hebergements') }}
),

controles as (

    select hebergement_id, 'Commune non rapprochée' as controle, 'Bloquante' as severite,
           'Code postal ' || code_postal || ' / libellé "' || commune_source
           || '" sans correspondance INSEE' as detail
    from f where code_insee = '99999'

    union all
    select hebergement_id, 'Rapprochement indirect', 'Info',
           '"' || commune_source || '" rattachée via ' || methode_rapprochement
    from f where methode_rapprochement in ('code postal unique')

    union all
    select hebergement_id, 'Capacité manquante', 'Bloquante',
           'Capacité d''accueil absente ou nulle'
    from f where coalesce(capacite_accueil, 0) = 0

    union all
    select hebergement_id, 'Ratio capacité / chambre incohérent', 'Avertissement',
           capacite_accueil || ' personnes pour ' || nb_chambres || ' chambres ('
           || round(capacite_accueil / nb_chambres, 1) || ' par chambre, attendu 1 à 5)'
    from f
    where typologie = 'HÔTEL DE TOURISME' and nb_chambres > 0
      and (capacite_accueil / nb_chambres > 5 or capacite_accueil / nb_chambres < 1)

    union all
    select hebergement_id, 'Ratio capacité / emplacement incohérent', 'Avertissement',
           capacite_accueil || ' personnes pour ' || nb_emplacements || ' emplacements'
    from f
    where typologie in ('CAMPING', 'PARC RÉSIDENTIEL DE LOISIRS') and nb_emplacements > 0
      and (capacite_accueil / nb_emplacements > 8 or capacite_accueil / nb_emplacements < 1)

    union all
    select hebergement_id, 'Unité d''offre manquante', 'Avertissement',
           'Typologie ' || typologie || ' sans nombre de '
           || case when typologie = 'HÔTEL DE TOURISME' then 'chambres' else 'emplacements' end
    from f
    where (typologie = 'HÔTEL DE TOURISME' and nb_chambres is null)
       or (typologie = 'CAMPING' and nb_emplacements is null)

    union all
    select f.hebergement_id, 'Doublon dans la source', 'Avertissement',
           'Ligne présente ' || s.nb_occurrences_source || ' fois dans le fichier Atout France'
    from f join s using (hebergement_id)
    where s.nb_occurrences_source > 1

    union all
    select hebergement_id, 'Date de classement future', 'Bloquante',
           'Classé le ' || strftime(date_classement, '%d/%m/%Y')
    from f where date_classement > {{ ref_date }}

    union all
    select hebergement_id, 'Classement expiré', 'Info',
           'Classement du ' || strftime(date_classement, '%d/%m/%Y') || ' échu le '
           || strftime(date_fin_validite, '%d/%m/%Y')
    from f where statut_classement = 'Expiré'

    union all
    select hebergement_id, 'Site internet invalide', 'Info',
           'Valeur : "' || site_internet || '"'
    from f
    where site_internet is not null
      and not regexp_matches(site_internet, '^https?://[^\s/]+\.[a-z]{2,}(/\S*)?$', 'i')
)

select
    md5(c.hebergement_id || c.controle)  as anomalie_id,
    c.controle,
    c.severite,
    c.hebergement_id,
    f.nom_commercial,
    f.typologie,
    f.code_insee,
    f.commune_source,
    c.detail,
    {{ ref_date }}                       as date_detection
from controles c
join f using (hebergement_id)
