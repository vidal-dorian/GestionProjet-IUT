from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/api/projects/{project_id}/members", tags=["members"])


@router.get("", response_model=list[schemas.MemberRead])
def list_members(project_id: int, db: Session = Depends(get_db)):
    if crud.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    return crud.list_members(db, project_id)


@router.post("", response_model=schemas.MemberRead, status_code=status.HTTP_201_CREATED)
def create_member(project_id: int, member: schemas.MemberCreate, db: Session = Depends(get_db)):
    if crud.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    name = member.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Le nom du membre est obligatoire.")

    if crud.get_member_by_name(db, project_id, name):
        raise HTTPException(status_code=409, detail="Un membre porte déjà ce nom sur ce projet.")

    return crud.create_member(db, project_id, schemas.MemberCreate(name=name, pin=member.pin))


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(project_id: int, member_id: int, db: Session = Depends(get_db)):
    if crud.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    db_member = crud.get_member(db, project_id, member_id)
    if db_member is None:
        raise HTTPException(status_code=404, detail="Membre introuvable.")

    crud.delete_member(db, db_member)
