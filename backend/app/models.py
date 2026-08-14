from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    github_repo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    github_last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    github_label_filter_raw: Mapped[str] = mapped_column(String(500), nullable=False, default="")

    time_entries: Mapped[list["TimeEntry"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    github_issues: Mapped[list["GithubIssue"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    sprints: Mapped[list["Sprint"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    categories: Mapped[list["Category"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    memberships: Mapped[list["ProjectMembership"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    @property
    def github_label_filter(self) -> list[str]:
        return [label for label in self.github_label_filter_raw.split(",") if label]


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class ProjectMembership(Base):
    """Rattache un compte à un projet, pour qu'il apparaisse dans sa liste "Mes projets".

    `status` vaut "pending" (demande en attente), "approved" (accès accordé,
    y compris le créateur du projet et les administrateurs qui rejoignent) ou
    "rejected" (refusée par un administrateur — peut être redemandée).
    """

    __tablename__ = "project_memberships"
    __table_args__ = (UniqueConstraint("project_id", "account_id", name="uq_project_membership_project_account"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="approved")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    project: Mapped[Project] = relationship(back_populates="memberships")
    account: Mapped["Account"] = relationship()


class TimeEntry(Base):
    __tablename__ = "time_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    duration_hours: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    github_issue_id: Mapped[int | None] = mapped_column(
        ForeignKey("github_issues.id", ondelete="SET NULL"), nullable=True
    )
    sprint_id: Mapped[int | None] = mapped_column(ForeignKey("sprints.id", ondelete="SET NULL"), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)

    project: Mapped[Project] = relationship(back_populates="time_entries")
    account: Mapped[Account] = relationship()
    github_issue: Mapped["GithubIssue | None"] = relationship()
    sprint: Mapped["Sprint | None"] = relationship()
    category: Mapped["Category | None"] = relationship()

    @property
    def account_email(self) -> str:
        return self.account.email


class GithubIssue(Base):
    __tablename__ = "github_issues"
    __table_args__ = (UniqueConstraint("project_id", "number", name="uq_github_issue_project_number"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    number: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    labels_raw: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    project: Mapped[Project] = relationship(back_populates="github_issues")

    @property
    def labels(self) -> list[str]:
        return [label for label in self.labels_raw.split(",") if label]


class Sprint(Base):
    __tablename__ = "sprints"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    project: Mapped[Project] = relationship(back_populates="sprints")


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_category_project_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    project: Mapped[Project] = relationship(back_populates="categories")
