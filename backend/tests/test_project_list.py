from tests.helpers import add_approved_member


def test_list_projects_empty(client):
    response = client.get("/api/projects")
    assert response.status_code == 200
    assert response.json() == []


def test_list_projects_returns_name_description_and_contributor_count(client):
    client.post("/api/projects", json={"name": "Site vitrine", "description": "Refonte du site"})
    client.post("/api/projects", json={"name": "App mobile"})

    response = client.get("/api/projects")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2

    by_name = {p["name"]: p for p in body}
    assert by_name["Site vitrine"]["description"] == "Refonte du site"
    assert by_name["Site vitrine"]["contributor_count"] == 0
    assert by_name["App mobile"]["description"] is None
    assert by_name["App mobile"]["contributor_count"] == 0


def test_list_contributors_requires_authentication(client):
    response = client.get("/api/projects/999/contributors")
    assert response.status_code == 401


def test_list_contributors_requires_membership(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Contributeurs Privé"}).json()
    client.headers["X-Dev-Email"] = "bob@test.local"
    response = client.get(f"/api/projects/{project['id']}/contributors")
    assert response.status_code == 403


def test_list_contributors_for_unknown_project_returns_404(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    response = client.get("/api/projects/999/contributors")
    assert response.status_code == 404


def test_list_contributors_empty_by_default(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Sans Contributeur"}).json()
    response = client.get(f"/api/projects/{project['id']}/contributors")
    assert response.status_code == 200
    assert response.json() == []


def test_list_contributors_reflects_hours_logged(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Contributeurs"}).json()
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 2, "description": "Dev"},
    )
    add_approved_member(project["id"], "bob@test.local")
    client.headers["X-Dev-Email"] = "bob@test.local"
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 3, "description": "Dev"},
    )

    response = client.get(f"/api/projects/{project['id']}/contributors")
    assert response.status_code == 200
    body = {c["account_email"]: c["hours"] for c in response.json()}
    assert body == {"alice@test.local": 2.0, "bob@test.local": 3.0}
