# Rescue 1122 Evaluation Backend

FastAPI backend for the Rescue 1122 Evaluation System. It provides authentication, staff testing, admin management, reporting, and question bank APIs.

## Stack

- FastAPI
- SQLAlchemy async
- PostgreSQL with `asyncpg`
- Alembic migration support
- Pytest test suite

## Setup

Use the existing virtual environment when working in the full project checkout:

```bash
../.venv/bin/python -m pip install -r requirements.txt
```

For a standalone backend checkout, create a virtual environment first:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Create a local `.env` from `.env.example` and fill values in your hosting dashboard or local shell. Never commit `.env`.

## Environment

Required variables:

- `DATABASE_URL`
- `SECRET_KEY`
- `FRONTEND_URL`
- `ALLOWED_HOSTS`

Optional variables:

- `RESEND_API_KEY`
- `EMAIL_FROM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `BCRYPT_ROUNDS`
- `ENVIRONMENT`

## Run Locally

From this folder:

```bash
../.venv/bin/python -m uvicorn main:app --reload
```

For a standalone checkout with a local `.venv`:

```bash
.venv/bin/python -m uvicorn main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Tests

```bash
../.venv/bin/python -m pytest
```

Or in a standalone checkout:

```bash
.venv/bin/python -m pytest
```

## Deployment

`render.yaml` is included for Render deployment. Configure secret environment variables in the Render dashboard. Do not store real keys, database URLs, or credentials in the repository.

Render start command:

```bash
python start.py
```

## Security Notes

- `.env`, database files, Python caches, and generated artifacts are ignored.
- Real database credentials must stay in deployment environment variables.
- Production disables FastAPI docs and adds security headers.
- Login and registration endpoints include rate limiting.
