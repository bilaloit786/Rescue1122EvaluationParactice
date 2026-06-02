from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, Integer as SAInteger, String, or_
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.question_topics import QUESTION_TOPIC_LABELS
from app.core.security import require_admin, get_password_hash
from app.models.user import User, StaffProfile, TestAttempt, QuestionBank, ActivityLog, MasterTestPaper
from app.schemas.schemas import UserOut, AdminCreateStaffRequest, AdminUpdateStaffRequest, StatsResponse, TestAttemptOut, MasterPaperGenerateRequest
from app.services.activity_service import get_request_access_details, log_activity
from app.services.export_service import generate_excel_report, generate_pdf_report, generate_staff_pdf_report, generate_attempt_pdf_report

router = APIRouter(prefix="/api/admin", tags=["admin"])

QUESTION_BANK_LABELS = QUESTION_TOPIC_LABELS
MASTER_PAPER_FIELDS = ("fire", "rescue", "building")


def _serialize_user(user: User, latest_access: dict | None = None) -> dict:
    profile = user.profile
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else "",
        "updated_at": user.updated_at.isoformat() if user.updated_at else "",
        "profile": {
            "full_name": profile.full_name if profile else "",
            "father_name": profile.father_name if profile else "",
            "designation": profile.designation if profile else "",
            "district": profile.district if profile else "",
            "station": profile.station if profile else "",
            "employee_id": profile.employee_id if profile else "",
            "phone": profile.phone if profile else "",
        } if profile else None,
        "access": latest_access or {},
    }


def _activity_access_payload(entry: ActivityLog | None) -> dict:
    if not entry:
        return {}
    details = entry.details or {}
    return {
        "action": entry.action,
        "ip_address": details.get("ip_address") or "Unknown",
        "location": details.get("location") or "Unknown",
        "user_agent": details.get("user_agent") or "Unknown",
        "created_at": entry.created_at.isoformat() if entry.created_at else "",
    }


def _question_field(topic_id: str) -> str:
    if topic_id.startswith("fire_"):
        return "fire"
    if topic_id.startswith("rescue_"):
        return "rescue"
    if topic_id.startswith("building_"):
        return "building"
    return "other"


def _paper_question(item: QuestionBank) -> dict:
    question = item.question or {}
    options = question.get("opts") or question.get("options") or []
    if isinstance(options, dict):
        options = [options.get(letter, "") for letter in ("A", "B", "C", "D")]
    return {
        "id": item.id,
        "bank_question_id": item.id,
        "topic_id": item.topic_id,
        "topic": QUESTION_BANK_LABELS.get(item.topic_id, item.topic_id.replace("_", " ").title()),
        "field": _question_field(item.topic_id),
        "difficulty": item.difficulty,
        "question": question.get("q") or question.get("question") or "",
        "q": question.get("q") or question.get("question") or "",
        "options": options,
        "opts": options,
        "answer_index": question.get("ans"),
        "ans": question.get("ans"),
        "explanation": question.get("explanation") or "",
    }


def _paper_summary(paper: MasterTestPaper) -> dict:
    return {
        "id": paper.id,
        "title": paper.title,
        "total_questions": paper.total_questions,
        "easy_count": paper.easy_count,
        "medium_count": paper.medium_count,
        "hard_count": paper.hard_count,
        "created_by_name": paper.created_by_name,
        "created_at": paper.created_at.isoformat() if paper.created_at else "",
    }


