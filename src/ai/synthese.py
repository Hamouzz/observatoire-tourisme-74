"""Note de synthèse rédigée automatiquement à partir des indicateurs.

Usage type pour un observatoire : chaque mois, une destination reçoit ses
chiffres ET un commentaire lisible par un élu ou un directeur d'office de
tourisme. L'IA rédige ; les chiffres viennent exclusivement des marts
(on lui interdit d'en inventer et on lui fournit tout ce qu'elle peut citer).
Sans clé API, un texte à trous déterministe est produit.
"""
from __future__ import annotations

import json
import logging
from datetime import date

from src import config, load
from src.ai import client

log = logging.getLogger(__name__)

SYSTEME = (
    "Tu es chargé d'études dans un observatoire du tourisme. Tu rédiges des notes "
    "courtes, factuelles et claires pour des élus et directeurs d'offices de tourisme. "
    "Tu n'utilises QUE les chiffres fournis, sans en calculer de nouveaux ni en inventer."
)


def collecter_indicateurs() -> dict:
    kpi = load.lire("""
        select count(*) as nb_etablissements,
               sum(capacite_accueil) as capacite_totale,
               count(*) filter (where statut_classement = 'Expiré') as nb_expires,
               count(*) filter (where statut_classement = 'Expire sous 6 mois') as nb_expire_6_mois
        from marts.fct_hebergements_classes
    """).iloc[0].to_dict()
    familles = load.lire("""
        select t.famille, count(*) as nb, sum(f.capacite_accueil) as capacite
        from marts.fct_hebergements_classes f join marts.dim_typologie t using (typologie)
        group by 1 order by capacite desc nulls last
    """).to_dict("records")
    top = load.lire("""
        select nom_commune, capacite_totale, taux_fonction_touristique
        from marts.mart_indicateurs_communes where code_insee <> '99999'
        order by capacite_totale desc limit 5
    """).to_dict("records")
    qualite = load.lire("select * from marts.mart_qualite_synthese").to_dict("records")
    return {
        "departement": config.DEPARTEMENT,
        "date": date.today().isoformat(),
        "kpi": {k: int(v) if v == v and v is not None else None for k, v in kpi.items()},
        "familles": familles,
        "top_communes_capacite": top,
        "qualite": qualite,
    }


def _nb(valeur) -> str:
    """12345 -> '12 345' (format français)."""
    return f"{int(valeur or 0):,}".replace(",", "\u202f")


def _modele(ind: dict) -> str:
    k = ind["kpi"]
    lignes = [
        f"# Offre d'hébergement classée - département {ind['departement']}",
        f"*Données au {ind['date']}*", "",
        f"Le département compte **{_nb(k['nb_etablissements'])} établissements classés** "
        f"pour une capacité de **{_nb(k['capacite_totale'])} personnes**.", "",
        "## Répartition par famille",
    ]
    lignes += [f"- {f['famille']} : {_nb(f['nb'])} établissements, {_nb(f['capacite'])} personnes"
               for f in ind["familles"]]
    lignes += ["", "## Principales communes"]
    lignes += [f"- {c['nom_commune']} : {_nb(c['capacite_totale'])} personnes "
               f"(taux de fonction touristique : {c['taux_fonction_touristique']} lits pour 100 habitants)"
               for c in ind["top_communes_capacite"]]
    bloquantes = sum(q["nb_etablissements_concernes"] for q in ind["qualite"]
                     if q["severite"] == "Bloquante")
    lignes += ["", "## Points d'attention",
               f"- {k['nb_expires']} classement(s) expiré(s) et {k['nb_expire_6_mois']} "
               "à renouveler dans les 6 mois.",
               f"- {bloquantes} anomalie(s) bloquante(s) de qualité des données à traiter."]
    return "\n".join(lignes)


def executer() -> str:
    ind = collecter_indicateurs()
    texte = None
    if client.disponible():
        prompt = (
            "Rédige une note de synthèse en markdown (250 mots maximum) sur l'offre "
            "d'hébergement touristique classée, avec : un titre, un paragraphe de chiffres "
            "clés, les communes qui concentrent l'offre, un point sur les classements à "
            "renouveler (enjeu d'accompagnement des hébergeurs) et un point sur la qualité "
            "des données. Indicateurs (JSON) :\n"
            + json.dumps(ind, ensure_ascii=False, default=str, indent=1)
        )
        try:
            texte = client.generer(prompt, SYSTEME, max_tokens=1200)
            texte += "\n\n*Note rédigée automatiquement par IA à partir des indicateurs du pipeline.*"
        except Exception as exc:
            log.warning("Synthèse IA indisponible (%s) : texte modèle utilisé", exc)
    if texte is None:
        texte = _modele(ind)
    (config.EXPORT_DIR / "synthese.md").write_text(texte, encoding="utf-8")
    log.info("Note de synthèse écrite (%s)", "IA" if client.disponible() else "modèle")
    return texte
