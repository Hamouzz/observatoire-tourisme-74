-- Historique des chargements et variation de volumétrie d'un run à l'autre.
select
    run_id,
    table_cible,
    nb_lignes,
    ingere_le,
    nb_lignes - lag(nb_lignes) over w                                   as variation,
    round(100.0 * (nb_lignes - lag(nb_lignes) over w)
          / nullif(lag(nb_lignes) over w, 0), 1)                        as variation_pct
from {{ source('raw', 'journal_ingestion') }}
window w as (partition by table_cible order by ingere_le)
