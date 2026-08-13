import asyncio
import logging

from sqlalchemy.orm import Session

from app import crud, github_client, models
from app.config import settings
from app.database import SessionLocal

logger = logging.getLogger(__name__)


async def sync_project(db: Session, db_project: models.Project) -> list[dict]:
    """Fetches issues from GitHub for the project's linked repo and persists them locally."""
    issues = await github_client.list_issues(db_project.github_repo)
    crud.replace_github_issues(db, db_project, issues)
    return issues


async def sync_all_projects() -> None:
    db = SessionLocal()
    try:
        for db_project in crud.list_projects_with_github_repo(db):
            try:
                await sync_project(db, db_project)
            except (github_client.GithubRepoNotFound, github_client.GithubApiError) as exc:
                logger.warning("Synchronisation GitHub échouée pour le projet %s: %s", db_project.id, exc)
    finally:
        db.close()


async def periodic_sync_loop() -> None:
    interval_seconds = settings.github_sync_interval_minutes * 60
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            await sync_all_projects()
        except Exception:
            logger.exception("Erreur inattendue lors de la synchronisation GitHub périodique.")
