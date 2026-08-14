from unittest.mock import AsyncMock, patch


def setup_authenticated_account(client, email="alice@test.local"):
    client.headers["X-Dev-Email"] = email
    project = client.post("/api/projects", json={"name": "Projet Heures"}).json()
    return project, email


def link_repo_and_sync_issues(client, project_id, issues):
    with patch("app.routers.github.github_client.verify_repo", new_callable=AsyncMock):
        client.put(f"/api/projects/{project_id}/github", json={"repo": "owner/repo"})
    with patch("app.github_sync.github_client.list_issues", new_callable=AsyncMock) as mock_list_issues:
        mock_list_issues.return_value = issues
        client.post(f"/api/projects/{project_id}/github/sync")
    return {issue["number"]: issue for issue in client.get(f"/api/projects/{project_id}/github/issues").json()}


def test_create_time_entry_requires_authentication(client):
    project = client.post("/api/projects", json={"name": "Projet Sans Session"}).json()
    response = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 2, "description": "Dev"},
    )
    assert response.status_code == 401


def test_create_time_entry_success_attaches_current_account_and_project(client):
    project, email = setup_authenticated_account(client)

    response = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 2.5, "description": "Développement du formulaire"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["project_id"] == project["id"]
    assert body["account"]["email"] == email
    assert body["duration_hours"] == 2.5
    assert body["description"] == "Développement du formulaire"


def test_duration_must_be_strictly_positive(client):
    project, _ = setup_authenticated_account(client)

    response = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 0, "description": "Dev"},
    )
    assert response.status_code == 422


def test_duration_is_capped_at_24_hours(client):
    project, _ = setup_authenticated_account(client)

    response = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 25, "description": "Dev"},
    )
    assert response.status_code == 422


def test_description_is_required(client):
    project, _ = setup_authenticated_account(client)

    response = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "   "},
    )
    assert response.status_code == 422


def test_new_entry_appears_first_in_history(client):
    project, _ = setup_authenticated_account(client)

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


def test_time_entries_are_scoped_per_project(client):
    project_a, _ = setup_authenticated_account(client)
    project_b = client.post("/api/projects", json={"name": "Autre Projet"}).json()

    client.post(
        f"/api/projects/{project_a['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "Sur A"},
    )

    response = client.get(f"/api/projects/{project_b['id']}/time-entries")
    assert response.status_code == 200
    assert response.json() == []


def test_update_time_entry_requires_authentication(client):
    project, _ = setup_authenticated_account(client)
    entry = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "Dev"},
    ).json()
    del client.headers["X-Dev-Email"]

    response = client.put(
        f"/api/projects/{project['id']}/time-entries/{entry['id']}",
        json={"date": "2026-08-14", "duration_hours": 2, "description": "Dev corrigé"},
    )
    assert response.status_code == 401


def test_update_own_time_entry_succeeds_with_prefilled_style_payload(client):
    project, _ = setup_authenticated_account(client)
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
    project, _ = setup_authenticated_account(client)
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
    project, _ = setup_authenticated_account(client)
    response = client.put(
        f"/api/projects/{project['id']}/time-entries/999",
        json={"date": "2026-08-14", "duration_hours": 1, "description": "Dev"},
    )
    assert response.status_code == 404


def test_cannot_update_another_accounts_entry(client):
    project, _ = setup_authenticated_account(client, email="alice@test.local")
    entry = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "Alice"},
    ).json()

    client.headers["X-Dev-Email"] = "bob@test.local"
    response = client.put(
        f"/api/projects/{project['id']}/time-entries/{entry['id']}",
        json={"date": "2026-08-14", "duration_hours": 2, "description": "Bob essaie de modifier"},
    )
    assert response.status_code == 403


def test_delete_own_time_entry_succeeds_after_confirmation(client):
    project, _ = setup_authenticated_account(client)
    entry = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "Dev"},
    ).json()

    response = client.delete(f"/api/projects/{project['id']}/time-entries/{entry['id']}")
    assert response.status_code == 204

    remaining = client.get(f"/api/projects/{project['id']}/time-entries").json()
    assert remaining == []


def test_cannot_delete_another_accounts_entry(client):
    project, _ = setup_authenticated_account(client, email="alice@test.local")
    entry = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "Alice"},
    ).json()

    client.headers["X-Dev-Email"] = "bob@test.local"
    response = client.delete(f"/api/projects/{project['id']}/time-entries/{entry['id']}")
    assert response.status_code == 403


def test_time_entry_without_github_issue_has_null_fields(client):
    project, _ = setup_authenticated_account(client)
    entry = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "Dev"},
    ).json()

    assert entry["github_issue_id"] is None
    assert entry["github_issue"] is None


