from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, github_client, github_sync, models, schemas
from app.config import settings
from app.database import get_db
from app.deps import require_project_member, require_project_owner

router = APIRouter(prefix="/api/projects/{project_id}/github", tags=["github"])


@router.put("", response_model=schemas.ProjectRead)
async def link_repo(
    project_id: int,
    link: schemas.GithubRepoLink,
    account: models.Account = Depends(require_project_owner),
    db: Session = Depends(get_db),
):
    db_project = crud.get_project(db, project_id)

    repo = link.repo.strip()
    if not github_client.is_valid_repo_format(repo):
        raise HTTPException(status_code=422, detail="Le dépôt doit être au format owner/repo.")

    try:
        is_private = await github_client.verify_repo(repo)
    except github_client.GithubRepoNotFound as exc:
        raise HTTPException(status_code=404, detail="Ce dépôt est introuvable ou inaccessible.") from exc
    except github_client.GithubApiError as exc:
        raise HTTPException(
            status_code=502, detail="Impossible de vérifier ce dépôt auprès de GitHub pour le moment."
        ) from exc

    # Le dépôt est lu avec le token GitHub du serveur, pas celui de l'utilisateur :
    # sans cette garde, n'importe quel compte pourrait créer un projet, y lier un
    # dépôt privé accessible à ce token et en lire les issues.
    if is_private and not account.is_admin:
        raise HTTPException(
            status_code=403, detail="Seul un administrateur peut lier un dépôt GitHub privé."
        )

    return crud.link_github_repo(db, db_project, repo)


@router.post("/sync", response_model=schemas.GithubSyncResult)
async def sync_repo(
    project_id: int, account: models.Account = Depends(require_project_owner), db: Session = Depends(get_db)
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
        issues, warning = await github_sync.sync_project(db, db_project)
    except github_client.GithubRepoNotFound as exc:
        raise HTTPException(status_code=404, detail="Ce dépôt est introuvable ou inaccessible.") from exc
    except github_client.GithubApiError as exc:
        raise HTTPException(
            status_code=502, detail=f"Impossible de synchroniser ce dépôt auprès de GitHub ({exc})."
        ) from exc

    return schemas.GithubSyncResult(
        synced_at=db_project.github_last_synced_at, issue_count=len(issues), warning=warning
    )


@router.get("/issues", response_model=list[schemas.GithubIssueRead])
async def list_issues(
    project_id: int, account: models.Account = Depends(require_project_member), db: Session = Depends(get_db)
):
    db_project = crud.get_project(db, project_id)
    return crud.list_visible_github_issues(db, db_project)


@router.put("/issues/{issue_id}/closed-on", response_model=schemas.BurndownIssue)
def update_issue_closed_on(
    project_id: int,
    issue_id: int,
    update: schemas.IssueClosedOnUpdate,
    account: models.Account = Depends(require_project_member),
    db: Session = Depends(get_db),
):
    """Corrige la date de clôture d'une US pour le burndown (US fermée en retard
    sur GitHub). La valeur saisie survit aux synchronisations ; `null` revient à
    la date de GitHub."""
    db_issue = crud.get_github_issue(db, project_id, issue_id)
    if db_issue is None:
        raise HTTPException(status_code=404, detail="US introuvable.")
    if update.closed_on is not None and db_issue.closed_at is None:
        raise HTTPException(
            status_code=422, detail="Cette US n'est pas fermée sur GitHub : sa date de clôture ne peut pas être modifiée."
        )
    crud.set_issue_closed_on_override(db, db_issue, update.closed_on)
    return db_issue


@router.put("/label-filter", response_model=schemas.ProjectRead)
async def update_label_filter(
    project_id: int,
    filter_update: schemas.GithubLabelFilterUpdate,
    account: models.Account = Depends(require_project_owner),
    db: Session = Depends(get_db),
):
    db_project = crud.get_project(db, project_id)
    return crud.set_github_label_filter(db, db_project, filter_update.labels)
