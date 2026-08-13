def setup_logged_in_member(client, project_name="Projet Dashboard", pin="1234"):
    project = client.post("/api/projects", json={"name": project_name}).json()
    member = client.post(f"/api/projects/{project['id']}/members", json={"name": "Alice", "pin": pin}).json()
    client.post(f"/api/projects/{project['id']}/members/{member['id']}/login", json={"pin": pin})
    return project, member


def test_hours_over_time_for_unknown_project_returns_404(client):
    response = client.get("/api/projects/999/dashboard/hours-over-time")
    assert response.status_code == 404


def test_hours_over_time_with_no_entries_returns_empty_series(client):
    project = client.post("/api/projects", json={"name": "Projet Vide"}).json()
    response = client.get(f"/api/projects/{project['id']}/dashboard/hours-over-time")
    assert response.status_code == 200
    body = response.json()
    assert body["granularity"] == "day"
    assert body["points"] == []


def test_hours_over_time_uses_daily_granularity_for_short_span_and_fills_gaps(client):
    project, _ = setup_logged_in_member(client)

    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-01", "duration_hours": 2, "description": "Jour 1"},
    )
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-03", "duration_hours": 1.5, "description": "Jour 3"},
    )

    response = client.get(f"/api/projects/{project['id']}/dashboard/hours-over-time")
    assert response.status_code == 200
    body = response.json()
    assert body["granularity"] == "day"
    assert body["points"] == [
        {"period": "2026-08-01", "hours": 2.0},
        {"period": "2026-08-02", "hours": 0.0},
        {"period": "2026-08-03", "hours": 1.5},
    ]


def test_hours_over_time_sums_entries_from_all_members(client):
    project, alice = setup_logged_in_member(client)
    bob = client.post(f"/api/projects/{project['id']}/members", json={"name": "Bob", "pin": "5678"}).json()
    client.post(f"/api/projects/{project['id']}/members/{bob['id']}/login", json={"pin": "5678"})

    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-01", "duration_hours": 2, "description": "Alice ou Bob selon la session"},
    )

    response = client.get(f"/api/projects/{project['id']}/dashboard/hours-over-time")
    body = response.json()
    assert body["points"] == [{"period": "2026-08-01", "hours": 2.0}]


def test_hours_over_time_uses_weekly_granularity_for_long_span(client):
    project, _ = setup_logged_in_member(client, project_name="Projet Long")

    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-01-05", "duration_hours": 3, "description": "Début (lundi)"},
    )
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-03-10", "duration_hours": 4, "description": "Fin (mardi)"},
    )

    response = client.get(f"/api/projects/{project['id']}/dashboard/hours-over-time")
    body = response.json()
    assert body["granularity"] == "week"
    assert body["points"][0] == {"period": "2026-01-05", "hours": 3.0}
    assert body["points"][-1] == {"period": "2026-03-09", "hours": 4.0}
    assert len(body["points"]) == 10


def test_recent_entries_for_unknown_project_returns_404(client):
    response = client.get("/api/projects/999/dashboard/recent-entries")
    assert response.status_code == 404


def test_recent_entries_empty_project_returns_empty_list(client):
    project = client.post("/api/projects", json={"name": "Projet Sans Entrées"}).json()
    response = client.get(f"/api/projects/{project['id']}/dashboard/recent-entries")
    assert response.status_code == 200
    assert response.json() == []


def test_recent_entries_includes_author_across_all_members_sorted_by_date_desc(client):
    project, alice = setup_logged_in_member(client, project_name="Projet Multi Auteurs")
    bob = client.post(f"/api/projects/{project['id']}/members", json={"name": "Bob", "pin": "5678"}).json()

    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-01", "duration_hours": 2, "description": "Entrée d'Alice"},
    )
    client.post(f"/api/projects/{project['id']}/members/{bob['id']}/login", json={"pin": "5678"})
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-05", "duration_hours": 1, "description": "Entrée de Bob"},
    )

    response = client.get(f"/api/projects/{project['id']}/dashboard/recent-entries")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["member_name"] == "Bob"
    assert body[0]["date"] == "2026-08-05"
    assert body[0]["duration_hours"] == 1
    assert body[0]["description"] == "Entrée de Bob"
    assert body[1]["member_name"] == "Alice"


def test_recent_entries_limited_to_ten(client):
    project, _ = setup_logged_in_member(client, project_name="Projet Beaucoup D'Entrées")
    for day in range(1, 13):
        client.post(
            f"/api/projects/{project['id']}/time-entries",
            json={"date": f"2026-08-{day:02d}", "duration_hours": 1, "description": f"Jour {day}"},
        )

    response = client.get(f"/api/projects/{project['id']}/dashboard/recent-entries")
    body = response.json()
    assert len(body) == 10
    assert body[0]["date"] == "2026-08-12"
    assert body[-1]["date"] == "2026-08-03"


def test_stats_for_unknown_project_returns_404(client):
    response = client.get("/api/projects/999/dashboard/stats")
    assert response.status_code == 404


def test_stats_for_project_without_members_or_entries(client):
    project = client.post("/api/projects", json={"name": "Projet Stats Vide"}).json()
    response = client.get(f"/api/projects/{project['id']}/dashboard/stats")
    assert response.status_code == 200
    assert response.json() == {
        "total_hours": 0.0,
        "member_count": 0,
        "active_member_count": 0,
        "entry_count": 0,
        "average_hours_per_member": 0.0,
    }


def test_stats_reflect_members_and_entries(client):
    project, alice = setup_logged_in_member(client, project_name="Projet Stats")
    bob = client.post(f"/api/projects/{project['id']}/members", json={"name": "Bob", "pin": "5678"}).json()
    # Zoe is a registered member but never logs any hours (inactive)
    client.post(f"/api/projects/{project['id']}/members", json={"name": "Zoe", "pin": "9999"})

    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-01", "duration_hours": 3, "description": "Alice 1"},
    )
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-02", "duration_hours": 2, "description": "Alice 2"},
    )
    client.post(f"/api/projects/{project['id']}/members/{bob['id']}/login", json={"pin": "5678"})
    client.post(
        f"/api/projects/{project['id']}/time-entries",
        json={"date": "2026-08-03", "duration_hours": 1, "description": "Bob 1"},
    )

    response = client.get(f"/api/projects/{project['id']}/dashboard/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["total_hours"] == 6.0
    assert body["member_count"] == 3
    assert body["active_member_count"] == 2
    assert body["entry_count"] == 3
    assert body["average_hours_per_member"] == 2.0
