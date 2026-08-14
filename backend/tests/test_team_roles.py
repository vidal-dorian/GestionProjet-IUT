from tests.helpers import add_approved_member


def create_test_project(client, name="Projet Rôles", email="alice@test.local"):
    client.headers["X-Dev-Email"] = email
    return client.post("/api/projects", json={"name": name}).json()


def test_project_creation_seeds_default_roles(client):
    project = create_test_project(client)
    response = client.get(f"/api/projects/{project['id']}/roles")
    assert response.status_code == 200
    names = [role["name"] for role in response.json()]
    assert names == ["Product Owner", "Gestion de projet", "Développeur"]


def test_list_roles_requires_membership(client):
    project = create_test_project(client)
    client.headers["X-Dev-Email"] = "bob@test.local"
    response = client.get(f"/api/projects/{project['id']}/roles")
    assert response.status_code == 403


def test_create_role_requires_name(client):
    project = create_test_project(client)
    response = client.post(f"/api/projects/{project['id']}/roles", json={"name": "   "})
    assert response.status_code == 422


def test_create_duplicate_role_name_returns_409(client):
    project = create_test_project(client)
    response = client.post(f"/api/projects/{project['id']}/roles", json={"name": "Product Owner"})
    assert response.status_code == 409


def test_create_custom_role_succeeds(client):
    project = create_test_project(client)
    response = client.post(f"/api/projects/{project['id']}/roles", json={"name": "Testeur"})
    assert response.status_code == 201
    assert response.json()["name"] == "Testeur"

    names = [role["name"] for role in client.get(f"/api/projects/{project['id']}/roles").json()]
    assert "Testeur" in names


def test_rename_role_succeeds(client):
    project = create_test_project(client)
    role_id = client.get(f"/api/projects/{project['id']}/roles").json()[0]["id"]

    response = client.put(f"/api/projects/{project['id']}/roles/{role_id}", json={"name": "PO"})
    assert response.status_code == 200
    assert response.json()["name"] == "PO"


def test_rename_role_to_existing_name_returns_409(client):
    project = create_test_project(client)
    roles = client.get(f"/api/projects/{project['id']}/roles").json()

    response = client.put(f"/api/projects/{project['id']}/roles/{roles[0]['id']}", json={"name": roles[1]["name"]})
    assert response.status_code == 409


def test_delete_role_succeeds(client):
    project = create_test_project(client)
    roles = client.get(f"/api/projects/{project['id']}/roles").json()

    response = client.delete(f"/api/projects/{project['id']}/roles/{roles[0]['id']}")
    assert response.status_code == 204

    remaining = client.get(f"/api/projects/{project['id']}/roles").json()
    assert len(remaining) == 2


def test_delete_unknown_role_returns_404(client):
    project = create_test_project(client)
    response = client.delete(f"/api/projects/{project['id']}/roles/999")
    assert response.status_code == 404


def create_sprint(client, project_id, name="Sprint 1", start="2026-08-01", end="2026-08-14"):
    return client.post(
        f"/api/projects/{project_id}/sprints", json={"name": name, "start_date": start, "end_date": end}
    ).json()["sprint"]


def test_sprint_has_no_role_assignments_by_default(client):
    project = create_test_project(client)
    sprint = create_sprint(client, project["id"])

    response = client.get(f"/api/projects/{project['id']}/sprints/{sprint['id']}/role-assignments")
    assert response.status_code == 200
    assert response.json() == []


def test_assigning_roles_to_multiple_members_and_multiple_roles_to_one_member(client):
    project = create_test_project(client)
    sprint = create_sprint(client, project["id"])
    roles = {r["name"]: r["id"] for r in client.get(f"/api/projects/{project['id']}/roles").json()}
    alice_id = client.get("/api/me").json()["id"]

    add_approved_member(project["id"], "bob@test.local")
    client.headers["X-Dev-Email"] = "bob@test.local"
    bob_id = client.get("/api/me").json()["id"]
    client.headers["X-Dev-Email"] = "alice@test.local"

    response = client.put(
        f"/api/projects/{project['id']}/sprints/{sprint['id']}/role-assignments",
        json={
            "assignments": [
                {"role_id": roles["Product Owner"], "account_id": alice_id},
                {"role_id": roles["Gestion de projet"], "account_id": alice_id},
                {"role_id": roles["Product Owner"], "account_id": bob_id},
            ]
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    alice_roles = {a["role_name"] for a in body if a["account_id"] == alice_id}
    assert alice_roles == {"Product Owner", "Gestion de projet"}
    po_people = {a["account_email"] for a in body if a["role_name"] == "Product Owner"}
    assert po_people == {"alice@test.local", "bob@test.local"}


def test_replacing_assignments_clears_previous_ones(client):
    project = create_test_project(client)
    sprint = create_sprint(client, project["id"])
    roles = {r["name"]: r["id"] for r in client.get(f"/api/projects/{project['id']}/roles").json()}
    alice_id = client.get("/api/me").json()["id"]

    client.put(
        f"/api/projects/{project['id']}/sprints/{sprint['id']}/role-assignments",
        json={"assignments": [{"role_id": roles["Product Owner"], "account_id": alice_id}]},
    )
    response = client.put(
        f"/api/projects/{project['id']}/sprints/{sprint['id']}/role-assignments",
        json={"assignments": [{"role_id": roles["Développeur"], "account_id": alice_id}]},
    )
    assert response.status_code == 200
    assert [a["role_name"] for a in response.json()] == ["Développeur"]


def test_assigning_a_role_from_another_project_returns_422(client):
    project = create_test_project(client)
    sprint = create_sprint(client, project["id"])
    other_project = create_test_project(client, name="Autre Projet Rôles")
    other_role_id = client.get(f"/api/projects/{other_project['id']}/roles").json()[0]["id"]
    alice_id = client.get("/api/me").json()["id"]

    response = client.put(
        f"/api/projects/{project['id']}/sprints/{sprint['id']}/role-assignments",
        json={"assignments": [{"role_id": other_role_id, "account_id": alice_id}]},
    )
    assert response.status_code == 422


def test_assigning_a_role_to_a_non_member_returns_422(client):
    project = create_test_project(client)
    sprint = create_sprint(client, project["id"])
    roles = {r["name"]: r["id"] for r in client.get(f"/api/projects/{project['id']}/roles").json()}

    client.headers["X-Dev-Email"] = "bob@test.local"
    bob_id = client.get("/api/me").json()["id"]
    client.headers["X-Dev-Email"] = "alice@test.local"

    response = client.put(
        f"/api/projects/{project['id']}/sprints/{sprint['id']}/role-assignments",
        json={"assignments": [{"role_id": roles["Product Owner"], "account_id": bob_id}]},
    )
    assert response.status_code == 422


def test_sprint_stats_include_role_assignments(client):
    project = create_test_project(client)
    sprint = create_sprint(client, project["id"])
    role_id = client.get(f"/api/projects/{project['id']}/roles").json()[0]["id"]
    alice_id = client.get("/api/me").json()["id"]

    client.put(
        f"/api/projects/{project['id']}/sprints/{sprint['id']}/role-assignments",
        json={"assignments": [{"role_id": role_id, "account_id": alice_id}]},
    )

    response = client.get(f"/api/projects/{project['id']}/dashboard/sprints/{sprint['id']}/stats")
    assert response.status_code == 200
    body = response.json()
    assert len(body["role_assignments"]) == 1
    assert body["role_assignments"][0]["account_email"] == "alice@test.local"
