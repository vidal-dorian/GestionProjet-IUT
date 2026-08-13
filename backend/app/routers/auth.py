from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.config import settings
from app.database import get_db
from app.security import verify_pin
from app.session import SESSION_COOKIE_NAME, SESSION_MAX_AGE_SECONDS, create_session_token, read_session_token

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/projects/{project_id}/members/{member_id}/login", response_model=schemas.SessionMember)
def login(project_id: int, member_id: int, credentials: schemas.MemberLogin, response: Response, db: Session = Depends(get_db)):
    member = crud.get_member(db, project_id, member_id)
    if member is None or not verify_pin(credentials.pin, member.pin_hash):
        raise HTTPException(status_code=401, detail="Nom ou PIN incorrect.")

    token = create_session_token(member.id, member.project_id)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    return member


@router.get("/auth/me", response_model=schemas.SessionMember)
def me(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    payload = read_session_token(token) if token else None
    if payload is None:
        raise HTTPException(status_code=401, detail="Non identifié.")

    member = crud.get_member(db, payload["project_id"], payload["member_id"])
    if member is None:
        raise HTTPException(status_code=401, detail="Non identifié.")
    return member


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE_NAME)