def _paper_detail(paper: MasterTestPaper) -> dict:
    payload = _paper_summary(paper)
    payload["questions"] = paper.questions or []
    return payload


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    total_staff = await db.scalar(select(func.count(User.id)).where(User.role == "staff"))
    total_tests = await db.scalar(select(func.count(TestAttempt.id)))
    passed_tests = await db.scalar(select(func.count(TestAttempt.id)).where(TestAttempt.passed == True))
    avg_score = await db.scalar(select(func.avg(TestAttempt.score_percent))) or 0

    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    tests_this_month = await db.scalar(
        select(func.count(TestAttempt.id)).where(TestAttempt.completed_at >= month_start)
    )

    # District breakdown
    district_rows = await db.execute(
        select(StaffProfile.district, func.count(TestAttempt.id).label("tests"),
               func.avg(TestAttempt.score_percent).label("avg_score"))
        .join(User, User.id == StaffProfile.user_id)
        .join(TestAttempt, TestAttempt.user_id == User.id)
        .group_by(StaffProfile.district)
        .order_by(desc("tests"))
        .limit(20)
    )
    district_breakdown = [
        {"district": r.district, "tests": r.tests, "avg_score": round(r.avg_score or 0, 1)}
        for r in district_rows
    ]

    # Topic breakdown
    topic_rows = await db.execute(
        select(TestAttempt.topic_label,
               func.count(TestAttempt.id).label("total"),
               func.sum(func.cast(TestAttempt.passed, SAInteger)).label("passed"),
               func.avg(TestAttempt.score_percent).label("avg_score"))
        .group_by(TestAttempt.topic_label)
        .order_by(desc("total"))
    )
    topic_breakdown = [
        {"topic": r.topic_label, "total": r.total, "passed": int(r.passed or 0),
         "avg_score": round(r.avg_score or 0, 1)}
        for r in topic_rows
    ]

    question_bank_rows = await db.execute(
        select(
            QuestionBank.topic_id,
            func.count(QuestionBank.id).label("total"),
            func.sum(func.cast(QuestionBank.is_valid == True, SAInteger)).label("valid"),
            func.sum(func.cast(QuestionBank.is_valid == False, SAInteger)).label("flagged"),
            func.sum(func.cast(QuestionBank.difficulty == "easy", SAInteger)).label("easy"),
            func.sum(func.cast(QuestionBank.difficulty == "medium", SAInteger)).label("medium"),
            func.sum(func.cast(QuestionBank.difficulty == "hard", SAInteger)).label("hard"),
        )
        .group_by(QuestionBank.topic_id)
        .order_by(QuestionBank.topic_id)
    )
    question_bank_breakdown = [
        {
            "topic_id": r.topic_id,
            "topic": QUESTION_BANK_LABELS.get(r.topic_id, r.topic_id.replace("_", " ").title()),
            "total": r.total,
            "valid": int(r.valid or 0),
            "flagged": int(r.flagged or 0),
            "easy": int(r.easy or 0),
            "medium": int(r.medium or 0),
            "hard": int(r.hard or 0),
        }
        for r in question_bank_rows
    ]

    # Recent attempts
    recent_rows = await db.execute(
        select(TestAttempt, StaffProfile)
        .join(User, User.id == TestAttempt.user_id)
        .outerjoin(StaffProfile, StaffProfile.user_id == User.id)
        .order_by(desc(TestAttempt.completed_at))
        .limit(10)
    )
    recent_attempts = []
    for attempt, profile in recent_rows:
        recent_attempts.append({
            "id": attempt.id,
            "staff_name": profile.full_name if profile else "Unknown",
            "district": profile.district if profile else "",
            "designation": profile.designation if profile else "",
            "topic": attempt.topic_label,
            "score": attempt.score_percent,
            "passed": attempt.passed,
            "date": attempt.completed_at.isoformat() if attempt.completed_at else "",
        })

    activity_rows = await db.execute(
        select(ActivityLog)
        .order_by(desc(ActivityLog.created_at))
        .limit(30)
    )
    activity_log = [
        {
            "id": entry.id,
            "action": entry.action,
            "entity_type": entry.entity_type,
            "entity_id": entry.entity_id,
            "actor_name": entry.actor_name,
            "description": entry.description,
            "details": entry.details or {},
            "created_at": entry.created_at.isoformat() if entry.created_at else "",
        }
        for entry in activity_rows.scalars().all()
    ]

    return StatsResponse(
        total_staff=total_staff or 0,
        total_tests=total_tests or 0,
        pass_rate=round((passed_tests / total_tests * 100) if total_tests else 0, 1),
        avg_score=round(float(avg_score), 1),
        tests_this_month=tests_this_month or 0,
        district_breakdown=district_breakdown,
        topic_breakdown=topic_breakdown,
        question_bank_breakdown=question_bank_breakdown,
        recent_attempts=recent_attempts,
        activity_log=activity_log,
    )


