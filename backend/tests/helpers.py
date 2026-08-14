from app import models
from tests.conftest import TestingSessionLocal


def add_approved_member(project_id: int, email: str) -> None:
    """Rattache directement un compte à un projet en tant que membre approuvé,
    sans passer par le flux de demande/validation — pratique pour les tests
    d'autres fonctionnalités qui ont juste besoin d'un deuxième compte membre.
    """
    db = TestingSessionLocal()
    try:
        account = db.query(models.Account).filter(models.Account.email == email).first()
        if account is None:
            account = models.Account(email=email)
            db.add(account)
            db.commit()
            db.refresh(account)
        db.add(models.ProjectMembership(project_id=project_id, account_id=account.id, status="approved"))
        db.commit()
    finally:
        db.close()


def promote_to_admin(email: str) -> None:
    """Positionne is_admin=True pour un compte déjà provisionné (ex. après un
    premier appel authentifié à /api/me)."""
    db = TestingSessionLocal()
    try:
        account = db.query(models.Account).filter(models.Account.email == email).one()
        account.is_admin = True
        db.commit()
    finally:
        db.close()
