import asyncio
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app import crud, github_sync
from app.config import settings
from app.database import Base, SessionLocal, engine, sync_missing_columns
from app.routers import (
    admin,
    auth,
    categories,
    dashboard,
    document_settings,
    exports,
    github,
    projects,
    reports,
    sprints,
    team_roles,
    time_entries,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Créer le schéma au démarrage plutôt qu'à l'import du module : un
    # simple `import app.main` (tests, outils) ne doit pas forcer une
    # connexion à la base réelle. Les tests désactivent ce comportement
    # (auto_create_schema=False) et gèrent leur propre schéma en mémoire.
    if settings.auto_create_schema:
        Base.metadata.create_all(bind=engine)
        sync_missing_columns(engine)
        with SessionLocal() as db:
            crud.backfill_legacy_memberships(db)
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

_cors_origins = [origin.strip().rstrip("/") for origin in settings.cors_origins.split(",") if origin.strip()]
# Avec allow_credentials, Starlette renvoie l'origine appelante quand "*" est
# autorisé : n'importe quel site pourrait alors appeler l'API avec la session
# de l'utilisateur. On refuse de démarrer plutôt que d'ouvrir cette porte.
if "*" in _cors_origins:
    raise RuntimeError("CORS_ORIGINS ne doit pas contenir « * » : liste les origines autorisées explicitement.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Nom des fichiers exportés : lisible par le frontend en dev (cross-origin).
    expose_headers=["Content-Disposition"],
)

@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Contrainte d'unicité violée par deux requêtes simultanées (même nom de
    catégorie, de rôle, de projet, même demande d'adhésion...) : les
    vérifications applicatives passent pour les deux, la base n'en accepte
    qu'une. Conflit explicite (409) plutôt qu'une erreur serveur ; la session
    est annulée à sa fermeture."""
    return JSONResponse(
        status_code=409,
        content={"detail": "Conflit : cette donnée vient d'être créée ou modifiée par une autre requête. Réessaie."},
    )


_STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def reject_cross_site_writes(request: Request, call_next):
    """Protection CSRF. L'identité vient du cookie Cloudflare Access, que le
    navigateur joint aussi aux requêtes déclenchées depuis un autre site : un
    simple formulaire piégé (POST sans corps, donc sans contrôle CORS
    préalable) pourrait alors agir au nom de la victime, par exemple valider
    une demande d'adhésion avec le compte d'un administrateur. Toute écriture
    venant d'une origine non autorisée est donc refusée."""
    if request.method in _STATE_CHANGING_METHODS:
        origin = request.headers.get("origin")
        cross_site = request.headers.get("sec-fetch-site") == "cross-site"
        if cross_site or (origin is not None and not _is_allowed_origin(origin, request)):
            return JSONResponse(status_code=403, content={"detail": "Requête d'une origine non autorisée."})
    return await call_next(request)


def _is_allowed_origin(origin: str, request: Request) -> bool:
    # Même hôte que celui appelé (déploiement same-origin derrière nginx) : un
    # navigateur ne laisse pas un site tiers choisir l'en-tête Host, cette
    # comparaison ne peut donc pas être contournée. Sinon, origine listée dans
    # CORS_ORIGINS (frontend servi sur un autre domaine, dev local).
    if origin.rstrip("/") in _cors_origins:
        return True
    host = request.headers.get("host")
    return host is not None and urlsplit(origin).netloc.lower() == host.lower()


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
app.include_router(reports.router)
app.include_router(document_settings.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
