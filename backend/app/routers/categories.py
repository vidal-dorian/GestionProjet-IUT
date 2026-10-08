from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.deps import require_project_member

router = APIRouter(prefix="/api/projects/{project_id}/categories", tags=["categories"])


def _validate_unique_name(db: Session, project_id: int, name: str, *, exclude_category_id: int | None = None) -> str:
    name = name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Le nom de la catégorie est obligatoire.")

    existing = [
        c
        for c in crud.list_categories(db, project_id)
        if c.name.lower() == name.lower() and c.id != exclude_category_id
    ]
    if existing:
        raise HTTPException(status_code=409, detail="Une catégorie porte déjà ce nom sur ce projet.")

    return name


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
    name = _validate_unique_name(db, project_id, category.name)
    return crud.create_category(db, project_id, schemas.CategoryCreate(name=name))


@router.put("/{category_id}", response_model=schemas.CategoryRead)
def rename_category(
    project_id: int,
    category_id: int,
    category: schemas.CategoryCreate,
    account: models.Account = Depends(require_project_member),
    db: Session = Depends(get_db),
):
    db_category = crud.get_category(db, project_id, category_id)
    if db_category is None:
        raise HTTPException(status_code=404, detail="Catégorie introuvable.")

    name = _validate_unique_name(db, project_id, category.name, exclude_category_id=category_id)
    return crud.rename_category(db, db_category, name)
