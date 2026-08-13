def setup_logged_in_member(client, pin="1234"):
    project = client.post("/api/projects", json={"name": "Projet Heures"}).json()
    member = client.post(f"/api/projects/{project['id']}/members", json={"name": "Alice", "pin": pin}).json()
    client.post(f"/api/projects/{project['id']}/members/{member['id']}/login", json={"pin": pin})
    return project, member


def test_create_time_entry_requires_authentication(client):
    project = client.post("/api/projects", json={"name": "Projet Sans Session"}).json()
    response = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 2, "description": "Dev"},
    )
    assert response.status_code == 401


def test_create_time_entry_success_attaches_current_member_and_project(client):
    project, member = setup_logged_in_member(client)

    response = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 2.5, "description": "Développement du formulaire"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["project_id"] == project["id"]
    assert body["member_id"] == member["id"]
    assert body["duration_hours"] == 2.5
    assert body["description"] == "Développement du formulaire"


def test_duration_must_be_strictly_positive(client):
    project, _ = setup_logged_in_member(client)

    response = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 0, "description": "Dev"},
    )
    assert response.status_code == 422


def test_duration_is_capped_at_24_hours(client):
    project, _ = setup_logged_in_member(client)

    response = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 25, "description": "Dev"},
    )
    assert response.status_code == 422


def test_description_is_required(client):
    project, _ = setup_logged_in_member(client)

    response = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "   "},
    )
    assert response.status_code == 422


def test_new_entry_appears_first_in_history(client):
    project, _ = setup_logged_in_member(client)

    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-01", "duration_hours": 1, "description": "Ancienne tâche"},
    )
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 2, "description": "Nouvelle tâche"},
    )

    response = client.get(f"/api/projects/{project['id']}/time-entries")
    assert response.status_code == 200
    descriptions = [entry["description"] for entry in response.json()]
    assert descriptions == ["Nouvelle tâche", "Ancienne tâche"]


def test_member_total_hours_reflects_time_entries(client):
    project, member = setup_logged_in_member(client)

    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 2.5, "description": "Dev"},
    )
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-14", "duration_hours": 1.5, "description": "Tests"},
    )

    response = client.get(f"/api/projects/{project['id']}/members")
    members_by_id = {m["id"]: m for m in response.json()}
    assert members_by_id[member["id"]]["total_hours"] == 4.0


def test_cannot_read_entries_for_a_different_project_than_session(client):
    project_a, _ = setup_logged_in_member(client, pin="1234")
    project_b = client.post("/api/projects", json={"name": "Autre Projet"}).json()

    response = client.get(f"/api/projects/{project_b['id']}/time-entries")
    assert response.status_code == 401
