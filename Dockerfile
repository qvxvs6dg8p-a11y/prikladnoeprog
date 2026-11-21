FROM python:3.11-slim
WORKDIR /planner
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements/backend.txt requirements/backend.txt
RUN pip install --no-cache-dir -r requirements/backend.txt
COPY app/__init__.py app/main.py app/schemas.py app/
COPY app/database app/database
COPY app/routers app/routers
COPY seed.py .
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
