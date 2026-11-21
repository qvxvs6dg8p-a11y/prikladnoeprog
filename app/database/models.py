from datetime import date
from enum import Enum

from sqlmodel import Field, Relationship, SQLModel


class Priority(str, Enum):
    low = "Низкий"
    normal = "Средний"
    high = "Высокий"


class Status(str, Enum):
    open = "К выполнению"
    active = "В работе"
    done = "Выполнена"


class Student(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    tasks: list["Task"] = Relationship(back_populates="student")


class Subject(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    tasks: list["Task"] = Relationship(back_populates="subject")


class Task(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    description: str = ""
    student_id: int = Field(foreign_key="student.id", index=True)
    subject_id: int = Field(foreign_key="subject.id", index=True)
    due_date: date = Field(index=True)
    priority: Priority = Priority.normal
    status: Status = Status.open

    student: Student = Relationship(back_populates="tasks")
    subject: Subject = Relationship(back_populates="tasks")
