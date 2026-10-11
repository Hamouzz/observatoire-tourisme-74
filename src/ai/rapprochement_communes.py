"""Rapprochement assisté par IA des communes non identifiées.

Problème métier : la source Atout France contient un libellé de commune saisi
librement. Les communes fusionnées (ex. Seynod ou Annecy-le-Vieux, devenues
Annecy en 2017 ; Talloires devenue Talloires-Montmin en 2016) ne se retrouvent
pas dans le référentiel INSEE actuel et faussent les indicateurs communaux.

Démarche :
1. dbt applique d'abord des règles déterministes ;
2. les cas restants sont soumis au modèle de langage, avec la liste fermée des
   communes candidates (il ne peut pas inventer un code INSEE : toute réponse
   hors liste est rejetée) ;
3. les propositions sont écrites dans `referentiels/correspondances_communes.csv`,
   versionné dans Git : un humain peut relire, corriger ou valider la
   correspondance (revue de code), et le run suivant l'applique.
Sans clé API, on utilise une similarité de chaînes (rapidfuzz) en repli.
"""
from __future__ import annotations

import json
import logging
import unicodedata

import pandas as pd
from rapidfuzz import fuzz, process, utils

from src import config, load
from src.ai import client

log = logging.getLogger(__name__)

SYSTEME = (
    "Tu es un expert du découpage communal français (fusions de communes, "
    "communes nouvelles, communes déléguées, codes postaux). Tu réponds "
    "uniquement en JSON valide, sans texte autour."
)


def cas_a_resoudre() -> pd.DataFrame:
    return load.lire("""
        select distinct f.code_postal, f.commune_source
        from marts.fct_hebergements_classes f
        where f.code_insee = '99999'
    """)


def candidats() -> pd.DataFrame:
    return load.lire("""
        select c.code_insee, c.nom_commune,
               string_agg(cp.code_postal, ',' order by cp.code_postal) as codes_postaux
        from staging.stg_geo__communes c
        left join staging.stg_geo__codes_postaux cp using (code_insee)
        group by all
    """)


def _par_ia(cas: pd.DataFrame, ref: pd.DataFrame) -> list[dict]:
    prompt = f"""Rattache chaque libellé de commune (issu d'un fichier d'hébergements
touristiques du département {config.DEPARTEMENT}) à une commune ACTUELLE du référentiel ci-dessous.
Cas fréquents : ancienne commune fusionnée dans une commune nouvelle, abréviation,
faute de frappe, nom de station ou de hameau.

Référentiel (code_insee;nom;codes_postaux) :
{ref.to_csv(sep=';', index=False)}

Cas à rattacher (code_postal;commune_source) :
{cas.to_csv(sep=';', index=False)}

Réponds par un tableau JSON, un objet par cas :
[{{"code_postal": "...", "commune_source": "...", "code_insee": "<code du référentiel ou null>",
  "confiance": <0 à 1>, "justification": "<courte explication>"}}]
Mets code_insee à null et une confiance basse si tu n'es pas sûr."""
    reponse = client.generer(prompt, SYSTEME)
    return client.extraire_json(reponse)


def _sans_accents(texte: str) -> str:
    """'ÉPAGNY' -> 'epagny' : comparaison insensible aux accents, à la casse et à la ponctuation."""
    texte = unicodedata.normalize("NFKD", str(texte)).encode("ascii", "ignore").decode()
    return utils.default_process(texte)


def _par_similarite(cas: pd.DataFrame, ref: pd.DataFrame) -> list[dict]:
    propositions = []
    for _, ligne in cas.iterrows():
        # On privilégie les communes desservies par le même code postal
        meme_cp = ref[ref["codes_postaux"].fillna("").str.contains(ligne.code_postal)]
        pool = meme_cp if not meme_cp.empty else ref
        meilleur = process.extractOne(ligne.commune_source.upper(),
                                      pool["nom_commune"].str.upper().tolist(),
                                      scorer=fuzz.token_set_ratio,
                                      processor=_sans_accents)
        if meilleur and meilleur[1] >= 85:
            code = pool.iloc[meilleur[2]]["code_insee"]
            propositions.append({
                "code_postal": ligne.code_postal, "commune_source": ligne.commune_source,
                "code_insee": code, "confiance": round(meilleur[1] / 100, 2),
                "justification": f"similarité de libellé avec {meilleur[0]} ({meilleur[1]:.0f}/100)",
            })
        else:
            propositions.append({
                "code_postal": ligne.code_postal, "commune_source": ligne.commune_source,
                "code_insee": None, "confiance": 0.0,
                "justification": "aucune commune suffisamment proche",
            })
    return propositions


def executer() -> int:
    """Retourne le nombre de nouvelles correspondances appliquées."""
    cas = cas_a_resoudre()
    if cas.empty:
        log.info("Rapprochement : aucune commune à résoudre")
        return 0
    ref = candidats()
    methode = "ia" if client.disponible() else "similarite"
    log.info("Rapprochement de %d libellé(s) par %s", len(cas), methode)
    try:
        propositions = _par_ia(cas, ref) if methode == "ia" else _par_similarite(cas, ref)
    except Exception as exc:  # l'IA ne doit jamais casser le pipeline
        log.warning("Échec de l'appel IA (%s) : repli sur la similarité", exc)
        methode, propositions = "similarite", _par_similarite(cas, ref)

    codes_valides = set(ref["code_insee"])
    seed = pd.read_csv(config.CORRESPONDANCES, dtype=str, keep_default_na=False)
    nouvelles = []
    for p in propositions:
        code = p.get("code_insee")
        if code and code not in codes_valides:  # garde-fou : pas de code inventé
            log.warning("Code INSEE %s proposé hors référentiel : rejeté", code)
            code = None
        confiance = float(p.get("confiance") or 0)
        applique = code is not None and confiance >= config.SEUIL_CONFIANCE_IA
        log.info("  %s %s -> %s (confiance %.2f) %s", p["code_postal"], p["commune_source"],
                 code, confiance, "appliqué" if applique else "à revoir manuellement")
        nouvelles.append({
            "code_postal": p["code_postal"], "commune_source": p["commune_source"],
            # Sous le seuil, on garde la trace sans l'appliquer (code_insee vide)
            "code_insee": code if applique else "",
            "methode": methode, "confiance": confiance,
            "justification": (p.get("justification") or "")
                             + ("" if applique or not code else f" | proposition non appliquée : {code}"),
        })

    # On ne touche jamais aux correspondances déjà résolues (validées par un humain).
    # Les cas restés sans code sont retentés à chaque run (ex. après ajout d'une clé API).
    resolues = seed[seed["code_insee"].fillna("") != ""]
    deja = set(zip(resolues["code_postal"], resolues["commune_source"]))
    nouvelles = [n for n in nouvelles if (n["code_postal"], n["commune_source"]) not in deja]
    if nouvelles:
        seed = pd.concat([resolues, pd.DataFrame(nouvelles)], ignore_index=True)
        seed.to_csv(config.CORRESPONDANCES, index=False, encoding="utf-8")
    (config.EXPORT_DIR / "propositions_rapprochement.json").write_text(
        json.dumps(propositions, ensure_ascii=False, indent=2), encoding="utf-8")
    return sum(1 for n in nouvelles if n["code_insee"])
