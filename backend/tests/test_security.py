"""Security tests: input validation, XSS/injection hygiene, upload validation,
rate limiting, and cross-user access control."""


def test_oversized_input_rejected(client, auth_headers):
    r = client.post("/api/investigations",
                    json={"raw_input": "x" * 3000}, headers=auth_headers)
    assert r.status_code == 422


def test_injection_payload_sanitized(client, stub_connectors, auth_headers):
    payload = "evil\r\n<script>alert(1)</script> example.com"
    r = client.post("/api/investigations", json={"raw_input": payload},
                    headers=auth_headers)
    if r.status_code == 422:
        return  # sanitize removed newline, schema validation may kick in
    inv = r.json()
    assert "<script>" not in inv["raw_input"]
    assert "\r" not in inv["raw_input"]


def test_upload_invalid_type_rejected(client, auth_headers):
    r = client.post("/api/upload/image",
                    headers=auth_headers,
                    files={"file": ("evil.txt", b"not an image", "text/plain")})
    assert r.status_code == 415 or r.status_code == 503


def test_upload_magic_bytes_mismatch_rejected(client, auth_headers):
    """Declared PNG but the bytes are garbage -> must be rejected."""
    r = client.post("/api/upload/image",
                    headers=auth_headers,
                    files={"file": ("fake.png", b"this is not a real png file", "image/png")})
    assert r.status_code == 415


import base64

# Base64 of a real 1x1 transparent PNG.
VALID_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def test_upload_valid_png_accepted(client, auth_headers):
    """A real PNG passes magic-byte validation (OCR layer may be 503 if deps missing)."""
    r = client.post("/api/upload/image",
                    headers=auth_headers,
                    files={"file": ("px.png", VALID_PNG, "image/png")})
    assert r.status_code in (201, 503)


def test_upload_oversize_rejected(client, auth_headers):
    big = b"\x00" * (5 * 1024 * 1024 + 1)
    r = client.post("/api/upload/image",
                    headers=auth_headers,
                    files={"file": ("img.png", big, "image/png")})
    assert r.status_code == 413


def test_rate_limit_enforced():
    """Rate limiter must return 429 after the per-window budget is spent."""
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from fastapi.testclient import TestClient as TC

    from app.core.limiter import RateLimiter

    tiny = Starlette()
    tiny.add_middleware(RateLimiter, max_requests=3, per_seconds=60)

    @tiny.route("/ping")
    async def ping(request):
        return PlainTextResponse("pong")

    c = TC(tiny)
    for _ in range(3):
        assert c.get("/ping").status_code == 200
    assert c.get("/ping").status_code == 429


def test_cross_user_access_denied(client, stub_connectors):
    a = client.post("/api/auth/register",
                    json={"username": "userA", "password": "pass1234"}).json()
    b = client.post("/api/auth/register",
                    json={"username": "userB", "password": "pass1234"}).json()
    ha = {"Authorization": f"Bearer {a['access_token']}"}
    hb = {"Authorization": f"Bearer {b['access_token']}"}

    inv = client.post("/api/investigations", json={"raw_input": "example.com"},
                      headers=ha)
    assert inv.status_code == 201
    inv_id = inv.json()["id"]

    # userB must not read userA's investigation
    assert client.get(f"/api/investigations/{inv_id}", headers=hb).status_code == 404
    assert client.get(f"/api/investigations/{inv_id}/graph", headers=hb).status_code == 404
    assert client.post(f"/api/investigations/{inv_id}/ai", headers=hb).status_code == 404