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


def test_removed_member_who_logged_time_loses_access(client):
    # Un membre ayant déjà saisi des heures était considéré membre "historique"
    # (repli sur les saisies) : le retirer supprimait sa ligne d'adhésion mais
    # lui laissait l'accès au projet.
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()
    add_approved_member(project["id"], "bob@test.local")

    client.headers["X-Dev-Email"] = "bob@test.local"
    bob_id = client.get("/api/me").json()["id"]
    created = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 2, "description": "Dev"},
    )
    assert created.status_code == 201

    client.headers["X-Dev-Email"] = "alice@test.local"
    assert client.delete(f"/api/admin/projects/{project['id']}/members/{bob_id}").status_code == 204

    client.headers["X-Dev-Email"] = "bob@test.local"
    assert client.get(f"/api/projects/{project['id']}/time-entries").status_code == 403
    assert client.get(f"/api/projects/{project['id']}/dashboard/recent-entries").status_code == 403
    assert client.get("/api/me/projects").json() == []

    # Il peut redemander à rejoindre le projet, ce qui repasse par une validation.
    join = client.post(f"/api/projects/{project['id']}/join")
    assert join.json()["status"] == "pending"


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


def test_removed_creator_loses_owner_powers(client):
    client.headers["X-Dev-Email"] = "creator@test.local"
    project = client.post("/api/projects", json={"name": "Projet du créateur"}).json()
    creator_id = client.get("/api/me").json()["id"]

    client.headers["X-Dev-Email"] = "admin@test.local"
    client.get("/api/me")
    promote_to_admin("admin@test.local")
    client.post(f"/api/projects/{project['id']}/join")
    assert client.delete(f"/api/admin/projects/{project['id']}/members/{creator_id}").status_code == 204

    client.headers["X-Dev-Email"] = "creator@test.local"
    assert client.delete(f"/api/projects/{project['id']}").status_code == 403
    assert client.put(f"/api/projects/{project['id']}", json={"name": "Volé"}).status_code == 403
    assert client.get(f"/api/admin/projects/{project['id']}/members").status_code == 403


def test_only_pending_requests_can_be_decided(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet décisions"}).json()

    client.headers["X-Dev-Email"] = "bob@test.local"
    client.post(f"/api/projects/{project['id']}/join")

    client.headers["X-Dev-Email"] = "admin@test.local"
    client.get("/api/me")
    promote_to_admin("admin@test.local")
    request_id = client.get("/api/admin/membership-requests").json()[0]["id"]
    assert client.post(f"/api/admin/membership-requests/{request_id}/approve").status_code == 200
    assert client.post(f"/api/admin/membership-requests/{request_id}/reject").status_code == 409


def test_joining_again_does_not_revoke_access(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet rejoindre"}).json()
    response = client.post(f"/api/projects/{project['id']}/join")
    assert response.json()["status"] == "approved"
    assert client.get(f"/api/projects/{project['id']}/time-entries").status_code == 200
