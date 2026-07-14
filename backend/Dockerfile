FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data ./data

# Writable runtime dir for SQLite (mounted as a volume in compose).
RUN mkdir -p /app/runtime

ENV COACH_DB_PATH=/app/runtime/coach.db
ENV COACH_PROBLEMS_PATH=/app/data/problems.json

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
