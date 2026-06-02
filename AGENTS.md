# Project Overview

This is an existing full-stack web application. Continue from the current codebase.

- React/Vite frontend
- FastAPI backend
- PostgreSQL database configured through `backend/.env`
- Preserved SQLite database file at `backend/test.db`
- Frontend located in `/frontend`
- Backend located in `/backend`
- Current frontend package manager is npm, with `frontend/package-lock.json`
- Current backend virtual environment is at project root `.venv`; `backend/.venv` is not present

# Very Important Rules

- Do not start from scratch.
- Do not recreate the React frontend.
- Do not recreate the FastAPI backend.
- Do not delete the database.
- Do not delete `backend/test.db`; it is preserved even though PostgreSQL is now configured.
- Do not print or commit secrets from `backend/.env`.
- Do not delete existing source code.
- Do not overwrite existing UI unless specifically asked.
- Do not reinstall dependencies unless required.
- Always inspect existing files before making changes.
- Continue from the current codebase.

# Folder Structure

Expected structure:

```text
project-root/
├── AGENTS.md
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── node_modules/
│   └── src/
├── backend/
│   ├── main.py
│   ├── app/
│   ├── requirements.txt
│   ├── .env
│   ├── alembic/
│   ├── scripts/
│   ├── tests/
│   └── test.db
└── .gitignore
```

Current observed structure notes:

- `frontend/package.json` exists.
- `frontend/package-lock.json` exists.
- `frontend/node_modules/` exists.
- `backend/main.py` exists.
- `backend/app/` exists.
- `backend/requirements.txt` exists.
- `backend/.env` exists and contains the active database configuration.
- `backend/test.db` exists and must be preserved.
- Project root `.venv/` exists and should be reused.
- `backend/.venv/` does not currently exist.
- `README.md` was not found during inspection.
- `.git/` exists and `git status` works.

# Current App State

- The backend uses SQLAlchemy async sessions.
- `backend/app/core/database.py` normalizes PostgreSQL URLs for `asyncpg`.
- The app has been migrated from SQLite to PostgreSQL/Neon using scripts in `backend/scripts/`.
- The old SQLite file remains at `backend/test.db`.
- The local PostgreSQL database currently keeps the intended active users only: `admin` and `Bilalkho`.
- Frontend branding uses `public/Mono.png` as the circular mono logo and favicon.
- The staff dashboard has a red animated alert border around the examination component.
- The app includes a 5 minute auto-refresh in `frontend/src/App.jsx`.

# Frontend Instructions

- Frontend is inside `/frontend`.
- Use existing React code.
- Run frontend with the command found in `package.json`:

```bash
cd frontend
npm run dev
```

- Only run `npm install` if `node_modules` is missing or package files changed.
- Do not create a new Vite/React project unless the user explicitly asks.

# Backend Instructions

- Backend is inside `/backend`.
- Use existing FastAPI code.
- Use existing database configuration from `backend/.env`.
- Do not print the database URL or API keys.
- `backend/.venv` does not exist; reuse the project root `.venv`.
- Run backend from `/backend` with:

```bash
../.venv/bin/python -m uvicorn main:app --reload
```

- If no usable virtual environment exists, ask before creating a new one.
- Install backend dependencies only when needed:

```bash
../.venv/bin/python -m pip install -r requirements.txt
```

- If the FastAPI app path changes, inspect the backend and use the correct app import path.

# Database Rules

- The active backend database is configured by `DATABASE_URL` in `backend/.env`.
- The current active configuration is PostgreSQL/Neon, not the old local SQLite database.
- Do not reveal the database connection string.
- Do not delete `backend/test.db`.
- Do not reset migrations or tables unless the user clearly asks.
- Before changing database-related code, identify the current database connection configuration.
- If schema changes are needed, explain them first.
- Use the existing migration/helper scripts in `backend/scripts/` when appropriate.

# Dependency Rules

- Do not reinstall packages every session.
- For frontend, check whether `node_modules` exists before running `npm install`.
- For backend, check whether root `.venv` exists before creating any new virtual environment.
- Use existing lock files such as `package-lock.json`.
- Do not change package managers unless asked.

# Testing And Verification

- Frontend build command:

```bash
cd frontend
npm run build
```

- Backend test command from `/backend`:

```bash
../.venv/bin/python -m pytest
```

- Backend tests may require network access when the active `.env` points to PostgreSQL/Neon.
- Do not run destructive database cleanup scripts unless the user explicitly requests it.

# Git Workflow

- Check `git status` before changes.
- Avoid large unrelated edits.
- After meaningful changes, suggest committing work.
- Do not remove `.git`.
- The repository has an initial commit:

```text
4aa1a3c Initial project snapshot with mono branding updates
```

- There are current uncommitted changes from backend hardening, PostgreSQL migration, tests, deployment config, and frontend UI updates.

# Safe Startup Checklist

1. Read `AGENTS.md`.
2. Check `git status`.
3. Inspect `/frontend/package.json`.
4. Inspect `/backend/main.py` and core database config.
5. Confirm `backend/.env` exists without printing secrets.
6. Confirm `backend/test.db` still exists.
7. Start backend from `/backend`.
8. Start frontend from `/frontend`.
9. Continue from the last existing code.

# Commands

Frontend:

```bash
cd frontend
npm run dev
```

Backend using the current project root virtual environment:

```bash
cd backend
../.venv/bin/python -m uvicorn main:app --reload
```

Git save progress:

```bash
git add .
git commit -m "save project progress"
```

# Next-Day Resume Prompt

```text
Resume this existing full-stack project from where we left off.

Do not start a new project.
Do not recreate the React frontend.
Do not recreate the FastAPI backend.
Do not delete the database.
Do not reinstall dependencies unless they are missing.

First read:
- AGENTS.md
- README.md
- frontend/package.json
- backend files
- current git status

Project structure:
- React frontend is inside /frontend
- FastAPI backend is inside /backend
- PostgreSQL database is configured by backend/.env
- backend/test.db still exists and must not be deleted

Your first task is to inspect the existing project and continue from the current codebase. Use existing dependencies and existing files. Only install packages if something is missing or broken.
```
