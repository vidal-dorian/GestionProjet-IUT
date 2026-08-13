from sqlalchemy.orm import Session

from app import models, schemas


def list_projects(db: Session) -> list[models.Project]:
    return db.query(models.Project).order_by(models.Project.created_at.desc()).all()


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
