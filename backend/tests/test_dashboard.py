from unittest.mock import AsyncMock, patch


def setup_authenticated_account(client, project_name="Projet Dashboard", email="alice@test.local"):
    project = client.post("/api/projects", json={"name": project_name}).json()
    client.headers["X-Dev-Email"] = email
    return project, email


def link_repo_and_sync_issues(client, project_id, issues):
    with patch("app.routers.github.github_client.verify_repo", new_callable=AsyncMock):
        client.put(f"/api/projects/{project_id}/github", json={"repo": "owner/repo"})
    with patch("app.github_sync.github_client.list_issues", new_callable=AsyncMock) as mock_list_issues:
        mock_list_issues.return_value = issues
        client.post(f"/api/projects/{project_id}/github/sync")
    return {issue["number"]: issue for issue in client.get(f"/api/projects/{project_id}/github/issues").json()}


def test_hours_over_time_for_unknown_project_returns_404(client):
    response = client.get("/api/projects/999/dashboard/hours-over-time")
    assert response.status_code == 404


def test_hours_over_time_with_no_entries_returns_empty_series(client):
    project = client.post("/api/projects", json={"name": "Projet Vide"}).json()
    response = client.get(f"/api/projects/{project['id']}/dashboard/hours-over-time")
    assert response.status_code == 200
    body = response.json()
    assert body["granularity"] == "day"
    assert body["points"] == []


def test_hours_over_time_uses_daily_granularity_for_short_span_and_fills_gaps(client):
    project, _ = setup_authenticated_account(client)

    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-01", "duration_hours": 2, "description": "Jour 1"},
    )
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-03", "duration_hours": 1.5, "description": "Jour 3"},
    )

    response = client.get(f"/api/projects/{project['id']}/dashboard/hours-over-time")
    assert response.status_code == 200
    body = response.json()
    assert body["granularity"] == "day"
    assert body["points"] == [
        {"period": "2026-08-01", "hours": 2.0},
        {"period": "2026-08-02", "hours": 0.0},
        {"period": "2026-08-03", "hours": 1.5},
    ]


def test_hours_over_time_sums_entries_from_all_accounts(client):
    project, _ = setup_authenticated_account(client)
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-01", "duration_hours": 2, "description": "Alice"},
    )
    client.headers["X-Dev-Email"] = "bob@test.local"
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-01", "duration_hours": 1, "description": "Bob"},
    )

    response = client.get(f"/api/projects/{project['id']}/dashboard/hours-over-time")
    body = response.json()
    assert body["points"] == [{"period": "2026-08-01", "hours": 3.0}]


def test_hours_over_time_uses_weekly_granularity_for_long_span(client):
    project, _ = setup_authenticated_account(client, project_name="Projet Long")

    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-01-05", "duration_hours": 3, "description": "Début (lundi)"},
    )
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-03-10", "duration_hours": 4, "description": "Fin (mardi)"},
    )

    response = client.get(f"/api/projects/{project['id']}/dashboard/hours-over-time")
    body = response.json()
    assert body["granularity"] == "week"
    assert body["points"][0] == {"period": "2026-01-05", "hours": 3.0}
    assert body["points"][-1] == {"period": "2026-03-09", "hours": 4.0}
    assert len(body["points"]) == 10


def test_recent_entries_for_unknown_project_returns_404(client):
    response = client.get("/api/projects/999/dashboard/recent-entries")
    assert response.status_code == 404


def test_recent_entries_empty_project_returns_empty_list(client):
    project = client.post("/api/projects", json={"name": "Projet Sans Entrées"}).json()
    response = client.get(f"/api/projects/{project['id']}/dashboard/recent-entries")
    assert response.status_code == 200
    assert response.json() == []


def test_recent_entries_includes_author_across_all_accounts_sorted_by_date_desc(client):
    project, _ = setup_authenticated_account(client, project_name="Projet Multi Auteurs")

    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-01", "duration_hours": 2, "description": "Entrée d'Alice"},
    )
    client.headers["X-Dev-Email"] = "bob@test.local"
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-05", "duration_hours": 1, "description": "Entrée de Bob"},
    )

    response = client.get(f"/api/projects/{project['id']}/dashboard/recent-entries")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["account_email"] == "bob@test.local"
    assert body[0]["date"] == "2026-08-05"
    assert body[0]["duration_hours"] == 1
    assert body[0]["description"] == "Entrée de Bob"
    assert body[1]["account_email"] == "alice@test.local"


