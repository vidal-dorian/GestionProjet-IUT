def setup_project_with_member(client, pin="1234"):
    project = client.post("/api/projects", json={"name": "Projet Auth"}).json()
    member = client.post(f"/api/projects/{project['id']}/members", json={"name": "Alice", "pin": pin}).json()
    return project, member


def test_login_with_correct_pin_succeeds_and_sets_session_cookie(client):
    project, member = setup_project_with_member(client)

    response = client.post(
        f"/api/projects/{project['id']}/members/{member['id']}/login", json={"pin": "1234"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Alice"
    assert "session_token" in response.cookies


def test_login_with_wrong_pin_returns_generic_error(client):
    project, member = setup_project_with_member(client)

    response = client.post(
        f"/api/projects/{project['id']}/members/{member['id']}/login", json={"pin": "0000"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Nom ou PIN incorrect."
    assert "session_token" not in response.cookies


def test_login_with_unknown_member_returns_same_generic_error(client):
    project = client.post("/api/projects", json={"name": "Projet Auth 2"}).json()

    response = client.post(
        f"/api/projects/{project['id']}/members/999/login", json={"pin": "1234"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Nom ou PIN incorrect."


def test_me_without_session_returns_401(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_after_login_returns_current_member(client):
    project, member = setup_project_with_member(client)

    client.post(f"/api/projects/{project['id']}/members/{member['id']}/login", json={"pin": "1234"})
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == member["id"]
    assert body["name"] == "Alice"
    assert body["project_id"] == project["id"]


def test_logout_clears_session(client):
    project, member = setup_project_with_member(client)

    client.post(f"/api/projects/{project['id']}/members/{member['id']}/login", json={"pin": "1234"})
    assert client.get("/api/auth/me").status_code == 200

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 204
    assert client.get("/api/auth/me").status_code == 401
