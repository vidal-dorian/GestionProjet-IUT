from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.deps import get_current_member

router = APIRouter(prefix="/api/projects/{project_id}/time-entries", tags=["time-entries"])


@router.get("", response_model=list[schemas.TimeEntryRead])
def list_my_time_entries(
    project_id: int, member: models.Member = Depends(get_current_member), db: Session = Depends(get_db)
):
    return crud.list_time_entries_for_member(db, project_id, member.id)


@router.post("", response_model=schemas.TimeEntryRead, status_code=status.HTTP_201_CREATED)
def create_time_entry(
    project_id: int,
    entry: schemas.TimeEntryCreate,
    member: models.Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    return crud.create_time_entry(db, project_id, member.id, entry)
