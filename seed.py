from datetime import date, timedelta

from sqlalchemy import text
from sqlmodel import Session, select

from app.database.db import engine, init_db
from app.database.models import Priority, Status, Student, Subject, Task


def seed_demo(bind=engine):
    init_db(bind)
    with Session(bind) as session:
        # Проверка и вставка проходят в одной транзакции с блокировкой записи.
        session.execute(text("BEGIN IMMEDIATE"))
        if session.exec(select(Student.id).limit(1)).first() is not None:
            return False

        students = [Student(name=name) for name in
                    ["Нурболат Арайлым", "Алихан Серик", "Дана Омарова"]]
        subjects = [Subject(name=name) for name in
                    ["Базы данных", "Программирование", "Математический анализ"]]
        session.add_all(students + subjects)
        session.flush()  # SQLite уже выдала id, транзакция ещё не завершена.
        examples = [
            (0, 0, "Построить ER-диаграмму", "Проверить ключи и связи трёх таблиц.", 1, Priority.high, Status.active),
            (0, 1, "Разобрать циклы", "Решить три задачи на циклы.", -2, Priority.normal, Status.open),
            (0, 2, "Сдать интегралы", "Прикрепить решения варианта 4.", -3, Priority.low, Status.done),
            (1, 1, "Написать тесты API", "Проверить чтение и создание записи.", 4, Priority.normal, Status.open),
            (2, 0, "Подготовить SQL-запросы", "Составить выборку с JOIN.", 0, Priority.high, Status.active),
        ]
        for student, subject, title, description, days, priority, status in examples:
            session.add(Task(
                title=title, description=description, student_id=students[student].id,
                subject_id=subjects[subject].id, due_date=date.today() + timedelta(days=days),
                priority=priority, status=status,
            ))
        session.commit()
        return True


if __name__ == "__main__":
    if seed_demo():
        print("Созданы 3 студента, 3 дисциплины и 5 задач.")
    else:
        print("База уже заполнена. Сохранены все существующие данные.")
