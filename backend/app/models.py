from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
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

    members: Mapped[list["Member"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    github_issues: Mapped[list["GithubIssue"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    sprints: Mapped[list["Sprint"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    categories: Mapped[list["Category"]] = relationship(back_populates="project", cascade="all, delete-orphan")

    @property
    def github_label_filter(self) -> list[str]:
        return [label for label in self.github_label_filter_raw.split(",") if label]


class Member(Base):
    __tablename__ = "members"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_member_project_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    pin_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    project: Mapped[Project] = relationship(back_populates="members")
    time_entries: Mapped[list["TimeEntry"]] = relationship(back_populates="member", cascade="all, delete-orphan")

    @property
    def total_hours(self) -> float:
        return sum(entry.duration_hours for entry in self.time_entries)


class TimeEntry(Base):
    __tablename__ = "time_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    duration_hours: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    github_issue_id: Mapped[int | None] = mapped_column(
        ForeignKey("github_issues.id", ondelete="SET NULL"), nullable=True
    )
    sprint_id: Mapped[int | None] = mapped_column(ForeignKey("sprints.id", ondelete="SET NULL"), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)

    member: Mapped[Member] = relationship(back_populates="time_entries")
    github_issue: Mapped["GithubIssue | None"] = relationship()
    sprint: Mapped["Sprint | None"] = relationship()
    category: Mapped["Category | None"] = relationship()

    @property
    def member_name(self) -> str:
        return self.member.name


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
