"""US : noter plusieurs US (issues GitHub) sur une seule entrée de temps.

En tant que membre d'un projet, quand je note ma journée, je veux rattacher
une même entrée de temps à plusieurs US, pour ne pas devoir découper
artificiellement une journée passée sur plusieurs US.
"""

import io
from unittest.mock import AsyncMock, patch

import sqlalchemy as sa
from openpyxl import load_workbook

from app import models  # noqa: F401 — peuple Base.metadata avant create_all()
from app.database import Base, sync_missing_columns

ISSUES = [
    {"number": 1, "title": "US-01", "state": "open", "labels": [], "html_url": "https://github.com/owner/repo/issues/1"},
    {"number": 2, "title": "US-02", "state": "open", "labels": [], "html_url": "https://github.com/owner/repo/issues/2"},
    {"number": 3, "title": "US-03", "state": "open", "labels": [], "html_url": "https://github.com/owner/repo/issues/3"},
]


def setup_project(client, email="alice@test.local", name="Projet Multi-US"):
    client.headers["X-Dev-Email"] = email
    return client.post("/api/projects", json={"name": name}).json()


def sync_issues(client, project_id, issues):
    with patch("app.routers.github.github_client.verify_repo", new_callable=AsyncMock, return_value=False):
        client.put(f"/api/projects/{project_id}/github", json={"repo": "owner/repo"})
    with patch("app.github_sync.github_client.list_issues", new_callable=AsyncMock) as mock_list_issues:
        mock_list_issues.return_value = issues
        client.post(f"/api/projects/{project_id}/github/sync")
    return {issue["number"]: issue for issue in client.get(f"/api/projects/{project_id}/github/issues").json()}


def post_entry(client, project_id, **fields):
    payload = {"date": "2026-08-13", "duration_hours": 3, "description": "Dev", **fields}
    return client.post(f"/api/projects/{project_id}/time-entries", json=payload)


def test_given_several_us_when_i_create_an_entry_then_it_is_attached_to_all_of_them(client):
    project = setup_project(client)
    issues = sync_issues(client, project["id"], ISSUES)

    response = post_entry(client, project["id"], github_issue_ids=[issues[2]["id"], issues[1]["id"]])

    assert response.status_code == 201
    body = response.json()
    assert body["github_issue_ids"] == [issues[1]["id"], issues[2]["id"]]
    assert [issue["number"] for issue in body["github_issues"]] == [1, 2]
    listed = client.get(f"/api/projects/{project['id']}/time-entries").json()
    assert [issue["number"] for issue in listed[0]["github_issues"]] == [1, 2]


def test_given_no_us_when_i_create_an_entry_then_its_us_list_is_empty(client):
    project = setup_project(client)

    body = post_entry(client, project["id"]).json()

    assert body["github_issue_ids"] == []
    assert body["github_issues"] == []


def test_given_an_entry_with_several_us_when_i_update_it_then_its_us_list_is_replaced(client):
    project = setup_project(client)
    issues = sync_issues(client, project["id"], ISSUES)
    entry = post_entry(client, project["id"], github_issue_ids=[issues[1]["id"], issues[2]["id"]]).json()

    updated = client.put(
        f"/api/projects/{project['id']}/time-entries/{entry['id']}",
        json={"date": "2026-08-13", "duration_hours": 3, "description": "Dev", "github_issue_ids": [issues[3]["id"]]},
    ).json()
    assert [issue["number"] for issue in updated["github_issues"]] == [3]

    cleared = client.put(
        f"/api/projects/{project['id']}/time-entries/{entry['id']}",
        json={"date": "2026-08-13", "duration_hours": 3, "description": "Dev", "github_issue_ids": []},
    ).json()
    assert cleared["github_issues"] == []


def test_given_the_same_us_twice_when_i_create_an_entry_then_it_is_attached_once(client):
    project = setup_project(client)
    issues = sync_issues(client, project["id"], ISSUES)

    body = post_entry(client, project["id"], github_issue_ids=[issues[1]["id"], issues[1]["id"]]).json()

    assert body["github_issue_ids"] == [issues[1]["id"]]


