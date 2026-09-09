from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class User:
    id: str
    username: str
    password_hash: str
    role: str = "user"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class Finding:
    key: str
    value: dict
    source: str
    query: str
    confidence: float
    evidence_count: int
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class Entity:
    id: str
    type: str
    value: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class Relationship:
    source_id: str
    target_id: str
    relation: str
    confidence: float


@dataclass
class Investigation:
    id: str
    user_id: str
    raw_input: str
    input_type: str
    entities: list = field(default_factory=list)
    findings: list = field(default_factory=list)
    relationships: list = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    report_path: str | None = None
    share_token: str | None = None
    ai_summary: str | None = None
    ai_classification: str | None = None
    tags: list = field(default_factory=list)