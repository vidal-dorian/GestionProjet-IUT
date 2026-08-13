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
