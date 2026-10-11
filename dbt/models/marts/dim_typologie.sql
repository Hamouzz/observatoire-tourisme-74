select
    typologie,
    case typologie
        when 'HÔTEL DE TOURISME'           then 'Hôtellerie'
        when 'CAMPING'                     then 'Hôtellerie de plein air'
        when 'PARC RÉSIDENTIEL DE LOISIRS' then 'Hôtellerie de plein air'
        when 'RÉSIDENCE DE TOURISME'       then 'Résidences et villages'
        when 'VILLAGE DE VACANCES'         then 'Résidences et villages'
        when 'AUBERGE COLLECTIVE'          then 'Hébergement collectif'
        else 'Autre'
    end as famille,
    case typologie
        when 'HÔTEL DE TOURISME'           then 'chambres'
        when 'CAMPING'                     then 'emplacements'
        when 'PARC RÉSIDENTIEL DE LOISIRS' then 'emplacements'
        when 'RÉSIDENCE DE TOURISME'       then 'unités d''habitation'
        when 'VILLAGE DE VACANCES'         then 'logements'
        else 'lits'
    end as unite_offre
from (select distinct typologie from {{ ref('stg_atout_france__hebergements') }})
