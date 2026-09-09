from abc import ABC, abstractmethod
from datetime import datetime, timezone
from dataclasses import dataclass, field


@dataclass
class ConnectorResult:
    name: str
    query: str
    value: dict
    source: str
    confidence: float
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    evidence_count: int = 0
    error: str | None = None

    def finding_key(self) -> str:
        return f"{self.name}:{self.query.lower()}"

    def as_finding(self):
        from app.models.entities import Finding

        return Finding(
            key=self.finding_key(),
            value=self.value,
            source=self.source,
            query=self.query,
            timestamp=self.timestamp,
            confidence=self.confidence,
            evidence_count=self.evidence_count,
        )


class Connector(ABC):
    name: str = "base"
    source: str = "base"

    @abstractmethod
    def query_conf(self, indicator_type: str, value: str) -> ConnectorResult:
        """Run the connector for a given indicator. Returns a uniform result."""

    def run(self, indicator_type: str, value: str) -> ConnectorResult:
        try:
            return self.query_conf(indicator_type, value)
        except Exception as exc:  # connectors must never break the pipeline
            return ConnectorResult(
                name=self.name,
                query=value,
                value={},
                source=self.source,
                confidence=0.0,
                evidence_count=0,
                error=str(exc),
            )

    def supports(self, indicator_type: str) -> bool:
        return indicator_type in {"domain", "ip", "url", "email"}