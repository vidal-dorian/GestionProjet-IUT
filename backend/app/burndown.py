from datetime import date

from app import models


def _matches_sprint(issue: models.GithubIssue, sprint: models.Sprint) -> bool:
    return sprint.name in issue.labels


def compute_burndown(sprint: models.Sprint, issues: list[models.GithubIssue], *, today: date | None = None) -> dict:
    """Calcule la courbe de burndown d'un sprint à partir des US GitHub qui portent
    un label correspondant exactement à son nom (ex: label "Sprint 1" pour le sprint
    "Sprint 1"), valorisées via le champ GitHub Projects "Valorisation".

    L'axe Y est la somme des story points restants ; elle baisse à la date de
    fermeture (`closed_at`) de chaque US, jusqu'à aujourd'hui (ou la fin du sprint
    s'il est déjà terminé).
    """
    today = today or date.today()
    matched = [issue for issue in issues if _matches_sprint(issue, sprint)]
    total_points = sum(issue.story_points or 0 for issue in matched)
    unestimated_issue_count = sum(1 for issue in matched if issue.story_points is None)

    ideal = [
        {"date": sprint.start_date, "remaining_points": round(total_points, 2)},
        {"date": sprint.end_date, "remaining_points": 0.0},
    ]

    closures = sorted(
        (
            (issue.closed_at.date(), issue.story_points or 0)
            for issue in matched
            if issue.closed_at is not None
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
        actual.append({"date": closed_date, "remaining_points": round(remaining, 2)})
    if actual[-1]["date"] != cutoff:
        actual.append({"date": cutoff, "remaining_points": round(remaining, 2)})

    return {
        "total_points": round(total_points, 2),
        "matched_issue_count": len(matched),
        "unestimated_issue_count": unestimated_issue_count,
        "ideal": ideal,
        "actual": actual,
    }
