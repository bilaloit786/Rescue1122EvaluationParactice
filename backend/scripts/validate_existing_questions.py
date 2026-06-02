import asyncio
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIR)
sys.path.append(str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.models.user import QuestionBank  # noqa: E402
from app.services.question_quality import is_valid_question  # noqa: E402
from scripts.seed_document_question_bank import ensure_question_bank_quality_column  # noqa: E402


async def main() -> None:
    await ensure_question_bank_quality_column()
    async with AsyncSessionLocal() as db:
        rows = await db.execute(select(QuestionBank).order_by(QuestionBank.id))
        questions = rows.scalars().all()

        total = len(questions)
        valid = 0
        flagged = 0

        for row in questions:
            row.is_valid = is_valid_question(row.question or {})
            if row.is_valid:
                valid += 1
            else:
                flagged += 1
            db.add(row)

        await db.commit()

    print(f"Total: {total} | Valid: {valid} | Flagged: {flagged}")


if __name__ == "__main__":
    asyncio.run(main())
