import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.database.db import get_session, make_engine
from app.database.models import Task
from app.main import create_app
from seed import seed_demo


@pytest.fixture
def database(tmp_path):
    engine = make_engine(tmp_path / "test.db")
    yield engine
    engine.dispose()


@pytest.fixture
def client(database):
    app = create_app(database)

    def test_session():
        with Session(database) as session:
            yield session

    app.dependency_overrides[get_session] = test_session
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def payload(client):
    return {
        "title": "Сдать отчёт по базам данных",
        "student_id": client.get("/students").json()[0]["id"],
        "subject_id": client.get("/subjects").json()[0]["id"],
        "due_date": "2026-12-01",
        "priority": "Высокий",
    }


def test_get_list(client):
    response = client.get("/tasks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 5


def test_create_and_read(client, payload):
    response = client.post("/tasks", json=payload)
    assert response.status_code == 201
    task = response.json()
    assert isinstance(task["id"], int)
    assert task["status"] == "К выполнению"
    assert all(task[key] == value for key, value in payload.items())
    assert client.get(f"/tasks/{task['id']}").json() == task


def test_patch_persists_only_requested_fields(client, payload):
    old = client.post("/tasks", json=payload).json()
    url = f"/tasks/{old['id']}"
    change = {"due_date": "2026-12-08"}
    assert client.patch(url, json=change).status_code == 200
    assert client.get(url).json() == old | change
    assert client.patch(url, json={"status": "Выполнена"}).json()["status"] == "Выполнена"


def test_combined_filters(client, payload):
    original = client.post("/tasks", json=payload).json()
    # Каждый сосед отличается ровно по одному критерию.
    for difference in [
        {"student_id": 2}, {"subject_id": 2}, {"status": "В работе"},
        {"due_date": "2026-11-30"}, {"due_date": "2026-12-02"}, {"title": "Сдать проект"},
    ]:
        assert client.post("/tasks", json=payload | difference).status_code == 201
    params = dict(student_id=1, subject_id=1, status="К выполнению",
                  due_from="2026-12-01", due_to="2026-12-01", search="ОТЧЁТ")
    assert client.get("/tasks", params=params).json() == [original]
    assert client.get("/tasks", params={"search": "%"}).json() == []
    assert client.get("/tasks", params={"due_from": "2026-12-02", "due_to": "2026-12-01"}).status_code == 422


def test_delete_then_404(client, payload, database):
    task_id = client.post("/tasks", json=payload).json()["id"]
    url = f"/tasks/{task_id}"
    assert client.delete(url).status_code == 204
    assert client.get(url).status_code == 404
    assert client.patch(url, json={"priority": "Низкий"}).status_code == 404
    assert client.delete(url).status_code == 404
    with Session(database) as session:
        assert session.get(Task, task_id) is None


@pytest.mark.parametrize("invalid", [
    {"title": "  "}, {"status": "готово"}, {"priority": "!"}, {"subject_id": 999},
    {"student_id": 999}, {"due_date": "завтра"}, {"id": 5},
])
def test_create_invalid(client, payload, invalid):
    assert client.post("/tasks", json=payload | invalid).status_code == 422


def test_required_fields(client):
    assert client.post("/tasks", json={}).status_code == 422


@pytest.mark.parametrize("invalid", [{"due_date": None}, {"title": " "}, {"subject_id": 999}])
def test_bad_patch_keeps_original(client, invalid):
    before = client.get("/tasks/1").json()
    assert client.patch("/tasks/1", json=invalid).status_code == 422
    assert client.get("/tasks/1").json() == before


def test_seed_preserves_user_changes(client, database):
    client.patch("/tasks/1", json={"title": "Моё название"})
    client.delete("/tasks/2")
    assert seed_demo(database) is False
    assert client.get("/tasks/1").json()["title"] == "Моё название"
    assert client.get("/tasks/2").status_code == 404
    with Session(database) as session:
        assert len(session.exec(select(Task)).all()) == 4
