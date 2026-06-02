import argparse
import asyncio
import json
import os
import sqlite3
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import psycopg2
from psycopg2.extras import Json, execute_values
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import Base
from app.models import user  # noqa: F401


TABLE_ORDER = [
    "users",
    "staff_profiles",
    "question_bank",
    "test_attempts",
    "activity_logs",
    "staff_seen_questions",
    "active_test_questions",
]

JSON_COLUMNS = {
    "question_bank": {"question"},
    "test_attempts": {"answers", "questions", "subtopic_scores"},
    "activity_logs": {"details"},
}

BOOL_COLUMNS = {
    "users": {"is_active"},
    "test_attempts": {"passed", "email_sent"},
}


def normalize_database_url(url: str, *, async_driver: bool) -> str:
    if async_driver:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgresql+asyncpg://"):
            parts = urlsplit(url)
            query = dict(parse_qsl(parts.query, keep_blank_values=True))
            if query.pop("sslmode", None):
                query.setdefault("ssl", "require")
            query.pop("channel_binding", None)
            return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
        return url

    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url


def sqlite_counts(sqlite_path: Path) -> dict[str, int]:
    with sqlite3.connect(sqlite_path) as conn:
        cursor = conn.cursor()
        return {
            table: cursor.execute(f"select count(*) from {table}").fetchone()[0]
            for table in TABLE_ORDER
            if cursor.execute(
                "select 1 from sqlite_master where type='table' and name=?",
                (table,),
            ).fetchone()
        }


def convert_value(table: str, column: str, value):
    if column in BOOL_COLUMNS.get(table, set()) and value is not None:
        return bool(value)
    if column in JSON_COLUMNS.get(table, set()) and value is not None:
        if isinstance(value, str):
            value = json.loads(value)
        return Json(value)
    return value


def copy_table(sqlite_conn, pg_conn, table: str) -> int:
    sqlite_conn.row_factory = sqlite3.Row
    rows = sqlite_conn.execute(f"select * from {table}").fetchall()
    if not rows:
        return 0

    columns = rows[0].keys()
    quoted_columns = ", ".join(f'"{column}"' for column in columns)
    values = [
        tuple(convert_value(table, column, row[column]) for column in columns)
        for row in rows
    ]

    with pg_conn.cursor() as cursor:
        cursor.execute(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE')
        execute_values(
            cursor,
            f'INSERT INTO "{table}" ({quoted_columns}) VALUES %s',
            values,
            page_size=1000,
        )
    return len(rows)


def pg_counts(pg_conn) -> dict[str, int]:
    with pg_conn.cursor() as cursor:
        counts = {}
        for table in TABLE_ORDER:
            cursor.execute("select to_regclass(%s)", (table,))
            if cursor.fetchone()[0]:
                cursor.execute(f'select count(*) from "{table}"')
                counts[table] = cursor.fetchone()[0]
        return counts


async def create_postgres_schema(database_url: str) -> None:
    engine = create_async_engine(
        normalize_database_url(database_url, async_driver=True),
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_timeout=30,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


def reset_sequences(pg_conn) -> None:
    with pg_conn.cursor() as cursor:
        for table in ("users", "staff_profiles", "question_bank", "test_attempts", "activity_logs"):
            cursor.execute(
                """
                select setval(
                    pg_get_serial_sequence(%s, 'id'),
                    coalesce((select max(id) from "%s"), 1),
                    (select count(*) from "%s") > 0
                )
                """ % ("%s", table, table),
                (table,),
            )


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", default="test.db")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    database_url = os.environ["NEON_DATABASE_URL"]
    sqlite_path = Path(args.sqlite).resolve()
    if not sqlite_path.exists():
        raise SystemExit(f"SQLite database not found: {sqlite_path}")

    source_counts = sqlite_counts(sqlite_path)
    print("SQLite counts:", source_counts)
    if args.dry_run:
        return

    await create_postgres_schema(database_url)

    pg_url = normalize_database_url(database_url, async_driver=False)
    with sqlite3.connect(sqlite_path) as sqlite_conn, psycopg2.connect(pg_url) as pg_conn:
        pg_conn.autocommit = False
        copied = {}
        try:
            for table in TABLE_ORDER:
                if table in source_counts:
                    copied[table] = copy_table(sqlite_conn, pg_conn, table)
            reset_sequences(pg_conn)
            pg_conn.commit()
        except Exception:
            pg_conn.rollback()
            raise

        target_counts = pg_counts(pg_conn)
    print("Copied counts:", copied)
    print("PostgreSQL counts:", target_counts)
    if source_counts != target_counts:
        raise SystemExit("Source and target row counts do not match")


if __name__ == "__main__":
    asyncio.run(main())