def test_recent_entries_limited_to_ten(client):
    project, _ = setup_authenticated_account(client, project_name="Projet Beaucoup D'Entrées")
    for day in range(1, 13):
        client.post(
            f"/api/projects/{project['id']}/time-entries",
            json={"date": f"2026-08-{day:02d}", "duration_hours": 1, "description": f"Jour {day}"},
        )

    response = client.get(f"/api/projects/{project['id']}/dashboard/recent-entries")
    body = response.json()
    assert len(body) == 10
    assert body[0]["date"] == "2026-08-12"
    assert body[-1]["date"] == "2026-08-03"


def test_stats_for_unknown_project_returns_404(client):
    response = client.get("/api/projects/999/dashboard/stats")
    assert response.status_code == 404


def test_stats_for_project_without_entries(client):
    project = client.post("/api/projects", json={"name": "Projet Stats Vide"}).json()
    response = client.get(f"/api/projects/{project['id']}/dashboard/stats")
    assert response.status_code == 200
    assert response.json() == {
        "total_hours": 0.0,
        "contributor_count": 0,
        "entry_count": 0,
        "average_hours_per_contributor": 0.0,
    }


def test_hours_by_issue_for_unknown_project_returns_404(client):
    response = client.get("/api/projects/999/dashboard/hours-by-issue")
    assert response.status_code == 404


def test_hours_by_issue_with_no_entries_returns_empty(client):
    project = client.post("/api/projects", json={"name": "Projet Sans Issues"}).json()
    response = client.get(f"/api/projects/{project['id']}/dashboard/hours-by-issue")
    assert response.status_code == 200
    assert response.json() == {"items": [], "unattached_hours": 0.0}


def test_hours_by_issue_groups_by_issue_and_separates_unattached(client):
    project, _ = setup_authenticated_account(client, project_name="Projet Hours By Issue")
    issues = link_repo_and_sync_issues(
        client,
        project["id"],
        [
            {"number": 1, "title": "US-01", "state": "open", "labels": [], "html_url": "https://x/1"},
            {"number": 2, "title": "US-02", "state": "open", "labels": [], "html_url": "https://x/2"},
        ],
    )

    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-01", "duration_hours": 3, "description": "A", "github_issue_id": issues[1]["id"]},
    )
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-02", "duration_hours": 2, "description": "B", "github_issue_id": issues[1]["id"]},
    )
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-03", "duration_hours": 1, "description": "C", "github_issue_id": issues[2]["id"]},
    )
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-04", "duration_hours": 4, "description": "Sans issue"},
    )

    response = client.get(f"/api/projects/{project['id']}/dashboard/hours-by-issue")
    assert response.status_code == 200
    body = response.json()
    assert body["unattached_hours"] == 4.0
    assert body["items"] == [
        {"issue_number": 1, "issue_title": "US-01", "issue_url": "https://x/1", "hours": 5.0},
        {"issue_number": 2, "issue_title": "US-02", "issue_url": "https://x/2", "hours": 1.0},
    ]


def create_sprint(client, project_id, name="Sprint 1", start="2026-08-01", end="2026-08-14"):
    return client.post(
        f"/api/projects/{project_id}/sprints", json={"name": name, "start_date": start, "end_date": end}
    ).json()["sprint"]


def test_sprint_stats_for_unknown_project_returns_404(client):
    response = client.get("/api/projects/999/dashboard/sprints/1/stats")
    assert response.status_code == 404


def test_sprint_stats_for_unknown_sprint_returns_404(client):
    project = client.post("/api/projects", json={"name": "Projet Sprint Stats"}).json()
    response = client.get(f"/api/projects/{project['id']}/dashboard/sprints/999/stats")
    assert response.status_code == 404


