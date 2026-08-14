from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.deps import require_project_member

router = APIRouter(prefix="/api/projects/{project_id}/categories", tags=["categories"])


@router.get("", response_model=list[schemas.CategoryRead])
def list_categories(
    project_id: int, account: models.Account = Depends(require_project_member), db: Session = Depends(get_db)
):
    return crud.list_categories(db, project_id)


@router.post("", response_model=schemas.CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    project_id: int,
    category: schemas.CategoryCreate,
    account: models.Account = Depends(require_project_member),
    db: Session = Depends(get_db),
):
    name = category.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Le nom de la catégorie est obligatoire.")

    existing = [c for c in crud.list_categories(db, project_id) if c.name.lower() == name.lower()]
    if existing:
        raise HTTPException(status_code=409, detail="Une catégorie porte déjà ce nom sur ce projet.")

    return crud.create_category(db, project_id, schemas.CategoryCreate(name=name))
