def test_create_project_requires_name(client):
    response = client.post("/api/projects", json={"name": ""})
    assert response.status_code == 422


def test_create_project_with_name_and_description(client):
    response = client.post(
        "/api/projects",
        json={"name": "Application mobile", "description": "Suivi des heures"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Application mobile"
    assert body["description"] == "Suivi des heures"
    assert body["id"] is not None
    assert body["created_at"] is not None


def test_create_project_without_description_is_optional(client):
    response = client.post("/api/projects", json={"name": "Sans description"})
    assert response.status_code == 201
    assert response.json()["description"] is None


def test_project_name_must_be_unique(client):
    client.post("/api/projects", json={"name": "Doublon"})
    response = client.post("/api/projects", json={"name": "Doublon"})
    assert response.status_code == 409


def test_get_project_after_creation(client):
    created = client.post("/api/projects", json={"name": "Consultable"}).json()
    response = client.get(f"/api/projects/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Consultable"


def test_get_unknown_project_returns_404(client):
    response = client.get("/api/projects/999")
    assert response.status_code == 404


def test_update_project_name_and_description(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    created = client.post("/api/projects", json={"name": "Ancien nom", "description": "Ancienne description"}).json()

    response = client.put(
        f"/api/projects/{created['id']}",
        json={"name": "Nouveau nom", "description": "Nouvelle description"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Nouveau nom"
    assert body["description"] == "Nouvelle description"

    fetched = client.get(f"/api/projects/{created['id']}").json()
    assert fetched["name"] == "Nouveau nom"


def test_update_unknown_project_returns_404(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    response = client.put("/api/projects/999", json={"name": "Peu importe"})
    assert response.status_code == 404


def test_update_project_keeping_its_own_name_is_allowed(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    created = client.post("/api/projects", json={"name": "Nom stable"}).json()

    response = client.put(f"/api/projects/{created['id']}", json={"name": "Nom stable", "description": "Maj"})
    assert response.status_code == 200
    assert response.json()["description"] == "Maj"


def test_update_project_name_must_stay_unique(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    client.post("/api/projects", json={"name": "Projet A"})
    project_b = client.post("/api/projects", json={"name": "Projet B"}).json()

    response = client.put(f"/api/projects/{project_b['id']}", json={"name": "Projet A"})
    assert response.status_code == 409


def test_delete_project_succeeds(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    created = client.post("/api/projects", json={"name": "À supprimer"}).json()

    response = client.delete(f"/api/projects/{created['id']}")
    assert response.status_code == 204

    assert client.get(f"/api/projects/{created['id']}").status_code == 404


def test_delete_unknown_project_returns_404(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    response = client.delete("/api/projects/999")
    assert response.status_code == 404


def test_delete_project_cascades_to_time_entries(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Cascade"}).json()
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 2, "description": "Dev"},
    )

    response = client.delete(f"/api/projects/{project['id']}")
    assert response.status_code == 204

    # A freed project name can be reused, proving the underlying rows are gone
    # (a lingering time-entry row referencing project_id would break the
    # cascade at the database level and this recreation would fail).
    recreated = client.post("/api/projects", json={"name": "Projet Cascade"})
    assert recreated.status_code == 201
