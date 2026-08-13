from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[schemas.ProjectSummary])
def list_projects(db: Session = Depends(get_db)):
    return [
        schemas.ProjectSummary(
            id=p.id,
            name=p.name,
            description=p.description,
            contributor_count=crud.count_contributors(db, p.id),
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
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    name = _validate_name(db, project.name)
    return crud.create_project(db, schemas.ProjectCreate(name=name, description=project.description))


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
def update_project(project_id: int, project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    db_project = crud.get_project(db, project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    name = _validate_name(db, project.name, exclude_project_id=project_id)
    return crud.update_project(db, db_project, schemas.ProjectCreate(name=name, description=project.description))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    db_project = crud.get_project(db, project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    crud.delete_project(db, db_project)
