from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app import crud, models
from app.database import get_db
from app.session import SESSION_COOKIE_NAME, read_session_token


def resolve_session_member(request: Request, db: Session) -> models.Member | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    payload = read_session_token(token) if token else None
    if payload is None:
        return None
    return crud.get_member(db, payload["project_id"], payload["member_id"])


def get_current_member(project_id: int, request: Request, db: Session = Depends(get_db)) -> models.Member:
    member = resolve_session_member(request, db)
    if member is None or member.project_id != project_id:
        raise HTTPException(status_code=401, detail="Non identifié.")
    return member
