from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.mysql import LONGTEXT, MEDIUMBLOB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    created_by_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    github_repo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    github_last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    github_label_filter_raw: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    # Texte du pied de page des comptes-rendus exportés en Word (ex. "SAE S4 -
    # Développement d'une application complexe"), à gauche du numéro de page.
    document_footer: Mapped[str | None] = mapped_column(String(255), nullable=True)

    time_entries: Mapped[list["TimeEntry"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    github_issues: Mapped[list["GithubIssue"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    sprints: Mapped[list["Sprint"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    categories: Mapped[list["Category"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    memberships: Mapped[list["ProjectMembership"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    team_roles: Mapped[list["TeamRole"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    meeting_reports: Mapped[list["MeetingReport"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    document_logos: Mapped[list["ProjectDocumentLogo"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    @property
    def github_label_filter(self) -> list[str]:
        return [label for label in self.github_label_filter_raw.split(",") if label]


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    # Nom affiché dans les comptes-rendus (ex. "VIDAL Dorian"), saisi par la
    # personne elle-même — l'e-mail sert de repli tant qu'il n'est pas renseigné.
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    @property
    def label(self) -> str:
        return (self.display_name or "").strip() or self.email


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
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="approved", server_default="approved")
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
    # Valeur du champ personnalisé "Valorisation" du GitHub Project (v2) auquel
    # l'issue est rattachée, récupérée via l'API GraphQL — None si l'issue n'a
    # pas ce champ renseigné (ou n'appartient à aucun Project).
    story_points: Mapped[float | None] = mapped_column(Float, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Titre de l'itération GitHub Projects (v2) de l'issue (ex: "Sprint 0"),
    # None si elle n'en a pas ou si le Project est illisible avec ce token.
    iteration: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Date de clôture saisie à la main depuis le burndown (US fermée en retard
    # sur GitHub). Jamais touchée par la synchro : elle prime sur `closed_at`
    # tant que l'US reste fermée.
    closed_on_override: Mapped[date | None] = mapped_column(Date, nullable=True)

    project: Mapped[Project] = relationship(back_populates="github_issues")

    @property
    def labels(self) -> list[str]:
        return [label for label in self.labels_raw.split(",") if label]

    @property
    def github_closed_on(self) -> date | None:
        return self.closed_at.date() if self.closed_at is not None else None

    @property
    def effective_closed_on(self) -> date | None:
        """Date de clôture retenue pour le burndown : celle saisie à la main si
        elle existe, sinon celle de GitHub. None tant que l'US est ouverte."""
        if self.closed_at is None:
            return None
        return self.closed_on_override or self.closed_at.date()


class Sprint(Base):
    __tablename__ = "sprints"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    project: Mapped[Project] = relationship(back_populates="sprints")
    role_assignments: Mapped[list["SprintRoleAssignment"]] = relationship(
        back_populates="sprint", cascade="all, delete-orphan"
    )


class TeamRole(Base):
    """Rôle d'équipe défini librement au niveau d'un projet (Product Owner,
    Gestion de projet, Développeur, ou tout rôle personnalisé), assignable à
    un ou plusieurs membres pour un sprint donné (SprintRoleAssignment)."""

    __tablename__ = "team_roles"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_team_role_project_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    project: Mapped[Project] = relationship(back_populates="team_roles")


class SprintRoleAssignment(Base):
    """Attribue un rôle d'équipe à un membre pour un sprint donné. Plusieurs
    personnes peuvent partager le même rôle sur le même sprint, et une
    personne peut cumuler plusieurs rôles sur le même sprint."""

    __tablename__ = "sprint_role_assignments"
    __table_args__ = (
        UniqueConstraint("sprint_id", "role_id", "account_id", name="uq_sprint_role_assignment"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sprint_id: Mapped[int] = mapped_column(ForeignKey("sprints.id", ondelete="CASCADE"), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("team_roles.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    sprint: Mapped[Sprint] = relationship(back_populates="role_assignments")
    role: Mapped[TeamRole] = relationship()
    account: Mapped["Account"] = relationship()


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_category_project_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    project: Mapped[Project] = relationship(back_populates="categories")


class MeetingReport(Base):
    """Compte-rendu d'une cérémonie Scrum (daily, planification, review,
    rétrospective), rempli collaborativement depuis l'application puis
    exportable en Word.

    Les champs propres à chaque type de cérémonie sont stockés en JSON dans
    `content_json` (validé par le schéma Pydantic du type, voir
    app/report_content.py) ; seules les réponses individuelles du daily vivent
    dans une table à part (DailyEntry) pour que chacun puisse remplir sa
    partie sans écraser celle des autres. `version` sert de verrou optimiste
    sur `content_json`.
    """

    __tablename__ = "meeting_reports"
    # Un seul daily par projet et par jour, garanti par la base : la
    # vérification applicative seule laisse passer deux créations simultanées
    # (toute l'équipe ouvre le daily du jour au même moment). `daily_date` vaut
    # meeting_date pour un daily et NULL sinon (les NULL ne se heurtent pas).
    __table_args__ = (UniqueConstraint("project_id", "daily_date", name="uq_meeting_report_project_daily_date"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    sprint_id: Mapped[int | None] = mapped_column(ForeignKey("sprints.id", ondelete="SET NULL"), nullable=True)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    meeting_date: Mapped[date] = mapped_column(Date, nullable=False)
    daily_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    content_json: Mapped[str] = mapped_column(
        Text().with_variant(LONGTEXT(), "mysql"), nullable=False, default="{}"
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_by_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )

    project: Mapped[Project] = relationship(back_populates="meeting_reports")
    sprint: Mapped["Sprint | None"] = relationship()
    created_by: Mapped["Account | None"] = relationship(foreign_keys=[created_by_account_id])
    updated_by: Mapped["Account | None"] = relationship(foreign_keys=[updated_by_account_id])
    daily_entries: Mapped[list["DailyEntry"]] = relationship(back_populates="report", cascade="all, delete-orphan")

    # Verrou optimiste géré par SQLAlchemy : chaque UPDATE porte
    # "WHERE version = <version lue>" et incrémente la version, si bien que deux
    # enregistrements simultanés ne peuvent pas réussir tous les deux.
    __mapper_args__ = {"version_id_col": version}


class DailyEntry(Base):
    """Réponses d'un participant aux trois questions du daily."""

    __tablename__ = "daily_entries"
    __table_args__ = (UniqueConstraint("report_id", "account_id", name="uq_daily_entry_report_account"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("meeting_reports.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    done: Mapped[str] = mapped_column(Text, nullable=False, default="")
    todo: Mapped[str] = mapped_column(Text, nullable=False, default="")
    blockers: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_by_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )

    report: Mapped[MeetingReport] = relationship(back_populates="daily_entries")
    account: Mapped[Account] = relationship(foreign_keys=[account_id])


class ProjectDocumentLogo(Base):
    """Logo affiché en tête des comptes-rendus exportés (à gauche ou à droite)."""

    __tablename__ = "project_document_logos"
    __table_args__ = (UniqueConstraint("project_id", "position", name="uq_project_document_logo_position"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    position: Mapped[str] = mapped_column(String(10), nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary().with_variant(MEDIUMBLOB(), "mysql"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    project: Mapped[Project] = relationship(back_populates="document_logos")