def test_sprint_stats_aggregates_hours_by_account_and_issue(client):
    project, _ = setup_authenticated_account(client, project_name="Projet Sprint Dashboard")

    sprint = create_sprint(client, project["id"])
    other_sprint = create_sprint(client, project["id"], name="Sprint 2", start="2026-09-01", end="2026-09-14")

    issues = link_repo_and_sync_issues(
        client,
        project["id"],
        [{"number": 1, "title": "US-01", "state": "open", "labels": [], "html_url": "https://x/1"}],
    )

    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={
            "date": "2026-08-05",
            "duration_hours": 3,
            "description": "Alice avec issue",
            "sprint_id": sprint["id"],
            "github_issue_id": issues[1]["id"],
        },
    )
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-06", "duration_hours": 1, "description": "Alice sans issue", "sprint_id": sprint["id"]},
    )
    client.headers["X-Dev-Email"] = "bob@test.local"
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-07", "duration_hours": 2, "description": "Bob", "sprint_id": sprint["id"]},
    )
    # Entry outside this sprint must not be counted.
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-09-05", "duration_hours": 5, "description": "Hors sprint", "sprint_id": other_sprint["id"]},
    )

    response = client.get(f"/api/projects/{project['id']}/dashboard/sprints/{sprint['id']}/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["sprint"]["id"] == sprint["id"]
    assert body["total_hours"] == 6.0
    assert {(a["account_email"], a["hours"]) for a in body["hours_by_account"]} == {
        ("alice@test.local", 4.0),
        ("bob@test.local", 2.0),
    }
    assert body["hours_by_issue"]["items"] == [
        {"issue_number": 1, "issue_title": "US-01", "issue_url": "https://x/1", "hours": 3.0}
    ]
    assert body["hours_by_issue"]["unattached_hours"] == 3.0


def create_category(client, project_id, name="Dev"):
    return client.post(f"/api/projects/{project_id}/categories", json={"name": name}).json()


def test_hours_by_category_for_unknown_project_returns_404(client):
    response = client.get("/api/projects/999/dashboard/hours-by-category")
    assert response.status_code == 404


def test_hours_by_category_with_no_entries_returns_empty(client):
    project = client.post("/api/projects", json={"name": "Projet Sans Catégories"}).json()
    response = client.get(f"/api/projects/{project['id']}/dashboard/hours-by-category")
    assert response.status_code == 200
    assert response.json() == {"items": [], "unattached_hours": 0.0}


def test_hours_by_category_groups_by_category_and_separates_unattached(client):
    project, _ = setup_authenticated_account(client, project_name="Projet Hours By Category")
    dev = create_category(client, project["id"], name="Dev")
    docs = create_category(client, project["id"], name="Documentation")

    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-01", "duration_hours": 3, "description": "A", "category_id": dev["id"]},
    )
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-02", "duration_hours": 2, "description": "B", "category_id": dev["id"]},
    )
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-03", "duration_hours": 1, "description": "C", "category_id": docs["id"]},
    )
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-04", "duration_hours": 4, "description": "Sans catégorie"},
    )

    response = client.get(f"/api/projects/{project['id']}/dashboard/hours-by-category")
    assert response.status_code == 200
    body = response.json()
    assert body["unattached_hours"] == 4.0
    assert body["items"] == [
        {"category_id": dev["id"], "category_name": "Dev", "hours": 5.0},
        {"category_id": docs["id"], "category_name": "Documentation", "hours": 1.0},
    ]


def test_stats_reflect_contributors_and_entries(client):
    project, _ = setup_authenticated_account(client, project_name="Projet Stats")

    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-01", "duration_hours": 3, "description": "Alice 1"},
    )
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-02", "duration_hours": 2, "description": "Alice 2"},
    )
    client.headers["X-Dev-Email"] = "bob@test.local"
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-03", "duration_hours": 1, "description": "Bob 1"},
    )

    response = client.get(f"/api/projects/{project['id']}/dashboard/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["total_hours"] == 6.0
    assert body["contributor_count"] == 2
    assert body["entry_count"] == 3
    assert body["average_hours_per_contributor"] == 3.0
