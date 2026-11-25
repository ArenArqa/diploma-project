import jwt
import pytest

from app.core.config import get_settings
from tests.conftest import PASSWORD

pytestmark = pytest.mark.integration


async def test_register_login_and_role_injection(client):
    body = {"email": "NEW@Example.com", "full_name": "New User", "password": PASSWORD}
    bad = await client.post("/api/v1/auth/register", json={**body, "role": "admin"})
    assert bad.status_code == 422
    result = await client.post("/api/v1/auth/register", json=body)
    assert result.status_code == 201, result.text
    assert result.json()["email"] == "new@example.com"
    assert result.json()["role"] == "user"
    assert "password_hash" not in result.json()
    assert (await client.post("/api/v1/auth/register", json=body)).status_code == 409
    auth = await client.post("/api/v1/auth/token", data={"username": body["email"], "password": PASSWORD})
    assert auth.status_code == 200
    me = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {auth.json()['access_token']}"}
    )
    assert me.status_code == 200


async def test_authentication_and_permissions(client, inventory, headers):
    assert (await client.get("/api/v1/users/me")).status_code == 401
    assert (await client.get("/api/v1/admin/users", headers=headers["user"])).status_code == 403
    assert (await client.get("/api/v1/analytics/inventory", headers=headers["user"])).status_code == 403
    assert (await client.get("/api/v1/admin/users", headers=headers["admin"])).status_code == 200
    bad = await client.post("/api/v1/auth/token", data={"username": "user@example.com", "password": "wrong"})
    assert bad.status_code == 401


async def test_expired_token(client, inventory):
    cfg = get_settings()
    token = jwt.encode(
        {
            "sub": str(inventory.users["user"].id),
            "iat": 1,
            "exp": 2,
            "iss": cfg.jwt_issuer,
            "aud": cfg.jwt_audience,
        },
        cfg.jwt_secret,
        algorithm="HS256",
    )
    assert (
        await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    ).status_code == 401


async def test_dealer_demotion_guard(client, inventory, headers):
    result = await client.patch(
        f"/api/v1/admin/users/{inventory.users['dealer'].id}/role",
        headers=headers["admin"],
        json={"role": "user"},
    )
    assert result.status_code == 409
