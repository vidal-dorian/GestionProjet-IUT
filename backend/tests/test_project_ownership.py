from unittest.mock import AsyncMock, patch

from tests.helpers import add_approved_member, promote_to_admin


def test_project_read_exposes_its_creator(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    alice_id = client.get("/api/me").json()["id"]

    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()
    assert project["created_by_account_id"] == alice_id


def test_project_created_unauthenticated_has_no_creator(client):
    project = client.post("/api/projects", json={"name": "Projet anonyme"}).json()
    assert project["created_by_account_id"] is None


def test_ordinary_member_cannot_update_or_delete_the_project(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()
    add_approved_member(project["id"], "bob@test.local")

    client.headers["X-Dev-Email"] = "bob@test.local"
    update_response = client.put(f"/api/projects/{project['id']}", json={"name": "Renommé par Bob"})
    assert update_response.status_code == 403

    delete_response = client.delete(f"/api/projects/{project['id']}")
    assert delete_response.status_code == 403

    fetched = client.get(f"/api/projects/{project['id']}").json()
    assert fetched["name"] == "Projet Alice"


def test_creator_can_update_and_delete_their_own_project(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()

    update_response = client.put(f"/api/projects/{project['id']}", json={"name": "Renommé par Alice"})
    assert update_response.status_code == 200

    delete_response = client.delete(f"/api/projects/{project['id']}")
    assert delete_response.status_code == 204


def test_admin_can_delete_a_project_they_did_not_create(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()

    client.headers["X-Dev-Email"] = "admin@test.local"
    client.get("/api/me")
    promote_to_admin("admin@test.local")

    response = client.delete(f"/api/projects/{project['id']}")
    assert response.status_code == 204


def test_project_without_a_creator_can_only_be_managed_by_an_admin(client):
    project = client.post("/api/projects", json={"name": "Projet anonyme"}).json()

    client.headers["X-Dev-Email"] = "alice@test.local"
    add_approved_member(project["id"], "alice@test.local")
    denied = client.put(f"/api/projects/{project['id']}", json={"name": "Piraté"})
    assert denied.status_code == 403

    client.headers["X-Dev-Email"] = "admin@test.local"
    client.get("/api/me")
    promote_to_admin("admin@test.local")
    allowed = client.put(f"/api/projects/{project['id']}", json={"name": "Corrigé par l'admin"})
    assert allowed.status_code == 200


def test_ordinary_member_cannot_configure_github(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()
    add_approved_member(project["id"], "bob@test.local")

    client.headers["X-Dev-Email"] = "bob@test.local"
    assert (
        client.put(f"/api/projects/{project['id']}/github", json={"repo": "owner/repo"}).status_code == 403
    )
    assert client.post(f"/api/projects/{project['id']}/github/sync").status_code == 403
    assert (
        client.put(f"/api/projects/{project['id']}/github/label-filter", json={"labels": ["x"]}).status_code
        == 403
    )


@patch("app.routers.github.github_client.verify_repo", new_callable=AsyncMock)
def test_creator_can_configure_github(mock_verify, client):
    mock_verify.return_value = None
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()

    response = client.put(f"/api/projects/{project['id']}/github", json={"repo": "owner/repo"})
    assert response.status_code == 200


def test_ordinary_member_can_still_read_github_issues(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()
    add_approved_member(project["id"], "bob@test.local")

    client.headers["X-Dev-Email"] = "bob@test.local"
    assert client.get(f"/api/projects/{project['id']}/github/issues").status_code == 200


def test_creator_can_list_and_remove_members_without_being_admin(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()
    add_approved_member(project["id"], "bob@test.local")

    client.headers["X-Dev-Email"] = "bob@test.local"
    bob_id = client.get("/api/me").json()["id"]

    client.headers["X-Dev-Email"] = "alice@test.local"
    members = client.get(f"/api/admin/projects/{project['id']}/members").json()
    assert {m["email"] for m in members} == {"alice@test.local", "bob@test.local"}

    response = client.delete(f"/api/admin/projects/{project['id']}/members/{bob_id}")
    assert response.status_code == 204


def test_ordinary_member_still_cannot_manage_other_members(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()
    add_approved_member(project["id"], "bob@test.local")
    add_approved_member(project["id"], "carol@test.local")

    client.headers["X-Dev-Email"] = "carol@test.local"
    carol_id = client.get("/api/me").json()["id"]

    client.headers["X-Dev-Email"] = "bob@test.local"
    assert client.get(f"/api/admin/projects/{project['id']}/members").status_code == 403
    assert client.delete(f"/api/admin/projects/{project['id']}/members/{carol_id}").status_code == 403


def test_sprints_and_categories_remain_open_to_ordinary_members(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()
    add_approved_member(project["id"], "bob@test.local")

    client.headers["X-Dev-Email"] = "bob@test.local"
    sprint_response = client.post(
        f"/api/projects/{project['id']}/sprints",
        json={"name": "Sprint 1", "start_date": "2026-08-01", "end_date": "2026-08-14"},
    )
    assert sprint_response.status_code == 201

    category_response = client.post(f"/api/projects/{project['id']}/categories", json={"name": "Dev"})
    assert category_response.status_code == 201
