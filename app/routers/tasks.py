from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.database.db import get_session
from app.database.models import Status, Student, Subject, Task
from app.schemas import DirectoryEntry, TaskCreate, TaskRead, TaskUpdate

router = APIRouter()
Database = Annotated[Session, Depends(get_session)]


def find_task(session, task_id):
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(404, "Задача с таким ID не найдена.")
    return task


def check_links(session, values):
    for field, model, label in [
        ("student_id", Student, "Студент"), ("subject_id", Subject, "Дисциплина")
    ]:
        if field in values and session.get(model, values[field]) is None:
            raise HTTPException(422, f"{label} с указанным ID отсутствует.")


@router.get("/students", response_model=list[DirectoryEntry], tags=["Справочники"])
def students(session: Database):
    return session.exec(select(Student).order_by(Student.id)).all()


@router.get("/subjects", response_model=list[DirectoryEntry], tags=["Справочники"])
def subjects(session: Database):
    return session.exec(select(Subject).order_by(Subject.id)).all()


@router.get("/tasks", response_model=list[TaskRead], tags=["Задачи"])
def list_tasks(
    session: Database,
    search: str | None = None,
    student_id: int | None = None,
    subject_id: int | None = None,
    status: Status | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
):
    if due_from and due_to and due_from > due_to:
        raise HTTPException(422, "Начало периода позже конца.")
    query = select(Task)
    if search and search.strip():
        query = query.where(func.casefold(Task.title).contains(search.strip().casefold(), autoescape=True))
    if student_id is not None:
        query = query.where(Task.student_id == student_id)
    if subject_id is not None:
        query = query.where(Task.subject_id == subject_id)
    if status is not None:
        query = query.where(Task.status == status)
    if due_from:
        query = query.where(Task.due_date >= due_from)
    if due_to:
        query = query.where(Task.due_date <= due_to)
    return session.exec(query.order_by(Task.due_date, Task.id)).all()


@router.get("/tasks/{id}", response_model=TaskRead, tags=["Задачи"])
def get_task(id: int, session: Database):
    return find_task(session, id)


@router.post("/tasks", response_model=TaskRead, status_code=201, tags=["Задачи"])
def create_task(data: TaskCreate, session: Database):
    check_links(session, data.model_dump())
    task = Task.model_validate(data)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.patch("/tasks/{id}", response_model=TaskRead, tags=["Задачи"])
def update_task(id: int, data: TaskUpdate, session: Database):
    task = find_task(session, id)
    changes = data.model_dump(exclude_unset=True)
    check_links(session, changes)
    task.sqlmodel_update(changes)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.delete("/tasks/{id}", status_code=204, tags=["Задачи"])
def delete_task(id: int, session: Database):
    task = find_task(session, id)
    session.delete(task)
    session.commit()
