from collections import Counter

from app.models.user import QuestionBank


def staff_payload(**overrides):
    payload = {
        "email": "created@example.com",
        "username": "created",
        "password": "password123",
        "full_name": "Created Staff",
        "designation": "OTHER",
        "district": "Lahore",
    }
    payload.update(overrides)
    return payload


class TestAdminAuthGuard:
    async def test_stats_requires_admin(self, client, staff_headers):
        assert (await client.get("/api/admin/stats", headers=staff_headers)).status_code == 403

    async def test_stats_requires_auth(self, client):
        assert (await client.get("/api/admin/stats")).status_code == 401

    async def test_staff_list_requires_admin(self, client, staff_headers):
        assert (await client.get("/api/admin/staff", headers=staff_headers)).status_code == 403

    async def test_delete_staff_requires_admin(self, client, staff_headers, staff_user):
        assert (await client.delete(f"/api/admin/staff/{staff_user.id}", headers=staff_headers)).status_code == 403


class TestAdminStats:
    async def test_stats_success(self, client, admin_headers, staff_user, question_bank):
        resp = await client.get("/api/admin/stats", headers=admin_headers)
        assert resp.status_code == 200
        for key in ["total_staff", "total_tests", "pass_rate", "avg_score", "tests_this_month", "district_breakdown", "topic_breakdown", "question_bank_breakdown", "recent_attempts", "activity_log"]:
            assert key in resp.json()

    async def test_stats_numeric_types(self, client, admin_headers):
        body = (await client.get("/api/admin/stats", headers=admin_headers)).json()
        assert isinstance(body["total_staff"], int)
        assert isinstance(body["pass_rate"], float)

    async def test_stats_counts_staff_correctly(self, client, admin_headers, staff_user):
        body = (await client.get("/api/admin/stats", headers=admin_headers)).json()
        assert body["total_staff"] >= 1


class TestAdminCreateStaff:
    async def test_create_success(self, client, admin_headers):
        assert (await client.post("/api/admin/staff", headers=admin_headers, json=staff_payload())).status_code == 201

    async def test_create_invalid_designation(self, client, admin_headers):
        assert (await client.post("/api/admin/staff", headers=admin_headers, json=staff_payload(designation="Bad"))).status_code == 422

    async def test_create_duplicate_email(self, client, admin_headers, staff_user):
        resp = await client.post("/api/admin/staff", headers=admin_headers, json=staff_payload(email="staff@example.com"))
        assert resp.status_code in (400, 409)

    async def test_create_missing_fields(self, client, admin_headers):
        assert (await client.post("/api/admin/staff", headers=admin_headers, json={"email": "x@example.com"})).status_code == 422


class TestAdminUpdateStaff:
    async def test_update_success(self, client, admin_headers, staff_user):
        resp = await client.put(f"/api/admin/staff/{staff_user.id}", headers=admin_headers, json={"full_name": "Updated Name"})
        assert resp.status_code in (200, 204)

    async def test_update_invalid_designation(self, client, admin_headers, staff_user):
        resp = await client.put(f"/api/admin/staff/{staff_user.id}", headers=admin_headers, json={"designation": "Bad"})
        assert resp.status_code == 422

    async def test_update_nonexistent_user(self, client, admin_headers):
        assert (await client.put("/api/admin/staff/999999", headers=admin_headers, json={"full_name": "Missing User"})).status_code == 404

    async def test_update_deactivate(self, client, admin_headers, staff_user):
        resp = await client.put(f"/api/admin/staff/{staff_user.id}", headers=admin_headers, json={"is_active": False})
        assert resp.status_code in (200, 204)


class TestAdminDeleteStaff:
    async def test_delete_success(self, client, admin_headers, staff_user):
        resp = await client.delete(f"/api/admin/staff/{staff_user.id}", headers=admin_headers)
        assert resp.status_code in (200, 204)

    async def test_delete_nonexistent(self, client, admin_headers):
        assert (await client.delete("/api/admin/staff/999999", headers=admin_headers)).status_code == 404


class TestLeaderboard:
    async def test_admin_can_access(self, client, admin_headers):
        assert (await client.get("/api/admin/leaderboard", headers=admin_headers)).status_code == 200

    async def test_staff_gets_403(self, client, staff_headers):
        assert (await client.get("/api/admin/leaderboard", headers=staff_headers)).status_code == 403


class TestQuestionBank:
    async def test_admin_can_access(self, client, admin_headers, question_bank):
        assert (await client.get("/api/admin/question-bank", headers=admin_headers)).status_code == 200

    async def test_staff_gets_403(self, client, staff_headers):
        assert (await client.get("/api/admin/question-bank", headers=staff_headers)).status_code == 403


async def create_master_paper_bank(db):
    topics = [
        ("fire_13_chemical_fire_2", "Fire"),
        ("rescue_14_emergencies_and_disasters", "Rescue"),
        ("building_safety", "Building"),
    ]
    rows = []
    for topic_id, label in topics:
        for difficulty, count in (("easy", 12), ("medium", 10), ("hard", 8)):
            for index in range(count):
                question = {
                    "q": f"{label} {difficulty} master paper question {index}:",
                    "question": f"{label} {difficulty} master paper question {index}:",
                    "opts": ["Correct", "Wrong A", "Wrong B", "Wrong C"],
                    "options": ["Correct", "Wrong A", "Wrong B", "Wrong C"],
                    "ans": 0,
                    "topic": label,
                }
                rows.append(QuestionBank(topic_id=topic_id, difficulty=difficulty, question=question, is_valid=True))
    db.add_all(rows)
    await db.commit()


class TestMasterPapers:
    async def test_admin_can_generate_master_paper(self, client, admin_headers, db):
        await create_master_paper_bank(db)
        resp = await client.post(
            "/api/admin/master-papers",
            headers=admin_headers,
            json={"title": "Competent Authority Master Test", "easy_count": 10, "medium_count": 8, "hard_count": 7},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Competent Authority Master Test"
        assert body["total_questions"] == 25
        assert len(body["questions"]) == 25

        difficulties = Counter(question["difficulty"] for question in body["questions"])
        assert difficulties == {"easy": 10, "medium": 8, "hard": 7}
        assert {"fire", "rescue", "building"}.issubset({question["field"] for question in body["questions"]})

    async def test_admin_can_list_and_view_master_paper(self, client, admin_headers, db):
        await create_master_paper_bank(db)
        created = await client.post("/api/admin/master-papers", headers=admin_headers, json={"title": "Master Test"})
        assert created.status_code == 200
        paper_id = created.json()["id"]

        listing = await client.get("/api/admin/master-papers", headers=admin_headers)
        assert listing.status_code == 200
        assert any(item["id"] == paper_id for item in listing.json())

        detail = await client.get(f"/api/admin/master-papers/{paper_id}", headers=admin_headers)
        assert detail.status_code == 200
        assert len(detail.json()["questions"]) == 25

    async def test_staff_cannot_generate_master_paper(self, client, staff_headers):
        resp = await client.post("/api/admin/master-papers", headers=staff_headers, json={"title": "No Access"})
        assert resp.status_code == 403


class TestActivityLog:
    async def test_admin_can_access(self, client, admin_headers):
        assert (await client.get("/api/admin/activity-log", headers=admin_headers)).status_code == 200

    async def test_staff_gets_403(self, client, staff_headers):
        assert (await client.get("/api/admin/activity-log", headers=staff_headers)).status_code == 403
