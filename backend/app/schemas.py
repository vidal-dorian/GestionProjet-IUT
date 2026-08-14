from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=5000)


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
    labels: list[str] = Field(default_factory=list)


class GithubIssueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int
    title: str
    state: str
    labels: list[str]
    url: str


class GithubSyncResult(BaseModel):
    synced_at: datetime
    issue_count: int


class SprintCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    start_date: date_type
    end_date: date_type

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


class TeamRoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


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
    name: str = Field(min_length=1, max_length=80)


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
    is_admin: bool
    created_at: datetime


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
    description: str = Field(min_length=1, max_length=2000)
    github_issue_id: int | None = None
    sprint_id: int | None = None
    category_id: int | None = None

    @field_validator("description")
    @classmethod
    def description_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("La description est obligatoire.")
        return value.strip()


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
