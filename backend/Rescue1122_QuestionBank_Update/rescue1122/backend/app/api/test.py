from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, not_, update
from datetime import datetime
from typing import List
import random

from app.core.database import get_db
from app.core.security import require_staff
from app.models.user import User, TestAttempt, StaffProfile, QuestionBank, StaffSeenQuestion
from app.schemas.schemas import GenerateQuestionsRequest, SubmitTestRequest, TestAttemptOut, TestAttemptSummary
from app.services.ai_service import generate_questions as ai_generate, generate_feedback
from app.services.email_service import send_result_email

router = APIRouter(prefix="/api/test", tags=["test"])

TOPIC_LABELS = {
    "fire_basics":         "Fire Chemistry & Causes",
    "ppe":                 "Personal Protective Equipment",
    "fire_suppression":    "Fire Suppression & Tactics",
    "fire_vehicles":       "Fire Vehicles & Equipment",
    "building_safety":     "Building Safety Regulations 2022",
    "ropes_knots":         "Ropes & Rescue Knots",
    "rope_rescue":         "Rope Rescue Techniques",
    "vehicle_extrication": "Vehicle Extrication",
    "ics":                 "Incident Command System",
    "disaster_response":   "Disaster Response Operations",
    "first_aid_rescue":    "First Aid & Rescue Basics",
    "fire_risk":           "Fire Risk Assessment",
}

DIFFICULTY_MIX = [("easy", 8), ("medium", 12), ("hard", 5)]


async def _get_unseen(db, user_id, topic_id, difficulty, count):
    seen_subq = (
        select(StaffSeenQuestion.question_id)
        .where(StaffSeenQuestion.user_id == user_id)
        .scalar_subquery()
    )
    result = await db.execute(
        select(QuestionBank)
        .where(
            QuestionBank.topic_id   == topic_id,
            QuestionBank.difficulty == difficulty,
            not_(QuestionBank.id.in_(seen_subq))
        )
        .order_by(func.random())
        .limit(count)
    )
    return result.scalars().all()


async def _reset_seen(db, user_id, topic_id):
    topic_ids = select(QuestionBank.id).where(QuestionBank.topic_id == topic_id)
    await db.execute(
        delete(StaffSeenQuestion).where(
            StaffSeenQuestion.user_id == user_id,
            StaffSeenQuestion.question_id.in_(topic_ids)
        )
    )
    await db.commit()


async def _serve_from_bank(db, user_id, topic_id):
    total = await db.scalar(
        select(func.count(QuestionBank.id)).where(QuestionBank.topic_id == topic_id)
    )
    if not total or total < 25:
        return None

    questions = []
    for difficulty, count in DIFFICULTY_MIX:
        qs = await _get_unseen(db, user_id, topic_id, difficulty, count)
        if len(qs) < count:
            await _reset_seen(db, user_id, topic_id)
            qs = await _get_unseen(db, user_id, topic_id, difficulty, count)
        questions.extend(qs)

    random.shuffle(questions)

    for q in questions:
        db.add(StaffSeenQuestion(user_id=user_id, question_id=q.id))
        await db.execute(
            update(QuestionBank)
            .where(QuestionBank.id == q.id)
            .values(times_served=QuestionBank.times_served + 1)
        )
    await db.commit()

    return [
        {
            "q":         q.question,
            "opts":      [q.option_a, q.option_b, q.option_c, q.option_d],
            "ans":       q.correct_ans,
            "topic":     q.subtopic or "General",
            "bank_id":   q.id,
            "difficulty": q.difficulty,
            "source":    q.source_doc or "",
        }
        for q in questions
    ]


@router.post("/generate")
async def generate(
    payload: GenerateQuestionsRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db)
):
    topic_label = TOPIC_LABELS.get(payload.topic_id, payload.topic_id)

    questions = await _serve_from_bank(db, current_user.id, payload.topic_id)
    source = "question_bank"

    if questions is None:
        try:
            questions = await ai_generate(payload.topic_id, topic_label, payload.designation)
            source = "ai_live"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Question generation failed: {str(e)}")

    return {"questions": questions, "topic_label": topic_label, "source": source, "total": len(questions)}


