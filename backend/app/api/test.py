from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.question_topics import QUESTION_TOPIC_LABELS
from app.core.security import require_staff
from app.models.user import User, TestAttempt, StaffProfile, QuestionBank, staff_seen_questions, active_test_questions
from app.schemas.schemas import GenerateQuestionsRequest, SubmitTestRequest, TestAttemptOut, TestAttemptSummary
from app.services.activity_service import log_activity
from app.services.ai_service import generate_feedback
from app.services.email_service import send_result_email
from app.services.question_quality import is_valid_question
from typing import List

router = APIRouter(prefix="/api/test", tags=["test"])
ACTIVE_TEST_RESERVATION_MINUTES = 180

TOPIC_LABELS = QUESTION_TOPIC_LABELS


def _question_text(question: dict) -> str:
    return question.get("q") or question.get("question") or ""


def _question_options(question: dict) -> list:
    return question.get("opts") or question.get("options") or []


def _correct_answer(question: dict) -> int:
    value = question.get("ans", question.get("correct", -1))
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


def _client_question(qb: QuestionBank) -> dict:
    source = qb.question.copy() if isinstance(qb.question, dict) else dict(qb.question or {})
    source.pop("ans", None)
    source.pop("correct", None)
    text = _question_text(source)
    options = _question_options(source)
    source.update({
        "id": qb.id,
        "q": text,
        "question": text,
        "opts": options,
        "options": options,
    })
    return source


@router.post("/generate")
async def generate(
    payload: GenerateQuestionsRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db)
):
    topic_label = TOPIC_LABELS.get(payload.topic_id, payload.topic_id)
    now = datetime.utcnow()
    expires_at = now + timedelta(minutes=ACTIVE_TEST_RESERVATION_MINUTES)

    total_available = await db.scalar(
        select(func.count(QuestionBank.id))
        .where(QuestionBank.topic_id == payload.topic_id)
        .where(QuestionBank.is_valid.is_(True))
    )
    if not total_available:
        raise HTTPException(status_code=404, detail="Topic not found or no questions available")

    await db.execute(delete(active_test_questions).where(active_test_questions.c.expires_at < now))
    await db.execute(delete(active_test_questions).where(active_test_questions.c.user_id == current_user.id))
    
    seen_subquery = select(staff_seen_questions.c.question_id).where(
        staff_seen_questions.c.user_id == current_user.id
    )
    active_subquery = select(active_test_questions.c.question_id).where(
        active_test_questions.c.topic_id == payload.topic_id
    )

    reserved_ids: set[int] = set()

    async def reserve_questions(candidates: list[QuestionBank], needed: int) -> list[QuestionBank]:
        selected = []
        for qb in candidates:
            if len(selected) >= needed or qb.id in reserved_ids:
                continue
            if not is_valid_question(qb.question or {}):
                continue
            await db.execute(
                active_test_questions.insert().values(
                    question_id=qb.id,
                    user_id=current_user.id,
                    topic_id=payload.topic_id,
                    expires_at=expires_at,
                )
            )
            selected.append(qb)
            reserved_ids.add(qb.id)
        return selected

    async def fetch_questions(diff: str, limit: int):
        q = (
            select(QuestionBank)
            .where(QuestionBank.topic_id == payload.topic_id)
            .where(QuestionBank.difficulty == diff)
            .where(QuestionBank.is_valid.is_(True))
            .where(QuestionBank.id.notin_(seen_subquery))
            .where(QuestionBank.id.notin_(active_subquery))
            .order_by(func.random())
            .limit(limit * 4)
        )
        res = await db.execute(q)
        candidates = res.scalars().all()
        return await reserve_questions(candidates, limit)

    easy_qs = await fetch_questions("easy", 10)
    med_qs = await fetch_questions("medium", 10)
    hard_qs = await fetch_questions("hard", 5)
    
    selected_db_qs = easy_qs + med_qs + hard_qs
    
    if len(selected_db_qs) < 25:
        # Fallback if not enough unseen questions
        fallback_limit = 25 - len(selected_db_qs)
        q = (
            select(QuestionBank)
            .where(QuestionBank.topic_id == payload.topic_id)
            .where(QuestionBank.is_valid.is_(True))
            .where(QuestionBank.id.notin_(active_subquery))
            .order_by(func.random())
            .limit(fallback_limit * 4)
        )
        res = await db.execute(q)
        selected_db_qs.extend(await reserve_questions(res.scalars().all(), fallback_limit))

    if len(selected_db_qs) < 25:
        raise HTTPException(
            status_code=409,
            detail="Not enough unique questions are currently available for this topic. Please try another topic or wait for active tests to finish."
        )

    questions = []
    for qb in selected_db_qs:
        questions.append(_client_question(qb))

    if selected_db_qs:
        # Ignore duplicates in seen_questions
        for qb in selected_db_qs:
            try:
                await db.execute(
                    staff_seen_questions.insert().values(user_id=current_user.id, question_id=qb.id)
                )
            except Exception:
                pass # Already seen
        await db.commit()

    return {"questions": questions, "topic_label": topic_label}


