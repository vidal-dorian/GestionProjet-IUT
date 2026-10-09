import unicodedata
from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app import burndown, crud, docx_export, models, schemas
from app.database import get_db
from app.deps import require_project_member
from app.report_content import (
    LONG_TEXT,
    MAX_USER_STORIES,
    REPORT_TYPES,
    SHORT_TEXT,
    dump_content,
    load_content,
    validate_content,
)

router = APIRouter(prefix="/api/projects/{project_id}/reports", tags=["reports"])

DAILY_EXISTS = "Un daily existe déjà à cette date."
REPORT_CHANGED = (
    "Ce compte-rendu a été modifié par quelqu'un d'autre entre-temps. "
    "Recharge-le pour récupérer ses changements avant d'enregistrer."
)

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower().strip()


def _get_report_or_404(db: Session, project_id: int, report_id: int) -> models.MeetingReport:
    report = crud.get_report(db, project_id, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Compte-rendu introuvable.")
    return report


def _get_sprint_or_422(db: Session, project_id: int, sprint_id: int | None) -> models.Sprint | None:
    if sprint_id is None:
        return None
    sprint = crud.get_sprint(db, project_id, sprint_id)
    if sprint is None:
        raise HTTPException(status_code=422, detail="Ce sprint n'existe pas pour ce projet.")
    return sprint


def _roles_by_account(db: Session, sprint: models.Sprint | None) -> dict[int, list[str]]:
    roles: dict[int, list[str]] = defaultdict(list)
    if sprint is not None:
        for assignment in crud.list_sprint_role_assignments(db, sprint.id):
            roles[assignment.account_id].append(assignment.role.name)
    return roles


def _team(db: Session, project_id: int, sprint: models.Sprint | None) -> list[schemas.TeamMember]:
    roles = _roles_by_account(db, sprint)
    members = crud.list_approved_members(db, project_id)
    team = [
        schemas.TeamMember(account_id=m.id, label=m.label, email=m.email, roles=roles.get(m.id, []))
        for m in members
    ]
    return sorted(team, key=lambda member: _normalize(member.label))


def _default_participant_ids(team: list[schemas.TeamMember]) -> list[int]:
    """L'équipe du sprint = les membres qui y ont un rôle ; à défaut (rôles pas
    encore attribués), tous les membres du projet."""
    with_role = [member.account_id for member in team if member.roles]
    return with_role or [member.account_id for member in team]


def _suggested_user_stories(
    db: Session, project_id: int, sprint: models.Sprint | None, report_type: str
) -> list[dict]:
    """US GitHub labellisées du nom du sprint (même règle que le burndown) :
    toutes pour la planification, seulement les fermées pour la review."""
    if sprint is None:
        return []
    issues = [issue for issue in crud.list_github_issues(db, project_id) if burndown.matches_sprint(issue, sprint)]
    if report_type == "sprint_review":
        issues = [issue for issue in issues if issue.state == "closed"]
    # Bornées aux limites du contenu, sans quoi le pré-remplissage produirait un
    # compte-rendu impossible à enregistrer (ou une erreur à la création).
    ordered = sorted(issues, key=lambda i: i.number)[:MAX_USER_STORIES]
    return [{"reference": f"#{issue.number}", "name": issue.title[:500]} for issue in ordered]


def _last_client(db: Session, project_id: int) -> str:
    for report in crud.list_reports(db, project_id):
        if report.type in ("sprint_planning", "sprint_review"):
            client = getattr(load_content(report.type, report.content_json), "client", "")
            if client.strip():
                return client
    return ""


def _initial_content(
    db: Session, project_id: int, report_type: str, sprint: models.Sprint | None, team: list[schemas.TeamMember]
) -> dict:
    content: dict = {"participant_ids": _default_participant_ids(team)}
    if report_type in ("sprint_planning", "sprint_review"):
        content["client"] = _last_client(db, project_id)[:SHORT_TEXT]
        content["user_stories"] = _suggested_user_stories(db, project_id, sprint, report_type)
    if report_type == "sprint_review" and sprint is not None:
        plannings = crud.list_reports(db, project_id, "sprint_planning", sprint.id)
        if plannings:
            content["objectives"] = load_content("sprint_planning", plannings[0].content_json).topics[:LONG_TEXT]
    if report_type == "retrospective":
        by_role: dict[str, list[str]] = defaultdict(list)
        for member in team:
            for role in member.roles:
                by_role[_normalize(role)].append(member.label)
        content["scrum_master"] = " et ".join(
            name for role, names in by_role.items() if "scrum" in role for name in names
        )[:SHORT_TEXT]
        content["product_owner"] = " et ".join(
            name for role, names in by_role.items() if "product owner" in role or role == "po" for name in names
        )[:SHORT_TEXT]
    return content


def _label(account: models.Account | None) -> str | None:
    return account.label if account is not None else None


def _to_summary(report: models.MeetingReport) -> schemas.ReportSummary:
    return schemas.ReportSummary(
        id=report.id,
        project_id=report.project_id,
        type=report.type,
        sprint_id=report.sprint_id,
        sprint_name=report.sprint.name if report.sprint else None,
        meeting_date=report.meeting_date,
        created_by_label=_label(report.created_by),
        updated_at=report.updated_at,
        updated_by_label=_label(report.updated_by),
    )


def _can_delete(report: models.MeetingReport, account: models.Account) -> bool:
    return (
        account.is_admin
        or report.created_by_account_id == account.id
        or report.project.created_by_account_id == account.id
    )


def _to_read(db: Session, report: models.MeetingReport, account: models.Account) -> schemas.ReportRead:
    return schemas.ReportRead(
        **_to_summary(report).model_dump(),
        content=load_content(report.type, report.content_json).model_dump(),
        version=report.version,
        team=_team(db, report.project_id, report.sprint),
        daily_entries=[
            schemas.DailyEntryRead(
                account_id=entry.account_id,
                done=entry.done,
                todo=entry.todo,
                blockers=entry.blockers,
                updated_at=entry.updated_at,
                updated_by_label=_label(db.get(models.Account, entry.updated_by_account_id))
                if entry.updated_by_account_id
                else None,
            )
            for entry in report.daily_entries
        ],
        can_delete=_can_delete(report, account),
    )


@router.get("", response_model=list[schemas.ReportSummary])
def list_reports(
    project_id: int,
    report_type: str | None = Query(default=None, alias="type"),
    sprint_id: int | None = Query(default=None),
    account: models.Account = Depends(require_project_member),
    db: Session = Depends(get_db),
):
    if report_type is not None and report_type not in REPORT_TYPES:
        raise HTTPException(status_code=422, detail="Type de compte-rendu inconnu.")
    return [_to_summary(report) for report in crud.list_reports(db, project_id, report_type, sprint_id)]


@router.post("", response_model=schemas.ReportRead, status_code=status.HTTP_201_CREATED)
def create_report(
    project_id: int,
    payload: schemas.ReportCreate,
    account: models.Account = Depends(require_project_member),
    db: Session = Depends(get_db),
):
    sprint = _get_sprint_or_422(db, project_id, payload.sprint_id)
    if sprint is None and payload.type != "daily":
        raise HTTPException(status_code=422, detail="Choisis le sprint concerné par ce compte-rendu.")
    # Un seul daily par jour : sinon deux membres qui ouvrent le daily du matin
    # en même temps rempliraient chacun le leur.
    if payload.type == "daily" and crud.find_daily_on_date(db, project_id, payload.meeting_date):
        raise HTTPException(status_code=409, detail=DAILY_EXISTS)

    team = _team(db, project_id, sprint)
    try:
        content = validate_content(payload.type, _initial_content(db, project_id, payload.type, sprint, team))
    except ValidationError as exc:
        raise RequestValidationError(exc.errors(include_url=False, include_context=False)) from exc
    now = datetime.utcnow()
    report = models.MeetingReport(
        project_id=project_id,
        sprint_id=sprint.id if sprint else None,
        type=payload.type,
        meeting_date=payload.meeting_date,
        daily_date=payload.meeting_date if payload.type == "daily" else None,
        content_json=dump_content(content),
        created_by_account_id=account.id,
        updated_by_account_id=account.id,
        created_at=now,
        updated_at=now,
    )
    db.add(report)
    try:
        db.commit()
    except IntegrityError as exc:
        # Création simultanée du même daily : l'autre a gagné, le client le rejoint.
        db.rollback()
        raise HTTPException(status_code=409, detail=DAILY_EXISTS) from exc
    db.refresh(report)
    return _to_read(db, report, account)


@router.get("/{report_id}", response_model=schemas.ReportRead)
def read_report(
    project_id: int,
    report_id: int,
    account: models.Account = Depends(require_project_member),
    db: Session = Depends(get_db),
):
    return _to_read(db, _get_report_or_404(db, project_id, report_id), account)


@router.put("/{report_id}", response_model=schemas.ReportRead)
def update_report(
    project_id: int,
    report_id: int,
    payload: schemas.ReportUpdate,
    account: models.Account = Depends(require_project_member),
    db: Session = Depends(get_db),
):
    report = _get_report_or_404(db, project_id, report_id)
    if payload.version != report.version:
        raise HTTPException(status_code=409, detail=REPORT_CHANGED)

    sprint = _get_sprint_or_422(db, project_id, payload.sprint_id)
    if sprint is None and report.type != "daily":
        raise HTTPException(status_code=422, detail="Choisis le sprint concerné par ce compte-rendu.")
    if (
        report.type == "daily"
        and payload.meeting_date != report.meeting_date
        and crud.find_daily_on_date(db, project_id, payload.meeting_date)
    ):
        raise HTTPException(status_code=409, detail=DAILY_EXISTS)

    try:
        content = validate_content(report.type, payload.content)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors(include_url=False, include_context=False)) from exc

    # Seuls les participants ajoutés doivent être membres : un participant déjà
    # présent qui a quitté le projet depuis reste dans le compte-rendu (il était
    # là ce jour-là), sinon le document ne pourrait plus être enregistré.
    previous_ids = set(load_content(report.type, report.content_json).participant_ids)
    member_ids = {member.id for member in crud.list_approved_members(db, project_id)}
    if any(account_id not in member_ids | previous_ids for account_id in content.participant_ids):
        raise HTTPException(status_code=422, detail="Un participant n'est pas membre approuvé de ce projet.")
    content.participant_ids = list(dict.fromkeys(content.participant_ids))

    report.sprint_id = sprint.id if sprint else None
    report.meeting_date = payload.meeting_date
    if report.type == "daily":
        report.daily_date = payload.meeting_date
    report.content_json = dump_content(content)
    report.updated_at = datetime.utcnow()
    report.updated_by_account_id = account.id
    try:
        db.commit()
    except StaleDataError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=REPORT_CHANGED) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=DAILY_EXISTS) from exc
    db.refresh(report)
    return _to_read(db, report, account)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(
    project_id: int,
    report_id: int,
    account: models.Account = Depends(require_project_member),
    db: Session = Depends(get_db),
):
    report = _get_report_or_404(db, project_id, report_id)
    if not _can_delete(report, account):
        raise HTTPException(
            status_code=403,
            detail="Seuls l'auteur du compte-rendu, le créateur du projet et les administrateurs peuvent le supprimer.",
        )
    db.delete(report)
    db.commit()