def test_given_an_unknown_us_among_several_when_i_create_an_entry_then_it_is_refused(client):
    project = setup_project(client)
    issues = sync_issues(client, project["id"], ISSUES)

    response = post_entry(client, project["id"], github_issue_ids=[issues[1]["id"], 999])

    assert response.status_code == 422
    assert client.get(f"/api/projects/{project['id']}/time-entries").json() == []


def test_given_a_us_of_another_project_when_i_update_an_entry_then_it_is_refused(client):
    project = setup_project(client)
    issues = sync_issues(client, project["id"], ISSUES)
    other_project = client.post("/api/projects", json={"name": "Autre Projet"}).json()
    other_issues = sync_issues(client, other_project["id"], ISSUES[:1])
    entry = post_entry(client, project["id"], github_issue_ids=[issues[1]["id"]]).json()

    response = client.put(
        f"/api/projects/{project['id']}/time-entries/{entry['id']}",
        json={
            "date": "2026-08-13",
            "duration_hours": 3,
            "description": "Dev",
            "github_issue_ids": [issues[2]["id"], other_issues[1]["id"]],
        },
    )

    assert response.status_code == 422
    unchanged = client.get(f"/api/projects/{project['id']}/time-entries").json()[0]
    assert [issue["number"] for issue in unchanged["github_issues"]] == [1]


def test_given_an_entry_on_several_us_when_i_look_at_hours_by_us_then_its_hours_are_split_evenly(client):
    project = setup_project(client)
    issues = sync_issues(client, project["id"], ISSUES)
    post_entry(client, project["id"], duration_hours=3, github_issue_ids=[issues[1]["id"], issues[2]["id"]])
    post_entry(client, project["id"], duration_hours=1, github_issue_ids=[issues[1]["id"]])
    post_entry(client, project["id"], duration_hours=2)

    body = client.get(f"/api/projects/{project['id']}/dashboard/hours-by-issue").json()

    assert {item["issue_number"]: item["hours"] for item in body["items"]} == {1: 2.5, 2: 1.5}
    assert body["items"][0]["issue_number"] == 1
    assert body["unattached_hours"] == 2.0


def test_given_an_entry_on_several_us_when_i_look_at_sprint_stats_then_its_hours_are_split_evenly(client):
    project = setup_project(client)
    sprint = client.post(
        f"/api/projects/{project['id']}/sprints",
        json={"name": "Sprint 1", "start_date": "2026-08-01", "end_date": "2026-08-14"},
    ).json()["sprint"]
    issues = sync_issues(client, project["id"], ISSUES)
    post_entry(
        client,
        project["id"],
        duration_hours=4,
        sprint_id=sprint["id"],
        github_issue_ids=[issues[1]["id"], issues[2]["id"]],
    )
    post_entry(client, project["id"], duration_hours=1, sprint_id=sprint["id"])

    body = client.get(f"/api/projects/{project['id']}/dashboard/sprints/{sprint['id']}/stats").json()

    assert body["total_hours"] == 5.0
    assert {item["issue_number"]: item["hours"] for item in body["hours_by_issue"]["items"]} == {1: 2.0, 2: 2.0}
    assert body["hours_by_issue"]["unattached_hours"] == 1.0


def test_given_an_entry_on_several_us_when_i_export_it_then_the_issue_column_lists_them_all(client):
    project = setup_project(client)
    issues = sync_issues(client, project["id"], ISSUES)
    post_entry(client, project["id"], github_issue_ids=[issues[1]["id"], issues[2]["id"]])

    response = client.get(f"/api/projects/{project['id']}/time-entries/export")

    ws = load_workbook(io.BytesIO(response.content))["Entrées"]
    headers = [cell.value for cell in ws[1]]
    assert ws.cell(row=2, column=headers.index("Issue") + 1).value == "#1 US-01, #2 US-02"


def test_given_an_entry_on_several_us_when_one_disappears_from_github_then_the_entry_keeps_the_others(client):
    project = setup_project(client)
    issues = sync_issues(client, project["id"], ISSUES)
    post_entry(client, project["id"], github_issue_ids=[issues[1]["id"], issues[2]["id"]])

    sync_issues(client, project["id"], [ISSUES[0]])

    entry = client.get(f"/api/projects/{project['id']}/time-entries").json()[0]
    assert [issue["number"] for issue in entry["github_issues"]] == [1]
    body = client.get(f"/api/projects/{project['id']}/dashboard/hours-by-issue").json()
    assert {item["issue_number"]: item["hours"] for item in body["items"]} == {1: 3.0}


