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


def test_update_time_entry_requires_authentication(client):
    project, _ = setup_logged_in_member(client)
    entry = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "Dev"},
    ).json()
    client.post("/api/auth/logout")

    response = client.put(
        f"/api/projects/{project['id']}/time-entries/{entry['id']}",
        json={"date": "2026-08-14", "duration_hours": 2, "description": "Dev corrigé"},
    )
    assert response.status_code == 401


def test_update_own_time_entry_succeeds_with_prefilled_style_payload(client):
    project, _ = setup_logged_in_member(client)
    entry = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "Dev"},
    ).json()

    response = client.put(
        f"/api/projects/{project['id']}/time-entries/{entry['id']}",
        json={"date": "2026-08-14", "duration_hours": 3.5, "description": "Dev corrigé"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == entry["id"]
    assert body["date"] == "2026-08-14"
    assert body["duration_hours"] == 3.5
    assert body["description"] == "Dev corrigé"


def test_update_time_entry_applies_same_validation_as_creation(client):
    project, _ = setup_logged_in_member(client)
    entry = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "Dev"},
    ).json()

    response = client.put(
        f"/api/projects/{project['id']}/time-entries/{entry['id']}",
        json={"date": "2026-08-14", "duration_hours": 25, "description": "Dev"},
    )
    assert response.status_code == 422


def test_update_unknown_entry_returns_404(client):
    project, _ = setup_logged_in_member(client)
    response = client.put(
        f"/api/projects/{project['id']}/time-entries/999",
        json={"date": "2026-08-14", "duration_hours": 1, "description": "Dev"},
    )
    assert response.status_code == 404


def test_cannot_update_another_members_entry(client):
    project, alice = setup_logged_in_member(client)
    entry = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "Alice"},
    ).json()

    bob = client.post(f"/api/projects/{project['id']}/members", json={"name": "Bob", "pin": "5678"}).json()
    client.post(f"/api/projects/{project['id']}/members/{bob['id']}/login", json={"pin": "5678"})

    response = client.put(
        f"/api/projects/{project['id']}/time-entries/{entry['id']}",
        json={"date": "2026-08-14", "duration_hours": 2, "description": "Bob essaie de modifier"},
    )
    assert response.status_code == 403


def test_delete_own_time_entry_succeeds_after_confirmation(client):
    project, _ = setup_logged_in_member(client)
    entry = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "Dev"},
    ).json()

    response = client.delete(f"/api/projects/{project['id']}/time-entries/{entry['id']}")
    assert response.status_code == 204

    remaining = client.get(f"/api/projects/{project['id']}/time-entries").json()
    assert remaining == []


def test_cannot_delete_another_members_entry(client):
    project, alice = setup_logged_in_member(client)
    entry = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "Alice"},
    ).json()

    bob = client.post(f"/api/projects/{project['id']}/members", json={"name": "Bob", "pin": "5678"}).json()
    client.post(f"/api/projects/{project['id']}/members/{bob['id']}/login", json={"pin": "5678"})

    response = client.delete(f"/api/projects/{project['id']}/time-entries/{entry['id']}")
    assert response.status_code == 403


def test_delete_recalculates_member_total_hours_immediately(client):
    project, member = setup_logged_in_member(client)
    entry = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 4, "description": "Dev"},
    ).json()

    client.delete(f"/api/projects/{project['id']}/time-entries/{entry['id']}")

    members = client.get(f"/api/projects/{project['id']}/members").json()
    assert next(m for m in members if m["id"] == member["id"])["total_hours"] == 0.0
