import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import crud, excel_export, models
from app.database import get_db
from app.deps import get_current_account

router = APIRouter(prefix="/api/projects/{project_id}", tags=["exports"])

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9_-]+")


def _filename_safe(value: str) -> str:
    return _UNSAFE_FILENAME_CHARS.sub("_", value).strip("_") or "export"


def _xlsx_response(buffer, filename: str) -> StreamingResponse:
    return StreamingResponse(
        buffer,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/time-entries/export")
def export_my_time_entries(
    project_id: int, account: models.Account = Depends(get_current_account), db: Session = Depends(get_db)
):
    db_project = crud.get_project(db, project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    entries = crud.list_time_entries_for_account(db, project_id, account.id)
    buffer = excel_export.build_account_export(db_project, account, entries)

    export_date = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"{_filename_safe(db_project.name)}_{_filename_safe(account.email)}_{export_date}.xlsx"
    return _xlsx_response(buffer, filename)


@router.get("/export")
def export_project(project_id: int, db: Session = Depends(get_db)):
    db_project = crud.get_project(db, project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    entries = crud.list_time_entries_for_project(db, project_id)
    contributors = [account for account, _ in crud.list_project_contributors(db, project_id)]
    buffer = excel_export.build_project_export(db_project, entries, contributors)

    export_date = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"{_filename_safe(db_project.name)}_export_{export_date}.xlsx"
    return _xlsx_response(buffer, filename)
