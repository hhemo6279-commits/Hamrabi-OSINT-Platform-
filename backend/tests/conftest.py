import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.store import Store
from app.connectors.base import Connector, ConnectorResult


class StubConnector(Connector):
    """Offline connector used by pipeline tests: no network calls."""

    def __init__(self, name="stub", value=None, confidence=0.7, evidence=2):
        self.name = name
        self.source = name
        self.fixed = value or {"note": "offline stub"}
        self.fixed_conf = confidence
        self.fixed_evidence = evidence

    def query_conf(self, indicator_type: str, value: str) -> ConnectorResult:
        return ConnectorResult(
            name=self.name, query=value, value=self.fixed,
            source=self.source, confidence=self.fixed_conf,
            evidence_count=self.fixed_evidence,
        )


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_store():
    """Reset in-memory store before every test so assertions are deterministic."""
    Store._data["users"].clear()
    Store._data["investigations"].clear()
    yield


@pytest.fixture
def stub_connectors(monkeypatch):
    from app.services import pipeline as pipeline_mod
    monkeypatch.setattr(pipeline_mod, "connectors_for", lambda t: [StubConnector()])
    return pipeline_mod.connectors_for


@pytest.fixture
def auth_headers(client):
    resp = client.post("/api/auth/register",
                       json={"username": "tester", "password": "testpass123"})
    if resp.status_code == 409:
        resp = client.post("/api/auth/login",
                           data={"username": "tester", "password": "testpass123"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}