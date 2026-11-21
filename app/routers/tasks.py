from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database.db import get_session
from app.database.models import Student, Subject, Task
from app.schemas import DirectoryEntry, TaskCreate, TaskRead

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
def list_tasks(session: Database):
    return session.exec(select(Task).order_by(Task.due_date, Task.id)).all()


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
