# Rescue 1122 Evaluation System

Full-stack evaluation and learning platform for Rescue 1122 staff.

The project contains a React/Vite frontend, a FastAPI backend, and a PostgreSQL-backed MCQ question bank. It supports staff registration/login, examinations, results, admin dashboards, user management, learning material PDFs, and admin-generated master papers.

## Project Structure

```text
.
├── frontend/      # React/Vite app
├── backend/       # FastAPI app
├── AGENTS.md      # Local project operating notes
└── .gitignore
```

## Frontend

See `frontend/README.md` for full frontend notes.

Run locally:

```bash
cd frontend
npm install
npm run dev
```

Build:

```bash
cd frontend
npm run build
```

Common environment variable:

```text
VITE_API_URL=https://your-backend.example.com
```

## Backend

See `backend/README.md` for full backend notes.

Run locally from the backend folder:

```bash
cd backend
../.venv/bin/python -m uvicorn main:app --reload
```

Install backend dependencies only when needed:

```bash
cd backend
../.venv/bin/python -m pip install -r requirements.txt
```

Required backend environment variables are documented in `backend/.env.example`.

## Deployment

- Frontend: Vercel, using `frontend/vercel.json`
- Backend: Render, using `backend/render.yaml`
- Database: PostgreSQL configured by backend environment variables

Do not commit real deployment secrets. Add them in the hosting dashboards.

## Security

This repository is safe for public source code when these rules are followed:

- Do not commit `.env` files.
- Do not commit database files such as `.db`, `.sqlite`, or `.sqlite3`.
- Do not commit API keys, database URLs, JWT secrets, passwords, or private keys.
- Use `backend/.env.example` and `frontend/.env.example` only as templates.
- Keep generated build/dependency folders out of Git: `node_modules/`, `.venv/`, `dist/`, and `build/`.

## Useful Commands

Run backend tests:

```bash
cd backend
../.venv/bin/python -m pytest
```

Run frontend build:

```bash
cd frontend
npm run build
```

## Notes

The backend may include scripts for question-bank import, validation, migration, and seeding. Run database-changing scripts carefully and only against the intended database.