@router.get("/leaderboard")
async def leaderboard(
    district: Optional[str] = None,
    topic: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin)
):
    q = (
        select(
            User.id.label("user_id"),
            User.username,
            User.email,
            StaffProfile.full_name,
            StaffProfile.designation,
            StaffProfile.district,
            func.count(TestAttempt.id).label("total_tests"),
            func.avg(TestAttempt.score_percent).label("avg_score"),
            func.sum(func.cast(TestAttempt.passed, SAInteger)).label("total_passed"),
        )
        .join(User, User.id == StaffProfile.user_id)
        .join(TestAttempt, TestAttempt.user_id == User.id)
        .group_by(User.id, User.username, User.email, StaffProfile.full_name, StaffProfile.designation, StaffProfile.district)
        .order_by(desc("avg_score"))
        .limit(limit)
    )
    if district:
        q = q.where(StaffProfile.district == district)
    if topic:
        q = q.where(TestAttempt.topic_label.ilike(f"%{topic}%"))

    rows = await db.execute(q)
    return [
        {
            "rank": i + 1,
            "user_id": r.user_id,
            "username": r.username,
            "email": r.email,
            "name": r.full_name,
            "designation": r.designation,
            "district": r.district,
            "avg_score": round(float(r.avg_score or 0), 1),
            "total_tests": r.total_tests,
            "total_passed": int(r.total_passed or 0),
        }
        for i, r in enumerate(rows)
    ]


@router.get("/attempts")
async def get_all_attempts(
    district: Optional[str] = None,
    topic: Optional[str] = None,
    passed: Optional[bool] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin)
):
    q = (
        select(TestAttempt, StaffProfile)
        .join(User, User.id == TestAttempt.user_id)
        .outerjoin(StaffProfile, StaffProfile.user_id == User.id)
        .order_by(desc(TestAttempt.completed_at))
        .limit(limit).offset(offset)
    )
    if district:
        q = q.where(StaffProfile.district == district)
    if topic:
        q = q.where(TestAttempt.topic_label.ilike(f"%{topic}%"))
    if passed is not None:
        q = q.where(TestAttempt.passed == passed)

    rows = await db.execute(q)
    result = []
    for attempt, profile in rows:
        result.append({
            "id": attempt.id,
            "user_id": attempt.user_id,
            "user": {"profile": {
                "full_name": profile.full_name if profile else "",
                "father_name": profile.father_name if profile else "",
                "designation": profile.designation if profile else "",
                "district": profile.district if profile else "",
                "station": profile.station if profile else "",
                "employee_id": profile.employee_id if profile else "",
            }} if profile else {},
            "topic_label": attempt.topic_label,
            "score_percent": attempt.score_percent,
            "correct_answers": attempt.correct_answers,
            "total_questions": attempt.total_questions,
            "passed": attempt.passed,
            "time_taken_seconds": attempt.time_taken_seconds,
            "ai_feedback": attempt.ai_feedback,
            "subtopic_scores": attempt.subtopic_scores,
            "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else "",
        })
    return result


@router.get("/export/excel")
async def export_excel(
    district: Optional[str] = None,
    topic: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin)
):
    attempts = await get_all_attempts(district=district, topic=topic, limit=5000, offset=0, db=db, _=_)
    excel_bytes = generate_excel_report(attempts)
    filename = f"rescue1122_results_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/pdf")
async def export_pdf(
    district: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin)
):
    attempts = await get_all_attempts(district=district, limit=1000, offset=0, db=db, _=_)
    pdf_bytes = generate_pdf_report(attempts, title=f"Staff Evaluation Report — {district or 'All Districts'}")
    filename = f"rescue1122_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


async def _get_attempt_detail_payload(attempt_id: int, db: AsyncSession):
    row = await db.execute(
        select(TestAttempt, User, StaffProfile)
        .join(User, User.id == TestAttempt.user_id)
        .outerjoin(StaffProfile, StaffProfile.user_id == User.id)
        .where(TestAttempt.id == attempt_id)
    )
    result = row.first()
    if not result:
        raise HTTPException(status_code=404, detail="Attempt not found")

    attempt, user, profile = result
    return {
        "id": attempt.id,
        "user_id": attempt.user_id,
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else "",
            "profile": {
                "full_name": profile.full_name if profile else "",
                "father_name": profile.father_name if profile else "",
                "designation": profile.designation if profile else "",
                "district": profile.district if profile else "",
                "station": profile.station if profile else "",
                "employee_id": profile.employee_id if profile else "",
                "phone": profile.phone if profile else "",
            } if profile else {},
        },
        "topic_id": attempt.topic_id,
        "topic_label": attempt.topic_label,
        "score_percent": attempt.score_percent,
        "correct_answers": attempt.correct_answers,
        "total_questions": attempt.total_questions,
        "passed": attempt.passed,
        "time_taken_seconds": attempt.time_taken_seconds,
        "ai_feedback": attempt.ai_feedback,
        "subtopic_scores": attempt.subtopic_scores,
        "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else "",
    }


