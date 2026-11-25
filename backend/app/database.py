from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.schema import CreateColumn

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)


def enable_sqlite_foreign_keys(target_engine: Engine) -> None:
    """SQLite (dev local, tests) n'applique les clés étrangères (ON DELETE
    CASCADE / SET NULL) que si on le lui demande à chaque connexion ; MySQL
    les applique toujours. Sans ça, le comportement local divergerait de la
    production (ex. attributions orphelines après suppression d'un rôle)."""
    if target_engine.dialect.name != "sqlite":
        return

    @event.listens_for(target_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


enable_sqlite_foreign_keys(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def sync_missing_columns(target_engine: Engine = engine) -> None:
    """Ajoute les colonnes manquantes sur les tables déjà existantes.

    `Base.metadata.create_all()` ne crée que les tables absentes : quand un
    modèle gagne une colonne, une table déjà présente en base (dev réutilisant
    un fichier sqlite existant, ou prod) ne la reçoit jamais et toute requête
    qui la touche échoue avec "no such column"/"Unknown column". On complète
    donc ici par des `ALTER TABLE ... ADD COLUMN` ciblés sur les colonnes
    manquantes, en se limitant volontairement aux colonnes nullables : ajouter
    une colonne NOT NULL sans valeur par défaut sur une table déjà peuplée
    n'a pas de réponse automatique sûre.
    """
    inspector = inspect(target_engine)
    existing_tables = set(inspector.get_table_names())

    with target_engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue

            existing_columns = {col["name"] for col in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue
                if not column.nullable and column.server_default is None:
                    raise RuntimeError(
                        f"Colonne {table.name}.{column.name} manquante et non nullable sans "
                        "valeur par défaut : ajout automatique impossible, une migration "
                        "manuelle est nécessaire."
                    )
                column_ddl = str(CreateColumn(column).compile(dialect=target_engine.dialect))
                conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {column_ddl}"))


def migrate_time_entry_issue_links(target_engine: Engine = engine) -> None:
    """Reporte l'US unique des anciennes entrées de temps dans time_entry_issues.

    Avant qu'une entrée puisse porter sur plusieurs US, l'issue était stockée
    dans la colonne time_entries.github_issue_id. Cette colonne n'est plus
    lue : son contenu est copié dans la table de liens puis vidé, dans la même
    transaction, pour que la copie n'ait lieu qu'une fois (un redémarrage ne
    doit pas recréer un lien retiré depuis l'application). La colonne elle-même
    est laissée en place : la supprimer demanderait de retrouver le nom de sa
    clé étrangère, propre à chaque base.
    """
    inspector = inspect(target_engine)
    if "time_entries" not in inspector.get_table_names():
        return
    if "github_issue_id" not in {col["name"] for col in inspector.get_columns("time_entries")}:
        return

    with target_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO time_entry_issues (time_entry_id, github_issue_id) "
                "SELECT te.id, te.github_issue_id FROM time_entries te "
                "JOIN github_issues gi ON gi.id = te.github_issue_id "
                "WHERE NOT EXISTS (SELECT 1 FROM time_entry_issues tei "
                "WHERE tei.time_entry_id = te.id AND tei.github_issue_id = te.github_issue_id)"
            )
        )
        conn.execute(text("UPDATE time_entries SET github_issue_id = NULL WHERE github_issue_id IS NOT NULL"))
