import base64
import json
from datetime import datetime, timedelta

from jose import jwt

from app.core.config import settings


def _b64(data: dict) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


class TestJWTSecurity:
    async def test_expired_token_rejected(self, client, staff_user):
        token = jwt.encode({"sub": str(staff_user.id), "exp": datetime.utcnow() - timedelta(minutes=1)}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        assert (await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})).status_code == 401

    async def test_token_with_wrong_secret_rejected(self, client, staff_user):
        token = jwt.encode({"sub": str(staff_user.id)}, "wrong-secret", algorithm=settings.ALGORITHM)
        assert (await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})).status_code == 401

    async def test_token_none_algorithm_rejected(self, client, staff_user):
        token = f"{_b64({'alg': 'none', 'typ': 'JWT'})}.{_b64({'sub': str(staff_user.id)})}."
        assert (await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})).status_code == 401

    async def test_token_missing_sub_rejected(self, client):
        token = jwt.encode({"name": "x"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        assert (await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})).status_code == 401

    async def test_token_nonexistent_user_id_rejected(self, client):
        token = jwt.encode({"sub": "999999"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        assert (await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})).status_code == 401

    async def test_token_non_integer_sub_rejected(self, client):
        token = jwt.encode({"sub": "not-an-int"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        assert (await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})).status_code == 401


class TestPrivilegeEscalation:
    async def test_staff_cannot_access_admin_stats(self, client, staff_headers):
        assert (await client.get("/api/admin/stats", headers=staff_headers)).status_code == 403

    async def test_staff_cannot_delete_other_users(self, client, staff_headers, admin_user):
        assert (await client.delete(f"/api/admin/staff/{admin_user.id}", headers=staff_headers)).status_code == 403

    async def test_staff_cannot_create_staff(self, client, staff_headers):
        assert (await client.post("/api/admin/staff", headers=staff_headers, json={})).status_code == 403

    async def test_staff_cannot_view_activity_log(self, client, staff_headers):
        assert (await client.get("/api/admin/activity-log", headers=staff_headers)).status_code == 403

    async def test_staff_cannot_export_reports(self, client, staff_headers):
        assert (await client.get("/api/admin/export/pdf", headers=staff_headers)).status_code == 403

    async def test_unauthenticated_cannot_access_any_protected_route(self, client):
        checks = [
            ("get", "/api/auth/me", None),
            ("get", "/api/admin/stats", None),
            ("get", "/api/test/history", None),
            ("post", "/api/test/generate", {"topic_id": "fire_safety", "designation": "OTHER"}),
        ]
        for method, path, payload in checks:
            response = await getattr(client, method)(path, json=payload) if payload else await getattr(client, method)(path)
            assert response.status_code in (401, 422)


class TestPasswordSecurity:
    async def test_password_not_returned_in_register(self, client):
        resp = await client.post("/api/auth/register", json={
            "email": "safe@example.com", "username": "safeuser", "password": "password123",
            "full_name": "Safe User", "designation": "OTHER", "district": "Lahore",
        })
        assert "hashed_password" not in resp.text

    async def test_password_not_returned_in_me(self, client, staff_headers):
        assert "hashed_password" not in (await client.get("/api/auth/me", headers=staff_headers)).text

    async def test_password_not_returned_in_admin_staff_list(self, client, admin_headers, staff_user):
        assert "hashed_password" not in (await client.get("/api/admin/staff", headers=admin_headers)).text


class TestInfrastructure:
    async def test_health_endpoint_public(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_root_endpoint_public(self, client):
        assert (await client.get("/")).status_code == 200

    async def test_nonexistent_route_returns_404(self, client):
        assert (await client.get("/missing-route")).status_code == 404

    async def test_security_headers_present(self, client):
        resp = await client.get("/health")
        assert resp.headers["x-content-type-options"] == "nosniff"
        assert resp.headers["x-frame-options"] == "DENY"
        assert resp.headers["x-xss-protection"] == "1; mode=block"

    async def test_method_not_allowed(self, client):
        assert (await client.put("/health")).status_code == 405


class TestInputValidation:
    async def test_oversized_payload_rejected(self, client):
        resp = await client.post("/api/auth/login", data={"username": "x" * 10_000_000, "password": "password123"})
        assert resp.status_code in (400, 401, 413, 422)

    async def test_unicode_in_username(self, client):
        resp = await client.post("/api/auth/login", data={"username": "عملہ", "password": "password123"})
        assert resp.status_code in (401, 422)

    async def test_null_bytes_in_password_login(self, client):
        resp = await client.post("/api/auth/login", data={"username": "staff_user", "password": "abc\x00def"})
        assert resp.status_code in (401, 422)
