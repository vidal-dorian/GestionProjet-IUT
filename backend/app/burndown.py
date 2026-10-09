import re
import unicodedata
from datetime import date

from app import models

_SEPARATORS = re.compile(r"[\s_-]+")


def _normalize_label(value: str) -> str:
    """Forme canonique d'un nom de sprint / label : sans accents, en minuscules,
    sans espaces ni tirets ni underscores ("Sprint 0", "sprint 0", "Sprint-0" et
    "sprint0" deviennent tous "sprint0")."""
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _SEPARATORS.sub("", without_accents).lower()


def matches_sprint(issue: models.GithubIssue, sprint: models.Sprint) -> bool:
    """Une US appartient au sprint si son itération GitHub Projects ou l'un de
    ses labels porte le nom du sprint."""
    sprint_key = _normalize_label(sprint.name)
    if not sprint_key:
        return False
    candidates = [*issue.labels, *([issue.iteration] if issue.iteration else [])]
    return any(_normalize_label(candidate) == sprint_key for candidate in candidates)


def compute_burndown(sprint: models.Sprint, issues: list[models.GithubIssue], *, today: date | None = None) -> dict:
    """Calcule la courbe de burndown d'un sprint à partir des US GitHub rattachées
    à ce sprint (itération GitHub Projects ou label portant son nom, à la casse,
    aux accents et aux séparateurs près — ex: "sprint 1" ou "Sprint-1" pour le
    sprint "Sprint 1"), valorisées via le champ GitHub Projects "Valorisation".

    L'axe Y est la somme des story points restants ; elle baisse à la date de
    fermeture de chaque US (celle saisie à la main si elle a été corrigée, sinon
    `closed_at`), jusqu'à aujourd'hui (ou la fin du sprint
    s'il est déjà terminé).
    """
    today = today or date.today()
    matched = [issue for issue in issues if matches_sprint(issue, sprint)]
    total_points = sum(issue.story_points or 0 for issue in matched)
    unestimated_issue_count = sum(1 for issue in matched if issue.story_points is None)

    ideal = [
        {"date": sprint.start_date, "remaining_points": round(total_points, 2)},
        {"date": sprint.end_date, "remaining_points": 0.0},
    ]

    closures = sorted(
        (
            (issue.effective_closed_on, issue.story_points or 0)
            for issue in matched
            if issue.effective_closed_on is not None
        ),
        key=lambda pair: pair[0],
    )

    cutoff = min(today, sprint.end_date)
    cutoff = max(cutoff, sprint.start_date)

    remaining = total_points - sum(points for closed_date, points in closures if closed_date < sprint.start_date)
    actual = [{"date": sprint.start_date, "remaining_points": round(remaining, 2)}]
    for closed_date, points in closures:
        if closed_date < sprint.start_date or closed_date > cutoff:
            continue
        remaining -= points
        # Plusieurs US fermées le même jour : un seul point (le premier point,
        # début du sprint, reste à part pour garder le total de départ).
        if len(actual) > 1 and actual[-1]["date"] == closed_date:
            actual[-1]["remaining_points"] = round(remaining, 2)
        else:
            actual.append({"date": closed_date, "remaining_points": round(remaining, 2)})
    if actual[-1]["date"] != cutoff:
        actual.append({"date": cutoff, "remaining_points": round(remaining, 2)})

    return {
        "total_points": round(total_points, 2),
        "matched_issue_count": len(matched),
        "unestimated_issue_count": unestimated_issue_count,
        "ideal": ideal,
        "actual": actual,
        "issues": sorted(matched, key=lambda issue: issue.number),
    }
