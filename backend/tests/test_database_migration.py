import sqlalchemy as sa
from sqlalchemy import inspect

from app import models  # noqa: F401 — nécessaire pour peupler Base.metadata avant create_all()
from app.database import Base, sync_missing_columns


def test_sync_missing_columns_adds_missing_nullable_columns():
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "CREATE TABLE github_issues ("
                "id INTEGER NOT NULL PRIMARY KEY, "
                "project_id INTEGER NOT NULL, "
                "number INTEGER NOT NULL, "
                "title VARCHAR(500) NOT NULL, "
                "state VARCHAR(20) NOT NULL, "
                "labels_raw VARCHAR(500) NOT NULL, "
                "url VARCHAR(500) NOT NULL, "
                "synced_at DATETIME NOT NULL"
                ")"
            )
        )

    sync_missing_columns(engine)

    columns = {col["name"] for col in inspect(engine).get_columns("github_issues")}
    assert "story_points" in columns
    assert "closed_at" in columns

    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO github_issues "
                "(id, project_id, number, title, state, labels_raw, url, synced_at, story_points, closed_at) "
                "VALUES (1, 1, 1, 'US', 'open', '', 'http://x', '2026-01-01T00:00:00', 5.0, NULL)"
            )
        )
        row = conn.execute(sa.text("SELECT story_points FROM github_issues WHERE id = 1")).fetchone()
        assert row[0] == 5.0


def test_sync_missing_columns_is_a_noop_when_no_tables_exist():
    engine = sa.create_engine("sqlite:///:memory:")
    sync_missing_columns(engine)  # ne doit pas lever d'exception


def test_sync_missing_columns_is_idempotent():
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "CREATE TABLE github_issues ("
                "id INTEGER NOT NULL PRIMARY KEY, "
                "project_id INTEGER NOT NULL, "
                "number INTEGER NOT NULL, "
                "title VARCHAR(500) NOT NULL, "
                "state VARCHAR(20) NOT NULL, "
                "labels_raw VARCHAR(500) NOT NULL, "
                "url VARCHAR(500) NOT NULL, "
                "synced_at DATETIME NOT NULL"
                ")"
            )
        )

    sync_missing_columns(engine)
    sync_missing_columns(engine)  # ne doit pas tenter de recréer les colonnes déjà ajoutées

    columns = {col["name"] for col in inspect(engine).get_columns("github_issues")}
    assert "story_points" in columns
    assert "closed_at" in columns


def test_sync_missing_columns_backfills_a_new_not_null_column_on_a_populated_table():
    """Régression pour l'incident PR #72 : `project_memberships.status` avait été
    ajoutée avec seulement `default=` (valeur par défaut côté ORM, invisible pour
    `sync_missing_columns`) et non `server_default=` (valeur par défaut SQL). Sur un
    déploiement où la table existait déjà, la colonne était donc détectée comme
    NOT NULL sans valeur de repli sûre, et `sync_missing_columns` refusait de
    démarrer — crash-loop en prod. Reproduit ici le schéma réel de l'application
    (via `Base.metadata`, pas une table reconstruite à la main) avec la colonne
    `status` absente et une ligne déjà présente, comme sur le déploiement touché.
    """
    engine = sa.create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(sa.text("DROP TABLE project_memberships"))
        conn.execute(
            sa.text(
                "CREATE TABLE project_memberships ("
                "id INTEGER NOT NULL PRIMARY KEY, "
                "project_id INTEGER NOT NULL, "
                "account_id INTEGER NOT NULL, "
                "created_at DATETIME NOT NULL"
                ")"
            )
        )
        conn.execute(sa.text("INSERT INTO project_memberships (id, project_id, account_id, created_at) VALUES (1, 1, 1, '2026-01-01T00:00:00')"))

    sync_missing_columns(engine)  # ne doit pas lever de RuntimeError

    with engine.begin() as conn:
        row = conn.execute(sa.text("SELECT status FROM project_memberships WHERE id = 1")).fetchone()
        assert row[0] == "approved"
