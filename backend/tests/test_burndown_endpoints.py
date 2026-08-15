from unittest.mock import AsyncMock, patch


def _setup_project_with_sprint(client, email="alice@test.local"):
    client.headers["X-Dev-Email"] = email
    project = client.post("/api/projects", json={"name": "Projet Burndown"}).json()
    sprint = client.post(
        f"/api/projects/{project['id']}/sprints",
        json={"name": "Sprint 1", "start_date": "2026-08-01", "end_date": "2026-08-14"},
    ).json()["sprint"]
    return project, sprint


def _sync_issues(client, project_id, issues):
    with patch("app.routers.github.github_client.verify_repo", new_callable=AsyncMock):
        client.put(f"/api/projects/{project_id}/github", json={"repo": "owner/repo"})
    with patch("app.github_sync.github_client.list_issues", new_callable=AsyncMock) as mock_list_issues:
        mock_list_issues.return_value = issues
        client.post(f"/api/projects/{project_id}/github/sync")


def test_burndown_for_unknown_sprint_returns_404(client):
    project, _ = _setup_project_with_sprint(client)
    response = client.get(f"/api/projects/{project['id']}/sprints/999/burndown")
    assert response.status_code == 404


def test_burndown_requires_membership(client):
    project, sprint = _setup_project_with_sprint(client)
    client.headers["X-Dev-Email"] = "bob@test.local"
    response = client.get(f"/api/projects/{project['id']}/sprints/{sprint['id']}/burndown")
    assert response.status_code == 403


def test_burndown_reflects_synced_issues_labelled_for_the_sprint(client):
    project, sprint = _setup_project_with_sprint(client)
    _sync_issues(
        client,
        project["id"],
        [
            {
                "number": 1,
                "title": "US ouverte",
                "state": "open",
                "labels": [{"name": "Sprint 1"}],
                "html_url": "https://x/1",
                "story_points": 5,
                "closed_at": None,
            },
            {
                "number": 2,
                "title": "US fermée",
                "state": "closed",
                "labels": [{"name": "Sprint 1"}],
                "html_url": "https://x/2",
                "story_points": 3,
                "closed_at": "2026-08-05T10:00:00Z",
            },
            {
                "number": 3,
                "title": "Autre sprint",
                "state": "open",
                "labels": [{"name": "Sprint 2"}],
                "html_url": "https://x/3",
                "story_points": 8,
                "closed_at": None,
            },
        ],
    )

    response = client.get(f"/api/projects/{project['id']}/sprints/{sprint['id']}/burndown")
    assert response.status_code == 200
    body = response.json()

    assert body["sprint"]["id"] == sprint["id"]
    assert body["matched_issue_count"] == 2
    assert body["total_points"] == 8
    assert body["unestimated_issue_count"] == 0
    assert body["ideal"][0] == {"date": "2026-08-01", "remaining_points": 8.0}
    assert body["ideal"][-1] == {"date": "2026-08-14", "remaining_points": 0.0}
    assert {"date": "2026-08-05", "remaining_points": 5.0} in body["actual"]


def test_burndown_counts_issues_without_a_valorisation_field(client):
    project, sprint = _setup_project_with_sprint(client)
    _sync_issues(
        client,
        project["id"],
        [
            {
                "number": 1,
                "title": "US sans valorisation",
                "state": "open",
                "labels": [{"name": "Sprint 1"}],
                "html_url": "https://x/1",
                "story_points": None,
                "closed_at": None,
            }
        ],
    )

    response = client.get(f"/api/projects/{project['id']}/sprints/{sprint['id']}/burndown")
    body = response.json()
    assert body["matched_issue_count"] == 1
    assert body["unestimated_issue_count"] == 1
    assert body["total_points"] == 0


def test_burndown_export_returns_an_xlsx_file(client):
    project, sprint = _setup_project_with_sprint(client)
    _sync_issues(
        client,
        project["id"],
        [
            {
                "number": 1,
                "title": "US",
                "state": "closed",
                "labels": [{"name": "Sprint 1"}],
                "html_url": "https://x/1",
                "story_points": 3,
                "closed_at": "2026-08-03T10:00:00Z",
            }
        ],
    )

    response = client.get(f"/api/projects/{project['id']}/sprints/{sprint['id']}/burndown/export")
    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert len(response.content) > 0


def test_burndown_export_for_unknown_sprint_returns_404(client):
    project, _ = _setup_project_with_sprint(client)
    response = client.get(f"/api/projects/{project['id']}/sprints/999/burndown/export")
    assert response.status_code == 404
