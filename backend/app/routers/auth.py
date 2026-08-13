from fastapi import APIRouter, Depends

from app import models, schemas
from app.deps import get_current_account

router = APIRouter(prefix="/api", tags=["auth"])


@router.get("/me", response_model=schemas.AccountRead)
def me(account: models.Account = Depends(get_current_account)):
    return account