def test_attaching_unknown_github_issue_returns_422(client):
    project, _ = setup_authenticated_account(client)

    response = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "Dev", "github_issue_id": 999},
    )
    assert response.status_code == 422


def test_attaching_a_github_issue_from_another_project_returns_422(client):
    project, _ = setup_authenticated_account(client)
    other_project = client.post("/api/projects", json={"name": "Autre Projet"}).json()
    issues = link_repo_and_sync_issues(
        client,
        other_project["id"],
        [{"number": 1, "title": "US-01", "state": "open", "labels": [], "html_url": "https://x/1"}],
    )

    response = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "Dev", "github_issue_id": issues[1]["id"]},
    )
    assert response.status_code == 422


def create_sprint(client, project_id, name="Sprint 1", start="2026-08-01", end="2026-08-14"):
    return client.post(
        f"/api/projects/{project_id}/sprints", json={"name": name, "start_date": start, "end_date": end}
    ).json()["sprint"]


def test_time_entry_without_sprint_has_null_fields(client):
    project, _ = setup_authenticated_account(client)
    entry = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "Dev"},
    ).json()

    assert entry["sprint_id"] is None
    assert entry["sprint"] is None


def test_attaching_unknown_sprint_returns_422(client):
    project, _ = setup_authenticated_account(client)

    response = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "Dev", "sprint_id": 999},
    )
    assert response.status_code == 422


def test_attaching_a_sprint_from_another_project_returns_422(client):
    project, _ = setup_authenticated_account(client)
    other_project = client.post("/api/projects", json={"name": "Autre Projet Sprint"}).json()
    sprint = create_sprint(client, other_project["id"])

    response = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "Dev", "sprint_id": sprint["id"]},
    )
    assert response.status_code == 422


def test_create_and_update_time_entry_can_attach_sprint(client):
    project, _ = setup_authenticated_account(client)
    sprint = create_sprint(client, project["id"])

    entry = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "Dev", "sprint_id": sprint["id"]},
    ).json()
    assert entry["sprint_id"] == sprint["id"]
    assert entry["sprint"]["name"] == "Sprint 1"

    updated = client.put(
        f"/api/projects/{project['id']}/time-entries/{entry['id']}",
        json={"date": "2026-08-13", "duration_hours": 2, "description": "Dev", "sprint_id": None},
    ).json()
    assert updated["sprint_id"] is None
    assert updated["sprint"] is None


def test_create_and_update_time_entry_can_attach_github_issue(client):
    project, _ = setup_authenticated_account(client)
    issues = link_repo_and_sync_issues(
        client,
        project["id"],
        [{"number": 5, "title": "US-05 — Se connecter", "state": "open", "labels": [], "html_url": "https://x/5"}],
    )
    issue_id = issues[5]["id"]

    entry = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "Dev", "github_issue_id": issue_id},
    ).json()
    assert entry["github_issue_id"] == issue_id
    assert entry["github_issue"]["number"] == 5
    assert entry["github_issue"]["title"] == "US-05 — Se connecter"

    updated = client.put(
        f"/api/projects/{project['id']}/time-entries/{entry['id']}",
        json={"date": "2026-08-13", "duration_hours": 2, "description": "Dev", "github_issue_id": None},
    ).json()
    assert updated["github_issue_id"] is None
    assert updated["github_issue"] is None


def create_category(client, project_id, name="Dev"):
    return client.post(f"/api/projects/{project_id}/categories", json={"name": name}).json()


def test_time_entry_without_category_has_null_fields(client):
    project, _ = setup_authenticated_account(client)
    entry = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "Dev"},
    ).json()

    assert entry["category_id"] is None
    assert entry["category"] is None


def test_attaching_unknown_category_returns_422(client):
    project, _ = setup_authenticated_account(client)

    response = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "Dev", "category_id": 999},
    )
    assert response.status_code == 422


def test_attaching_a_category_from_another_project_returns_422(client):
    project, _ = setup_authenticated_account(client)
    other_project = client.post("/api/projects", json={"name": "Autre Projet Catégorie"}).json()
    category = create_category(client, other_project["id"])

    response = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "Dev", "category_id": category["id"]},
    )
    assert response.status_code == 422


def test_create_and_update_time_entry_can_attach_category(client):
    project, _ = setup_authenticated_account(client)
    category = create_category(client, project["id"])

    entry = client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-13", "duration_hours": 1, "description": "Dev", "category_id": category["id"]},
    ).json()
    assert entry["category_id"] == category["id"]
    assert entry["category"]["name"] == "Dev"

    updated = client.put(
        f"/api/projects/{project['id']}/time-entries/{entry['id']}",
        json={"date": "2026-08-13", "duration_hours": 2, "description": "Dev", "category_id": None},
    ).json()
    assert updated["category_id"] is None
    assert updated["category"] is None
