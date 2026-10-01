import asyncio
import logging

from sqlalchemy.orm import Session

from app import crud, github_client, models
from app.config import settings
from app.database import SessionLocal

logger = logging.getLogger(__name__)


STORY_POINTS_UNAVAILABLE_WARNING = (
    "Les issues ont été synchronisées, mais la valorisation (champ « %s » du GitHub Project) "
    "n'a pas pu être lue : le token GitHub n'a pas accès au Project lié au dépôt (GitHub : %s). "
    "Utilisez un token classique avec le scope read:project, appartenant à un compte membre du Project."
)


async def sync_project(db: Session, db_project: models.Project) -> tuple[list[dict], str | None]:
    """Fetches issues from GitHub for the project's linked repo and persists them locally.

    Returns the issues and, when the story points could not be read, a warning
    explaining why (the issues are then synced without them rather than not at all).
    """
    warning = None
    try:
        issues = await github_client.list_issues(db_project.github_repo)
    except github_client.GithubProjectsUnavailable as exc:
        logger.warning("Valorisation illisible pour le projet %s: %s", db_project.id, exc)
        warning = STORY_POINTS_UNAVAILABLE_WARNING % (github_client.STORY_POINTS_FIELD_NAME, exc)
        issues = await github_client.list_issues(db_project.github_repo, with_story_points=False)
    crud.replace_github_issues(db, db_project, issues)
    return issues, warning


async def sync_all_projects() -> None:
    db = SessionLocal()
    try:
        for db_project in crud.list_projects_with_github_repo(db):
            try:
                await sync_project(db, db_project)
            except (github_client.GithubRepoNotFound, github_client.GithubApiError) as exc:
                logger.warning("Synchronisation GitHub échouée pour le projet %s: %s", db_project.id, exc)
            except Exception:
                # Une erreur base de données sur un projet laisserait la session
                # dans un état invalide et ferait échouer tous les suivants.
                db.rollback()
                logger.exception("Erreur inattendue lors de la synchronisation du projet %s.", db_project.id)
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
