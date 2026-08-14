def create_test_project(client, name="Projet Catégories", email="alice@test.local"):
    client.headers["X-Dev-Email"] = email
    return client.post("/api/projects", json={"name": name}).json()


def test_list_categories_for_unknown_project_returns_404(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    response = client.get("/api/projects/999/categories")
    assert response.status_code == 404


def test_list_categories_empty_by_default(client):
    project = create_test_project(client)
    response = client.get(f"/api/projects/{project['id']}/categories")
    assert response.status_code == 200
    assert response.json() == []


def test_create_category_for_unknown_project_returns_404(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    response = client.post("/api/projects/999/categories", json={"name": "Dev"})
    assert response.status_code == 404


def test_create_category_requires_name(client):
    project = create_test_project(client)
    response = client.post(f"/api/projects/{project['id']}/categories", json={"name": "   "})
    assert response.status_code == 422


def test_create_category_success(client):
    project = create_test_project(client)
    response = client.post(f"/api/projects/{project['id']}/categories", json={"name": "Dev"})
    assert response.status_code == 201
    assert response.json()["name"] == "Dev"

    listed = client.get(f"/api/projects/{project['id']}/categories").json()
    assert len(listed) == 1


def test_create_duplicate_category_name_returns_409(client):
    project = create_test_project(client)
    client.post(f"/api/projects/{project['id']}/categories", json={"name": "Dev"})

    response = client.post(f"/api/projects/{project['id']}/categories", json={"name": "dev"})
    assert response.status_code == 409
