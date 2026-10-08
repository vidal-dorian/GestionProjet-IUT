from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.deps import get_current_account

router = APIRouter(prefix="/api", tags=["auth"])


@router.get("/me", response_model=schemas.AccountRead)
def me(account: models.Account = Depends(get_current_account)):
    return account


@router.put("/me", response_model=schemas.AccountRead)
def update_me(
    payload: schemas.DisplayNameUpdate,
    account: models.Account = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Chacun renseigne son propre nom (ex. "VIDAL Dorian"), utilisé dans les
    comptes-rendus à la place de l'adresse e-mail. Une chaîne vide l'efface."""
    return crud.set_display_name(db, account, payload.display_name.strip() or None)


@router.get("/me/projects", response_model=list[schemas.ProjectSummary])
def my_projects(account: models.Account = Depends(get_current_account), db: Session = Depends(get_db)):
    return [
        schemas.ProjectSummary(
            id=p.id,
            name=p.name,
            description=p.description,
            contributor_count=crud.count_contributors(db, p.id),
            is_member=True,
        )
        for p in crud.list_projects_for_account(db, account.id)
    ]