@router.get("/attempts/{attempt_id}/details")
async def get_attempt_details(
    attempt_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin)
):
    return await _get_attempt_detail_payload(attempt_id, db)


@router.get("/attempts/{attempt_id}/pdf")
async def export_attempt_pdf(
    attempt_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin)
):
    attempt = await _get_attempt_detail_payload(attempt_id, db)
    profile = attempt.get("user", {}).get("profile", {}) or {}
    name = profile.get("full_name") or attempt.get("user", {}).get("username", "staff")
    safe_name = "".join(ch for ch in name.lower().replace(" ", "_") if ch.isalnum() or ch == "_")
    pdf_bytes = generate_attempt_pdf_report(attempt)
    filename = f"rescue1122_attempt_{safe_name}_{attempt_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/districts/{district}/details")
async def get_district_details(
    district: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin)
):
    attempts = await get_all_attempts(district=district, limit=500, offset=0, db=db, _=_)
    staff_count = await db.scalar(
        select(func.count(User.id))
        .join(StaffProfile, StaffProfile.user_id == User.id)
        .where(User.role == "staff", StaffProfile.district == district)
    )
    total_tests = len(attempts)
    passed_tests = sum(1 for attempt in attempts if attempt.get("passed"))
    avg_score = sum(float(attempt.get("score_percent") or 0) for attempt in attempts) / total_tests if total_tests else 0
    topic_map = {}
    for attempt in attempts:
        label = attempt.get("topic_label") or "Unknown"
        topic_map.setdefault(label, {"topic": label, "total": 0, "passed": 0, "score_total": 0})
        topic_map[label]["total"] += 1
        topic_map[label]["passed"] += 1 if attempt.get("passed") else 0
        topic_map[label]["score_total"] += float(attempt.get("score_percent") or 0)

    topics = [
        {
            "topic": item["topic"],
            "total": item["total"],
            "passed": item["passed"],
            "avg_score": round(item["score_total"] / item["total"], 1) if item["total"] else 0,
        }
        for item in topic_map.values()
    ]
    topics.sort(key=lambda item: item["total"], reverse=True)

    return {
        "district": district,
        "stats": {
            "staff_count": staff_count or 0,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "pass_rate": round((passed_tests / total_tests * 100) if total_tests else 0, 1),
            "avg_score": round(avg_score, 1),
        },
        "topics": topics,
        "recent_attempts": attempts[:10],
    }


@router.get("/districts/{district}/pdf")
async def export_district_pdf(
    district: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin)
):
    attempts = await get_all_attempts(district=district, limit=5000, offset=0, db=db, _=_)
    pdf_bytes = generate_pdf_report(attempts, title=f"District Performance Report - {district}")
    safe_district = "".join(ch for ch in district.lower().replace(" ", "_") if ch.isalnum() or ch == "_")
    filename = f"rescue1122_district_{safe_district}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/staff")
async def list_staff(
    district: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin)
):
    q = select(User).where(User.role == "staff").order_by(User.created_at.desc())
    if district:
        q = q.join(StaffProfile, StaffProfile.user_id == User.id).where(StaffProfile.district == district)
    rows = await db.execute(q)
    users = rows.scalars().all()

    user_ids = [user.id for user in users]
    access_by_user = {}
    if user_ids:
        access_rows = await db.execute(
            select(ActivityLog)
            .where(
                ActivityLog.entity_id.in_(user_ids),
                ActivityLog.action.in_(["login_success", "user_registered", "staff_created"]),
            )
            .order_by(desc(ActivityLog.created_at))
        )
        for entry in access_rows.scalars().all():
            if entry.entity_id not in access_by_user:
                access_by_user[entry.entity_id] = _activity_access_payload(entry)

    return [_serialize_user(user, access_by_user.get(user.id)) for user in users]


