from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.deps import get_current_admin, require_project_owner

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _to_membership_request_read(membership: models.ProjectMembership) -> schemas.MembershipRequestRead:
    return schemas.MembershipRequestRead(
        id=membership.id,
        project_id=membership.project_id,
        project_name=membership.project.name,
        account_id=membership.account_id,
        account_email=membership.account.email,
        status=membership.status,
        created_at=membership.created_at,
    )


def _get_pending_request(db: Session, request_id: int) -> models.ProjectMembership:
    """Seules les demandes en attente se décident ici : retirer un membre déjà
    approuvé passe par la gestion des membres du projet, pas par un "refus"
    d'une demande déjà traitée (qui contournerait les règles de retrait)."""
    membership = crud.get_membership_request(db, request_id)
    if membership is None:
        raise HTTPException(status_code=404, detail="Demande introuvable.")
    if membership.status != "pending":
        raise HTTPException(status_code=409, detail="Cette demande a déjà été traitée.")
    return membership


@router.get("/membership-requests", response_model=list[schemas.MembershipRequestRead])
def list_membership_requests(
    admin: models.Account = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return [_to_membership_request_read(m) for m in crud.list_pending_membership_requests(db)]


@router.post("/membership-requests/{request_id}/approve", response_model=schemas.MembershipRequestRead)
def approve_membership_request(
    request_id: int,
    admin: models.Account = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    membership = _get_pending_request(db, request_id)
    membership = crud.decide_membership_request(db, membership, approve=True)
    return _to_membership_request_read(membership)


@router.post("/membership-requests/{request_id}/reject", response_model=schemas.MembershipRequestRead)
def reject_membership_request(
    request_id: int,
    admin: models.Account = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    membership = _get_pending_request(db, request_id)
    membership = crud.decide_membership_request(db, membership, approve=False)
    return _to_membership_request_read(membership)


@router.get("/projects/{project_id}/members", response_model=list[schemas.AccountRead])
def list_project_members(
    project_id: int,
    account: models.Account = Depends(require_project_owner),
    db: Session = Depends(get_db),
):
    return crud.list_approved_members(db, project_id)


@router.delete("/projects/{project_id}/members/{account_id}", status_code=204)
def remove_project_member(
    project_id: int,
    account_id: int,
    account: models.Account = Depends(require_project_owner),
    db: Session = Depends(get_db),
):
    membership = crud.get_approved_membership(db, project_id, account_id)
    if membership is None:
        raise HTTPException(status_code=404, detail="Ce compte n'est pas membre approuvé de ce projet.")
    crud.remove_project_member(db, membership)
