from unittest.mock import AsyncMock, patch

from app import github_client
from app.config import settings
from tests.helpers import promote_to_admin


def create_test_project(client, name="Projet GitHub", email="alice@test.local"):
    client.headers["X-Dev-Email"] = email
    return client.post("/api/projects", json={"name": name}).json()


def test_link_repo_requires_owner_repo_format(client):
    project = create_test_project(client)

    response = client.put(f"/api/projects/{project['id']}/github", json={"repo": "not-a-repo"})
    assert response.status_code == 422


def test_link_repo_for_unknown_project_returns_404(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    response = client.put("/api/projects/999/github", json={"repo": "owner/repo"})
    assert response.status_code == 404


@patch("app.routers.github.github_client.verify_repo", new_callable=AsyncMock, return_value=False)
def test_link_repo_not_found_on_github_returns_404(mock_verify, client):
    mock_verify.side_effect = github_client.GithubRepoNotFound("owner/repo")
    project = create_test_project(client)

    response = client.put(f"/api/projects/{project['id']}/github", json={"repo": "owner/repo"})
    assert response.status_code == 404
    assert "introuvable" in response.json()["detail"]


@patch("app.routers.github.github_client.verify_repo", new_callable=AsyncMock, return_value=False)
def test_link_repo_github_api_error_returns_502(mock_verify, client):
    mock_verify.side_effect = github_client.GithubApiError("boom")
    project = create_test_project(client)

    response = client.put(f"/api/projects/{project['id']}/github", json={"repo": "owner/repo"})
    assert response.status_code == 502


@patch("app.routers.github.github_client.verify_repo", new_callable=AsyncMock, return_value=False)
def test_link_repo_success_persists_repo(mock_verify, client):
    project = create_test_project(client)

    response = client.put(f"/api/projects/{project['id']}/github", json={"repo": "vidal-dorian/GestionProjet-IUT"})
    assert response.status_code == 200
    assert response.json()["github_repo"] == "vidal-dorian/GestionProjet-IUT"

    fetched = client.get(f"/api/projects/{project['id']}").json()
    assert fetched["github_repo"] == "vidal-dorian/GestionProjet-IUT"


@patch("app.routers.github.github_client.verify_repo", new_callable=AsyncMock, return_value=True)
def test_non_admin_cannot_link_a_private_repo(mock_verify, client):
    project = create_test_project(client)

    response = client.put(f"/api/projects/{project['id']}/github", json={"repo": "owner/private-repo"})
    assert response.status_code == 403
    assert client.get(f"/api/projects/{project['id']}").json()["github_repo"] is None


@patch("app.routers.github.github_client.verify_repo", new_callable=AsyncMock, return_value=True)
def test_admin_can_link_a_private_repo(mock_verify, client):
    project = create_test_project(client)
    promote_to_admin("alice@test.local")

    response = client.put(f"/api/projects/{project['id']}/github", json={"repo": "owner/private-repo"})
    assert response.status_code == 200


@patch("app.github_sync.github_client.list_issues", new_callable=AsyncMock)
def test_changing_repo_clears_previous_issues_and_sync_cooldown(mock_list_issues, client, monkeypatch):
    monkeypatch.setattr(settings, "github_sync_interval_minutes", 15)
    mock_list_issues.return_value = [
        {"number": 1, "title": "Ancien", "state": "open", "labels": [], "html_url": "https://x/1"},
    ]
    project = create_test_project(client)
    _link_repo(client, project["id"], repo="owner/old")
    assert client.post(f"/api/projects/{project['id']}/github/sync").status_code == 200

    _link_repo(client, project["id"], repo="owner/new")
    assert client.get(f"/api/projects/{project['id']}/github/issues").json() == []
    assert client.get(f"/api/projects/{project['id']}").json()["github_last_synced_at"] is None
    assert client.post(f"/api/projects/{project['id']}/github/sync").status_code == 200


@patch("app.github_sync.github_client.list_issues", new_callable=AsyncMock)
def test_relinking_the_same_repo_keeps_issues(mock_list_issues, client):
    mock_list_issues.return_value = [
        {"number": 1, "title": "US", "state": "open", "labels": [], "html_url": "https://x/1"},
    ]
    project = create_test_project(client)
    _link_repo(client, project["id"], repo="owner/repo")
    client.post(f"/api/projects/{project['id']}/github/sync")

    _link_repo(client, project["id"], repo="Owner/Repo")
    assert len(client.get(f"/api/projects/{project['id']}/github/issues").json()) == 1


def test_project_without_github_repo_has_null_field(client):
    project = create_test_project(client)
    assert project["github_repo"] is None
    assert project["github_last_synced_at"] is None


def test_sync_without_linked_repo_returns_400(client):
    project = create_test_project(client)

    response = client.post(f"/api/projects/{project['id']}/github/sync")
    assert response.status_code == 400


def test_sync_for_unknown_project_returns_404(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    response = client.post("/api/projects/999/github/sync")
    assert response.status_code == 404


def _link_repo(client, project_id, repo="owner/repo"):
    with patch("app.routers.github.github_client.verify_repo", new_callable=AsyncMock, return_value=False):
        client.put(f"/api/projects/{project_id}/github", json={"repo": repo})


@patch("app.github_sync.github_client.list_issues", new_callable=AsyncMock)
def test_sync_persists_issues_and_updates_timestamp(mock_list_issues, client):
    mock_list_issues.return_value = [
        {"number": 1, "title": "Bug A", "state": "open", "labels": [{"name": "bug"}], "html_url": "https://x/1"},
        {"number": 2, "title": "Feature B", "state": "open", "labels": [], "html_url": "https://x/2"},
    ]
    project = create_test_project(client)
    _link_repo(client, project["id"])

    response = client.post(f"/api/projects/{project['id']}/github/sync")
    assert response.status_code == 200
    assert response.json()["issue_count"] == 2
    assert response.json()["warning"] is None

    project_after = client.get(f"/api/projects/{project['id']}").json()
    assert project_after["github_last_synced_at"] is not None

    issues = client.get(f"/api/projects/{project['id']}/github/issues").json()
    assert len(issues) == 2
    issue_by_number = {i["number"]: i for i in issues}
    assert issue_by_number[1]["labels"] == ["bug"]
    assert issue_by_number[2]["state"] == "open"


@patch("app.github_sync.github_client.list_issues", new_callable=AsyncMock)
def test_sync_falls_back_without_story_points_when_projects_unavailable(mock_list_issues, client):
    issue = {"number": 1, "title": "US", "state": "open", "labels": [{"name": "Sprint 1"}], "html_url": "https://x/1"}
    mock_list_issues.side_effect = [
        github_client.GithubProjectsUnavailable("Resource not accessible by personal access token"),
        [issue],
    ]
    project = create_test_project(client)
    _link_repo(client, project["id"])

    response = client.post(f"/api/projects/{project['id']}/github/sync")
    assert response.status_code == 200
    body = response.json()
    assert body["issue_count"] == 1
    assert "read:project" in body["warning"]
    assert mock_list_issues.call_args_list[1].kwargs == {"with_story_points": False}

    issues = client.get(f"/api/projects/{project['id']}/github/issues").json()
    assert [i["number"] for i in issues] == [1]


@patch("app.github_sync.github_client.list_issues", new_callable=AsyncMock)
def test_sync_github_api_error_returns_502_with_reason(mock_list_issues, client):
    mock_list_issues.side_effect = github_client.GithubApiError("Bad credentials")
    project = create_test_project(client)
    _link_repo(client, project["id"])

    response = client.post(f"/api/projects/{project['id']}/github/sync")
    assert response.status_code == 502
    assert "Bad credentials" in response.json()["detail"]


@patch("app.github_sync.github_client.list_issues", new_callable=AsyncMock)
def test_sync_removes_issues_no_longer_returned(mock_list_issues, client):
    project = create_test_project(client)
    _link_repo(client, project["id"])
    client.put(f"/api/projects/{project['id']}/github/label-filter", json={"labels": ["us"]})

    mock_list_issues.return_value = [
        {"number": 1, "title": "First", "state": "open", "labels": [{"name": "us"}], "html_url": "https://x/1"},
        {"number": 2, "title": "Second", "state": "open", "labels": [{"name": "us"}], "html_url": "https://x/2"},
    ]
    client.post(f"/api/projects/{project['id']}/github/sync")

    mock_list_issues.return_value = [
        {"number": 1, "title": "First", "state": "closed", "labels": [{"name": "us"}], "html_url": "https://x/1"},
    ]
    client.post(f"/api/projects/{project['id']}/github/sync")

    issues = client.get(f"/api/projects/{project['id']}/github/issues").json()
    assert len(issues) == 1
    assert issues[0]["number"] == 1
    assert issues[0]["state"] == "closed"


@patch("app.github_sync.github_client.list_issues", new_callable=AsyncMock)
def test_sync_is_rate_limited_within_configured_interval(mock_list_issues, client, monkeypatch):
    monkeypatch.setattr(settings, "github_sync_interval_minutes", 15)
    mock_list_issues.return_value = []
    project = create_test_project(client)
    _link_repo(client, project["id"])

    first = client.post(f"/api/projects/{project['id']}/github/sync")
    assert first.status_code == 200

    second = client.post(f"/api/projects/{project['id']}/github/sync")
    assert second.status_code == 429


def test_issues_for_unknown_project_returns_404(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    response = client.get("/api/projects/999/github/issues")
    assert response.status_code == 404


def test_issues_empty_for_unsynced_project(client):
    project = create_test_project(client)
    response = client.get(f"/api/projects/{project['id']}/github/issues")
    assert response.status_code == 200
    assert response.json() == []


def test_project_has_empty_label_filter_by_default(client):
    project = create_test_project(client)
    assert project["github_label_filter"] == []


def test_label_filter_for_unknown_project_returns_404(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    response = client.put("/api/projects/999/github/label-filter", json={"labels": ["user-story"]})
    assert response.status_code == 404


def test_label_filter_persists_and_strips_blanks(client):
    project = create_test_project(client)

    response = client.put(
        f"/api/projects/{project['id']}/github/label-filter",
        json={"labels": [" user-story ", "", "bug"]},
    )
    assert response.status_code == 200
    assert response.json()["github_label_filter"] == ["user-story", "bug"]

    fetched = client.get(f"/api/projects/{project['id']}").json()
    assert fetched["github_label_filter"] == ["user-story", "bug"]


@patch("app.github_sync.github_client.list_issues", new_callable=AsyncMock)
def test_issues_without_filter_only_returns_open(mock_list_issues, client):
    mock_list_issues.return_value = [
        {"number": 1, "title": "Open one", "state": "open", "labels": [], "html_url": "https://x/1"},
        {"number": 2, "title": "Closed one", "state": "closed", "labels": [], "html_url": "https://x/2"},
    ]
    project = create_test_project(client)
    _link_repo(client, project["id"])
    client.post(f"/api/projects/{project['id']}/github/sync")

    issues = client.get(f"/api/projects/{project['id']}/github/issues").json()
    assert [i["number"] for i in issues] == [1]


@patch("app.github_sync.github_client.list_issues", new_callable=AsyncMock)
def test_issues_with_filter_matches_any_state(mock_list_issues, client):
    mock_list_issues.return_value = [
        {"number": 1, "title": "US open", "state": "open", "labels": [{"name": "user-story"}], "html_url": "https://x/1"},
        {"number": 2, "title": "US closed", "state": "closed", "labels": [{"name": "user-story"}], "html_url": "https://x/2"},
        {"number": 3, "title": "Tech ticket", "state": "open", "labels": [{"name": "tech"}], "html_url": "https://x/3"},
    ]
    project = create_test_project(client)
    _link_repo(client, project["id"])
    client.post(f"/api/projects/{project['id']}/github/sync")

    client.put(f"/api/projects/{project['id']}/github/label-filter", json={"labels": ["user-story"]})

    issues = client.get(f"/api/projects/{project['id']}/github/issues").json()
    assert sorted(i["number"] for i in issues) == [1, 2]


def test_label_filter_too_long_is_rejected(client):
    project = create_test_project(client)
    _link_repo(client, project["id"])

    response = client.put(
        f"/api/projects/{project['id']}/github/label-filter", json={"labels": ["x" * 60] * 10}
    )
    assert response.status_code == 422


def test_repo_format_rejects_path_traversal_and_non_github_names():
    from app.github_client import is_valid_repo_format

    assert is_valid_repo_format("vidal-dorian/GestionProjet-IUT")
    assert is_valid_repo_format("octo/my.repo_name-2")
    for invalid in ["../..", "owner/..", "owner/.", "-owner/repo", "own er/repo", "owner/repo/extra", "owner", "ownér/repo", "owner/repo\n"]:
        assert not is_valid_repo_format(invalid), invalid


def test_synced_issue_url_is_forced_to_github(client):
    from app import crud, models
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()
    try:
        project = models.Project(name="Projet URL", github_repo="owner/repo")
        db.add(project)
        db.commit()
        crud.replace_github_issues(
            db,
            project,
            [{"number": 4, "title": "US", "state": "open", "labels": [], "html_url": "javascript:alert(1)"}],
        )
        assert db.query(models.GithubIssue).one().url == "https://github.com/owner/repo/issues/4"
    finally:
        db.close()
