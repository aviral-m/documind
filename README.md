# DocuMind

Chat with your PDFs. DocuMind answers questions grounded in your uploaded documents and cites the exact pages it used.

## Stack

- **Frontend:** React, Vite, TypeScript, Tailwind CSS v4, shadcn/ui, TanStack Query
- **Backend:** FastAPI, SQLAlchemy, Alembic, Python 3.12
- **Database:** Neon (PostgreSQL)

## Project layout

```text
documind/
├─ frontend/   # React + Vite SPA
└─ backend/    # FastAPI API
```

## Setup

All commands are run in Windows Command Prompt (cmd).

### Backend

```bat
cd backend
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements-dev.txt
```

Create `backend/.env` (it is gitignored). Set `DATABASE_URL` to the **pooled** Neon connection string with `sslmode=require`.

```bat
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Frontend

In a second terminal:

```bat
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

## Checks

```bat
REM backend (from backend\ with the venv active)
ruff check .
pytest

REM frontend (from frontend\)
npm.cmd run lint
npx.cmd tsc --noEmit
npm.cmd run build
```

Integration tests need `TEST_DATABASE_URL` pointing at a database that is **not** your main one. Without it, they are skipped.

## Status

Phase 1 (foundation): project layout, configuration, Neon connectivity, health checks, tests.
