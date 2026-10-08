"""Contenu propre à chaque type de compte-rendu de cérémonie Scrum.

Le contenu est stocké en JSON dans MeetingReport.content_json ; ces modèles
le valident à l'écriture et lui donnent des valeurs par défaut à la lecture
(un compte-rendu créé avant l'ajout d'un champ reste lisible).

Les listes à puces (objectifs, points de la rétrospective, notes...) sont
saisies en texte libre : une ligne par point, une ligne indentée (espaces ou
tabulation) devient un sous-point — voir `parse_bullets`.
"""

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

REPORT_TYPES = ("daily", "sprint_planning", "sprint_review", "retrospective")
ReportType = Literal["daily", "sprint_planning", "sprint_review", "retrospective"]

REPORT_TYPE_LABELS = {
    "daily": "Daily",
    "sprint_planning": "Planification de sprint",
    "sprint_review": "Review de sprint",
    "retrospective": "Rétrospective",
}

# Position du point rouge sur le diagramme Temps / Qualité / Respect du cahier
# des charges du daily : au centre quand les trois contraintes sont tenues, à
# l'intersection de deux cercles ou dans un seul cercle sinon.
BALANCE_VALUES = ("all", "time_quality", "time_scope", "quality_scope", "time", "quality", "scope")
Balance = Literal["all", "time_quality", "time_scope", "quality_scope", "time", "quality", "scope"]

LONG_TEXT = 10000


class UserStoryRow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reference: str = Field(default="", max_length=50)
    name: str = Field(default="", max_length=500)


class _Content(BaseModel):
    model_config = ConfigDict(extra="ignore")

    participant_ids: list[int] = Field(default_factory=list, max_length=100)


class DailyContent(_Content):
    scrum_master_notes: str = Field(default="", max_length=LONG_TEXT)
    balance: Balance = "all"


class SprintPlanningContent(_Content):
    client: str = Field(default="", max_length=200)
    topics: str = Field(default="", max_length=LONG_TEXT)
    hours_per_member: float | None = Field(default=None, ge=0, le=10000)
    user_stories: list[UserStoryRow] = Field(default_factory=list, max_length=300)


class SprintReviewContent(_Content):
    client: str = Field(default="", max_length=200)
    objectives: str = Field(default="", max_length=LONG_TEXT)
    user_stories: list[UserStoryRow] = Field(default_factory=list, max_length=300)


class RetrospectiveContent(_Content):
    scrum_master: str = Field(default="", max_length=200)
    product_owner: str = Field(default="", max_length=200)
    went_well: str = Field(default="", max_length=LONG_TEXT)
    to_improve: str = Field(default="", max_length=LONG_TEXT)
    actions: str = Field(default="", max_length=LONG_TEXT)
    product_owner_notes: str = Field(default="", max_length=LONG_TEXT)
    include_burndown: bool = True
    burndown_comment: str = Field(default="", max_length=LONG_TEXT)


CONTENT_MODELS: dict[str, type[_Content]] = {
    "daily": DailyContent,
    "sprint_planning": SprintPlanningContent,
    "sprint_review": SprintReviewContent,
    "retrospective": RetrospectiveContent,
}


def validate_content(report_type: str, raw: dict) -> _Content:
    return CONTENT_MODELS[report_type].model_validate(raw)


def load_content(report_type: str, content_json: str) -> _Content:
    try:
        raw = json.loads(content_json or "{}")
    except ValueError:
        raw = {}
    return CONTENT_MODELS[report_type].model_validate(raw if isinstance(raw, dict) else {})


def dump_content(content: _Content) -> str:
    return json.dumps(content.model_dump(), ensure_ascii=False)


def parse_bullets(text: str) -> list[tuple[int, str]]:
    """Découpe un texte libre en points (niveau, texte) : niveau 1 pour une
    ligne indentée, 0 sinon. Les puces tapées à la main ("-", "•", "*") en
    début de ligne sont retirées, les lignes vides ignorées."""
    items: list[tuple[int, str]] = []
    for line in (text or "").splitlines():
        if not line.strip():
            continue
        level = 1 if line[:1] in (" ", "\t") else 0
        stripped = line.strip()
        for marker in ("- ", "• ", "* ", "-\t", "•\t", "*\t"):
            if stripped.startswith(marker):
                stripped = stripped[len(marker) :].strip()
                break
        if stripped:
            items.append((level, stripped))
    return items
