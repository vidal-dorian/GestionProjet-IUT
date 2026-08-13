from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/api/projects/{project_id}/categories", tags=["categories"])


def _get_project_or_404(project_id: int, db: Session):
    db_project = crud.get_project(db, project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    return db_project


@router.get("", response_model=list[schemas.CategoryRead])
def list_categories(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(project_id, db)
    return crud.list_categories(db, project_id)


@router.post("", response_model=schemas.CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(project_id: int, category: schemas.CategoryCreate, db: Session = Depends(get_db)):
    _get_project_or_404(project_id, db)

    name = category.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Le nom de la catégorie est obligatoire.")

    existing = [c for c in crud.list_categories(db, project_id) if c.name.lower() == name.lower()]
    if existing:
        raise HTTPException(status_code=409, detail="Une catégorie porte déjà ce nom sur ce projet.")

    return crud.create_category(db, project_id, schemas.CategoryCreate(name=name))
