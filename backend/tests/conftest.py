import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def _disable_github_sync_rate_limit(monkeypatch):
    monkeypatch.setattr(settings, "github_sync_interval_minutes", 0)


@pytest.fixture(autouse=True)
def _enable_dev_bypass_auth(monkeypatch):
    monkeypatch.setattr(settings, "dev_bypass_auth_enabled", True)


@pytest.fixture(autouse=True)
def _disable_auto_create_schema(monkeypatch):
    # Le schéma de test est géré par le fixture `client` ci-dessous, sur son
    # propre moteur sqlite en mémoire — la création automatique du schéma au
    # démarrage de l'app (contre la vraie base configurée) doit rester
    # désactivée pendant les tests.
    monkeypatch.setattr(settings, "auto_create_schema", False)


@pytest.fixture(autouse=True)
def _disable_background_sync(monkeypatch):
    # Même raison que ci-dessus : la boucle périodique de synchronisation
    # GitHub utilise le moteur de production, pas la session de test.
    monkeypatch.setattr(settings, "enable_background_sync", False)


@pytest.fixture()
def client():
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
