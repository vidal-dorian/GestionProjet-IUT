from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.deps import get_current_account

router = APIRouter(prefix="/api", tags=["auth"])


@router.get("/me", response_model=schemas.AccountRead)
def me(account: models.Account = Depends(get_current_account)):
    return account


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