@router.post("/submit", response_model=TestAttemptOut)
async def submit_test(
    payload: SubmitTestRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db)
):
    questions  = payload.questions
    answer_map = {a.q_index: a.selected for a in payload.answers}

    correct_count   = 0
    subtopic_scores = {}

    for i, q in enumerate(questions):
        selected   = answer_map.get(i, -1)
        is_correct = (selected == q.get("ans", -1))
        if is_correct:
            correct_count += 1

        subtopic = q.get("topic", "General")
        if subtopic not in subtopic_scores:
            subtopic_scores[subtopic] = {"correct": 0, "total": 0}
        subtopic_scores[subtopic]["total"] += 1
        if is_correct:
            subtopic_scores[subtopic]["correct"] += 1

        bank_id = q.get("bank_id")
        if bank_id and not is_correct:
            await db.execute(
                update(QuestionBank)
                .where(QuestionBank.id == bank_id)
                .values(times_wrong=QuestionBank.times_wrong + 1)
            )

    for topic, data in subtopic_scores.items():
        data["percent"] = round(
            (data["correct"] / data["total"] * 100) if data["total"] > 0 else 0, 1
        )

    total     = len(questions)
    score_pct = round((correct_count / total * 100), 1) if total > 0 else 0
    passed    = score_pct >= 60
    weak_topics = [t for t, d in subtopic_scores.items() if d["percent"] < 60]

    profile_res = await db.execute(
        select(StaffProfile).where(StaffProfile.user_id == current_user.id)
    )
    profile     = profile_res.scalar_one_or_none()
    staff_name  = profile.full_name   if profile else current_user.username
    designation = profile.designation if profile else "Staff"
    district    = profile.district    if profile else "Unknown"

    feedback = await generate_feedback(
        staff_name=staff_name, designation=designation, district=district,
        topic_label=payload.topic_label, correct=correct_count, total=total,
        score_pct=score_pct, passed=passed, weak_topics=weak_topics
    )

    started_at = None
    try:
        started_at = datetime.fromisoformat(payload.started_at.replace("Z", "+00:00"))
    except Exception:
        pass

    attempt = TestAttempt(
        user_id=current_user.id, topic_id=payload.topic_id,
        topic_label=payload.topic_label, total_questions=total,
        correct_answers=correct_count, score_percent=score_pct, passed=passed,
        time_taken_seconds=payload.time_taken_seconds,
        answers=[
            {"q_index": a.q_index, "selected": a.selected,
             "correct": questions[a.q_index].get("ans", -1) if a.q_index < len(questions) else -1}
            for a in payload.answers
        ],
        questions=questions, subtopic_scores=subtopic_scores,
        ai_feedback=feedback, started_at=started_at, email_sent=False,
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)

    if current_user.email:
        sent = await send_result_email(
            to_email=current_user.email, staff_name=staff_name,
            designation=designation, district=district, topic=payload.topic_label,
            score_pct=score_pct, correct=correct_count, total=total,
            passed=passed, feedback=feedback,
        )
        if sent:
            attempt.email_sent = True
            await db.commit()

    return attempt


@router.get("/history", response_model=List[TestAttemptSummary])
async def get_history(current_user: User = Depends(require_staff), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TestAttempt).where(TestAttempt.user_id == current_user.id)
        .order_by(TestAttempt.completed_at.desc()).limit(50)
    )
    return result.scalars().all()


@router.get("/attempt/{attempt_id}", response_model=TestAttemptOut)
async def get_attempt(attempt_id: int, current_user: User = Depends(require_staff), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TestAttempt).where(TestAttempt.id == attempt_id, TestAttempt.user_id == current_user.id)
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    return attempt


@router.get("/bank/stats")
async def bank_stats(current_user: User = Depends(require_staff), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(QuestionBank.topic_label, QuestionBank.difficulty, func.count(QuestionBank.id).label("count"))
        .group_by(QuestionBank.topic_label, QuestionBank.difficulty)
        .order_by(QuestionBank.topic_label)
    )
    stats = {}
    for row in result.all():
        if row.topic_label not in stats:
            stats[row.topic_label] = {"easy": 0, "medium": 0, "hard": 0, "total": 0}
        stats[row.topic_label][row.difficulty] = row.count
        stats[row.topic_label]["total"] += row.count
    return stats
