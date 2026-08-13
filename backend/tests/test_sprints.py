def create_test_project(client, name="Projet Sprints"):
    return client.post("/api/projects", json={"name": name}).json()


def test_list_sprints_for_unknown_project_returns_404(client):
    response = client.get("/api/projects/999/sprints")
    assert response.status_code == 404


def test_list_sprints_empty_by_default(client):
    project = create_test_project(client)
    response = client.get(f"/api/projects/{project['id']}/sprints")
    assert response.status_code == 200
    assert response.json() == []


def test_create_sprint_for_unknown_project_returns_404(client):
    response = client.post(
        "/api/projects/999/sprints",
        json={"name": "Sprint 1", "start_date": "2026-08-01", "end_date": "2026-08-14"},
    )
    assert response.status_code == 404


def test_create_sprint_requires_name(client):
    project = create_test_project(client)
    response = client.post(
        f"/api/projects/{project['id']}/sprints",
        json={"name": "", "start_date": "2026-08-01", "end_date": "2026-08-14"},
    )
    assert response.status_code == 422


def test_create_sprint_end_date_must_be_after_start_date(client):
    project = create_test_project(client)
    response = client.post(
        f"/api/projects/{project['id']}/sprints",
        json={"name": "Sprint 1", "start_date": "2026-08-14", "end_date": "2026-08-01"},
    )
    assert response.status_code == 422


def test_create_sprint_success_has_no_overlap_warning(client):
    project = create_test_project(client)
    response = client.post(
        f"/api/projects/{project['id']}/sprints",
        json={"name": "Sprint 1", "start_date": "2026-08-01", "end_date": "2026-08-14"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["sprint"]["name"] == "Sprint 1"
    assert body["sprint"]["project_id"] == project["id"]
    assert body["overlap_warning"] is None

    listed = client.get(f"/api/projects/{project['id']}/sprints").json()
    assert len(listed) == 1


def test_create_overlapping_sprint_returns_explicit_warning_but_still_creates(client):
    project = create_test_project(client)
    client.post(
        f"/api/projects/{project['id']}/sprints",
        json={"name": "Sprint 1", "start_date": "2026-08-01", "end_date": "2026-08-14"},
    )

    response = client.post(
        f"/api/projects/{project['id']}/sprints",
        json={"name": "Sprint 2", "start_date": "2026-08-10", "end_date": "2026-08-24"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["overlap_warning"] is not None
    assert "Sprint 1" in body["overlap_warning"]

    listed = client.get(f"/api/projects/{project['id']}/sprints").json()
    assert len(listed) == 2


def test_create_non_overlapping_sprint_has_no_warning(client):
    project = create_test_project(client)
    client.post(
        f"/api/projects/{project['id']}/sprints",
        json={"name": "Sprint 1", "start_date": "2026-08-01", "end_date": "2026-08-14"},
    )

    response = client.post(
        f"/api/projects/{project['id']}/sprints",
        json={"name": "Sprint 2", "start_date": "2026-08-15", "end_date": "2026-08-28"},
    )
    assert response.status_code == 201
    assert response.json()["overlap_warning"] is None
