FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim AS runtime

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./
COPY floorcast/ ./floorcast/
COPY migrations/ ./migrations/
COPY alembic.ini ./
COPY main.py ./

RUN uv sync --no-dev

ENV PATH="/app/.venv/bin:$PATH"

COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

EXPOSE 8000

CMD ["python", "main.py"]
