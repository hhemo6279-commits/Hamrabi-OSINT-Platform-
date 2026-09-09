"""Test runner — verifies Hamrabi backend boots and the pipelines work."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def run_checks():
    h = client.get("/api/health")
    assert h.status_code == 200, h.text
    print("[1/4] health OK")

    reg = client.post("/api/auth/register", json={"username": "demo", "password": "secret123"})
    assert reg.status_code == 201, reg.text
    tok = reg.json()["access_token"]
    auth = {"Authorization": f"Bearer {tok}"}
    print("[2/4] register/login OK")

    inv = client.post("/api/investigations", json={"raw_input": "example.com"},
                      headers=auth)
    assert inv.status_code == 201, inv.text
    data = inv.json()
    print(f"[3/4] investigation created: {data['input_type']} "
          f"({len(data['entities'])} entities, {len(data['findings'])} findings)")

    g = client.get(f"/api/investigations/{data['id']}/graph", headers=auth)
    assert g.status_code == 200
    print("[4/4] graph endpoint OK")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    run_checks()