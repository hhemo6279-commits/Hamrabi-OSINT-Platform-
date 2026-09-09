from typing import Any, Literal

from pydantic import BaseModel, Field

InputType = Literal["text", "username", "email", "domain", "ip", "url", "image"]
ConfidenceStatus = Literal["Confirmed", "Likely", "Needs Verification"]


class NewInvestigationRequest(BaseModel):
    raw_input: str = Field(..., min_length=1, max_length=2000)


class EntityOut(BaseModel):
    id: str
    type: str
    value: str
    created_at: str


class FindingOut(BaseModel):
    key: str
    value: dict
    source: str
    query: str
    timestamp: str
    confidence: float
    evidence_count: int


class RelationshipOut(BaseModel):
    key: str
    source_id: str
    target_id: str
    relation: str
    confidence: float


class InvestigationOut(BaseModel):
    id: str
    raw_input: str
    input_type: str
    entities: list[EntityOut]
    findings: list[FindingOut]
    relationships: list[RelationshipOut]
    created_at: str
    report_path: str | None = None
    ai_summary: str | None = None
    ai_classification: str | None = None
    tags: list[str] = Field(default_factory=list)


class TagRequest(BaseModel):
    tags: list[str] = Field(default_factory=list, max_length=20)


class SuggestOut(BaseModel):
    suggestions: list[dict]
    stats: dict


class AIAnalysisOut(BaseModel):
    summary: str
    classification: str
    provider: str
    enabled: bool


class GraphOut(BaseModel):
    nodes: list[dict]
    links: list[dict]


class AuthRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=6, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str