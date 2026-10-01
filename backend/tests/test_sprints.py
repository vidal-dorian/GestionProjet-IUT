def create_test_project(client, name="Projet Sprints", email="alice@test.local"):
    client.headers["X-Dev-Email"] = email
    return client.post("/api/projects", json={"name": name}).json()


def test_list_sprints_for_unknown_project_returns_404(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    response = client.get("/api/projects/999/sprints")
    assert response.status_code == 404


def test_list_sprints_empty_by_default(client):
    project = create_test_project(client)
    response = client.get(f"/api/projects/{project['id']}/sprints")
    assert response.status_code == 200
    assert response.json() == []


def test_create_sprint_for_unknown_project_returns_404(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
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


def _create_sprint(client, project_id, name="Sprint 1", start="2026-08-01", end="2026-08-14"):
    return client.post(
        f"/api/projects/{project_id}/sprints",
        json={"name": name, "start_date": start, "end_date": end},
    ).json()["sprint"]


def test_update_sprint_changes_dates_and_name(client):
    project = create_test_project(client)
    sprint = _create_sprint(client, project["id"])

    response = client.put(
        f"/api/projects/{project['id']}/sprints/{sprint['id']}",
        json={"name": "Sprint 1 bis", "start_date": "2026-08-03", "end_date": "2026-08-17"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sprint"]["id"] == sprint["id"]
    assert body["sprint"]["name"] == "Sprint 1 bis"
    assert body["sprint"]["start_date"] == "2026-08-03"
    assert body["sprint"]["end_date"] == "2026-08-17"
    assert body["overlap_warning"] is None

    listed = client.get(f"/api/projects/{project['id']}/sprints").json()
    assert [(s["name"], s["start_date"], s["end_date"]) for s in listed] == [
        ("Sprint 1 bis", "2026-08-03", "2026-08-17")
    ]


def test_update_sprint_end_date_must_be_after_start_date(client):
    project = create_test_project(client)
    sprint = _create_sprint(client, project["id"])

    response = client.put(
        f"/api/projects/{project['id']}/sprints/{sprint['id']}",
        json={"name": "Sprint 1", "start_date": "2026-08-14", "end_date": "2026-08-01"},
    )
    assert response.status_code == 422


def test_update_sprint_into_overlap_returns_warning(client):
    project = create_test_project(client)
    _create_sprint(client, project["id"], name="Sprint 1", start="2026-08-01", end="2026-08-14")
    sprint_2 = _create_sprint(client, project["id"], name="Sprint 2", start="2026-08-15", end="2026-08-28")

    response = client.put(
        f"/api/projects/{project['id']}/sprints/{sprint_2['id']}",
        json={"name": "Sprint 2", "start_date": "2026-08-10", "end_date": "2026-08-28"},
    )
    assert response.status_code == 200
    assert "Sprint 1" in response.json()["overlap_warning"]


def test_update_sprint_does_not_warn_about_itself(client):
    project = create_test_project(client)
    sprint = _create_sprint(client, project["id"])

    response = client.put(
        f"/api/projects/{project['id']}/sprints/{sprint['id']}",
        json={"name": "Sprint 1", "start_date": "2026-08-02", "end_date": "2026-08-13"},
    )
    assert response.json()["overlap_warning"] is None


def test_update_unknown_sprint_returns_404(client):
    project = create_test_project(client)

    response = client.put(
        f"/api/projects/{project['id']}/sprints/999",
        json={"name": "Sprint 1", "start_date": "2026-08-01", "end_date": "2026-08-14"},
    )
    assert response.status_code == 404


def test_update_sprint_of_another_project_returns_404(client):
    project_a = create_test_project(client, name="Projet A")
    project_b = create_test_project(client, name="Projet B")
    sprint = _create_sprint(client, project_a["id"])

    response = client.put(
        f"/api/projects/{project_b['id']}/sprints/{sprint['id']}",
        json={"name": "Sprint 1", "start_date": "2026-08-01", "end_date": "2026-08-14"},
    )
    assert response.status_code == 404


def test_update_sprint_requires_project_membership(client):
    project = create_test_project(client)
    sprint = _create_sprint(client, project["id"])

    client.headers["X-Dev-Email"] = "mallory@test.local"
    response = client.put(
        f"/api/projects/{project['id']}/sprints/{sprint['id']}",
        json={"name": "Sprint 1", "start_date": "2026-09-01", "end_date": "2026-09-14"},
    )
    assert response.status_code == 403
