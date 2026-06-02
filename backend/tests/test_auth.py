TEST_DESIGNATIONS = [
    "LEAD FIRE RESCUER (LFR)",
    "FIRE & DISASTER RESCUE (FDR)",
    "OTHER",
]


def register_payload(**overrides):
    payload = {
        "email": "new@example.com",
        "username": "newuser",
        "password": "password123",
        "full_name": "New User",
        "designation": "OTHER",
        "district": "Lahore",
    }
    payload.update(overrides)
    return payload


class TestLogin:
    async def test_login_success_staff(self, client, staff_user):
        resp = await client.post("/api/auth/login", data={"username": "staff_user", "password": "password123"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"]
        assert body["role"] == "staff"

    async def test_login_success_admin(self, client, admin_user):
        resp = await client.post("/api/auth/login", data={"username": "admin_user", "password": "password123"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

    async def test_login_wrong_password(self, client, staff_user):
        resp = await client.post("/api/auth/login", data={"username": "staff_user", "password": "bad"})
        assert resp.status_code == 401
        assert "Incorrect" in resp.json()["detail"]

    async def test_login_nonexistent_username(self, client):
        resp = await client.post("/api/auth/login", data={"username": "missing", "password": "bad"})
        assert resp.status_code == 401
        assert "Incorrect" in resp.json()["detail"]

    async def test_login_inactive_account(self, client, inactive_user):
        resp = await client.post("/api/auth/login", data={"username": "inactive_user", "password": "password123"})
        assert resp.status_code == 403
        assert "deactivated" in resp.json()["detail"]

    async def test_login_empty_credentials(self, client):
        resp = await client.post("/api/auth/login", data={"username": "", "password": ""})
        assert resp.status_code in (401, 422)

    async def test_login_sql_injection_attempt(self, client):
        resp = await client.post("/api/auth/login", data={"username": "' OR 1=1; --", "password": "password123"})
        assert resp.status_code in (401, 422)

    async def test_login_returns_jwt_structure(self, client, staff_user):
        resp = await client.post("/api/auth/login", data={"username": "staff_user", "password": "password123"})
        assert len(resp.json()["access_token"].split(".")) == 3

    async def test_login_case_sensitive_username(self, client, staff_user):
        resp = await client.post("/api/auth/login", data={"username": "STAFF_USER", "password": "password123"})
        assert resp.status_code == 401


class TestRegister:
    async def test_register_success(self, client):
        resp = await client.post("/api/auth/register", json=register_payload())
        assert resp.status_code == 201
        body = resp.json()
        assert body["role"] == "staff"
        assert "password" not in body
        assert "hashed_password" not in body

    async def test_register_duplicate_username(self, client, staff_user):
        resp = await client.post("/api/auth/register", json=register_payload(username="staff_user", email="unique@example.com"))
        assert resp.status_code == 400

    async def test_register_duplicate_email(self, client, staff_user):
        resp = await client.post("/api/auth/register", json=register_payload(username="unique", email="staff@example.com"))
        assert resp.status_code == 400

    async def test_register_invalid_email(self, client):
        resp = await client.post("/api/auth/register", json=register_payload(email="not-an-email"))
        assert resp.status_code == 422

    async def test_register_short_password(self, client):
        resp = await client.post("/api/auth/register", json=register_payload(password="123"))
        assert resp.status_code == 422

    async def test_register_short_username(self, client):
        resp = await client.post("/api/auth/register", json=register_payload(username="ab"))
        assert resp.status_code == 422

    async def test_register_invalid_designation(self, client):
        resp = await client.post("/api/auth/register", json=register_payload(designation="Commander"))
        assert resp.status_code == 422

    async def test_register_valid_designations(self, client):
        for i, designation in enumerate(TEST_DESIGNATIONS):
            resp = await client.post("/api/auth/register", json=register_payload(
                email=f"valid{i}@example.com",
                username=f"valid{i}",
                designation=designation,
            ))
            assert resp.status_code == 201

    async def test_register_role_cannot_be_set_to_admin(self, client):
        resp = await client.post("/api/auth/register", json=register_payload(role="admin"))
        if resp.status_code == 201:
            assert resp.json()["role"] == "staff"

    async def test_register_missing_required_fields(self, client):
        resp = await client.post("/api/auth/register", json={"email": "x@example.com"})
        assert resp.status_code == 422


class TestMe:
    async def test_me_authenticated(self, client, staff_user, staff_headers):
        resp = await client.get("/api/auth/me", headers=staff_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == staff_user.id
        assert "hashed_password" not in resp.text

    async def test_me_no_token(self, client):
        assert (await client.get("/api/auth/me")).status_code == 401

    async def test_me_invalid_token(self, client):
        assert (await client.get("/api/auth/me", headers={"Authorization": "Bearer bad"})).status_code == 401

    async def test_me_malformed_bearer(self, client):
        assert (await client.get("/api/auth/me", headers={"Authorization": "Bad token"})).status_code == 401

    async def test_me_profile_included(self, client, staff_headers):
        resp = await client.get("/api/auth/me", headers=staff_headers)
        profile = resp.json()["profile"]
        assert profile["full_name"] == "Staff User"
        assert profile["district"] == "Lahore"


class TestChangePassword:
    async def test_change_password_success(self, client, staff_headers):
        resp = await client.post(
            "/api/auth/change-password",
            headers=staff_headers,
            json={"current_password": "password123", "new_password": "newpassword123"},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Password changed successfully"

        old_login = await client.post("/api/auth/login", data={"username": "staff_user", "password": "password123"})
        assert old_login.status_code == 401

        new_login = await client.post("/api/auth/login", data={"username": "staff_user", "password": "newpassword123"})
        assert new_login.status_code == 200

    async def test_change_password_wrong_current_password(self, client, staff_headers):
        resp = await client.post(
            "/api/auth/change-password",
            headers=staff_headers,
            json={"current_password": "wrong-password", "new_password": "newpassword123"},
        )
        assert resp.status_code == 400
        assert "incorrect" in resp.json()["detail"].lower()

    async def test_change_password_requires_auth(self, client):
        resp = await client.post(
            "/api/auth/change-password",
            json={"current_password": "password123", "new_password": "newpassword123"},
        )
        assert resp.status_code == 401
