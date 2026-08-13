from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas


def list_projects(db: Session) -> list[models.Project]:
    return db.query(models.Project).order_by(models.Project.created_at.desc()).all()


def count_contributors(db: Session, project_id: int) -> int:
    return (
        db.query(func.count(func.distinct(models.TimeEntry.account_id)))
        .filter(models.TimeEntry.project_id == project_id)
        .scalar()
        or 0
    )


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


def list_visible_github_issues(db: Session, db_project: models.Project) -> list[models.GithubIssue]:
    issues = list_github_issues(db, db_project.id)
    label_filter = set(db_project.github_label_filter)
    if label_filter:
        return [issue for issue in issues if label_filter & set(issue.labels)]
    return [issue for issue in issues if issue.state == "open"]


def set_github_label_filter(db: Session, db_project: models.Project, labels: list[str]) -> models.Project:
    cleaned = [label.strip() for label in labels if label.strip()]
    db_project.github_label_filter_raw = ",".join(cleaned)
    db.commit()
    db.refresh(db_project)
    return db_project


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


def list_sprints(db: Session, project_id: int) -> list[models.Sprint]:
    return (
        db.query(models.Sprint)
        .filter(models.Sprint.project_id == project_id)
        .order_by(models.Sprint.start_date.desc())
        .all()
    )


def get_sprint(db: Session, project_id: int, sprint_id: int) -> models.Sprint | None:
    return (
        db.query(models.Sprint)
        .filter(models.Sprint.project_id == project_id, models.Sprint.id == sprint_id)
        .first()
    )


def find_overlapping_sprint(
    db: Session, project_id: int, start_date, end_date, exclude_id: int | None = None
) -> models.Sprint | None:
    query = db.query(models.Sprint).filter(
        models.Sprint.project_id == project_id,
        models.Sprint.start_date <= end_date,
        models.Sprint.end_date >= start_date,
    )
    if exclude_id is not None:
        query = query.filter(models.Sprint.id != exclude_id)
    return query.first()


def create_sprint(db: Session, project_id: int, sprint: schemas.SprintCreate) -> models.Sprint:
    db_sprint = models.Sprint(
        project_id=project_id,
        name=sprint.name.strip(),
        start_date=sprint.start_date,
        end_date=sprint.end_date,
    )
    db.add(db_sprint)
    db.commit()
    db.refresh(db_sprint)
    return db_sprint


def list_categories(db: Session, project_id: int) -> list[models.Category]:
    return (
        db.query(models.Category)
        .filter(models.Category.project_id == project_id)
        .order_by(models.Category.name)
        .all()
    )


def get_category(db: Session, project_id: int, category_id: int) -> models.Category | None:
    return (
        db.query(models.Category)
        .filter(models.Category.project_id == project_id, models.Category.id == category_id)
        .first()
    )


def create_category(db: Session, project_id: int, category: schemas.CategoryCreate) -> models.Category:
    db_category = models.Category(project_id=project_id, name=category.name.strip())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


def get_account(db: Session, account_id: int) -> models.Account | None:
    return db.get(models.Account, account_id)


def get_or_create_account(db: Session, email: str) -> models.Account:
    account = db.query(models.Account).filter(models.Account.email == email).first()
    if account is not None:
        return account

    account = models.Account(email=email)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def list_project_contributors(db: Session, project_id: int) -> list[tuple[models.Account, float]]:
    return (
        db.query(models.Account, func.coalesce(func.sum(models.TimeEntry.duration_hours), 0.0))
        .join(models.TimeEntry, models.TimeEntry.account_id == models.Account.id)
        .filter(models.TimeEntry.project_id == project_id)
        .group_by(models.Account.id)
        .order_by(models.Account.email)
        .all()
    )


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


def sum_hours_by_github_issue(db: Session, project_id: int) -> list[tuple[models.GithubIssue, float]]:
    return (
        db.query(models.GithubIssue, func.coalesce(func.sum(models.TimeEntry.duration_hours), 0.0))
        .join(models.TimeEntry, models.TimeEntry.github_issue_id == models.GithubIssue.id)
        .filter(models.TimeEntry.project_id == project_id)
        .group_by(models.GithubIssue.id)
        .all()
    )