@router.post("/submit", response_model=TestAttemptOut)
async def submit_test(
    payload: SubmitTestRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db)
):
    questions = payload.questions
    answer_map = {a.q_index: a.selected for a in payload.answers}
    question_ids = [q.get("id") for q in questions if q.get("id")]
    db_questions: dict[int, QuestionBank] = {}
    if question_ids:
        rows = await db.execute(select(QuestionBank).where(QuestionBank.id.in_(question_ids)))
        db_questions = {item.id: item for item in rows.scalars().all()}

    correct_count = 0
    subtopic_scores: dict = {}
    wrong_topics = []

    for i, q in enumerate(questions):
        selected = answer_map.get(i, -1)
        db_q = db_questions.get(q.get("id")) if q.get("id") else None
        correct_answer = _correct_answer(db_q.question) if db_q else _correct_answer(q)
        is_correct = (selected == correct_answer)
        
        # Update analytics in DB
        if db_q:
            db_q.times_served = (db_q.times_served or 0) + 1
            if not is_correct:
                db_q.times_wrong = (db_q.times_wrong or 0) + 1
            db.add(db_q)

        if is_correct:
            correct_count += 1

        subtopic = q.get("topic") or (db_q.question or {}).get("topic") if db_q else q.get("topic", "General")
        if subtopic not in subtopic_scores:
            subtopic_scores[subtopic] = {"correct": 0, "total": 0}
        subtopic_scores[subtopic]["total"] += 1
        if is_correct:
            subtopic_scores[subtopic]["correct"] += 1

    for topic, data in subtopic_scores.items():
        pct = (data["correct"] / data["total"] * 100) if data["total"] > 0 else 0
        data["percent"] = round(pct, 1)
        if pct < 60:
            wrong_topics.append(topic)

    total = len(questions)
    score_pct = round((correct_count / total * 100), 1) if total > 0 else 0
    passed = score_pct >= 60

    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one()

    profile_result = await db.execute(select(StaffProfile).where(StaffProfile.user_id == current_user.id))
    profile = profile_result.scalar_one_or_none()

    staff_name = profile.full_name if profile else user.username
    designation = profile.designation if profile else "Staff"
    district = profile.district if profile else "Unknown"

    feedback = await generate_feedback(
        staff_name=staff_name,
        designation=designation,
        district=district,
        topic_label=payload.topic_label,
        correct=correct_count,
        total=total,
        score_pct=score_pct,
        passed=passed,
        weak_topics=wrong_topics
    )

    started_at = None
    try:
        started_at = datetime.fromisoformat(payload.started_at.replace("Z", "+00:00"))
    except Exception:
        pass

    attempt = TestAttempt(
        user_id=current_user.id,
        topic_id=payload.topic_id,
        topic_label=payload.topic_label,
        total_questions=total,
        correct_answers=correct_count,
        score_percent=score_pct,
        passed=passed,
        time_taken_seconds=payload.time_taken_seconds,
        answers=[{
            "q_index": a.q_index,
            "selected": a.selected,
            "correct": _correct_answer(db_questions[questions[a.q_index]["id"]].question) if questions[a.q_index].get("id") in db_questions else _correct_answer(questions[a.q_index]),
        } for a in payload.answers if a.q_index < len(questions)],
        questions=questions,
        subtopic_scores=subtopic_scores,
        ai_feedback=feedback,
        started_at=started_at,
        email_sent=False,
    )
    db.add(attempt)
    if question_ids:
        await db.execute(
            delete(active_test_questions).where(
                active_test_questions.c.user_id == current_user.id,
                active_test_questions.c.question_id.in_(question_ids),
            )
        )
    await db.commit()
    await db.refresh(attempt)
    await log_activity(
        db,
        action="test_submitted",
        entity_type="test_attempt",
        entity_id=attempt.id,
        actor=current_user,
        description=f"{staff_name} submitted {payload.topic_label} and scored {score_pct}%",
        details={
            "staff_name": staff_name,
            "topic": payload.topic_label,
            "score_percent": score_pct,
            "passed": passed,
            "correct": correct_count,
            "total": total,
        },
    )
    await db.commit()

    if user.email:
        email_sent = await send_result_email(
            to_email=user.email,
            staff_name=staff_name,
            designation=designation,
            district=district,
            topic=payload.topic_label,
            score_pct=score_pct,
            correct=correct_count,
            total=total,
            passed=passed,
            feedback=feedback,
        )
        if email_sent:
            attempt.email_sent = True
            await db.commit()

    return attempt


@router.get("/history", response_model=List[TestAttemptSummary])
async def get_history(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(TestAttempt)
        .where(TestAttempt.user_id == current_user.id)
        .order_by(TestAttempt.completed_at.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.get("/attempt/{attempt_id}", response_model=TestAttemptOut)
async def get_attempt(
    attempt_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(TestAttempt).where(
            TestAttempt.id == attempt_id,
            TestAttempt.user_id == current_user.id
        )
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    return attempt
