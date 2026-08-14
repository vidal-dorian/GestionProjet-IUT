from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, github_client, github_sync, models, schemas
from app.config import settings
from app.database import get_db
from app.deps import require_project_member

router = APIRouter(prefix="/api/projects/{project_id}/github", tags=["github"])


@router.put("", response_model=schemas.ProjectRead)
async def link_repo(
    project_id: int,
    link: schemas.GithubRepoLink,
    account: models.Account = Depends(require_project_member),
    db: Session = Depends(get_db),
):
    db_project = crud.get_project(db, project_id)

    repo = link.repo.strip()
    if not github_client.is_valid_repo_format(repo):
        raise HTTPException(status_code=422, detail="Le dépôt doit être au format owner/repo.")

    try:
        await github_client.verify_repo(repo)
    except github_client.GithubRepoNotFound as exc:
        raise HTTPException(status_code=404, detail="Ce dépôt est introuvable ou inaccessible.") from exc
    except github_client.GithubApiError as exc:
        raise HTTPException(
            status_code=502, detail="Impossible de vérifier ce dépôt auprès de GitHub pour le moment."
        ) from exc

    return crud.link_github_repo(db, db_project, repo)


@router.post("/sync", response_model=schemas.GithubSyncResult)
async def sync_repo(
    project_id: int, account: models.Account = Depends(require_project_member), db: Session = Depends(get_db)
):
    db_project = crud.get_project(db, project_id)
    if not db_project.github_repo:
        raise HTTPException(status_code=400, detail="Aucun dépôt GitHub n'est lié à ce projet.")

    min_interval = timedelta(minutes=settings.github_sync_interval_minutes)
    if db_project.github_last_synced_at is not None:
        elapsed = datetime.utcnow() - db_project.github_last_synced_at
        if elapsed < min_interval:
            retry_in_minutes = int((min_interval - elapsed).total_seconds() // 60) + 1
            raise HTTPException(
                status_code=429,
                detail=(
                    "Une synchronisation a déjà été effectuée récemment. "
                    f"Réessayez dans {retry_in_minutes} minute(s)."
                ),
            )

    try:
        issues = await github_sync.sync_project(db, db_project)
    except github_client.GithubRepoNotFound as exc:
        raise HTTPException(status_code=404, detail="Ce dépôt est introuvable ou inaccessible.") from exc
    except github_client.GithubApiError as exc:
        raise HTTPException(
            status_code=502, detail="Impossible de synchroniser ce dépôt auprès de GitHub pour le moment."
        ) from exc

    return schemas.GithubSyncResult(synced_at=db_project.github_last_synced_at, issue_count=len(issues))


@router.get("/issues", response_model=list[schemas.GithubIssueRead])
async def list_issues(
    project_id: int, account: models.Account = Depends(require_project_member), db: Session = Depends(get_db)
):
    db_project = crud.get_project(db, project_id)
    return crud.list_visible_github_issues(db, db_project)


@router.put("/label-filter", response_model=schemas.ProjectRead)
async def update_label_filter(
    project_id: int,
    filter_update: schemas.GithubLabelFilterUpdate,
    account: models.Account = Depends(require_project_member),
    db: Session = Depends(get_db),
):
    db_project = crud.get_project(db, project_id)
    return crud.set_github_label_filter(db, db_project, filter_update.labels)
