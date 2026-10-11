"""Accès au modèle de langage (optionnel).

Sans clé API, `disponible()` renvoie False et chaque usage de l'IA
bascule sur une méthode déterministe : le pipeline ne dépend jamais de l'IA
pour fonctionner.
"""
from __future__ import annotations

import json
import logging
import re

from src import config

log = logging.getLogger(__name__)


def disponible() -> bool:
    return bool(config.ANTHROPIC_API_KEY)


def generer(prompt: str, systeme: str, max_tokens: int = 2000) -> str:
    import anthropic  # import local : dépendance inutile sans clé

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    reponse = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        system=systeme,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in reponse.content if b.type == "text")


def extraire_json(texte: str):
    """Récupère le premier bloc JSON d'une réponse (avec ou sans ```json)."""
    bloc = re.search(r"```(?:json)?\s*(.*?)```", texte, re.S)
    brut = bloc.group(1) if bloc else texte
    debut = min((i for i in (brut.find("["), brut.find("{")) if i >= 0), default=0)
    return json.loads(brut[debut:])
