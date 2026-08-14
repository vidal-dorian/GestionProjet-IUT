def test_creating_a_project_while_authenticated_joins_it_automatically(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Site vitrine"}).json()

    response = client.get("/api/me/projects")
    assert response.status_code == 200
    body = response.json()
    assert [p["id"] for p in body] == [project["id"]]
    assert body[0]["is_member"] is True


def test_creating_a_project_unauthenticated_does_not_crash_and_has_no_member(client):
    response = client.post("/api/projects", json={"name": "Projet anonyme"})
    assert response.status_code == 201


def test_me_projects_requires_authentication(client):
    response = client.get("/api/me/projects")
    assert response.status_code == 401


def test_me_projects_is_empty_when_not_a_member_of_anything(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    response = client.get("/api/me/projects")
    assert response.status_code == 200
    assert response.json() == []


def test_joining_a_project_adds_it_to_my_projects(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()

    client.headers["X-Dev-Email"] = "bob@test.local"
    join_response = client.post(f"/api/projects/{project['id']}/join")
    assert join_response.status_code == 200

    my_projects = client.get("/api/me/projects").json()
    assert [p["id"] for p in my_projects] == [project["id"]]


def test_joining_an_unknown_project_returns_404(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    response = client.post("/api/projects/999/join")
    assert response.status_code == 404


def test_joining_twice_is_idempotent(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Idempotent"}).json()

    client.headers["X-Dev-Email"] = "bob@test.local"
    client.post(f"/api/projects/{project['id']}/join")
    client.post(f"/api/projects/{project['id']}/join")

    my_projects = client.get("/api/me/projects").json()
    assert len(my_projects) == 1


def test_list_projects_flags_membership_for_the_current_account(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    mine = client.post("/api/projects", json={"name": "Le mien"}).json()

    client.headers["X-Dev-Email"] = "bob@test.local"
    others = client.post("/api/projects", json={"name": "Celui de Bob"}).json()

    client.headers["X-Dev-Email"] = "alice@test.local"
    by_id = {p["id"]: p for p in client.get("/api/projects").json()}
    assert by_id[mine["id"]]["is_member"] is True
    assert by_id[others["id"]]["is_member"] is False


def test_list_projects_without_authentication_flags_no_membership(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    client.post("/api/projects", json={"name": "Un projet"})
    del client.headers["X-Dev-Email"]

    body = client.get("/api/projects").json()
    assert all(p["is_member"] is False for p in body)


def test_existing_contributor_without_explicit_membership_still_sees_the_project(client):
    project = client.post("/api/projects", json={"name": "Projet legacy"}).json()

    client.headers["X-Dev-Email"] = "alice@test.local"
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 2, "description": "Dev"},
    )

    my_projects = client.get("/api/me/projects").json()
    assert [p["id"] for p in my_projects] == [project["id"]]
