from unittest.mock import AsyncMock, patch

from app import github_client


def create_test_project(client, name="Projet GitHub"):
    return client.post("/api/projects", json={"name": name}).json()


def test_link_repo_requires_owner_repo_format(client):
    project = create_test_project(client)

    response = client.put(f"/api/projects/{project['id']}/github", json={"repo": "not-a-repo"})
    assert response.status_code == 422


def test_link_repo_for_unknown_project_returns_404(client):
    response = client.put("/api/projects/999/github", json={"repo": "owner/repo"})
    assert response.status_code == 404


@patch("app.routers.github.github_client.verify_repo", new_callable=AsyncMock)
def test_link_repo_not_found_on_github_returns_404(mock_verify, client):
    mock_verify.side_effect = github_client.GithubRepoNotFound("owner/repo")
    project = create_test_project(client)

    response = client.put(f"/api/projects/{project['id']}/github", json={"repo": "owner/repo"})
    assert response.status_code == 404
    assert "introuvable" in response.json()["detail"]


@patch("app.routers.github.github_client.verify_repo", new_callable=AsyncMock)
def test_link_repo_github_api_error_returns_502(mock_verify, client):
    mock_verify.side_effect = github_client.GithubApiError("boom")
    project = create_test_project(client)

    response = client.put(f"/api/projects/{project['id']}/github", json={"repo": "owner/repo"})
    assert response.status_code == 502


@patch("app.routers.github.github_client.verify_repo", new_callable=AsyncMock)
def test_link_repo_success_persists_repo(mock_verify, client):
    mock_verify.return_value = None
    project = create_test_project(client)

    response = client.put(f"/api/projects/{project['id']}/github", json={"repo": "vidal-dorian/GestionProjet-IUT"})
    assert response.status_code == 200
    assert response.json()["github_repo"] == "vidal-dorian/GestionProjet-IUT"

    fetched = client.get(f"/api/projects/{project['id']}").json()
    assert fetched["github_repo"] == "vidal-dorian/GestionProjet-IUT"


def test_project_without_github_repo_has_null_field(client):
    project = create_test_project(client)
    assert project["github_repo"] is None
    assert project["github_last_synced_at"] is None


def test_sync_without_linked_repo_returns_400(client):
    project = create_test_project(client)

    response = client.post(f"/api/projects/{project['id']}/github/sync")
    assert response.status_code == 400


def test_sync_for_unknown_project_returns_404(client):
    response = client.post("/api/projects/999/github/sync")
    assert response.status_code == 404


def _link_repo(client, project_id, repo="owner/repo"):
    with patch("app.routers.github.github_client.verify_repo", new_callable=AsyncMock):
        client.put(f"/api/projects/{project_id}/github", json={"repo": repo})


@patch("app.github_sync.github_client.list_issues", new_callable=AsyncMock)
def test_sync_persists_issues_and_updates_timestamp(mock_list_issues, client):
    mock_list_issues.return_value = [
        {"number": 1, "title": "Bug A", "state": "open", "labels": [{"name": "bug"}], "html_url": "https://x/1"},
        {"number": 2, "title": "Feature B", "state": "closed", "labels": [], "html_url": "https://x/2"},
    ]
    project = create_test_project(client)
    _link_repo(client, project["id"])

    response = client.post(f"/api/projects/{project['id']}/github/sync")
    assert response.status_code == 200
    assert response.json()["issue_count"] == 2

    project_after = client.get(f"/api/projects/{project['id']}").json()
    assert project_after["github_last_synced_at"] is not None

    issues = client.get(f"/api/projects/{project['id']}/github/issues").json()
    assert len(issues) == 2
    issue_by_number = {i["number"]: i for i in issues}
    assert issue_by_number[1]["labels"] == ["bug"]
    assert issue_by_number[2]["state"] == "closed"


@patch("app.github_sync.github_client.list_issues", new_callable=AsyncMock)
def test_sync_removes_issues_no_longer_returned(mock_list_issues, client):
    project = create_test_project(client)
    _link_repo(client, project["id"])

    mock_list_issues.return_value = [
        {"number": 1, "title": "First", "state": "open", "labels": [], "html_url": "https://x/1"},
        {"number": 2, "title": "Second", "state": "open", "labels": [], "html_url": "https://x/2"},
    ]
    client.post(f"/api/projects/{project['id']}/github/sync")

    mock_list_issues.return_value = [
        {"number": 1, "title": "First", "state": "closed", "labels": [], "html_url": "https://x/1"},
    ]
    client.post(f"/api/projects/{project['id']}/github/sync")

    issues = client.get(f"/api/projects/{project['id']}/github/issues").json()
    assert len(issues) == 1
    assert issues[0]["number"] == 1
    assert issues[0]["state"] == "closed"


def test_issues_for_unknown_project_returns_404(client):
    response = client.get("/api/projects/999/github/issues")
    assert response.status_code == 404


def test_issues_empty_for_unsynced_project(client):
    project = create_test_project(client)
    response = client.get(f"/api/projects/{project['id']}/github/issues")
    assert response.status_code == 200
    assert response.json() == []