@router.put("/{report_id}/daily-entries/{entry_account_id}", response_model=schemas.ReportRead)
def save_daily_entry(
    project_id: int,
    report_id: int,
    entry_account_id: int,
    payload: schemas.DailyEntryUpdate,
    account: models.Account = Depends(require_project_member),
    db: Session = Depends(get_db),
):
    """Enregistre les réponses d'une personne au daily. Chacun remplit
    normalement sa partie, mais n'importe quel membre peut compléter celle
    d'un autre (ex. le Scrum Master pendant la réunion)."""
    report = _get_report_or_404(db, project_id, report_id)
    if report.type != "daily":
        raise HTTPException(status_code=422, detail="Ce compte-rendu n'est pas un daily.")
    if not crud.is_approved_member(db, project_id, entry_account_id):
        raise HTTPException(status_code=422, detail="Ce compte n'est pas membre approuvé de ce projet.")

    def upsert() -> None:
        entry = crud.get_daily_entry(db, report.id, entry_account_id)
        if entry is None:
            entry = models.DailyEntry(report_id=report.id, account_id=entry_account_id)
            db.add(entry)
        # Texte gardé tel quel (pas de strip) : la saisie s'enregistre
        # automatiquement pendant la frappe, et retirer l'espace qu'on vient de
        # taper le ferait disparaître de l'écran. L'export nettoie le texte.
        entry.done = payload.done
        entry.todo = payload.todo
        entry.blockers = payload.blockers
        entry.updated_at = datetime.utcnow()
        entry.updated_by_account_id = account.id
        db.commit()

    try:
        upsert()
    except IntegrityError:
        # Création simultanée de la même ligne : l'autre écriture a gagné la
        # course, on retombe sur une mise à jour.
        db.rollback()
        upsert()

    db.refresh(report)
    return _to_read(db, report, account)


