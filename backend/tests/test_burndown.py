from datetime import date, datetime

from app import burndown, models


def _sprint(name="Sprint 1", start="2026-08-01", end="2026-08-10") -> models.Sprint:
    return models.Sprint(
        id=1,
        project_id=1,
        name=name,
        start_date=date.fromisoformat(start),
        end_date=date.fromisoformat(end),
    )


def _issue(labels: str, story_points: float | None = None, closed_at: str | None = None) -> models.GithubIssue:
    return models.GithubIssue(
        id=1,
        project_id=1,
        number=1,
        title="Titre",
        state="closed" if closed_at else "open",
        labels_raw=labels,
        url="https://x",
        synced_at=datetime.utcnow(),
        story_points=story_points,
        closed_at=datetime.fromisoformat(closed_at) if closed_at else None,
    )


def test_only_issues_labelled_with_the_sprint_name_are_counted():
    sprint = _sprint()
    issues = [
        _issue("Sprint 1", story_points=3),
        _issue("Sprint 2", story_points=5),  # different sprint, excluded
        _issue("Sprint 1,bug", story_points=2),  # extra label alongside the sprint one
    ]

    result = burndown.compute_burndown(sprint, issues, today=date(2026, 8, 5))

    assert result["matched_issue_count"] == 2
    assert result["total_points"] == 5


def test_unestimated_issues_count_as_zero_points_but_are_reported():
    sprint = _sprint()
    issues = [_issue("Sprint 1", story_points=3), _issue("Sprint 1", story_points=None)]

    result = burndown.compute_burndown(sprint, issues, today=date(2026, 8, 5))

    assert result["total_points"] == 3
    assert result["unestimated_issue_count"] == 1


def test_ideal_line_goes_from_total_points_to_zero():
    sprint = _sprint(start="2026-08-01", end="2026-08-10")
    issues = [_issue("Sprint 1", story_points=8)]

    result = burndown.compute_burndown(sprint, issues, today=date(2026, 8, 5))

    assert result["ideal"] == [
        {"date": date(2026, 8, 1), "remaining_points": 8.0},
        {"date": date(2026, 8, 10), "remaining_points": 0.0},
    ]


def test_actual_line_decreases_when_an_issue_closes_mid_sprint():
    sprint = _sprint(start="2026-08-01", end="2026-08-10")
    issues = [
        _issue("Sprint 1", story_points=3, closed_at="2026-08-03T10:00:00"),
        _issue("Sprint 1", story_points=5),  # still open
    ]

    result = burndown.compute_burndown(sprint, issues, today=date(2026, 8, 5))

    assert result["actual"] == [
        {"date": date(2026, 8, 1), "remaining_points": 8.0},
        {"date": date(2026, 8, 3), "remaining_points": 5.0},
        {"date": date(2026, 8, 5), "remaining_points": 5.0},
    ]


def test_actual_line_is_capped_at_todays_date_for_an_ongoing_sprint():
    sprint = _sprint(start="2026-08-01", end="2026-08-31")
    issues = [_issue("Sprint 1", story_points=3, closed_at="2026-08-20T10:00:00")]

    result = burndown.compute_burndown(sprint, issues, today=date(2026, 8, 10))

    # The closure on 08-20 is after "today" (08-10): not reflected yet, but the
    # line still extends to today so the chart doesn't stop at day one.
    assert result["actual"] == [
        {"date": date(2026, 8, 1), "remaining_points": 3.0},
        {"date": date(2026, 8, 10), "remaining_points": 3.0},
    ]


def test_actual_line_reaches_the_end_date_for_a_finished_sprint():
    sprint = _sprint(start="2026-08-01", end="2026-08-10")
    issues = [_issue("Sprint 1", story_points=4, closed_at="2026-08-05T10:00:00")]

    result = burndown.compute_burndown(sprint, issues, today=date(2026, 9, 1))

    assert result["actual"][-1] == {"date": date(2026, 8, 10), "remaining_points": 0.0}


def test_issue_closed_before_sprint_start_is_already_excluded_from_start():
    sprint = _sprint(start="2026-08-01", end="2026-08-10")
    issues = [_issue("Sprint 1", story_points=3, closed_at="2026-07-20T10:00:00")]

    result = burndown.compute_burndown(sprint, issues, today=date(2026, 8, 5))

    assert result["actual"][0] == {"date": date(2026, 8, 1), "remaining_points": 0.0}


def test_no_matching_issues_gives_an_empty_flat_burndown():
    sprint = _sprint()
    result = burndown.compute_burndown(sprint, [], today=date(2026, 8, 5))

    assert result["total_points"] == 0
    assert result["matched_issue_count"] == 0
    assert result["actual"] == [
        {"date": date(2026, 8, 1), "remaining_points": 0.0},
        {"date": date(2026, 8, 5), "remaining_points": 0.0},
    ]
