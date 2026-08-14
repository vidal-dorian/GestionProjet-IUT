from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.deps import get_current_account, get_current_account_optional, require_project_member

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[schemas.ProjectSummary])
def list_projects(
    account: models.Account | None = Depends(get_current_account_optional),
    db: Session = Depends(get_db),
):
    statuses = crud.list_membership_statuses_for_account(db, account.id) if account else {}
    return [
        schemas.ProjectSummary(
            id=p.id,
            name=p.name,
            description=p.description,
            contributor_count=crud.count_contributors(db, p.id),
            is_member=statuses.get(p.id) == "approved",
            membership_status=statuses.get(p.id),
        )
        for p in crud.list_projects(db)
    ]


def _validate_name(db: Session, name: str, *, exclude_project_id: int | None = None) -> str:
    name = name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Le nom du projet est obligatoire.")

    existing = crud.get_project_by_name(db, name)
    if existing and existing.id != exclude_project_id:
        raise HTTPException(status_code=409, detail="Un projet porte déjà ce nom.")

    return name


@router.post("", response_model=schemas.ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    project: schemas.ProjectCreate,
    account: models.Account | None = Depends(get_current_account_optional),
    db: Session = Depends(get_db),
):
    name = _validate_name(db, project.name)
    db_project = crud.create_project(db, schemas.ProjectCreate(name=name, description=project.description))
    if account is not None:
        crud.add_project_member(db, db_project.id, account.id)
    return db_project


@router.post("/{project_id}/join", response_model=schemas.MembershipRead)
def join_project(
    project_id: int,
    account: models.Account = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    db_project = crud.get_project(db, project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    # Un administrateur a de toute façon l'autorité de valider les demandes :
    # inutile de lui faire attendre sa propre approbation.
    if account.is_admin:
        membership = crud.add_project_member(db, project_id, account.id)
    else:
        membership = crud.request_project_membership(db, project_id, account.id)
    return schemas.MembershipRead(project_id=project_id, status=membership.status)


@router.get("/{project_id}/contributors", response_model=list[schemas.AccountHours])
def list_contributors(project_id: int, db: Session = Depends(get_db)):
    if crud.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    return [
        schemas.AccountHours(account_id=account.id, account_email=account.email, hours=round(hours, 2))
        for account, hours in crud.list_project_contributors(db, project_id)
    ]


@router.get("/{project_id}", response_model=schemas.ProjectRead)
def read_project(project_id: int, db: Session = Depends(get_db)):
    db_project = crud.get_project(db, project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    return db_project


@router.put("/{project_id}", response_model=schemas.ProjectRead)
def update_project(
    project_id: int,
    project: schemas.ProjectCreate,
    account: models.Account = Depends(require_project_member),
    db: Session = Depends(get_db),
):
    db_project = crud.get_project(db, project_id)

    name = _validate_name(db, project.name, exclude_project_id=project_id)
    return crud.update_project(db, db_project, schemas.ProjectCreate(name=name, description=project.description))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int, account: models.Account = Depends(require_project_member), db: Session = Depends(get_db)
):
    db_project = crud.get_project(db, project_id)
    crud.delete_project(db, db_project)
