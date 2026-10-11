-- Calendrier avec saisons touristiques de montagne / lac.
with jours as (
    select cast(range as date) as date_jour
    from range(date '2010-01-01', date '2033-01-01', interval 1 day)
)
select
    date_jour,
    year(date_jour)                                       as annee,
    month(date_jour)                                      as mois,
    quarter(date_jour)                                    as trimestre,
    ['janvier','février','mars','avril','mai','juin','juillet','août',
     'septembre','octobre','novembre','décembre'][month(date_jour)] as nom_mois,
    strftime(date_jour, '%Y-%m')                          as annee_mois,
    case
        when month(date_jour) in (12, 1, 2, 3, 4) then 'Hiver'
        when month(date_jour) in (6, 7, 8, 9)     then 'Été'
        else 'Intersaison'
    end                                                   as saison_touristique
from jours
