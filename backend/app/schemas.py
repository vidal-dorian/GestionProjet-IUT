from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.report_content import ReportType
from app.text import CleanStr


# Bornes de saisie des dates : au-delà, une seule valeur aberrante (ex. an 1)
# fait générer au dashboard des dizaines de milliers de points hebdomadaires.
MIN_DATE = date_type(2000, 1, 1)
MAX_SPRINT_DATE = date_type(2100, 12, 31)


class ProjectCreate(BaseModel):
    name: CleanStr = Field(min_length=1, max_length=120)
    description: CleanStr | None = Field(default=None, max_length=5000)


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime
    created_by_account_id: int | None
    github_repo: str | None
    github_last_synced_at: datetime | None
    github_label_filter: list[str]


class GithubRepoLink(BaseModel):
    repo: str = Field(min_length=1, max_length=255)


class GithubLabelFilterUpdate(BaseModel):
    labels: list[CleanStr] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def fits_storage_column(self) -> "GithubLabelFilterUpdate":
        # Stocké joint par des virgules dans une colonne VARCHAR(500) : au-delà,
        # MySQL refuse l'écriture et la requête échouerait en erreur 500.
        if len(",".join(label.strip() for label in self.labels if label.strip())) > 500:
            raise ValueError("La liste de labels est trop longue (500 caractères au maximum).")
        return self


class GithubIssueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int
    title: str
    state: str
    labels: list[str]
    url: str
    story_points: float | None = None
    closed_at: datetime | None = None
    iteration: str | None = None


class GithubSyncResult(BaseModel):
    synced_at: datetime
    issue_count: int
    warning: str | None = None


class SprintCreate(BaseModel):
    name: CleanStr = Field(min_length=1, max_length=120)
    start_date: date_type
    end_date: date_type

    @field_validator("start_date", "end_date")
    @classmethod
    def date_within_bounds(cls, value: date_type) -> date_type:
        if not MIN_DATE <= value <= MAX_SPRINT_DATE:
            raise ValueError(f"La date doit être comprise entre {MIN_DATE:%d/%m/%Y} et {MAX_SPRINT_DATE:%d/%m/%Y}.")
        return value

    @model_validator(mode="after")
    def end_after_start(self) -> "SprintCreate":
        if self.end_date <= self.start_date:
            raise ValueError("La date de fin doit être postérieure à la date de début.")
        return self


class SprintRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    start_date: date_type
    end_date: date_type
    created_at: datetime


class SprintWriteResult(BaseModel):
    sprint: SprintRead
    overlap_warning: str | None = None


class BurndownPoint(BaseModel):
    date: date_type
    remaining_points: float


class BurndownChartData(BaseModel):
    sprint: SprintRead
    total_points: float
    matched_issue_count: int
    unestimated_issue_count: int
    ideal: list[BurndownPoint]
    actual: list[BurndownPoint]


class TeamRoleCreate(BaseModel):
    name: CleanStr = Field(min_length=1, max_length=80)


class TeamRoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    created_at: datetime


class SprintRoleAssignmentInput(BaseModel):
    role_id: int
    account_id: int


class SprintRoleAssignmentRead(BaseModel):
    role_id: int
    role_name: str
    account_id: int
    account_email: str


class SprintRoleAssignmentsUpdate(BaseModel):
    assignments: list[SprintRoleAssignmentInput]


class CategoryCreate(BaseModel):
    name: CleanStr = Field(min_length=1, max_length=80)


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    created_at: datetime


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str | None = None
    is_admin: bool
    created_at: datetime


class DisplayNameUpdate(BaseModel):
    display_name: CleanStr = Field(max_length=120)


class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    contributor_count: int
    is_member: bool = False
    membership_status: str | None = None


class MembershipRead(BaseModel):
    project_id: int
    status: str


class MembershipRequestRead(BaseModel):
    id: int
    project_id: int
    project_name: str
    account_id: int
    account_email: str
    status: str
    created_at: datetime


class TimeEntryCreate(BaseModel):
    date: date_type
    duration_hours: float = Field(gt=0, le=24)
    description: CleanStr = Field(min_length=1, max_length=2000)
    github_issue_id: int | None = None
    sprint_id: int | None = None
    category_id: int | None = None

    @field_validator("description")
    @classmethod
    def description_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("La description est obligatoire.")
        return value.strip()

    @field_validator("date")
    @classmethod
    def date_must_not_be_in_the_future(cls, value: date_type) -> date_type:
        if value > date_type.today():
            raise ValueError("La date ne peut pas être dans le futur.")
        if value < MIN_DATE:
            raise ValueError(f"La date ne peut pas être antérieure au {MIN_DATE:%d/%m/%Y}.")
        return value


class TimeEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    account_id: int
    account: AccountRead
    date: date_type
    duration_hours: float
    description: str
    created_at: datetime
    github_issue_id: int | None
    github_issue: GithubIssueRead | None
    sprint_id: int | None
    sprint: SprintRead | None
    category_id: int | None
    category: CategoryRead | None


class HoursOverTimePoint(BaseModel):
    period: date_type
    hours: float


class HoursOverTime(BaseModel):
    granularity: str
    points: list[HoursOverTimePoint]


class RecentTimeEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    account_email: str
    date: date_type
    duration_hours: float
    description: str


class ProjectStats(BaseModel):
    total_hours: float
    contributor_count: int
    entry_count: int
    average_hours_per_contributor: float


class HoursByIssueItem(BaseModel):
    issue_number: int
    issue_title: str
    issue_url: str
    hours: float


class HoursByIssue(BaseModel):
    items: list[HoursByIssueItem]
    unattached_hours: float


class AccountHours(BaseModel):
    account_id: int
    account_email: str
    hours: float


class SprintStats(BaseModel):
    sprint: SprintRead
    total_hours: float
    hours_by_account: list[AccountHours]
    hours_by_issue: HoursByIssue
    role_assignments: list[SprintRoleAssignmentRead] = Field(default_factory=list)


class HoursByCategoryItem(BaseModel):
    category_id: int
    category_name: str
    hours: float


class HoursByCategory(BaseModel):
    items: list[HoursByCategoryItem]
    unattached_hours: float


class ReportCreate(BaseModel):
    type: ReportType
    sprint_id: int | None = None
    meeting_date: date_type

    @field_validator("meeting_date")
    @classmethod
    def date_within_bounds(cls, value: date_type) -> date_type:
        if not MIN_DATE <= value <= MAX_SPRINT_DATE:
            raise ValueError(f"La date doit être comprise entre {MIN_DATE:%d/%m/%Y} et {MAX_SPRINT_DATE:%d/%m/%Y}.")
        return value


class ReportUpdate(BaseModel):
    sprint_id: int | None = None
    meeting_date: date_type
    content: dict
    # Version lue avant modification : refusée (409) si quelqu'un a enregistré
    # entre-temps, pour ne pas écraser silencieusement son travail.
    version: int

    @field_validator("meeting_date")
    @classmethod
    def date_within_bounds(cls, value: date_type) -> date_type:
        if not MIN_DATE <= value <= MAX_SPRINT_DATE:
            raise ValueError(f"La date doit être comprise entre {MIN_DATE:%d/%m/%Y} et {MAX_SPRINT_DATE:%d/%m/%Y}.")
        return value


class ReportSummary(BaseModel):
    id: int
    project_id: int
    type: str
    sprint_id: int | None
    sprint_name: str | None
    meeting_date: date_type
    created_by_label: str | None
    updated_at: datetime
    updated_by_label: str | None


class TeamMember(BaseModel):
    account_id: int
    label: str
    email: str
    roles: list[str]


class DailyEntryRead(BaseModel):
    account_id: int
    done: str
    todo: str
    blockers: str
    updated_at: datetime
    updated_by_label: str | None


class DailyEntryUpdate(BaseModel):
    done: CleanStr = Field(default="", max_length=5000)
    todo: CleanStr = Field(default="", max_length=5000)
    blockers: CleanStr = Field(default="", max_length=5000)


class ReportRead(ReportSummary):
    content: dict
    version: int
    team: list[TeamMember]
    daily_entries: list[DailyEntryRead]
    can_delete: bool


class SuggestedUserStories(BaseModel):
    user_stories: list[dict]
    source_label: str | None


class DocumentSettings(BaseModel):
    footer: CleanStr = Field(default="", max_length=255)


class DocumentSettingsRead(DocumentSettings):
    logos: list[str]


class LogoUpload(BaseModel):
    # Image encodée en base64 (sans le préfixe "data:...;base64,").
    data_base64: str = Field(min_length=1, max_length=2_000_000)
