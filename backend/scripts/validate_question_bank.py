import asyncio
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIR)
sys.path.append(str(BACKEND_DIR))

from sqlalchemy import inspect, select, text  # noqa: E402

from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.models.user import QuestionBank  # noqa: E402
from app.services.question_quality import is_valid_question  # noqa: E402


def _has_is_valid_column(sync_conn) -> bool:
    inspector = inspect(sync_conn)
    if "question_bank" not in inspector.get_table_names():
        return True
    return any(column["name"] == "is_valid" for column in inspector.get_columns("question_bank"))


async def ensure_is_valid_column() -> None:
    async with engine.begin() as conn:
        has_column = await conn.run_sync(_has_is_valid_column)
        if has_column:
            return
        default_value = "1" if conn.dialect.name == "sqlite" else "TRUE"
        await conn.execute(text(f"ALTER TABLE question_bank ADD COLUMN is_valid BOOLEAN NOT NULL DEFAULT {default_value}"))


async def main() -> None:
    await ensure_is_valid_column()
    async with AsyncSessionLocal() as db:
        rows = await db.execute(select(QuestionBank).order_by(QuestionBank.id))
        questions = rows.scalars().all()

        total = len(questions)
        valid = 0
        flagged = 0

        for row in questions:
            row_is_valid = is_valid_question(row.question or {})
            row.is_valid = row_is_valid
            if row_is_valid:
                valid += 1
            else:
                flagged += 1
            db.add(row)

        await db.commit()

    print(f"Total: {total} | Valid: {valid} | Flagged: {flagged}")


if __name__ == "__main__":
    asyncio.run(main())
