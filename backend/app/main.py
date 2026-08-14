import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import github_sync
from app.config import settings
from app.database import Base, engine
from app.routers import admin, auth, categories, dashboard, exports, github, projects, sprints, team_roles, time_entries


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Créer le schéma au démarrage plutôt qu'à l'import du module : un
    # simple `import app.main` (tests, outils) ne doit pas forcer une
    # connexion à la base réelle. Les tests désactivent ce comportement
    # (auto_create_schema=False) et gèrent leur propre schéma en mémoire.
    if settings.auto_create_schema:
        Base.metadata.create_all(bind=engine)
    # La boucle périodique utilise le moteur de production (SessionLocal), pas
    # la session de test injectée par dépendance : elle doit rester désactivée
    # pendant les tests, sous peine de tenter une vraie connexion MySQL.
    task = asyncio.create_task(github_sync.periodic_sync_loop()) if settings.enable_background_sync else None
    try:
        yield
    finally:
        if task is not None:
            task.cancel()


app = FastAPI(title="GestionProjet-IUT API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(auth.router)
app.include_router(time_entries.router)
app.include_router(dashboard.router)
app.include_router(github.router)
app.include_router(sprints.router)
app.include_router(categories.router)
app.include_router(exports.router)
app.include_router(admin.router)
app.include_router(team_roles.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
