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
