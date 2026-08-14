from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.deps import require_project_member

router = APIRouter(prefix="/api/projects/{project_id}/sprints", tags=["sprints"])


def _to_assignment_read(assignment: models.SprintRoleAssignment) -> schemas.SprintRoleAssignmentRead:
    return schemas.SprintRoleAssignmentRead(
        role_id=assignment.role_id,
        role_name=assignment.role.name,
        account_id=assignment.account_id,
        account_email=assignment.account.email,
    )


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


@router.get("/{sprint_id}/role-assignments", response_model=list[schemas.SprintRoleAssignmentRead])
def list_role_assignments(
    project_id: int,
    sprint_id: int,
    account: models.Account = Depends(require_project_member),
    db: Session = Depends(get_db),
):
    if crud.get_sprint(db, project_id, sprint_id) is None:
        raise HTTPException(status_code=404, detail="Sprint introuvable.")
    return [_to_assignment_read(a) for a in crud.list_sprint_role_assignments(db, sprint_id)]


@router.put("/{sprint_id}/role-assignments", response_model=list[schemas.SprintRoleAssignmentRead])
def replace_role_assignments(
    project_id: int,
    sprint_id: int,
    update: schemas.SprintRoleAssignmentsUpdate,
    account: models.Account = Depends(require_project_member),
    db: Session = Depends(get_db),
):
    if crud.get_sprint(db, project_id, sprint_id) is None:
        raise HTTPException(status_code=404, detail="Sprint introuvable.")

    role_ids = {role.id for role in crud.list_team_roles(db, project_id)}
    member_ids = {member.id for member in crud.list_approved_members(db, project_id)}
    for item in update.assignments:
        if item.role_id not in role_ids:
            raise HTTPException(status_code=422, detail="Ce rôle n'existe pas pour ce projet.")
        if item.account_id not in member_ids:
            raise HTTPException(status_code=422, detail="Ce compte n'est pas membre approuvé de ce projet.")

    assignments = crud.replace_sprint_role_assignments(
        db, sprint_id, [(item.role_id, item.account_id) for item in update.assignments]
    )
    return [_to_assignment_read(a) for a in assignments]
