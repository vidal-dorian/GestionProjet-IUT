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
            member_count=crud.count_members(db, p.id),
        )
        for p in crud.list_projects(db)
    ]


@router.post("", response_model=schemas.ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    name = project.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Le nom du projet est obligatoire.")

    if crud.get_project_by_name(db, name):
        raise HTTPException(status_code=409, detail="Un projet porte déjà ce nom.")

    return crud.create_project(db, schemas.ProjectCreate(name=name, description=project.description))


@router.get("/{project_id}", response_model=schemas.ProjectRead)
def read_project(project_id: int, db: Session = Depends(get_db)):
    db_project = crud.get_project(db, project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    return db_project