def sum_unattached_hours(db: Session, project_id: int) -> float:
    return (
        db.query(func.coalesce(func.sum(models.TimeEntry.duration_hours), 0.0))
        .filter(models.TimeEntry.project_id == project_id, models.TimeEntry.github_issue_id.is_(None))
        .scalar()
        or 0.0
    )


def sum_hours_by_category(db: Session, project_id: int) -> list[tuple[models.Category, float]]:
    return (
        db.query(models.Category, func.coalesce(func.sum(models.TimeEntry.duration_hours), 0.0))
        .join(models.TimeEntry, models.TimeEntry.category_id == models.Category.id)
        .filter(models.TimeEntry.project_id == project_id)
        .group_by(models.Category.id)
        .all()
    )


def sum_unattached_category_hours(db: Session, project_id: int) -> float:
    return (
        db.query(func.coalesce(func.sum(models.TimeEntry.duration_hours), 0.0))
        .filter(models.TimeEntry.project_id == project_id, models.TimeEntry.category_id.is_(None))
        .scalar()
        or 0.0
    )


def sum_hours_for_sprint(db: Session, project_id: int, sprint_id: int) -> float:
    return (
        db.query(func.coalesce(func.sum(models.TimeEntry.duration_hours), 0.0))
        .filter(models.TimeEntry.project_id == project_id, models.TimeEntry.sprint_id == sprint_id)
        .scalar()
        or 0.0
    )


def sum_hours_by_account_for_sprint(
    db: Session, project_id: int, sprint_id: int
) -> list[tuple[models.Account, float]]:
    return (
        db.query(models.Account, func.coalesce(func.sum(models.TimeEntry.duration_hours), 0.0))
        .join(models.TimeEntry, models.TimeEntry.account_id == models.Account.id)
        .filter(models.TimeEntry.project_id == project_id, models.TimeEntry.sprint_id == sprint_id)
        .group_by(models.Account.id)
        .all()
    )


def sum_hours_by_github_issue_for_sprint(
    db: Session, project_id: int, sprint_id: int
) -> list[tuple[models.GithubIssue, float]]:
    return (
        db.query(models.GithubIssue, func.coalesce(func.sum(models.TimeEntry.duration_hours), 0.0))
        .join(models.TimeEntry, models.TimeEntry.github_issue_id == models.GithubIssue.id)
        .filter(models.TimeEntry.project_id == project_id, models.TimeEntry.sprint_id == sprint_id)
        .group_by(models.GithubIssue.id)
        .all()
    )


def sum_unattached_hours_for_sprint(db: Session, project_id: int, sprint_id: int) -> float:
    return (
        db.query(func.coalesce(func.sum(models.TimeEntry.duration_hours), 0.0))
        .filter(
            models.TimeEntry.project_id == project_id,
            models.TimeEntry.sprint_id == sprint_id,
            models.TimeEntry.github_issue_id.is_(None),
        )
        .scalar()
        or 0.0
    )


def list_time_entries_for_account(db: Session, project_id: int, account_id: int) -> list[models.TimeEntry]:
    return (
        db.query(models.TimeEntry)
        .filter(models.TimeEntry.project_id == project_id, models.TimeEntry.account_id == account_id)
        .order_by(models.TimeEntry.date.desc(), models.TimeEntry.id.desc())
        .all()
    )


def get_github_issue(db: Session, project_id: int, issue_id: int) -> models.GithubIssue | None:
    return (
        db.query(models.GithubIssue)
        .filter(models.GithubIssue.project_id == project_id, models.GithubIssue.id == issue_id)
        .first()
    )


def create_time_entry(
    db: Session, project_id: int, account_id: int, entry: schemas.TimeEntryCreate
) -> models.TimeEntry:
    db_entry = models.TimeEntry(
        project_id=project_id,
        account_id=account_id,
        date=entry.date,
        duration_hours=entry.duration_hours,
        description=entry.description,
        github_issue_id=entry.github_issue_id,
        sprint_id=entry.sprint_id,
        category_id=entry.category_id,
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
    db_entry.github_issue_id = entry.github_issue_id
    db_entry.sprint_id = entry.sprint_id
    db_entry.category_id = entry.category_id
    db.commit()
    db.refresh(db_entry)
    return db_entry


def delete_time_entry(db: Session, db_entry: models.TimeEntry) -> None:
    db.delete(db_entry)
    db.commit()
