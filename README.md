# KnowledgeHub

> AI-powered personal knowledge platform — learn by building it from scratch.

KnowledgeHub is a learning-focused AI engineering project that implements a full pipeline from raw document ingestion to LLM-generated answers with citations, built explicitly and incrementally without unnecessary frameworks.

## Current Milestone

**Milestone 0 — Project Foundation** ✅

The foundation is in place: full-stack dev environment, PostgreSQL + pgvector, FastAPI health endpoint, React landing page, and a working test suite.

---

## Architecture

```
Browser
  │
  │  HTTP (port 5173 in dev)
  ▼
React + TypeScript (Vite)
  │
  │  HTTP (port 8000)
  ▼
FastAPI + Uvicorn (Python 3.12)
  │
  │  TCP (port 5432)
  ▼
PostgreSQL 17 + pgvector (Docker)
```

No API gateway, no extra service layer, no ORMs, no external vector stores.

---

## Technology Stack

| Layer    | Technology                         |
|----------|------------------------------------|
| Frontend | React 19, TypeScript, Vite         |
| Backend  | Python 3.12, FastAPI, asyncpg      |
| Database | PostgreSQL 17, pgvector            |
| Testing  | pytest + pytest-asyncio, Vitest    |
| Infra    | Docker Compose                     |

---

## Project Structure

```
KnowledgeHub/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py       ← pydantic-settings, all config from env vars
│   │   ├── database.py     ← asyncpg pool, connectivity check
│   │   └── main.py         ← FastAPI app, lifespan, /health route
│   ├── tests/
│   │   ├── test_health.py  ← /health endpoint tests
│   │   └── test_database.py← DB connectivity tests
│   ├── .env.example        ← copy to .env, fill secrets
│   ├── pyproject.toml      ← project metadata + pytest config
│   └── requirements.txt    ← pinned Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx         ← KnowledgeHub landing page
│   │   ├── App.css         ← dark-mode styles
│   │   ├── main.tsx        ← React entry point
│   │   └── test/
│   │       ├── setup.ts    ← jest-dom setup
│   │       └── App.test.tsx← Vitest smoke tests
│   ├── .env.example        ← copy to .env with VITE_API_BASE_URL
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts      ← Vite + Vitest config
│
├── database/
│   └── init/
│       └── 01_enable_pgvector.sql  ← auto-runs on first container start
│
├── docs/                   ← ADRs and milestone notes (future)
├── .gitignore
├── docker-compose.yml
└── README.md
```

---

## Prerequisites

| Tool          | Version   | Notes                           |
|---------------|-----------|---------------------------------|
| Node.js       | ≥ 18      | v20 LTS recommended             |
| Python        | 3.12      | Use `py -3.12` on Windows       |
| Docker        | ≥ 24      | Docker Desktop on Mac/Windows   |
| Docker Compose| ≥ 2.20    | Bundled with Docker Desktop     |
| Git           | any       |                                 |

---

## Setup & Running

### 1 — Clone and configure environment

```bash
git clone <repo-url>
cd KnowledgeHub

# Backend config
cp backend/.env.example backend/.env
# Edit backend/.env if needed (defaults work with docker-compose as-is)

# Frontend config (optional in dev — defaults to localhost:8000)
cp frontend/.env.example frontend/.env
```

### 2 — Start PostgreSQL + pgvector

```bash
docker compose up -d

# Verify the container is healthy
docker compose ps

# Check that pgvector was enabled on first start
docker compose logs db | grep -i pgvector
```

Expected: container status `healthy`, logs show pgvector version.

### 3 — Start the backend

```bash
cd backend

# Create and activate virtual environment (first time only)
py -3.12 -m venv .venv          # Windows
# python3.12 -m venv .venv       # macOS / Linux

# Activate
.venv\Scripts\activate           # Windows PowerShell
# source .venv/bin/activate       # macOS / Linux

# Install dependencies (first time only)
pip install -r requirements.txt

# Run dev server
uvicorn app.main:app --reload
```

Backend runs at **http://localhost:8000**  
Swagger UI: **http://localhost:8000/docs**

### 4 — Start the frontend

```bash
cd frontend
npm install        # first time only
npm run dev
```

Frontend runs at **http://localhost:5173**

---

## Running Tests

### Backend tests

```bash
cd backend
.venv\Scripts\activate           # or source .venv/bin/activate

# All tests (health tests run without DB; DB tests skip gracefully if DB is down)
pytest

# Health tests only (no Docker required)
pytest tests/test_health.py -v

# Database connectivity tests (requires docker compose up -d)
pytest tests/test_database.py -v
```

### Frontend tests

```bash
cd frontend

# Run once
npm run test

# Watch mode (re-runs on file changes)
npm run test:watch

# Interactive browser UI
npm run test:ui
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable           | Default                                                                          | Description                      |
|--------------------|----------------------------------------------------------------------------------|----------------------------------|
| `APP_ENV`          | `development`                                                                    | Application environment          |
| `APP_DEBUG`        | `true`                                                                           | Enable debug mode                |
| `DATABASE_URL`     | `postgresql://knowledgehub:knowledgehub_dev_password@localhost:5432/knowledgehub`| Full asyncpg connection string   |
| `POSTGRES_HOST`    | `localhost`                                                                      | Postgres host                    |
| `POSTGRES_PORT`    | `5432`                                                                           | Postgres port                    |
| `POSTGRES_USER`    | `knowledgehub`                                                                   | Postgres user                    |
| `POSTGRES_PASSWORD`| `knowledgehub_dev_password`                                                      | Postgres password (change in prod)|
| `POSTGRES_DB`      | `knowledgehub`                                                                   | Database name                    |

### Frontend (`frontend/.env`)

| Variable            | Default                  | Description              |
|---------------------|--------------------------|--------------------------|
| `VITE_API_BASE_URL` | `http://localhost:8000`  | Backend API base URL     |

> ⚠️ Never commit `.env` files. Only `.env.example` files are safe to commit.

---

## API Reference

### `GET /health`

Returns structured JSON about the application state.

**Response example (DB connected):**
```json
{
  "status": "ok",
  "environment": "development",
  "uptime_seconds": 42.1,
  "database": {
    "connected": true,
    "postgres_version": "PostgreSQL 17.x ...",
    "pgvector_version": "0.8.0",
    "error": null
  }
}
```

**Response example (DB unreachable):**
```json
{
  "status": "ok",
  "environment": "development",
  "uptime_seconds": 1.2,
  "database": {
    "connected": false,
    "postgres_version": null,
    "pgvector_version": null,
    "error": "connection refused"
  }
}
```

---

## Roadmap

| Milestone | Name                         | Status      |
|-----------|------------------------------|-------------|
| 0         | Project Foundation           | ✅ Complete  |
| 1         | Document Ingestion           | 🔜 Next     |
| 2         | Embeddings + Vector Store    | Planned     |
| 3         | Semantic Retrieval           | Planned     |
| 4         | RAG + LLM Answers            | Planned     |
| 5         | Evaluation + Citations       | Planned     |

---

## Development Principles

- **Explicit over implicit** — raw SQL, no ORM, no magic
- **Testable by default** — every endpoint and DB function has tests
- **No unnecessary infrastructure** — no Redis, Kafka, Kubernetes, LangChain etc.
- **Clear failure modes** — connection failures surface with readable messages
- **Incremental** — each milestone is self-contained and runnable
