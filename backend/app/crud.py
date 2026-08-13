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
