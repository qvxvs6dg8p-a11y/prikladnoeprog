import os
from datetime import date, timedelta

import requests
import streamlit as st
from st_keyup import st_keyup

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
STATUSES = ["К выполнению", "В работе", "Выполнена"]
PRIORITIES = ["Низкий", "Средний", "Высокий"]

st.set_page_config(page_title="Учебный планировщик", page_icon="📚", layout="wide")


def api(method, path, **kwargs):
    try:
        response = requests.request(method, BASE_URL + path, timeout=5, **kwargs)
        response.raise_for_status()
    except requests.HTTPError as error:
        code = error.response.status_code
        if code == 404:
            st.error("Задача уже удалена. Обновите страницу.")
        elif code == 422:
            st.error("Проверьте название, даты и выбранные значения.")
        else:
            st.error(f"Сервер вернул ошибку {code}. Попробуйте ещё раз.")
        st.stop()
    except requests.RequestException:
        st.error("Не удалось связаться с сервером. Проверьте, запущен ли FastAPI.")
        st.button("Повторить загрузку")
        st.stop()
    if response.status_code != 204:
        return response.json()


def saved(message):
    st.session_state["notice"] = message
    st.rerun()


def deadline_label(task):
    days = (date.fromisoformat(task["due_date"]) - date.today()).days
    if task["status"] == "Выполнена":
        return "Выполнена"
    if days < 0:
        return f"Просрочена · {abs(days)} дн."
    if days == 0:
        return "Сегодня"
    if days == 1:
        return "Завтра"
    return f"Через {days} дн."


def task_form(subjects, student_id, task=None):
    # Ключ формы включает студента и задачу, чтобы поля разных записей не смешивались.
    editing = task is not None
    current = task or {}
    subject_ids = list(subjects)
    form_id = current["id"] if editing else f"new_{st.session_state.get('created_count', 0)}"
    with st.form(f"form_{student_id}_{form_id}"):
        title = st.text_input("Название", value=current.get("title", ""), max_chars=160)
        description = st.text_area("Описание", value=current.get("description", ""), max_chars=3000)
        left, right = st.columns(2)
        subject = left.selectbox("Дисциплина", subject_ids, format_func=subjects.get,
                                 index=subject_ids.index(current.get("subject_id", subject_ids[0])))
        due = right.date_input("Срок сдачи", value=date.fromisoformat(current["due_date"])
                               if editing else date.today() + timedelta(days=1), format="DD.MM.YYYY",
                               min_value=date.min, max_value=date.max)
        priority = left.selectbox("Приоритет", PRIORITIES,
                                  index=PRIORITIES.index(current.get("priority", "Средний")))
        status = right.selectbox("Статус", STATUSES,
                                 index=STATUSES.index(current.get("status", STATUSES[0])))
        submitted = st.form_submit_button("Сохранить изменения" if editing else "Создать задачу",
                                          type="primary")
    if submitted:
        if not title.strip() or due is None:
            st.error("Введите название задачи и выберите срок сдачи.")
            return
        values = dict(title=title.strip(), description=description, subject_id=subject,
                      student_id=student_id, due_date=due.isoformat(), priority=priority, status=status)
        if editing:
            changes = {key: value for key, value in values.items() if value != task[key]}
            if changes:
                api("PATCH", f"/tasks/{task['id']}", json=changes)
            saved(f"Изменения задачи №{task['id']} сохранены.")
        else:
            created = api("POST", "/tasks", json=values)
            st.session_state["created_count"] = st.session_state.get("created_count", 0) + 1
            saved(f"Создана задача №{created['id']}.")


