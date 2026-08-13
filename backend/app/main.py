import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import github_sync
from app.config import settings
from app.database import Base, engine
from app.routers import auth, categories, dashboard, github, members, projects, sprints, time_entries

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
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
app.include_router(members.router)
app.include_router(auth.router)
app.include_router(time_entries.router)
app.include_router(dashboard.router)
app.include_router(github.router)
app.include_router(sprints.router)
app.include_router(categories.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
