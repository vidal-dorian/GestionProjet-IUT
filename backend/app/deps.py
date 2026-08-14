import logging

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app import cloudflare_auth, crud, models
from app.config import settings
from app.database import get_db

logger = logging.getLogger(__name__)

DEV_BYPASS_EMAIL_HEADER = "X-Dev-Email"


def resolve_authenticated_email(request: Request) -> str | None:
    """Resolves the caller's verified email, or None if unauthenticated.

    In production, identity comes exclusively from a Cloudflare Access JWT
    (Cf-Access-Jwt-Assertion), validated against Cloudflare's JWKS and the
    configured Access application audience. The X-Dev-Email bypass only
    activates when DEV_BYPASS_AUTH_ENABLED=true, which must never be set in
    production — Cloudflare Access is the only real gate protecting the app.
    """
    if settings.cloudflare_team_domain and settings.cloudflare_access_aud:
        token = request.headers.get(cloudflare_auth.CF_ACCESS_JWT_HEADER)
        if not token:
            return None
        try:
            return cloudflare_auth.verify_access_jwt(token)
        except cloudflare_auth.CloudflareAuthError:
            return None

    if settings.dev_bypass_auth_enabled:
        logger.warning("DEV_BYPASS_AUTH_ENABLED is on — accepting unverified %s header.", DEV_BYPASS_EMAIL_HEADER)
        return request.headers.get(DEV_BYPASS_EMAIL_HEADER)

    return None


def get_current_account(request: Request, db: Session = Depends(get_db)) -> models.Account:
    email = resolve_authenticated_email(request)
    if not email:
        raise HTTPException(status_code=401, detail="Authentification requise.")
    return crud.get_or_create_account(db, email)


def get_current_account_optional(request: Request, db: Session = Depends(get_db)) -> models.Account | None:
    email = resolve_authenticated_email(request)
    if not email:
        return None
    return crud.get_or_create_account(db, email)


def get_current_admin(account: models.Account = Depends(get_current_account)) -> models.Account:
    if not account.is_admin:
        raise HTTPException(status_code=403, detail="Réservé aux administrateurs.")
    return account


def get_project_or_404(project_id: int, db: Session = Depends(get_db)) -> models.Project:
    db_project = crud.get_project(db, project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    return db_project


def require_project_member(
    project_id: int,
    account: models.Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> models.Account:
    """Un compte doit être membre approuvé du projet (ou administrateur) pour accéder à
    son contenu (saisies, dashboard, sprints, catégories, configuration GitHub, exports).
    """
    get_project_or_404(project_id, db)
    if not account.is_admin and not crud.is_approved_member(db, project_id, account.id):
        raise HTTPException(status_code=403, detail="Vous devez être membre de ce projet pour effectuer cette action.")
    return account


def require_project_owner(
    project_id: int,
    account: models.Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> models.Account:
    """Seuls le créateur du projet et les administrateurs peuvent effectuer les actions
    sensibles : suppression du projet, configuration GitHub, gestion des membres. Les
    autres membres conservent la saisie et la consultation (require_project_member).
    """
    db_project = get_project_or_404(project_id, db)
    if not account.is_admin and db_project.created_by_account_id != account.id:
        raise HTTPException(
            status_code=403, detail="Réservé au créateur du projet ou à un administrateur."
        )
    return account
