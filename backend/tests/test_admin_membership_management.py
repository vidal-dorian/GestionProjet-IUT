from tests.helpers import add_approved_member, promote_to_admin


def test_non_member_cannot_create_a_time_entry(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()

    client.headers["X-Dev-Email"] = "bob@test.local"
    response = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 2, "description": "Dev"},
    )
    assert response.status_code == 403


def test_non_member_cannot_view_the_dashboard(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()

    client.headers["X-Dev-Email"] = "bob@test.local"
    response = client.get(f"/api/projects/{project['id']}/dashboard/stats")
    assert response.status_code == 403


def test_non_member_cannot_update_or_delete_the_project(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()

    client.headers["X-Dev-Email"] = "bob@test.local"
    assert client.put(f"/api/projects/{project['id']}", json={"name": "Piraté"}).status_code == 403
    assert client.delete(f"/api/projects/{project['id']}").status_code == 403


def test_approved_member_can_use_project_endpoints(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()

    add_approved_member(project["id"], "bob@test.local")
    client.headers["X-Dev-Email"] = "bob@test.local"
    response = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 2, "description": "Dev"},
    )
    assert response.status_code == 201
    assert client.get(f"/api/projects/{project['id']}/dashboard/stats").status_code == 200


def test_admin_bypasses_membership_requirement(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()

    client.headers["X-Dev-Email"] = "admin@test.local"
    client.get("/api/me")
    promote_to_admin("admin@test.local")

    response = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 2, "description": "Dev admin"},
    )
    assert response.status_code == 201
    assert client.get(f"/api/projects/{project['id']}/dashboard/stats").status_code == 200
    assert client.put(f"/api/projects/{project['id']}", json={"name": "Renommé par l'admin"}).status_code == 200


def test_admin_can_list_approved_members(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()
    add_approved_member(project["id"], "bob@test.local")

    client.headers["X-Dev-Email"] = "admin@test.local"
    client.get("/api/me")
    promote_to_admin("admin@test.local")

    response = client.get(f"/api/admin/projects/{project['id']}/members")
    assert response.status_code == 200
    emails = {member["email"] for member in response.json()}
    assert emails == {"alice@test.local", "bob@test.local"}


def test_non_admin_cannot_list_or_remove_members(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()
    add_approved_member(project["id"], "bob@test.local")

    client.headers["X-Dev-Email"] = "bob@test.local"
    assert client.get(f"/api/admin/projects/{project['id']}/members").status_code == 403


def test_admin_can_remove_a_member(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()
    add_approved_member(project["id"], "bob@test.local")

    client.headers["X-Dev-Email"] = "bob@test.local"
    bob_id = client.get("/api/me").json()["id"]

    client.headers["X-Dev-Email"] = "admin@test.local"
    client.get("/api/me")
    promote_to_admin("admin@test.local")

    response = client.delete(f"/api/admin/projects/{project['id']}/members/{bob_id}")
    assert response.status_code == 204

    remaining = {m["email"] for m in client.get(f"/api/admin/projects/{project['id']}/members").json()}
    assert remaining == {"alice@test.local"}

    client.headers["X-Dev-Email"] = "bob@test.local"
    response = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 2, "description": "Dev"},
    )
    assert response.status_code == 403


def test_removing_a_non_member_returns_404(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()

    client.headers["X-Dev-Email"] = "bob@test.local"
    bob_id = client.get("/api/me").json()["id"]

    client.headers["X-Dev-Email"] = "admin@test.local"
    client.get("/api/me")
    promote_to_admin("admin@test.local")

    response = client.delete(f"/api/admin/projects/{project['id']}/members/{bob_id}")
    assert response.status_code == 404
