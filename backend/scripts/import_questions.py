import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIR)
sys.path.append(str(BACKEND_DIR))

from sqlalchemy import delete, func, select  # noqa: E402

from app.core.question_topics import QUESTION_TOPIC_LABELS  # noqa: E402
from app.core.database import AsyncSessionLocal, Base, engine  # noqa: E402
from app.models.user import QuestionBank, active_test_questions, staff_seen_questions  # noqa: E402
from app.services.question_quality import is_valid_question  # noqa: E402
from scripts.seed_document_question_bank import ensure_question_bank_quality_column  # noqa: E402


DEFAULT_BANK = BACKEND_DIR / "data" / "question_bank_5500.json"
LABEL_TO_TOPIC_ID = {label: topic_id for topic_id, label in QUESTION_TOPIC_LABELS.items()}


async def import_questions(path: Path, reset: bool = False) -> None:
    questions = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(questions, list):
        raise ValueError("Question file must contain a JSON list.")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_question_bank_quality_column()

    async with AsyncSessionLocal() as db:
        if reset:
            print("Reset enabled: clearing question bank rows, active reservations, and seen-question links.")
            await db.execute(delete(active_test_questions))
            await db.execute(delete(staff_seen_questions))
            await db.execute(delete(QuestionBank))
            await db.commit()

        existing_rows = await db.execute(select(QuestionBank.question))
        existing_ids = {
            row[0].get("id")
            for row in existing_rows.all()
            if isinstance(row[0], dict) and row[0].get("id")
        }

        inserted = 0
        skipped_duplicate = 0
        skipped_invalid = 0

        for question in questions:
            question_id = question.get("id") if isinstance(question, dict) else None
            if not question_id:
                skipped_invalid += 1
                continue
            if question_id in existing_ids:
                skipped_duplicate += 1
                continue
            if not is_valid_question(question):
                skipped_invalid += 1
                continue

            topic_id = (
                question.get("topic_id")
                or LABEL_TO_TOPIC_ID.get(question.get("source_chapter"))
                or LABEL_TO_TOPIC_ID.get(question.get("topic"))
            )
            if not topic_id:
                skipped_invalid += 1
                continue

            db.add(QuestionBank(
                topic_id=topic_id,
                difficulty=question.get("difficulty", "easy"),
                question=question,
                is_valid=True,
            ))
            existing_ids.add(question_id)
            inserted += 1
            if inserted % 250 == 0:
                await db.commit()

        await db.commit()
        total = await db.scalar(select(func.count(QuestionBank.id)))

    print(
        f"Inserted: {inserted} | Duplicate skipped: {skipped_duplicate} | "
        f"Invalid skipped: {skipped_invalid} | Total rows: {total}"
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description="Import generated MCQs into PostgreSQL.")
    parser.add_argument("path", nargs="?", default=str(DEFAULT_BANK), help="Path to question_bank_5500.json")
    parser.add_argument("--reset", action="store_true", help="Replace current question_bank rows before import.")
    args = parser.parse_args()
    await import_questions(Path(args.path), reset=args.reset)


if __name__ == "__main__":
    asyncio.run(main())
