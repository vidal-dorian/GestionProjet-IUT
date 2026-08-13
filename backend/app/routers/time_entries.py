from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.deps import get_current_member

router = APIRouter(prefix="/api/projects/{project_id}/time-entries", tags=["time-entries"])


def _get_owned_entry(
    db: Session, project_id: int, entry_id: int, member: models.Member
) -> models.TimeEntry:
    entry = crud.get_time_entry(db, project_id, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entrée introuvable.")
    if entry.member_id != member.id:
        raise HTTPException(status_code=403, detail="Vous ne pouvez modifier que vos propres entrées.")
    return entry


def _validate_github_issue(db: Session, project_id: int, entry: schemas.TimeEntryCreate) -> None:
    if entry.github_issue_id is not None and crud.get_github_issue(db, project_id, entry.github_issue_id) is None:
        raise HTTPException(status_code=422, detail="Cette issue GitHub n'existe pas pour ce projet.")


def _validate_sprint(db: Session, project_id: int, entry: schemas.TimeEntryCreate) -> None:
    if entry.sprint_id is not None and crud.get_sprint(db, project_id, entry.sprint_id) is None:
        raise HTTPException(status_code=422, detail="Ce sprint n'existe pas pour ce projet.")


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
    _validate_github_issue(db, project_id, entry)
    _validate_sprint(db, project_id, entry)
    return crud.create_time_entry(db, project_id, member.id, entry)


@router.put("/{entry_id}", response_model=schemas.TimeEntryRead)
def update_time_entry(
    project_id: int,
    entry_id: int,
    entry: schemas.TimeEntryCreate,
    member: models.Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    db_entry = _get_owned_entry(db, project_id, entry_id, member)
    _validate_github_issue(db, project_id, entry)
    _validate_sprint(db, project_id, entry)
    return crud.update_time_entry(db, db_entry, entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_time_entry(
    project_id: int,
    entry_id: int,
    member: models.Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    db_entry = _get_owned_entry(db, project_id, entry_id, member)
    crud.delete_time_entry(db, db_entry)
