from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=5000)


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime


class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    member_count: int


class MemberCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    pin: str

    @field_validator("pin")
    @classmethod
    def pin_must_be_four_digits(cls, value: str) -> str:
        if not value.isdigit() or len(value) != 4:
            raise ValueError("Le PIN doit être composé de 4 chiffres.")
        return value


class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    project_id: int
    created_at: datetime
    total_hours: float


class MemberLogin(BaseModel):
    pin: str


class SessionMember(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    project_id: int


class TimeEntryCreate(BaseModel):
    date: date_type
    duration_hours: float = Field(gt=0, le=24)
    description: str = Field(min_length=1, max_length=2000)

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
    member_id: int
    date: date_type
    duration_hours: float
    description: str
    created_at: datetime


class HoursOverTimePoint(BaseModel):
    period: date_type
    hours: float


class HoursOverTime(BaseModel):
    granularity: str
    points: list[HoursOverTimePoint]
