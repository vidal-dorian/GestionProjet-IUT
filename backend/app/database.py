from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.schema import CreateColumn

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
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
