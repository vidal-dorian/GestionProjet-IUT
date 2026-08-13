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
