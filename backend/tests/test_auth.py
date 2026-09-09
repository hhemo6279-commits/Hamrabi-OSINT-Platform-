"""Authentication & access-control tests."""
import datetime

import jwt


def _make_token(user_id, secret, exp_offset):
    import os
    return jwt.encode(
        {"sub": user_id,
         "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=exp_offset)},
        secret, algorithm="HS256",
    )


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_and_login(client):
    r = client.post("/api/auth/register",
                    json={"username": "alice", "password": "correctHorse"})
    assert r.status_code == 201
    assert r.json()["access_token"]

    login = client.post("/api/auth/login",
                        data={"username": "alice", "password": "correctHorse"})
    assert login.status_code == 200
    assert login.json()["username"] == "alice"


def test_register_duplicate(client):
    client.post("/api/auth/register",
                json={"username": "bob", "password": "pass1234"})
    r = client.post("/api/auth/register",
                    json={"username": "bob", "password": "pass1234"})
    assert r.status_code == 409


def test_login_wrong_password(client):
    client.post("/api/auth/register",
                json={"username": "carol", "password": "pass1234"})
    r = client.post("/api/auth/login",
                    data={"username": "carol", "password": "wrongpass"})
    assert r.status_code == 401


def test_no_token_allowed(client):
    """Local login-free mode: requests without a token are allowed."""
    r = client.get("/api/investigations")
    assert r.status_code == 200


def test_invalid_token_falls_back(client):
    """An invalid token falls back to the default local user instead of 401."""
    r = client.get("/api/investigations",
                   headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 200


def test_expired_token_falls_back(client):
    from app.core.config import SECRET_KEY
    token = _make_token("some-user", SECRET_KEY, exp_offset=-120)
    r = client.get("/api/investigations",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_tampered_token_falls_back(client):
    from app.core.config import SECRET_KEY

    reg = client.post("/api/auth/register",
                      json={"username": "tamper", "password": "pass1234"})
    original = reg.json()["access_token"]
    # Same token signed with a different key must not be trusted, but access
    # continues under the default local user.
    forged = _make_token("some-user", "attacker-secret", exp_offset=1200).encode()
    assert forged != original
    r = client.get("/api/investigations", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 200


def test_short_password_rejected(client):
    r = client.post("/api/auth/register",
                    json={"username": "shorty", "password": "x"})
    assert r.status_code == 422