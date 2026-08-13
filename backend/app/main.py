from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import auth, dashboard, github, members, projects, time_entries

Base.metadata.create_all(bind=engine)

app = FastAPI(title="GestionProjet-IUT API")

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


@app.get("/api/health")
def health():
    return {"status": "ok"}