@router.get("/activity-log")
async def activity_log(
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin)
):
    rows = await db.execute(
        select(ActivityLog)
        .order_by(desc(ActivityLog.created_at))
        .limit(limit)
    )
    return [
        {
            "id": entry.id,
            "action": entry.action,
            "entity_type": entry.entity_type,
            "entity_id": entry.entity_id,
            "actor_name": entry.actor_name,
            "description": entry.description,
            "details": entry.details or {},
            "created_at": entry.created_at.isoformat() if entry.created_at else "",
        }
        for entry in rows.scalars().all()
    ]


@router.get("/question-bank")
async def list_question_bank(
    topic_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    search: Optional[str] = None,
    is_valid: Optional[bool] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin)
):
    filters = []
    if topic_id:
        filters.append(QuestionBank.topic_id == topic_id)
    if difficulty:
        filters.append(QuestionBank.difficulty == difficulty)
    if is_valid is not None:
        filters.append(QuestionBank.is_valid.is_(is_valid))
    if search:
        like = f"%{search.strip()}%"
        filters.append(QuestionBank.question.cast(String).ilike(like))

    total_query = select(func.count(QuestionBank.id))
    rows_query = select(QuestionBank).order_by(QuestionBank.topic_id, QuestionBank.difficulty, QuestionBank.id)
    if filters:
        total_query = total_query.where(*filters)
        rows_query = rows_query.where(*filters)

    total = await db.scalar(total_query) or 0
    rows = await db.execute(rows_query.limit(limit).offset(offset))

    topic_rows = await db.execute(
        select(
            QuestionBank.topic_id,
            func.count(QuestionBank.id).label("total"),
        )
        .group_by(QuestionBank.topic_id)
        .order_by(QuestionBank.topic_id)
    )
    topics = [
        {
            "topic_id": row.topic_id,
            "topic": QUESTION_BANK_LABELS.get(row.topic_id, row.topic_id.replace("_", " ").title()),
            "total": row.total,
        }
        for row in topic_rows
    ]

    items = []
    for item in rows.scalars().all():
        question = item.question or {}
        items.append({
            "id": item.id,
            "topic_id": item.topic_id,
            "topic": QUESTION_BANK_LABELS.get(item.topic_id, item.topic_id.replace("_", " ").title()),
            "difficulty": item.difficulty,
            "question": question.get("q") or question.get("question") or "",
            "options": question.get("opts") or question.get("options") or [],
            "answer_index": question.get("ans"),
            "explanation": question.get("explanation") or "",
            "is_valid": item.is_valid,
            "times_served": item.times_served or 0,
            "times_wrong": item.times_wrong or 0,
        })

    return {
        "items": items,
        "topics": topics,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


async def _difficulty_candidates(db: AsyncSession, difficulty: str) -> list[QuestionBank]:
    rows = await db.execute(
        select(QuestionBank)
        .where(QuestionBank.difficulty == difficulty)
        .where(QuestionBank.is_valid.is_(True))
        .order_by(func.random())
    )
    return rows.scalars().all()


@router.post("/master-papers")
async def generate_master_paper(
    payload: MasterPaperGenerateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    quotas = {
        "easy": payload.easy_count,
        "medium": payload.medium_count,
        "hard": payload.hard_count,
    }
    candidates = {
        difficulty: await _difficulty_candidates(db, difficulty)
        for difficulty in quotas
    }

    selected: list[QuestionBank] = []
    selected_ids: set[int] = set()

    def add_question(item: QuestionBank) -> None:
        selected.append(item)
        selected_ids.add(item.id)
        quotas[item.difficulty] -= 1

    # Ensure the official paper includes Fire, Rescue, and Building.
    for field in MASTER_PAPER_FIELDS:
        candidate = next(
            (item for item in candidates["easy"] if item.id not in selected_ids and _question_field(item.topic_id) == field),
            None,
        )
        if not candidate:
            raise HTTPException(status_code=409, detail=f"Not enough easy questions available for {field}")
        add_question(candidate)

    for difficulty, remaining in list(quotas.items()):
        if remaining <= 0:
            continue
        for item in candidates[difficulty]:
            if quotas[difficulty] <= 0:
                break
            if item.id in selected_ids:
                continue
            add_question(item)
        if quotas[difficulty] > 0:
            raise HTTPException(status_code=409, detail=f"Not enough {difficulty} questions available")

    fields = {_question_field(item.topic_id) for item in selected}
    if not set(MASTER_PAPER_FIELDS).issubset(fields):
        raise HTTPException(status_code=409, detail="Generated paper must include Fire, Rescue, and Building questions")

    paper_questions = [_paper_question(item) for item in selected]
    paper = MasterTestPaper(
        title=payload.title.strip(),
        total_questions=len(paper_questions),
        easy_count=payload.easy_count,
        medium_count=payload.medium_count,
        hard_count=payload.hard_count,
        questions=paper_questions,
        created_by_id=current_admin.id,
        created_by_name=current_admin.username,
    )
    db.add(paper)
    await db.flush()
    await log_activity(
        db,
        action="master_paper_created",
        entity_type="master_test_paper",
        entity_id=paper.id,
        actor=current_admin,
        description=f"{current_admin.username} generated master paper '{paper.title}'",
        details={
            "title": paper.title,
            "easy_count": paper.easy_count,
            "medium_count": paper.medium_count,
            "hard_count": paper.hard_count,
            **get_request_access_details(request),
        },
    )
    await db.commit()
    await db.refresh(paper)
    return _paper_detail(paper)


@router.get("/master-papers")
async def list_master_papers(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    rows = await db.execute(
        select(MasterTestPaper)
        .where(MasterTestPaper.is_active.is_(True))
        .order_by(desc(MasterTestPaper.created_at), desc(MasterTestPaper.id))
        .limit(50)
    )
    return [_paper_summary(paper) for paper in rows.scalars().all()]


@router.get("/master-papers/{paper_id}")
async def get_master_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    paper = await db.get(MasterTestPaper, paper_id)
    if not paper or not paper.is_active:
        raise HTTPException(status_code=404, detail="Master paper not found")
    return _paper_detail(paper)


@router.delete("/master-papers/{paper_id}")
async def delete_master_paper(
    paper_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    paper = await db.get(MasterTestPaper, paper_id)
    if not paper or not paper.is_active:
        raise HTTPException(status_code=404, detail="Master paper not found")
    paper.is_active = False
    await log_activity(
        db,
        action="master_paper_deleted",
        entity_type="master_test_paper",
        entity_id=paper.id,
        actor=current_admin,
        description=f"{current_admin.username} deleted master paper '{paper.title}'",
        details={"title": paper.title, **get_request_access_details(request)},
    )
    await db.commit()
    return {"message": "Deleted"}


async def _get_staff_detail_payload(user_id: int, db: AsyncSession):
    result = await db.execute(select(User).where(User.id == user_id, User.role == "staff"))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Staff not found")

    attempts_rows = await db.execute(
        select(TestAttempt)
        .where(TestAttempt.user_id == user.id)
        .order_by(desc(TestAttempt.completed_at))
    )
    attempts = []
    for attempt in attempts_rows.scalars().all():
        attempts.append({
            "id": attempt.id,
            "topic_label": attempt.topic_label,
            "score_percent": attempt.score_percent,
            "correct_answers": attempt.correct_answers,
            "total_questions": attempt.total_questions,
            "passed": attempt.passed,
            "time_taken_seconds": attempt.time_taken_seconds,
            "ai_feedback": attempt.ai_feedback,
            "subtopic_scores": attempt.subtopic_scores,
            "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else "",
        })

    total_tests = len(attempts)
    passed_tests = sum(1 for attempt in attempts if attempt["passed"])
    avg_score = sum(float(attempt["score_percent"] or 0) for attempt in attempts) / total_tests if total_tests else 0
    best_score = max((float(attempt["score_percent"] or 0) for attempt in attempts), default=0)

    activity_rows = await db.execute(
        select(ActivityLog)
        .where(
            or_(ActivityLog.entity_id == user.id, ActivityLog.actor_id == user.id),
            ActivityLog.action.in_(["login_success", "login_failed", "user_registered", "staff_created", "staff_updated"]),
        )
        .order_by(desc(ActivityLog.created_at))
        .limit(30)
    )
    activity = []
    latest_access = {}
    for entry in activity_rows.scalars().all():
        payload = _activity_access_payload(entry)
        activity.append({
            "id": entry.id,
            "action": entry.action,
            "description": entry.description,
            "created_at": entry.created_at.isoformat() if entry.created_at else "",
            **payload,
        })
        if not latest_access and entry.action in ("login_success", "user_registered", "staff_created"):
            latest_access = payload

    return {
        "staff": _serialize_user(user, latest_access),
        "stats": {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "pass_rate": round((passed_tests / total_tests * 100) if total_tests else 0, 1),
            "avg_score": round(avg_score, 1),
            "best_score": round(best_score, 1),
        },
        "attempts": attempts,
        "activity": activity,
    }


@router.get("/staff/{user_id}/details")
async def get_staff_details(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin)
):
    return await _get_staff_detail_payload(user_id, db)


@router.get("/staff/{user_id}/pdf")
async def export_staff_pdf(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin)
):
    payload = await _get_staff_detail_payload(user_id, db)
    profile = payload["staff"].get("profile") or {}
    name = profile.get("full_name") or payload["staff"].get("username", "staff")
    safe_name = "".join(ch for ch in name.lower().replace(" ", "_") if ch.isalnum() or ch == "_")
    pdf_bytes = generate_staff_pdf_report(payload["staff"], payload["attempts"], payload["stats"])
    filename = f"rescue1122_staff_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/staff", response_model=UserOut, status_code=201)
async def create_staff(
    payload: AdminCreateStaffRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    existing = await db.execute(
        select(User).where((User.email == payload.email) | (User.username == payload.username))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email or username already exists")

    user = User(
        email=payload.email, username=payload.username,
        hashed_password=get_password_hash(payload.password), role="staff"
    )
    db.add(user)
    await db.flush()
    profile = StaffProfile(
        user_id=user.id, full_name=payload.full_name, father_name=payload.father_name,
        designation=payload.designation, district=payload.district, station=payload.station,
        employee_id=payload.employee_id, phone=payload.phone
    )
    db.add(profile)
    await log_activity(
        db,
        action="staff_created",
        entity_type="staff",
        entity_id=user.id,
        actor=current_admin,
        description=f"{payload.full_name} was added by admin",
        details={
            "username": payload.username,
            "designation": payload.designation,
            "district": payload.district,
            **get_request_access_details(request),
        },
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.put("/staff/{user_id}", response_model=UserOut)
async def update_staff(
    user_id: int,
    payload: AdminUpdateStaffRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    result = await db.execute(select(User).where(User.id == user_id, User.role == "staff"))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Staff not found")

    if payload.email or payload.username:
        duplicate_conditions = []
        if payload.email:
            duplicate_conditions.append(User.email == payload.email)
        if payload.username:
            duplicate_conditions.append(User.username == payload.username)
        duplicate = await db.execute(
            select(User).where(
                User.id != user_id,
                or_(*duplicate_conditions)
            )
        )
        if duplicate.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email or username already exists")

    changed_fields = []
    for field in ("email", "username", "is_active"):
        value = getattr(payload, field)
        if value is not None and getattr(user, field) != value:
            setattr(user, field, value)
            changed_fields.append(field)

    if payload.password:
        user.hashed_password = get_password_hash(payload.password)
        changed_fields.append("password")

    if not user.profile:
        user.profile = StaffProfile(user_id=user.id, full_name=payload.full_name or user.username, designation=payload.designation or "OTHER", district=payload.district or "")

    for field in ("full_name", "father_name", "designation", "district", "station", "employee_id", "phone"):
        value = getattr(payload, field)
        if value is not None and getattr(user.profile, field) != value:
            setattr(user.profile, field, value)
            changed_fields.append(field)

    if changed_fields:
        await log_activity(
            db,
            action="staff_updated",
            entity_type="staff",
            entity_id=user.id,
            actor=current_admin,
            description=f"{user.profile.full_name if user.profile else user.username} profile was updated",
            details={"username": user.username, "changed_fields": changed_fields, **get_request_access_details(request)},
        )

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/staff/{user_id}")
async def delete_staff(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    result = await db.execute(select(User).where(User.id == user_id, User.role == "staff"))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Staff not found")
    name = user.profile.full_name if user.profile else user.username
    await log_activity(
        db,
        action="staff_deleted",
        entity_type="staff",
        entity_id=user.id,
        actor=current_admin,
        description=f"{name} account was deleted",
        details={"username": user.username, "email": user.email, **get_request_access_details(request)},
    )
    await db.delete(user)
    await db.commit()
    return {"message": "Deleted"}