@router.get("/{report_id}/suggested-user-stories", response_model=schemas.SuggestedUserStories)
def suggested_user_stories(
    project_id: int,
    report_id: int,
    sprint_id: int | None = Query(default=None),
    account: models.Account = Depends(require_project_member),
    db: Session = Depends(get_db),
):
    """Tableau des US proposé à partir de GitHub, sans l'enregistrer : le
    formulaire le reprend et l'utilisateur garde la main avant d'enregistrer."""
    report = _get_report_or_404(db, project_id, report_id)
    sprint = _get_sprint_or_422(db, project_id, sprint_id if sprint_id is not None else report.sprint_id)
    return schemas.SuggestedUserStories(
        user_stories=_suggested_user_stories(db, project_id, sprint, report.type),
        source_label=sprint.name if sprint else None,
    )


def _filename(report: models.MeetingReport) -> str:
    sprint = report.sprint.name if report.sprint else ""
    base = {
        "daily": f"Daily - {report.meeting_date:%d_%m_%Y}",
        "sprint_planning": f"Planification de {sprint}",
        "sprint_review": f"Review de {sprint}",
        "retrospective": f"Retrospective {sprint}",
    }[report.type]
    ascii_only = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in ascii_only).strip("_")
    return f"{safe or 'compte-rendu'}.docx"


