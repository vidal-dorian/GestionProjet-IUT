import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import github_sync
from app.config import settings
from app.database import Base, engine
from app.routers import auth, categories, dashboard, exports, github, projects, sprints, time_entries


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Créer le schéma au démarrage plutôt qu'à l'import du module : un
    # simple `import app.main` (tests, outils) ne doit pas forcer une
    # connexion à la base réelle. Les tests désactivent ce comportement
    # (auto_create_schema=False) et gèrent leur propre schéma en mémoire.
    if settings.auto_create_schema:
        Base.metadata.create_all(bind=engine)
    task = asyncio.create_task(github_sync.periodic_sync_loop())
    try:
        yield
    finally:
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


@app.get("/api/health")
def health():
    return {"status": "ok"}