def main():
    st.title("Учебный планировщик")
    students = {row["id"]: row["name"] for row in api("GET", "/students")}
    subjects = {row["id"]: row["name"] for row in api("GET", "/subjects")}
    if not students or not subjects:
        st.info("Для работы нужны студенты и дисциплины. Проверьте заполнение базы.")
        return

    st.sidebar.header("Мой план")
    student = st.sidebar.selectbox("Студент", list(students), format_func=students.get)
    st.sidebar.divider()
    st.sidebar.subheader("Фильтры")
    subject = st.sidebar.selectbox("Дисциплина", [None, *subjects],
                                   format_func=lambda key: subjects.get(key, "Все дисциплины"))
    status = st.sidebar.selectbox("Статус", [None, *STATUSES],
                                  format_func=lambda value: value or "Все статусы")
    start = st.sidebar.date_input("Срок с", value=None, format="DD.MM.YYYY")
    end = st.sidebar.date_input("Срок по", value=None, format="DD.MM.YYYY")

    notice = st.empty()
    if "notice" in st.session_state:
        notice.success(st.session_state.pop("notice"))
    # Обзор показывает весь план студента, даже когда таблица отфильтрована.
    all_tasks = api("GET", "/tasks", params={"student_id": student})
    pending = [task for task in all_tasks if task["status"] != "Выполнена"]
    today = date.today().isoformat()
    late = [task for task in pending if task["due_date"] < today]
    upcoming = [task for task in pending if task["due_date"] >= today]
    a, b, c = st.columns(3)
    a.metric("Открытые задачи", len(pending), border=True)
    b.metric("Просрочены", len(late), border=True)
    c.metric("Выполнены", len(all_tasks) - len(pending), border=True)
    st.subheader("Ближайшие сроки")
    with st.container():
        if upcoming:
            for task in upcoming[:3]:
                with st.container(border=True):
                    due = date.fromisoformat(task["due_date"]).strftime("%d.%m.%Y")
                    st.text(f"{deadline_label(task)}  ·  {due}  ·  {subjects[task['subject_id']]}")
                    st.text(task["title"])
        else:
            st.caption("Предстоящих дедлайнов пока нет.")
        if late:
            st.warning("Самая ранняя просроченная задача — " + late[0]["title"])

    st.subheader("Мои задачи")
    search = st_keyup("Поиск по названию", placeholder="Введите часть названия", debounce=250, key="search_title") or ""
    if start and end and start > end:
        st.warning("Начало периода должно быть раньше конца или совпадать с ним.")
        tasks = []
    else:
        params = dict(student_id=student, subject_id=subject, status=status,
                      search=search.strip() or None, due_from=start, due_to=end)
        tasks = api("GET", "/tasks", params=params)
    if tasks:
        st.dataframe([{
            "№": t["id"], "Задача": t["title"], "Дисциплина": subjects[t["subject_id"]],
            "Срок": date.fromisoformat(t["due_date"]), "Приоритет": t["priority"],
            "Статус": t["status"], "До срока": deadline_label(t),
        } for t in tasks], hide_index=True, width="stretch",
            column_config={"Срок": st.column_config.DateColumn(format="DD.MM.YYYY")})
    else:
        st.info("Задач по выбранным условиям нет. Измените фильтры или добавьте задачу.")

    with st.expander("Добавить задачу", expanded=not all_tasks):
        task_form(subjects, student)
    if tasks:
        st.subheader("Действия с задачей")
        by_id = {t["id"]: t for t in tasks}
        task_id = st.selectbox("Выберите задачу", list(by_id), key=f"choice_{student}",
                               format_func=lambda key: f"№{key} · {by_id[key]['title']}")
        task = by_id[task_id]
        if task["description"]:
            st.text(task["description"])
        if task["status"] != "Выполнена" and st.button("Отметить выполнение"):
            api("PATCH", f"/tasks/{task_id}", json={"status": "Выполнена"})
            saved(f"Задача №{task_id} выполнена.")
        with st.expander("Редактировать задачу"):
            task_form(subjects, student, task)
        with st.expander("Удалить задачу"):
            confirm = st.checkbox(f"Подтверждаю удаление задачи №{task_id}",
                                  key=f"confirm_{student}_{task_id}")
            if st.button("Удалить окончательно", disabled=not confirm):
                api("DELETE", f"/tasks/{task_id}")
                saved(f"Задача №{task_id} удалена.")


main()
