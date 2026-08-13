from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.security import hash_pin


def list_projects(db: Session) -> list[models.Project]:
    return db.query(models.Project).order_by(models.Project.created_at.desc()).all()


def count_members(db: Session, project_id: int) -> int:
    return db.query(func.count(models.Member.id)).filter(models.Member.project_id == project_id).scalar() or 0


def get_project(db: Session, project_id: int) -> models.Project | None:
    return db.get(models.Project, project_id)


def get_project_by_name(db: Session, name: str) -> models.Project | None:
    return db.query(models.Project).filter(models.Project.name == name).first()


def create_project(db: Session, project: schemas.ProjectCreate) -> models.Project:
    db_project = models.Project(name=project.name.strip(), description=project.description)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def update_project(db: Session, db_project: models.Project, project: schemas.ProjectCreate) -> models.Project:
    db_project.name = project.name.strip()
    db_project.description = project.description
    db.commit()
    db.refresh(db_project)
    return db_project


def delete_project(db: Session, db_project: models.Project) -> None:
    db.delete(db_project)
    db.commit()


def link_github_repo(db: Session, db_project: models.Project, repo: str) -> models.Project:
    db_project.github_repo = repo
    db.commit()
    db.refresh(db_project)
    return db_project


def list_projects_with_github_repo(db: Session) -> list[models.Project]:
    return db.query(models.Project).filter(models.Project.github_repo.isnot(None)).all()


def list_github_issues(db: Session, project_id: int) -> list[models.GithubIssue]:
    return (
        db.query(models.GithubIssue)
        .filter(models.GithubIssue.project_id == project_id)
        .order_by(models.GithubIssue.number.desc())
        .all()
    )


def replace_github_issues(db: Session, db_project: models.Project, issues: list[dict]) -> None:
    existing = {
        issue.number: issue
        for issue in db.query(models.GithubIssue).filter(models.GithubIssue.project_id == db_project.id)
    }
    synced_at = datetime.utcnow()

    for payload in issues:
        number = payload["number"]
        labels_raw = ",".join(label["name"] for label in payload.get("labels", []))
        db_issue = existing.pop(number, None)
        if db_issue is None:
            db_issue = models.GithubIssue(project_id=db_project.id, number=number)
            db.add(db_issue)
        db_issue.title = payload["title"]
        db_issue.state = payload["state"]
        db_issue.labels_raw = labels_raw
        db_issue.url = payload["html_url"]
        db_issue.synced_at = synced_at

    for stale_issue in existing.values():
        db.delete(stale_issue)

    db_project.github_last_synced_at = synced_at
    db.commit()


def list_members(db: Session, project_id: int) -> list[models.Member]:
    return (
        db.query(models.Member)
        .filter(models.Member.project_id == project_id)
        .order_by(models.Member.name)
        .all()
    )


def get_member(db: Session, project_id: int, member_id: int) -> models.Member | None:
    return (
        db.query(models.Member)
        .filter(models.Member.project_id == project_id, models.Member.id == member_id)
        .first()
    )


def get_member_by_name(db: Session, project_id: int, name: str) -> models.Member | None:
    return (
        db.query(models.Member)
        .filter(models.Member.project_id == project_id, models.Member.name == name)
        .first()
    )


def create_member(db: Session, project_id: int, member: schemas.MemberCreate) -> models.Member:
    db_member = models.Member(
        project_id=project_id,
        name=member.name.strip(),
        pin_hash=hash_pin(member.pin),
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member


def delete_member(db: Session, db_member: models.Member) -> None:
    db.delete(db_member)
    db.commit()


def list_time_entries_for_project(db: Session, project_id: int) -> list[models.TimeEntry]:
    return db.query(models.TimeEntry).filter(models.TimeEntry.project_id == project_id).all()


def list_recent_time_entries_for_project(db: Session, project_id: int, limit: int) -> list[models.TimeEntry]:
    return (
        db.query(models.TimeEntry)
        .filter(models.TimeEntry.project_id == project_id)
        .order_by(models.TimeEntry.date.desc(), models.TimeEntry.id.desc())
        .limit(limit)
        .all()
    )


def count_time_entries(db: Session, project_id: int) -> int:
    return db.query(func.count(models.TimeEntry.id)).filter(models.TimeEntry.project_id == project_id).scalar() or 0


def sum_project_hours(db: Session, project_id: int) -> float:
    return (
        db.query(func.coalesce(func.sum(models.TimeEntry.duration_hours), 0.0))
        .filter(models.TimeEntry.project_id == project_id)
        .scalar()
        or 0.0
    )


def count_active_members(db: Session, project_id: int) -> int:
    return (
        db.query(func.count(func.distinct(models.TimeEntry.member_id)))
        .filter(models.TimeEntry.project_id == project_id)
        .scalar()
        or 0
    )


def list_time_entries_for_member(db: Session, project_id: int, member_id: int) -> list[models.TimeEntry]:
    return (
        db.query(models.TimeEntry)
        .filter(models.TimeEntry.project_id == project_id, models.TimeEntry.member_id == member_id)
        .order_by(models.TimeEntry.date.desc(), models.TimeEntry.id.desc())
        .all()
    )


def create_time_entry(
    db: Session, project_id: int, member_id: int, entry: schemas.TimeEntryCreate
) -> models.TimeEntry:
    db_entry = models.TimeEntry(
        project_id=project_id,
        member_id=member_id,
        date=entry.date,
        duration_hours=entry.duration_hours,
        description=entry.description,
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry


def get_time_entry(db: Session, project_id: int, entry_id: int) -> models.TimeEntry | None:
    return (
        db.query(models.TimeEntry)
        .filter(models.TimeEntry.project_id == project_id, models.TimeEntry.id == entry_id)
        .first()
    )


def update_time_entry(
    db: Session, db_entry: models.TimeEntry, entry: schemas.TimeEntryCreate
) -> models.TimeEntry:
    db_entry.date = entry.date
    db_entry.duration_hours = entry.duration_hours
    db_entry.description = entry.description
    db.commit()
    db.refresh(db_entry)
    return db_entry


def delete_time_entry(db: Session, db_entry: models.TimeEntry) -> None:
    db.delete(db_entry)
    db.commit()
