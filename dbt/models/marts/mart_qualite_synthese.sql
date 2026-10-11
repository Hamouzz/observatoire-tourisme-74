-- Taux d'anomalies par contrôle : l'indicateur de santé du jeu de données.
with total as (select count(*) as nb from {{ ref('fct_hebergements_classes') }})
select
    a.controle,
    a.severite,
    count(distinct a.hebergement_id)                                   as nb_etablissements_concernes,
    round(100.0 * count(distinct a.hebergement_id) / total.nb, 2)      as taux_pct
from {{ ref('mart_qualite_anomalies') }} a, total
group by a.controle, a.severite, total.nb
order by case a.severite when 'Bloquante' then 1 when 'Avertissement' then 2 else 3 end,
         nb_etablissements_concernes desc
