"""
test_all.py — Complete pytest suite for the Rescue 1122 FastAPI backend.

Coverage:
  AUTH  (tests 1–9)   : register, login, /me
  TEST  (tests 10–20) : generate questions, submit, history, attempt
  ADMIN (tests 21–29) : stats, staff CRUD, leaderboard, attempts, exports
"""

import json
import pytest
import pytest_asyncio
from httpx import AsyncClient
from unittest.mock import patch

pytestmark = pytest.mark.skip(reason="Superseded by focused auth/security/admin/exam test modules.")

from tests.conftest import (
    _create_user,
    TestingSessionLocal,
    make_questions,
    SAMPLE_QUESTIONS,
)
from app.core.security import create_access_token, get_password_hash
from app.models.user import User, StaffProfile, TestAttempt

# ─────────────────────────────────────────────────────────────────────────────
#  HELPER — build a valid SubmitTestRequest payload
# ─────────────────────────────────────────────────────────────────────────────

def _submit_payload(
    questions: list,
    n_correct: int,
    correct_idx: int = 0,
) -> dict:
    """
    Build a SubmitTestRequest body.

    `n_correct` of the first `n_correct` answers select the correct option;
    the rest select option 1 (wrong when correct_idx != 1).
    """
    wrong_idx = 1 if correct_idx != 1 else 2
    answers = []
    for i, q in enumerate(questions):
        if i < n_correct:
            answers.append({"q_index": i, "selected": correct_idx})
        else:
            answers.append({"q_index": i, "selected": wrong_idx})
    return {
        "topic_id": "fire_basics",
        "topic_label": "Fire Chemistry & Causes",
        "questions": questions,
        "answers": answers,
        "started_at": "2024-01-01T10:00:00Z",
        "time_taken_seconds": 600,
    }


# ═════════════════════════════════════════════════════════════════════════════
#  AUTH TESTS  (1 – 9)
# ═════════════════════════════════════════════════════════════════════════════

class TestAuth:

    # 1. Successful registration ──────────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_register_success(self, async_client: AsyncClient):
        payload = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "securepass",
            "full_name": "New User",
            "designation": "Firefighter",
            "district": "Lahore",
        }
        resp = await async_client.post("/api/auth/register", json=payload)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["username"] == "newuser"
        assert body["role"] == "staff"
        assert "id" in body

    # 2. Duplicate username ───────────────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, async_client: AsyncClient):
        payload = {
            "email": "first@example.com",
            "username": "dupuser",
            "password": "pass1234",
            "full_name": "First User",
            "designation": "Firefighter",
            "district": "Lahore",
        }
        r1 = await async_client.post("/api/auth/register", json=payload)
        assert r1.status_code == 201

        payload["email"] = "second@example.com"   # different email, same username
        r2 = await async_client.post("/api/auth/register", json=payload)
        assert r2.status_code == 400
        assert "already registered" in r2.json()["detail"].lower()

    # 3. Duplicate email ──────────────────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, async_client: AsyncClient):
        payload = {
            "email": "shared@example.com",
            "username": "userA",
            "password": "pass1234",
            "full_name": "User A",
            "designation": "Firefighter",
            "district": "Lahore",
        }
        r1 = await async_client.post("/api/auth/register", json=payload)
        assert r1.status_code == 201

        payload["username"] = "userB"             # different username, same email
        r2 = await async_client.post("/api/auth/register", json=payload)
        assert r2.status_code == 400

    # 4. Missing required fields → 422 ────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_register_missing_required_fields(self, async_client: AsyncClient):
        payload = {
            "email": "incomplete@example.com",
            "username": "incomplete_user",
            "password": "pass1234",
            # missing full_name and district
        }
        resp = await async_client.post("/api/auth/register", json=payload)
        assert resp.status_code == 422

    # 5. Successful login ─────────────────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_login_success(self, async_client: AsyncClient):
        await _create_user(
            username="loginuser",
            email="loginuser@example.com",
            password="loginpass",
            role="staff",
        )
        resp = await async_client.post(
            "/api/auth/login",
            data={"username": "loginuser", "password": "loginpass"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["role"] in ("staff", "admin")
        assert "user_id" in body

    # 6. Wrong password → 401 ─────────────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, async_client: AsyncClient):
        await _create_user(
            username="wrongpw",
            email="wrongpw@example.com",
            password="correct_password",
            role="staff",
        )
        resp = await async_client.post(
            "/api/auth/login",
            data={"username": "wrongpw", "password": "wrong_password"},
        )
        assert resp.status_code == 401

    # 7. Non-existent user → 401 ──────────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/api/auth/login",
            data={"username": "ghost_user", "password": "whatever"},
        )
        assert resp.status_code == 401

    # 8. GET /me with valid token ──────────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_get_me_authenticated(
        self, async_client: AsyncClient, staff_token: str
    ):
        resp = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "id" in body
        assert "email" in body
        assert "role" in body

    # 9. GET /me without token → 401 ──────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_get_me_unauthenticated(self, async_client: AsyncClient):
        resp = await async_client.get("/api/auth/me")
        assert resp.status_code == 401


