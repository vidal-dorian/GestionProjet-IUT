from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.deps import require_project_member

router = APIRouter(prefix="/api/projects/{project_id}/sprints", tags=["sprints"])


def _overlap_warning(db: Session, project_id: int, sprint: models.Sprint, exclude_id: int | None) -> str | None:
    overlap = crud.find_overlapping_sprint(db, project_id, sprint.start_date, sprint.end_date, exclude_id)
    if overlap is None:
        return None
    return f"Ce sprint chevauche « {overlap.name} »."


@router.get("", response_model=list[schemas.SprintRead])
def list_sprints(
    project_id: int, account: models.Account = Depends(require_project_member), db: Session = Depends(get_db)
):
    return crud.list_sprints(db, project_id)


@router.post("", response_model=schemas.SprintWriteResult, status_code=status.HTTP_201_CREATED)
def create_sprint(
    project_id: int,
    sprint: schemas.SprintCreate,
    account: models.Account = Depends(require_project_member),
    db: Session = Depends(get_db),
):
    db_sprint = crud.create_sprint(db, project_id, sprint)
    warning = _overlap_warning(db, project_id, db_sprint, exclude_id=db_sprint.id)
    return schemas.SprintWriteResult(sprint=db_sprint, overlap_warning=warning)
