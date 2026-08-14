from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.deps import require_project_member

router = APIRouter(prefix="/api/projects/{project_id}/roles", tags=["team-roles"])


def _validate_unique_name(db: Session, project_id: int, name: str, *, exclude_role_id: int | None = None) -> str:
    name = name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Le nom du rôle est obligatoire.")

    existing = [
        role
        for role in crud.list_team_roles(db, project_id)
        if role.name.lower() == name.lower() and role.id != exclude_role_id
    ]
    if existing:
        raise HTTPException(status_code=409, detail="Un rôle porte déjà ce nom sur ce projet.")

    return name


@router.get("", response_model=list[schemas.TeamRoleRead])
def list_roles(
    project_id: int, account: models.Account = Depends(require_project_member), db: Session = Depends(get_db)
):
    return crud.list_team_roles(db, project_id)


@router.post("", response_model=schemas.TeamRoleRead, status_code=status.HTTP_201_CREATED)
def create_role(
    project_id: int,
    role: schemas.TeamRoleCreate,
    account: models.Account = Depends(require_project_member),
    db: Session = Depends(get_db),
):
    name = _validate_unique_name(db, project_id, role.name)
    return crud.create_team_role(db, project_id, name)


@router.put("/{role_id}", response_model=schemas.TeamRoleRead)
def rename_role(
    project_id: int,
    role_id: int,
    role: schemas.TeamRoleCreate,
    account: models.Account = Depends(require_project_member),
    db: Session = Depends(get_db),
):
    db_role = crud.get_team_role(db, project_id, role_id)
    if db_role is None:
        raise HTTPException(status_code=404, detail="Rôle introuvable.")

    name = _validate_unique_name(db, project_id, role.name, exclude_role_id=role_id)
    return crud.rename_team_role(db, db_role, name)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    project_id: int,
    role_id: int,
    account: models.Account = Depends(require_project_member),
    db: Session = Depends(get_db),
):
    db_role = crud.get_team_role(db, project_id, role_id)
    if db_role is None:
        raise HTTPException(status_code=404, detail="Rôle introuvable.")
    crud.delete_team_role(db, db_role)