def test_given_entries_saved_with_a_single_us_when_the_app_starts_then_they_keep_their_us():
    """Données d'avant la fonctionnalité : la colonne time_entries.github_issue_id
    portait l'unique US de l'entrée. Le démarrage la reporte dans la nouvelle
    liste, une seule fois (un redémarrage ne doit pas recréer un lien retiré)."""
    from app.database import migrate_time_entry_issue_links

    engine = sa.create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(sa.text("ALTER TABLE time_entries ADD COLUMN github_issue_id INTEGER"))
        conn.execute(sa.text("INSERT INTO projects (id, name, github_label_filter_raw) VALUES (1, 'P', '')"))
        conn.execute(sa.text("INSERT INTO accounts (id, email, is_admin) VALUES (1, 'a@test.local', 0)"))
        conn.execute(
            sa.text(
                "INSERT INTO github_issues (id, project_id, number, title, state, labels_raw, url, synced_at) "
                "VALUES (10, 1, 1, 'US-01', 'open', '', 'https://x/1', '2026-08-01 00:00:00')"
            )
        )
        conn.execute(
            sa.text(
                "INSERT INTO time_entries (id, project_id, account_id, date, duration_hours, description, "
                "github_issue_id) VALUES "
                "(1, 1, 1, '2026-08-01', 2, 'Avec US', 10), (2, 1, 1, '2026-08-02', 1, 'Sans US', NULL)"
            )
        )

    sync_missing_columns(engine)
    migrate_time_entry_issue_links(engine)

    with engine.begin() as conn:
        links = conn.execute(sa.text("SELECT time_entry_id, github_issue_id FROM time_entry_issues")).fetchall()
        assert [tuple(row) for row in links] == [(1, 10)]
        conn.execute(sa.text("DELETE FROM time_entry_issues"))

    migrate_time_entry_issue_links(engine)

    with engine.begin() as conn:
        assert conn.execute(sa.text("SELECT COUNT(*) FROM time_entry_issues")).scalar() == 0


def test_given_a_fresh_database_when_the_app_starts_then_the_link_migration_is_a_noop():
    from app.database import migrate_time_entry_issue_links

    engine = sa.create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    migrate_time_entry_issue_links(engine)  # ne doit pas lever d'exception


def count_links():
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as db:
        return db.execute(sa.select(sa.func.count()).select_from(models.time_entry_issues)).scalar()


def test_given_an_entry_on_several_us_when_i_delete_it_then_its_links_are_removed(client):
    project = setup_project(client)
    issues = sync_issues(client, project["id"], ISSUES)
    entry = post_entry(client, project["id"], github_issue_ids=[issues[1]["id"], issues[2]["id"]]).json()
    kept = post_entry(client, project["id"], github_issue_ids=[issues[3]["id"]]).json()
    assert count_links() == 3

    client.delete(f"/api/projects/{project['id']}/time-entries/{entry['id']}")

    assert count_links() == 1
    remaining = client.get(f"/api/projects/{project['id']}/time-entries").json()
    assert [(e["id"], e["github_issue_ids"]) for e in remaining] == [(kept["id"], [issues[3]["id"]])]


def test_given_an_entry_on_several_us_when_the_project_is_deleted_then_its_links_are_removed(client):
    project = setup_project(client)
    issues = sync_issues(client, project["id"], ISSUES)
    post_entry(client, project["id"], github_issue_ids=[issues[1]["id"], issues[2]["id"]])

    response = client.delete(f"/api/projects/{project['id']}")

    assert response.status_code == 204
    assert count_links() == 0


def test_given_an_old_client_sending_a_single_us_when_i_create_an_entry_then_the_us_is_kept(client):
    """Onglet resté ouvert sur l'ancienne version pendant un déploiement : il
    envoie encore github_issue_id, qui ne doit pas être ignoré en silence."""
    project = setup_project(client)
    issues = sync_issues(client, project["id"], ISSUES)

    body = post_entry(client, project["id"], github_issue_id=issues[2]["id"]).json()
    assert body["github_issue_ids"] == [issues[2]["id"]]

    body = post_entry(client, project["id"], github_issue_id=None).json()
    assert body["github_issue_ids"] == []