# ═════════════════════════════════════════════════════════════════════════════
#  TEST / EXAM TESTS  (10 – 20)
# ═════════════════════════════════════════════════════════════════════════════

class TestExam:

    # 10. Generate questions — valid topic ────────────────────────────────────
    @pytest.mark.asyncio
    async def test_generate_questions_valid_topic(
        self, async_client: AsyncClient, staff_token: str
    ):
        resp = await async_client.post(
            "/api/test/generate",
            json={"topic_id": "fire_basics", "designation": "Firefighter"},
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "questions" in body
        assert len(body["questions"]) == 25
        assert "topic_label" in body

    # 11. Generate questions — unknown topic (falls back gracefully) ──────────
    @pytest.mark.asyncio
    async def test_generate_questions_invalid_topic(
        self, async_client: AsyncClient, staff_token: str
    ):
        resp = await async_client.post(
            "/api/test/generate",
            json={"topic_id": "nonexistent_xyz", "designation": "Firefighter"},
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        # The API either returns questions (with fallback content) or 500 —
        # it must NOT return 422 for an unknown topic_id (it's just a string).
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            assert "questions" in resp.json()

    # 12. Generate questions — unauthenticated → 401 ──────────────────────────
    @pytest.mark.asyncio
    async def test_generate_questions_unauthenticated(
        self, async_client: AsyncClient
    ):
        resp = await async_client.post(
            "/api/test/generate",
            json={"topic_id": "fire_basics", "designation": "Firefighter"},
        )
        assert resp.status_code == 401

    # 13. Submit — all correct → score 100%, passed=True ─────────────────────
    @pytest.mark.asyncio
    async def test_submit_test_all_correct(
        self, async_client: AsyncClient, staff_token: str, sample_questions: list
    ):
        payload = _submit_payload(sample_questions, n_correct=25, correct_idx=0)
        resp = await async_client.post(
            "/api/test/submit",
            json=payload,
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["score_percent"] == 100.0
        assert body["passed"] is True
        assert body["correct_answers"] == 25

    # 14. Submit — all wrong → score 0%, passed=False ─────────────────────────
    @pytest.mark.asyncio
    async def test_submit_test_all_wrong(
        self, async_client: AsyncClient, staff_token: str, sample_questions: list
    ):
        payload = _submit_payload(sample_questions, n_correct=0, correct_idx=0)
        resp = await async_client.post(
            "/api/test/submit",
            json=payload,
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["score_percent"] == 0.0
        assert body["passed"] is False
        assert body["correct_answers"] == 0

    # 15. Submit — 16/25 correct (64%) → passed=True ──────────────────────────
    @pytest.mark.asyncio
    async def test_submit_test_passing_score(
        self, async_client: AsyncClient, staff_token: str, sample_questions: list
    ):
        payload = _submit_payload(sample_questions, n_correct=16, correct_idx=0)
        resp = await async_client.post(
            "/api/test/submit",
            json=payload,
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["score_percent"] == 64.0
        assert body["passed"] is True

    # 16. Submit — 14/25 correct (56%) → passed=False ─────────────────────────
    @pytest.mark.asyncio
    async def test_submit_test_failing_score(
        self, async_client: AsyncClient, staff_token: str, sample_questions: list
    ):
        payload = _submit_payload(sample_questions, n_correct=14, correct_idx=0)
        resp = await async_client.post(
            "/api/test/submit",
            json=payload,
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["score_percent"] == 56.0
        assert body["passed"] is False

    # 17. Submit — some answers = -1 (unanswered) → handled gracefully ────────
    @pytest.mark.asyncio
    async def test_submit_test_unanswered_questions(
        self, async_client: AsyncClient, staff_token: str, sample_questions: list
    ):
        # First 10 answered correctly, rest are unanswered (-1)
        answers = [
            {"q_index": i, "selected": 0 if i < 10 else -1}
            for i in range(len(sample_questions))
        ]
        payload = {
            "topic_id": "fire_basics",
            "topic_label": "Fire Chemistry & Causes",
            "questions": sample_questions,
            "answers": answers,
            "started_at": "2024-01-01T10:00:00Z",
            "time_taken_seconds": 300,
        }
        resp = await async_client.post(
            "/api/test/submit",
            json=payload,
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # -1 never equals ans=0, so only 10 correct
        assert body["correct_answers"] == 10

    # NEW TESTS FOR SCORE CALCULATION EDGE CASES
    # 1. test_score_exactly_60_percent — 15/25 correct → passed=True (boundary)
    @pytest.mark.asyncio
    async def test_score_exactly_60_percent(
        self, async_client: AsyncClient, staff_token: str, sample_questions: list
    ):
        payload = _submit_payload(sample_questions, n_correct=15, correct_idx=0)
        resp = await async_client.post(
            "/api/test/submit",
            json=payload,
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["score_percent"] == 60.0
        assert body["passed"] is True
        assert body["correct_answers"] == 15

    # 2. test_score_59_point_9_percent — 14/25 correct (56%) → passed=False (boundary)
    @pytest.mark.asyncio
    async def test_score_59_point_9_percent(
        self, async_client: AsyncClient, staff_token: str, sample_questions: list
    ):
        payload = _submit_payload(sample_questions, n_correct=14, correct_idx=0)
        resp = await async_client.post(
            "/api/test/submit",
            json=payload,
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["score_percent"] == 56.0
        assert body["passed"] is False

    # 3. test_score_zero — 0/25 correct → score=0.0, passed=False
    @pytest.mark.asyncio
    async def test_score_zero(
        self, async_client: AsyncClient, staff_token: str, sample_questions: list
    ):
        payload = _submit_payload(sample_questions, n_correct=0, correct_idx=0)
        resp = await async_client.post(
            "/api/test/submit",
            json=payload,
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["score_percent"] == 0.0
        assert body["passed"] is False

    # 4. test_score_100 — 25/25 correct → score=100.0, passed=True
    @pytest.mark.asyncio
    async def test_score_100(
        self, async_client: AsyncClient, staff_token: str, sample_questions: list
    ):
        payload = _submit_payload(sample_questions, n_correct=25, correct_idx=0)
        resp = await async_client.post(
            "/api/test/submit",
            json=payload,
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["score_percent"] == 100.0
        assert body["passed"] is True
        assert body["correct_answers"] == 25

    # 5. test_subtopic_scores_computed — verify subtopic_scores dict is built correctly
    @pytest.mark.asyncio
    async def test_subtopic_scores_computed(
        self, async_client: AsyncClient, staff_token: str, sample_questions: list
    ):
        for i in range(10):
            sample_questions[i]["topic"] = "Topic A"
        for i in range(10, 25):
            sample_questions[i]["topic"] = "Topic B"
        
        answers = []
        for i in range(25):
            if i < 5: 
                answers.append({"q_index": i, "selected": 0})
            elif i < 10: 
                answers.append({"q_index": i, "selected": 1})
            elif i < 20: 
                answers.append({"q_index": i, "selected": 0})
            else: 
                answers.append({"q_index": i, "selected": 1})

        payload = {
            "topic_id": "fire_basics",
            "topic_label": "Fire Chemistry",
            "questions": sample_questions,
            "answers": answers,
            "started_at": "2024-01-01T10:00:00Z",
        }
        resp = await async_client.post(
            "/api/test/submit",
            json=payload,
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        
        sub = body["subtopic_scores"]
        assert "Topic A" in sub
        assert sub["Topic A"]["correct"] == 5
        assert sub["Topic A"]["total"] == 10
        assert sub["Topic A"]["percent"] == 50.0
        
        assert "Topic B" in sub
        assert sub["Topic B"]["correct"] == 10
        assert sub["Topic B"]["total"] == 15
        assert sub["Topic B"]["percent"] == 66.7

    # 6. test_weak_topics_identified — topics below 60% appear in the feedback prompt
    @pytest.mark.asyncio
    async def test_weak_topics_identified(
        self, async_client: AsyncClient, staff_token: str, sample_questions: list
    ):
        for i in range(10):
            sample_questions[i]["topic"] = "Weak Topic"
        for i in range(10, 25):
            sample_questions[i]["topic"] = "Strong Topic"
        
        answers = []
        for i in range(25):
            if i < 5: answers.append({"q_index": i, "selected": 0})
            elif i < 10: answers.append({"q_index": i, "selected": 1})
            else: answers.append({"q_index": i, "selected": 0})
        
        payload = {
            "topic_id": "fire_basics",
            "topic_label": "Fire",
            "questions": sample_questions,
            "answers": answers,
            "started_at": "2024-01-01T10:00:00Z",
        }
        
        with patch("app.api.test.generate_feedback", return_value="Feedback") as mock_fb:
            resp = await async_client.post(
                "/api/test/submit",
                json=payload,
                headers={"Authorization": f"Bearer {staff_token}"},
            )
            assert resp.status_code == 200, resp.text
            
            mock_fb.assert_called_once()
            kwargs = mock_fb.call_args.kwargs
            assert "Weak Topic" in kwargs.get("weak_topics", [])
            assert "Strong Topic" not in kwargs.get("weak_topics", [])

    # 7. test_time_taken_saved — time_taken_seconds is stored in the DB correctly
    @pytest.mark.asyncio
    async def test_time_taken_saved(
        self, async_client: AsyncClient, staff_token: str, sample_questions: list
    ):
        payload = _submit_payload(sample_questions, n_correct=25, correct_idx=0)
        payload["time_taken_seconds"] = 1234
        resp = await async_client.post(
            "/api/test/submit",
            json=payload,
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["time_taken_seconds"] == 1234
        
        attempt_id = body["id"]
        resp2 = await async_client.get(
            f"/api/test/attempt/{attempt_id}",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp2.json()["time_taken_seconds"] == 1234

    # 8. test_empty_answers_list — answers=[] submitted, all counted as unanswered (-1)
    @pytest.mark.asyncio
    async def test_empty_answers_list(
        self, async_client: AsyncClient, staff_token: str, sample_questions: list
    ):
        payload = {
            "topic_id": "fire_basics",
            "topic_label": "Fire Chemistry",
            "questions": sample_questions,
            "answers": [],
            "started_at": "2024-01-01T10:00:00Z",
        }
        resp = await async_client.post(
            "/api/test/submit",
            json=payload,
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["correct_answers"] == 0
        assert body["score_percent"] == 0.0
        assert body["passed"] is False

    # 18. GET /history — returns a list ───────────────────────────────────────
    @pytest.mark.asyncio
    async def test_get_history_returns_list(
        self, async_client: AsyncClient, staff_token: str, sample_questions: list
    ):
        # Submit one attempt first
        await async_client.post(
            "/api/test/submit",
            json=_submit_payload(sample_questions, 15),
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        resp = await async_client.get(
            "/api/test/history",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1
        # Each summary should have these keys
        first = body[0]
        for key in ("id", "topic_label", "score_percent", "passed", "completed_at"):
            assert key in first

    # 19. GET /attempt/{id} — own attempt → 200 ───────────────────────────────
    @pytest.mark.asyncio
    async def test_get_attempt_own(
        self, async_client: AsyncClient, staff_token: str, sample_questions: list
    ):
        submit_resp = await async_client.post(
            "/api/test/submit",
            json=_submit_payload(sample_questions, 20),
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        attempt_id = submit_resp.json()["id"]

        resp = await async_client.get(
            f"/api/test/attempt/{attempt_id}",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["id"] == attempt_id

    # 20. GET /attempt/{id} — other user's attempt → 404 ─────────────────────
    @pytest.mark.asyncio
    async def test_get_attempt_other_user(
        self, async_client: AsyncClient, staff_token: str, sample_questions: list
    ):
        # Create a *second* staff user and submit under their token
        other_user = await _create_user(
            username="other_staff",
            email="other@example.com",
            password="otherpass",
            role="staff",
        )
        other_token = create_access_token({"sub": str(other_user.id)})

        submit_resp = await async_client.post(
            "/api/test/submit",
            json=_submit_payload(sample_questions, 15),
            headers={"Authorization": f"Bearer {other_token}"},
        )
        attempt_id = submit_resp.json()["id"]

        # staff_token user tries to fetch other user's attempt
        resp = await async_client.get(
            f"/api/test/attempt/{attempt_id}",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
#  ADMIN TESTS  (21 – 29)
# ═════════════════════════════════════════════════════════════════════════════

class TestAdmin:

    # ── Shared helper: seed data for stat-heavy tests ─────────────────────────
    @staticmethod
    async def _seed_attempt(
        user_id: int,
        score: float,
        passed: bool,
        topic_label: str = "Fire Chemistry & Causes",
    ):
        async with TestingSessionLocal() as session:
            attempt = TestAttempt(
                user_id=user_id,
                topic_id="fire_basics",
                topic_label=topic_label,
                total_questions=25,
                correct_answers=int(score / 100 * 25),
                score_percent=score,
                passed=passed,
                time_taken_seconds=600,
                answers=[],
                questions=SAMPLE_QUESTIONS,
                subtopic_scores={"Fire Chemistry": {"correct": 10, "total": 25, "percent": 40.0}},
                ai_feedback="Test feedback",
                email_sent=False,
            )
            session.add(attempt)
            await session.commit()

    # 21. GET /admin/stats — admin token → all KPI fields ─────────────────────
    @pytest.mark.asyncio
    async def test_admin_stats(
        self, async_client: AsyncClient, admin_token: str
    ):
        resp = await async_client.get(
            "/api/admin/stats",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        for key in (
            "total_staff", "total_tests", "pass_rate",
            "avg_score", "tests_this_month",
            "district_breakdown", "topic_breakdown", "recent_attempts",
        ):
            assert key in body, f"Missing KPI: {key}"

    # 22. GET /admin/stats — staff token → 403 ────────────────────────────────
    @pytest.mark.asyncio
    async def test_admin_stats_forbidden_for_staff(
        self, async_client: AsyncClient, staff_token: str
    ):
        resp = await async_client.get(
            "/api/admin/stats",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 403

    # 23. GET /admin/staff — returns list ─────────────────────────────────────
    @pytest.mark.asyncio
    async def test_admin_list_staff(
        self, async_client: AsyncClient, admin_token: str
    ):
        # Seed a staff user
        await _create_user(
            username="listedstaff",
            email="listedstaff@example.com",
            password="pass123",
            role="staff",
        )
        resp = await async_client.get(
            "/api/admin/staff",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert isinstance(body, list)
        assert any(u["username"] == "listedstaff" for u in body)

    # 24. POST /admin/staff — creates account ─────────────────────────────────
    @pytest.mark.asyncio
    async def test_admin_create_staff(
        self, async_client: AsyncClient, admin_token: str
    ):
        payload = {
            "email": "newstaff@example.com",
            "username": "newstaff",
            "password": "newpass123",
            "full_name": "New Staff Member",
            "designation": "Rescue Officer",
            "district": "Rawalpindi",
        }
        resp = await async_client.post(
            "/api/admin/staff",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["username"] == "newstaff"
        assert body["role"] == "staff"

    # 25. DELETE /admin/staff/{id} → 200 ──────────────────────────────────────
    @pytest.mark.asyncio
    async def test_admin_delete_staff(
        self, async_client: AsyncClient, admin_token: str
    ):
        # Create staff to delete
        create_resp = await async_client.post(
            "/api/admin/staff",
            json={
                "email": "tobedeleted@example.com",
                "username": "tobedeleted",
                "password": "pass123",
                "full_name": "To Be Deleted",
                "designation": "Firefighter",
                "district": "Faisalabad",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert create_resp.status_code == 200
        user_id = create_resp.json()["id"]

        del_resp = await async_client.delete(
            f"/api/admin/staff/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert del_resp.status_code == 200
        assert del_resp.json()["message"] == "Deleted"

        # Confirm it's gone from the list
        list_resp = await async_client.get(
            "/api/admin/staff",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        ids = [u["id"] for u in list_resp.json()]
        assert user_id not in ids

    # 26. GET /admin/leaderboard — returns ranked list ─────────────────────────
    @pytest.mark.asyncio
    async def test_admin_leaderboard(
        self, async_client: AsyncClient, admin_token: str
    ):
        # Seed staff + attempt so leaderboard has data
        user = await _create_user(
            username="leaderstaff",
            email="leaderstaff@example.com",
            password="pass",
            role="staff",
            district="Multan",
        )
        await self._seed_attempt(user.id, score=80.0, passed=True)

        resp = await async_client.get(
            "/api/admin/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1
        for entry in body:
            assert "rank" in entry
            assert "avg_score" in entry
            assert "total_tests" in entry

    # 27. GET /admin/attempts — returns results list ───────────────────────────
    @pytest.mark.asyncio
    async def test_admin_all_attempts(
        self, async_client: AsyncClient, admin_token: str
    ):
        user = await _create_user(
            username="attemptstaff",
            email="attemptstaff@example.com",
            password="pass",
            role="staff",
        )
        await self._seed_attempt(user.id, score=72.0, passed=True)

        resp = await async_client.get(
            "/api/admin/attempts",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1
        first = body[0]
        for key in ("id", "topic_label", "score_percent", "passed", "total_questions"):
            assert key in first

    # 28. GET /admin/export/excel — xlsx content-type ─────────────────────────
    @pytest.mark.asyncio
    async def test_admin_export_excel(
        self, async_client: AsyncClient, admin_token: str
    ):
        # Seed at least one attempt so the export is non-trivial
        user = await _create_user(
            username="excelstaff",
            email="excelstaff@example.com",
            password="pass",
            role="staff",
        )
        await self._seed_attempt(user.id, score=60.0, passed=True)

        resp = await async_client.get(
            "/api/admin/export/excel",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200, resp.text
        assert (
            "spreadsheetml" in resp.headers["content-type"]
            or "excel" in resp.headers["content-type"]
            or "octet-stream" in resp.headers["content-type"]
        )
        assert len(resp.content) > 0

    # 29. GET /admin/export/pdf — pdf content-type ────────────────────────────
    @pytest.mark.asyncio
    async def test_admin_export_pdf(
        self, async_client: AsyncClient, admin_token: str
    ):
        user = await _create_user(
            username="pdfstaff",
            email="pdfstaff@example.com",
            password="pass",
            role="staff",
        )
        await self._seed_attempt(user.id, score=55.0, passed=False)

        resp = await async_client.get(
            "/api/admin/export/pdf",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200, resp.text
        assert "pdf" in resp.headers["content-type"]
        assert len(resp.content) > 0
        # PDF magic bytes
        assert resp.content[:4] == b"%PDF"


# ═════════════════════════════════════════════════════════════════════════════
#  SECURITY TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestSecurity:

    # 1. test_expired_token
    @pytest.mark.asyncio
    async def test_expired_token(self, async_client: AsyncClient, clean_db):
        from app.core.security import create_access_token
        from datetime import timedelta
        # Create token that expired 1 minute ago
        token = create_access_token({"sub": "999"}, expires_delta=timedelta(minutes=-1))
        resp = await async_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert "validate credentials" in resp.json()["detail"].lower()

    # 2. test_tampered_token
    @pytest.mark.asyncio
    async def test_tampered_token(self, async_client: AsyncClient, staff_token: str):
        # Change the signature or payload
        parts = staff_token.split(".")
        if len(parts) == 3:
            tampered = f"{parts[0]}.{parts[1]}A.{parts[2]}"
            resp = await async_client.get("/api/auth/me", headers={"Authorization": f"Bearer {tampered}"})
            assert resp.status_code == 401

    # 3. test_staff_cannot_delete_staff
    @pytest.mark.asyncio
    async def test_staff_cannot_delete_staff(self, async_client: AsyncClient, staff_token: str):
        resp = await async_client.delete("/api/admin/staff/1", headers={"Authorization": f"Bearer {staff_token}"})
        assert resp.status_code == 403

    # 4. test_staff_cannot_view_all_results
    @pytest.mark.asyncio
    async def test_staff_cannot_view_all_results(self, async_client: AsyncClient, staff_token: str):
        resp = await async_client.get("/api/admin/attempts", headers={"Authorization": f"Bearer {staff_token}"})
        assert resp.status_code == 403

    # 5. test_staff_cannot_access_leaderboard_admin
    @pytest.mark.asyncio
    async def test_staff_cannot_access_leaderboard_admin(self, async_client: AsyncClient, staff_token: str):
        resp = await async_client.get("/api/admin/leaderboard", headers={"Authorization": f"Bearer {staff_token}"})
        assert resp.status_code == 403

    # 6. test_password_is_hashed
    @pytest.mark.asyncio
    async def test_password_is_hashed(self, clean_db):
        from sqlalchemy import select
        user = await _create_user("hashtest", "hash@example.com", "PlainPassword123", "staff")
        from tests.conftest import TestingSessionLocal
        from app.models.user import User
        async with TestingSessionLocal() as session:
            db_user = (await session.execute(select(User).where(User.username == "hashtest"))).scalar_one()
            assert db_user.hashed_password != "PlainPassword123"
            assert len(db_user.hashed_password) > 20

    # 7. test_sql_injection_username
    @pytest.mark.asyncio
    async def test_sql_injection_username(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/api/auth/login",
            data={"username": "admin' OR '1'='1", "password": "password"},
        )
        assert resp.status_code == 401
        
    # 8. test_cannot_access_other_user_history
    @pytest.mark.asyncio
    async def test_cannot_access_other_user_history(
        self, async_client: AsyncClient, staff_token: str, sample_questions: list
    ):
        from app.core.security import create_access_token
        
        # User A makes an attempt
        await async_client.post(
            "/api/test/submit",
            json=_submit_payload(sample_questions, 25),
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        
        # User B makes an attempt
        user_b = await _create_user("user_b", "b@example.com", "pass", "staff")
        token_b = create_access_token({"sub": str(user_b.id)})
        await async_client.post(
            "/api/test/submit",
            json=_submit_payload(sample_questions, 10),
            headers={"Authorization": f"Bearer {token_b}"},
        )
        
        # User A should only see their own attempt in history
        resp_a = await async_client.get("/api/test/history", headers={"Authorization": f"Bearer {staff_token}"})
        assert resp_a.status_code == 200
        history_a = resp_a.json()
        assert len(history_a) == 1
        assert history_a[0]["score_percent"] == 100.0  # Only sees their 25/25 attempt
