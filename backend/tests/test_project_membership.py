from app import models
from tests.conftest import TestingSessionLocal


def _promote_to_admin(email: str) -> None:
    db = TestingSessionLocal()
    try:
        account = db.query(models.Account).filter(models.Account.email == email).one()
        account.is_admin = True
        db.commit()
    finally:
        db.close()


def test_creating_a_project_while_authenticated_joins_it_automatically(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Site vitrine"}).json()

    response = client.get("/api/me/projects")
    assert response.status_code == 200
    body = response.json()
    assert [p["id"] for p in body] == [project["id"]]
    assert body[0]["is_member"] is True


def test_creating_a_project_unauthenticated_does_not_crash_and_has_no_member(client):
    response = client.post("/api/projects", json={"name": "Projet anonyme"})
    assert response.status_code == 201


def test_me_projects_requires_authentication(client):
    response = client.get("/api/me/projects")
    assert response.status_code == 401


def test_me_projects_is_empty_when_not_a_member_of_anything(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    response = client.get("/api/me/projects")
    assert response.status_code == 200
    assert response.json() == []


def test_joining_a_project_creates_a_pending_request_without_immediate_access(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()

    client.headers["X-Dev-Email"] = "bob@test.local"
    join_response = client.post(f"/api/projects/{project['id']}/join")
    assert join_response.status_code == 200
    assert join_response.json() == {"project_id": project["id"], "status": "pending"}

    my_projects = client.get("/api/me/projects").json()
    assert my_projects == []


def test_joining_an_unknown_project_returns_404(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    response = client.post("/api/projects/999/join")
    assert response.status_code == 404


def test_joining_twice_stays_a_single_pending_request(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Idempotent"}).json()

    client.headers["X-Dev-Email"] = "bob@test.local"
    client.post(f"/api/projects/{project['id']}/join")
    client.post(f"/api/projects/{project['id']}/join")

    client.headers["X-Dev-Email"] = "admin@test.local"
    client.get("/api/me")
    _promote_to_admin("admin@test.local")
    requests_ = client.get("/api/admin/membership-requests").json()
    matching = [r for r in requests_ if r["project_id"] == project["id"] and r["account_email"] == "bob@test.local"]
    assert len(matching) == 1


def test_project_creator_has_immediate_approved_access(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Le mien"}).json()

    by_id = {p["id"]: p for p in client.get("/api/projects").json()}
    assert by_id[project["id"]]["is_member"] is True
    assert by_id[project["id"]]["membership_status"] == "approved"


def test_list_projects_flags_pending_status_after_a_join_request(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()

    client.headers["X-Dev-Email"] = "bob@test.local"
    client.post(f"/api/projects/{project['id']}/join")

    by_id = {p["id"]: p for p in client.get("/api/projects").json()}
    assert by_id[project["id"]]["is_member"] is False
    assert by_id[project["id"]]["membership_status"] == "pending"


def test_list_projects_without_authentication_flags_no_membership(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    client.post("/api/projects", json={"name": "Un projet"})
    del client.headers["X-Dev-Email"]

    body = client.get("/api/projects").json()
    assert all(p["is_member"] is False and p["membership_status"] is None for p in body)


def test_existing_contributor_without_explicit_membership_still_sees_the_project(client):
    project = client.post("/api/projects", json={"name": "Projet legacy"}).json()

    client.headers["X-Dev-Email"] = "alice@test.local"
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 2, "description": "Dev"},
    )

    my_projects = client.get("/api/me/projects").json()
    assert [p["id"] for p in my_projects] == [project["id"]]


def test_admin_who_joins_a_project_gets_immediate_access(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()

    client.headers["X-Dev-Email"] = "admin@test.local"
    client.get("/api/me")  # provision the account before promoting it
    _promote_to_admin("admin@test.local")

    join_response = client.post(f"/api/projects/{project['id']}/join")
    assert join_response.json() == {"project_id": project["id"], "status": "approved"}

    my_projects = client.get("/api/me/projects").json()
    assert [p["id"] for p in my_projects] == [project["id"]]


def test_non_admin_cannot_list_membership_requests(client):
    client.headers["X-Dev-Email"] = "bob@test.local"
    response = client.get("/api/admin/membership-requests")
    assert response.status_code == 403


def test_admin_endpoints_require_authentication(client):
    response = client.get("/api/admin/membership-requests")
    assert response.status_code == 401


def test_admin_can_list_and_approve_a_pending_request(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()

    client.headers["X-Dev-Email"] = "bob@test.local"
    client.post(f"/api/projects/{project['id']}/join")

    client.headers["X-Dev-Email"] = "admin@test.local"
    client.get("/api/me")
    _promote_to_admin("admin@test.local")

    pending = client.get("/api/admin/membership-requests").json()
    assert len(pending) == 1
    request_id = pending[0]["id"]
    assert pending[0]["project_id"] == project["id"]
    assert pending[0]["account_email"] == "bob@test.local"
    assert pending[0]["status"] == "pending"

    approve_response = client.post(f"/api/admin/membership-requests/{request_id}/approve")
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    assert client.get("/api/admin/membership-requests").json() == []

    client.headers["X-Dev-Email"] = "bob@test.local"
    my_projects = client.get("/api/me/projects").json()
    assert [p["id"] for p in my_projects] == [project["id"]]


def test_admin_can_reject_a_pending_request(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()

    client.headers["X-Dev-Email"] = "bob@test.local"
    client.post(f"/api/projects/{project['id']}/join")

    client.headers["X-Dev-Email"] = "admin@test.local"
    client.get("/api/me")
    _promote_to_admin("admin@test.local")

    request_id = client.get("/api/admin/membership-requests").json()[0]["id"]
    reject_response = client.post(f"/api/admin/membership-requests/{request_id}/reject")
    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "rejected"

    client.headers["X-Dev-Email"] = "bob@test.local"
    assert client.get("/api/me/projects").json() == []
    by_id = {p["id"]: p for p in client.get("/api/projects").json()}
    assert by_id[project["id"]]["membership_status"] == "rejected"


def test_rejected_request_can_be_resubmitted(client):
    client.headers["X-Dev-Email"] = "alice@test.local"
    project = client.post("/api/projects", json={"name": "Projet Alice"}).json()

    client.headers["X-Dev-Email"] = "bob@test.local"
    client.post(f"/api/projects/{project['id']}/join")

    client.headers["X-Dev-Email"] = "admin@test.local"
    client.get("/api/me")
    _promote_to_admin("admin@test.local")
    request_id = client.get("/api/admin/membership-requests").json()[0]["id"]
    client.post(f"/api/admin/membership-requests/{request_id}/reject")

    client.headers["X-Dev-Email"] = "bob@test.local"
    resubmit_response = client.post(f"/api/projects/{project['id']}/join")
    assert resubmit_response.json() == {"project_id": project["id"], "status": "pending"}

    client.headers["X-Dev-Email"] = "admin@test.local"
    pending = client.get("/api/admin/membership-requests").json()
    assert len(pending) == 1
    assert pending[0]["status"] == "pending"


def test_approving_an_unknown_request_returns_404(client):
    client.headers["X-Dev-Email"] = "admin@test.local"
    client.get("/api/me")
    _promote_to_admin("admin@test.local")

    response = client.post("/api/admin/membership-requests/999/approve")
    assert response.status_code == 404