@router.get("/{report_id}/export")
def export_report(
    project_id: int,
    report_id: int,
    account: models.Account = Depends(require_project_member),
    db: Session = Depends(get_db),
):
    report = _get_report_or_404(db, project_id, report_id)
    content = load_content(report.type, report.content_json)
    sprint = report.sprint

    roles = _roles_by_account(db, sprint)
    participants = []
    for account_id in content.participant_ids:
        participant = db.get(models.Account, account_id)
        if participant is not None:
            participants.append(
                docx_export.Participant(account_id=participant.id, label=participant.label, roles=roles.get(participant.id, []))
            )

    burndown_data = None
    if report.type == "retrospective" and sprint is not None:
        burndown_data = burndown.compute_burndown(sprint, crud.list_github_issues(db, project_id))

    data = docx_export.ReportExportData(
        type=report.type,
        meeting_date=report.meeting_date,
        sprint_name=sprint.name if sprint else None,
        sprint_start=sprint.start_date if sprint else None,
        sprint_end=sprint.end_date if sprint else None,
        content=content,
        participants=participants,
        daily_answers={
            entry.account_id: docx_export.DailyAnswers(done=entry.done, todo=entry.todo, blockers=entry.blockers)
            for entry in report.daily_entries
        },
        # Pied de page par défaut : le nom du projet, personnalisable dans les paramètres.
        footer=report.project.document_footer or report.project.name,
        logos={logo.position: logo.data for logo in report.project.document_logos},
        burndown=burndown_data,
    )
    buffer = docx_export.build_report_docx(data)
    return StreamingResponse(
        buffer,
        media_type=DOCX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{_filename(report)}"'},
    )
