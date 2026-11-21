from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, StringConstraints, model_validator

from app.database.models import Priority, Status


Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
Description = Annotated[str, Field(max_length=3000)]


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title
    description: Description = ""
    student_id: PositiveInt
    subject_id: PositiveInt
    due_date: date
    priority: Priority = Priority.normal
    status: Status = Status.open


class TaskRead(TaskCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class DirectoryEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title | None = None
    description: Description | None = None
    student_id: PositiveInt | None = None
    subject_id: PositiveInt | None = None
    due_date: date | None = None
    priority: Priority | None = None
    status: Status | None = None

    @model_validator(mode="after")
    def reject_explicit_nulls(self):
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"Поле {field} не может быть null.")
        return self
