def create_test_project(client, name="Projet avec membres"):
    return client.post("/api/projects", json={"name": name}).json()


def test_add_member_requires_name_and_four_digit_pin(client):
    project = create_test_project(client)

    response = client.post(f"/api/projects/{project['id']}/members", json={"name": "Alice", "pin": "123"})
    assert response.status_code == 422

    response = client.post(f"/api/projects/{project['id']}/members", json={"name": "Alice", "pin": "abcd"})
    assert response.status_code == 422

    response = client.post(f"/api/projects/{project['id']}/members", json={"name": "", "pin": "1234"})
    assert response.status_code == 422


def test_add_member_success(client):
    project = create_test_project(client)

    response = client.post(f"/api/projects/{project['id']}/members", json={"name": "Alice", "pin": "1234"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Alice"
    assert body["project_id"] == project["id"]
    assert "pin" not in body
    assert "pin_hash" not in body


def test_member_name_must_be_unique_within_project(client):
    project = create_test_project(client)
    client.post(f"/api/projects/{project['id']}/members", json={"name": "Alice", "pin": "1234"})

    response = client.post(f"/api/projects/{project['id']}/members", json={"name": "Alice", "pin": "5678"})
    assert response.status_code == 409


def test_same_member_name_allowed_on_different_projects(client):
    project_a = create_test_project(client, "Projet A")
    project_b = create_test_project(client, "Projet B")

    response_a = client.post(f"/api/projects/{project_a['id']}/members", json={"name": "Alice", "pin": "1234"})
    response_b = client.post(f"/api/projects/{project_b['id']}/members", json={"name": "Alice", "pin": "5678"})
    assert response_a.status_code == 201
    assert response_b.status_code == 201


def test_add_member_to_unknown_project_returns_404(client):
    response = client.post("/api/projects/999/members", json={"name": "Alice", "pin": "1234"})
    assert response.status_code == 404


def test_member_appears_immediately_in_project_members_list(client):
    project = create_test_project(client)
    client.post(f"/api/projects/{project['id']}/members", json={"name": "Alice", "pin": "1234"})

    response = client.get(f"/api/projects/{project['id']}/members")
    assert response.status_code == 200
    names = [m["name"] for m in response.json()]
    assert names == ["Alice"]


def test_members_list_shows_name_and_total_hours(client):
    project = create_test_project(client)
    client.post(f"/api/projects/{project['id']}/members", json={"name": "Bob", "pin": "1234"})
    client.post(f"/api/projects/{project['id']}/members", json={"name": "Alice", "pin": "5678"})

    response = client.get(f"/api/projects/{project['id']}/members")
    assert response.status_code == 200
    body = response.json()
    assert [m["name"] for m in body] == ["Alice", "Bob"]
    assert all(m["total_hours"] == 0 for m in body)


def test_project_list_member_count_reflects_added_members(client):
    project = create_test_project(client)
    client.post(f"/api/projects/{project['id']}/members", json={"name": "Alice", "pin": "1234"})
    client.post(f"/api/projects/{project['id']}/members", json={"name": "Bob", "pin": "4321"})

    response = client.get("/api/projects")
    body = {p["id"]: p for p in response.json()}
    assert body[project["id"]]["member_count"] == 2


def test_delete_member_succeeds(client):
    project = create_test_project(client)
    member = client.post(
        f"/api/projects/{project['id']}/members", json={"name": "Alice", "pin": "1234"}
    ).json()

    response = client.delete(f"/api/projects/{project['id']}/members/{member['id']}")
    assert response.status_code == 204

    remaining = client.get(f"/api/projects/{project['id']}/members").json()
    assert remaining == []


def test_delete_unknown_member_returns_404(client):
    project = create_test_project(client)
    response = client.delete(f"/api/projects/{project['id']}/members/999")
    assert response.status_code == 404


def test_delete_member_for_unknown_project_returns_404(client):
    response = client.delete("/api/projects/999/members/1")
    assert response.status_code == 404


def test_delete_member_removes_their_time_entries(client):
    project = create_test_project(client)
    member = client.post(
        f"/api/projects/{project['id']}/members", json={"name": "Alice", "pin": "1234"}
    ).json()
    client.post(f"/api/projects/{project['id']}/members/{member['id']}/login", json={"pin": "1234"})
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 2, "description": "Dev"},
    )

    response = client.delete(f"/api/projects/{project['id']}/members/{member['id']}")
    assert response.status_code == 204

    recent = client.get(f"/api/projects/{project['id']}/dashboard/recent-entries").json()
    assert recent == []


def test_deleted_members_session_is_rejected(client):
    project = create_test_project(client)
    member = client.post(
        f"/api/projects/{project['id']}/members", json={"name": "Alice", "pin": "1234"}
    ).json()
    client.post(f"/api/projects/{project['id']}/members/{member['id']}/login", json={"pin": "1234"})
    assert client.get("/api/auth/me").status_code == 200

    client.delete(f"/api/projects/{project['id']}/members/{member['id']}")

    assert client.get("/api/auth/me").status_code == 401
