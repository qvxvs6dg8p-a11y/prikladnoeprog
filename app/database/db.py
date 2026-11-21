import os
from pathlib import Path

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from app.database import models  # Регистрирует таблицы до вызова create_all.

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "database.db"


def make_engine(path):
    engine = create_engine(
        f"sqlite:///{Path(path).as_posix()}",
        connect_args={"check_same_thread": False},
        echo=os.getenv("SQL_ECHO") == "1",
    )

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection, _):
        connection.execute("PRAGMA foreign_keys = ON")
        # Встроенный lower() SQLite учитывает регистр только для латиницы.
        connection.create_function("casefold", 1, str.casefold, deterministic=True)

    return engine


engine = make_engine(os.getenv("DATABASE_PATH", DEFAULT_PATH))


def init_db(bind=engine):
    SQLModel.metadata.create_all(bind)


def get_session():
    with Session(engine) as session:
        yield session
