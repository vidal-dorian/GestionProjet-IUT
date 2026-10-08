import base64
import binascii
from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Response, status
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.deps import require_project_member, require_project_owner

router = APIRouter(prefix="/api/projects/{project_id}/document-settings", tags=["document-settings"])

LOGO_POSITIONS = ("left", "right")
MAX_LOGO_BYTES = 1024 * 1024
# Un PNG de quelques Ko peut décrire une image de plusieurs gigapixels (bombe
# de décompression) : on borne les dimensions avant tout décodage. 2000 px
# laisse de la marge pour un logo tout en gardant le décodage léger sur le Pi.
MAX_LOGO_SIDE = 2000
# Taille de stockage : un logo occupe ~2 cm de haut dans le document.
STORED_LOGO_SIDE = 800
# Formats qu'acceptent à la fois python-docx et les navigateurs (aperçu).
LOGO_FORMATS = {"PNG": "image/png", "JPEG": "image/jpeg", "GIF": "image/gif"}


def _check_position(position: str) -> None:
    if position not in LOGO_POSITIONS:
        raise HTTPException(status_code=404, detail="Emplacement de logo inconnu.")


def _read_settings(db: Session, db_project: models.Project) -> schemas.DocumentSettingsRead:
    return schemas.DocumentSettingsRead(
        footer=db_project.document_footer or "",
        logos=crud.list_document_logo_positions(db, db_project.id),
    )


@router.get("", response_model=schemas.DocumentSettingsRead)
def read_document_settings(
    project_id: int, account: models.Account = Depends(require_project_member), db: Session = Depends(get_db)
):
    return _read_settings(db, crud.get_project(db, project_id))


@router.put("", response_model=schemas.DocumentSettingsRead)
def update_document_settings(
    project_id: int,
    payload: schemas.DocumentSettings,
    account: models.Account = Depends(require_project_owner),
    db: Session = Depends(get_db),
):
    db_project = crud.get_project(db, project_id)
    db_project.document_footer = payload.footer.strip() or None
    db.commit()
    return _read_settings(db, db_project)


@router.get("/logos/{position}")
def read_logo(
    project_id: int,
    position: str,
    account: models.Account = Depends(require_project_member),
    db: Session = Depends(get_db),
):
    _check_position(position)
    logo = crud.get_document_logo(db, project_id, position)
    if logo is None:
        raise HTTPException(status_code=404, detail="Aucun logo à cet emplacement.")
    return Response(content=logo.data, media_type=logo.content_type)


def _normalize_logo(data: bytes) -> bytes:
    """Décode l'image et la réencode en PNG réduit.

    Seuls les décodeurs PNG/JPEG/GIF de Pillow sont essayés (pas les dizaines
    d'autres formats qu'il sait lire). Le réencodage garantit que le logo
    stocké est lisible par python-docx (certains JPEG valides ne le sont pas
    et faisaient échouer tous les exports), et en retire les métadonnées
    (EXIF, géolocalisation...)."""
    with Image.open(BytesIO(data), formats=list(LOGO_FORMATS)) as image:
        width, height = image.size
        if width > MAX_LOGO_SIDE or height > MAX_LOGO_SIDE:
            raise HTTPException(
                status_code=422, detail=f"Le logo ne doit pas dépasser {MAX_LOGO_SIDE} pixels de côté."
            )
        image.load()
        converted = image.convert("RGBA")
    converted.thumbnail((STORED_LOGO_SIDE, STORED_LOGO_SIDE))
    output = BytesIO()
    converted.save(output, format="PNG", optimize=True)
    return output.getvalue()


@router.put("/logos/{position}", response_model=schemas.DocumentSettingsRead)
def upload_logo(
    project_id: int,
    position: str,
    payload: schemas.LogoUpload,
    account: models.Account = Depends(require_project_owner),
    db: Session = Depends(get_db),
):
    _check_position(position)
    try:
        data = base64.b64decode(payload.data_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Image illisible.") from exc
    if len(data) > MAX_LOGO_BYTES:
        raise HTTPException(status_code=422, detail="Le logo ne doit pas dépasser 1 Mo.")
    try:
        png = _normalize_logo(data)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Image illisible (formats acceptés : PNG, JPEG ou GIF).") from exc

    logo = crud.get_document_logo(db, project_id, position)
    if logo is None:
        logo = models.ProjectDocumentLogo(project_id=project_id, position=position)
        db.add(logo)
    logo.content_type = "image/png"
    logo.data = png
    logo.updated_at = datetime.utcnow()
    db.commit()
    return _read_settings(db, crud.get_project(db, project_id))


@router.delete("/logos/{position}", status_code=status.HTTP_204_NO_CONTENT)
def delete_logo(
    project_id: int,
    position: str,
    account: models.Account = Depends(require_project_owner),
    db: Session = Depends(get_db),
):
    _check_position(position)
    logo = crud.get_document_logo(db, project_id, position)
    if logo is not None:
        db.delete(logo)
        db.commit()
