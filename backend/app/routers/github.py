from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, github_client, schemas
from app.database import get_db

router = APIRouter(prefix="/api/projects/{project_id}/github", tags=["github"])


@router.put("", response_model=schemas.ProjectRead)
async def link_repo(project_id: int, link: schemas.GithubRepoLink, db: Session = Depends(get_db)):
    db_project = crud.get_project(db, project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

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
