from sqlalchemy import select

from app.models.user import TestAttempt


async def generated_questions(client, staff_headers, question_bank):
    resp = await client.post("/api/test/generate", headers=staff_headers, json={"topic_id": "fire_safety", "designation": "OTHER"})
    assert resp.status_code == 200, resp.text
    return resp.json()["questions"]


def submit_payload(questions, answers=None):
    return {
        "topic_id": "fire_safety",
        "topic_label": "Fire Safety",
        "questions": questions,
        "answers": answers if answers is not None else [{"q_index": i, "selected": 0} for i in range(len(questions))],
        "started_at": "2026-01-01T00:00:00Z",
        "time_taken_seconds": 60,
    }


class TestExamAuthGuard:
    async def test_generate_returns_401_without_token(self, client):
        assert (await client.post("/api/test/generate", json={"topic_id": "fire_safety", "designation": "OTHER"})).status_code == 401

    async def test_submit_returns_401_without_token(self, client):
        assert (await client.post("/api/test/submit", json=submit_payload([]))).status_code == 401

    async def test_history_returns_401_without_token(self, client):
        assert (await client.get("/api/test/history")).status_code == 401


class TestGenerateQuestions:
    async def test_generate_returns_25_questions(self, client, staff_headers, question_bank):
        questions = await generated_questions(client, staff_headers, question_bank)
        assert len(questions) == 25

    async def test_generate_question_structure(self, client, staff_headers, question_bank):
        questions = await generated_questions(client, staff_headers, question_bank)
        for question in questions:
            assert question["question"]
            assert len(question["options"]) == 4
            assert "correct" not in question
            assert "ans" not in question

    async def test_generate_missing_topic_id(self, client, staff_headers):
        resp = await client.post("/api/test/generate", headers=staff_headers, json={"designation": "OTHER"})
        assert resp.status_code == 422

    async def test_generate_unknown_topic(self, client, staff_headers):
        resp = await client.post("/api/test/generate", headers=staff_headers, json={"topic_id": "unknown_topic", "designation": "OTHER"})
        assert resp.status_code in (400, 404, 422)

    async def test_generate_no_duplicate_questions(self, client, staff_headers, question_bank):
        questions = await generated_questions(client, staff_headers, question_bank)
        texts = [question["question"] for question in questions]
        assert len(texts) == len(set(texts))

    async def test_generate_allowed_by_admin(self, client, admin_headers, question_bank):
        resp = await client.post("/api/test/generate", headers=admin_headers, json={"topic_id": "fire_safety", "designation": "OTHER"})
        assert resp.status_code == 200


class TestSubmitExam:
    async def test_submit_exam_returns_result(self, client, staff_headers, question_bank):
        questions = await generated_questions(client, staff_headers, question_bank)
        resp = await client.post("/api/test/submit", headers=staff_headers, json=submit_payload(questions))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "score_percent" in body
        assert "passed" in body
        assert "correct_answers" in body
        assert body["total_questions"] == 25

    async def test_submit_score_range(self, client, staff_headers, question_bank):
        questions = await generated_questions(client, staff_headers, question_bank)
        score = (await client.post("/api/test/submit", headers=staff_headers, json=submit_payload(questions))).json()["score_percent"]
        assert 0.0 <= score <= 100.0

    async def test_submit_pass_threshold(self, client, staff_headers, question_bank):
        questions = await generated_questions(client, staff_headers, question_bank)
        body = (await client.post("/api/test/submit", headers=staff_headers, json=submit_payload(questions))).json()
        if body["score_percent"] >= 60:
            assert body["passed"] is True

    async def test_submit_empty_answers_scores_zero(self, client, staff_headers, question_bank):
        questions = await generated_questions(client, staff_headers, question_bank)
        answers = [{"q_index": i, "selected": -1} for i in range(25)]
        body = (await client.post("/api/test/submit", headers=staff_headers, json=submit_payload(questions, answers))).json()
        assert body["correct_answers"] == 0
        assert body["passed"] is False

    async def test_submit_missing_topic_id(self, client, staff_headers):
        payload = submit_payload([])
        payload.pop("topic_id")
        assert (await client.post("/api/test/submit", headers=staff_headers, json=payload)).status_code == 422

    async def test_submit_creates_attempt_record(self, client, staff_headers, question_bank, db):
        questions = await generated_questions(client, staff_headers, question_bank)
        resp = await client.post("/api/test/submit", headers=staff_headers, json=submit_payload(questions))
        attempt_id = resp.json()["id"]
        result = await db.execute(select(TestAttempt).where(TestAttempt.id == attempt_id))
        assert result.scalar_one_or_none() is not None


class TestHistory:
    async def test_history_empty_initially(self, client, staff_headers):
        resp = await client.get("/api/test/history", headers=staff_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_history_shows_own_attempts_only(self, client, staff_headers, admin_headers, question_bank):
        questions = await generated_questions(client, staff_headers, question_bank)
        await client.post("/api/test/submit", headers=staff_headers, json=submit_payload(questions))
        admin_history = await client.get("/api/test/history", headers=admin_headers)
        assert admin_history.status_code == 200
        assert admin_history.json() == []
