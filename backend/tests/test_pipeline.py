"""Core logic tests: input classification, entity extraction, confidence
rules, correlation engine and domain->IP expansion (all offline)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.entities import Finding
from app.modules.confidence import compute_confidence, status_label
from app.modules.correlation import (
    correlate_entities,
    entity_from,
    find_domain_ip_links,
)
from app.modules.entity_extraction import extract_entities
from app.modules.input_manager import classify_input, sanitize


def _dns_finding(query, records):
    return Finding(key=f"dns:{query}", value={"records": records},
                   source="dns", query=query, confidence=0.9, evidence_count=1)


def test_classify_input():
    assert classify_input("example.com") == "domain"
    assert classify_input("8.8.8.8") == "ip"
    assert classify_input("999.1.1.1") != "ip"  # > 255 handled
    assert classify_input("john@example.com") == "email"
    assert classify_input("https://example.com/x") == "url"
    assert classify_input("some free text here") == "text"
    assert classify_input("  ") == "empty"


def test_sanitize_strips_control_chars():
    assert "\x00" not in sanitize("ab\x00cd")
    assert "\r" not in sanitize("a\r\nb")
    assert sanitize(" hi ") == "hi"


def test_extract_entities_from_text():
    text = "reach me at john+tag@example.com or https://site.io/p and 10.0.0.1 @johndoe"
    result = extract_entities(text)
    kinds = {e["type"] for e in result}
    assert "email" in kinds
    assert "domain" in kinds
    assert "url" in kinds
    assert "ip" in kinds
    assert "username" in kinds
    values = [e["value"] for e in result]
    assert "example.com" in values


def test_confidence_rules():
    score1, status = compute_confidence(1, {"dns"})
    assert status == "Likely" or status == "Needs Verification"
    assert 0.0 <= score1 <= 1.0
    score3, status3 = compute_confidence(3, {"dns", "whois", "certificate"})
    assert score3 > score1
    assert status3 == "Confirmed"
    assert compute_confidence(0, set())[0] == 0.0


def test_status_label():
    assert status_label(0.95) == "Confirmed"
    assert status_label(0.6) == "Likely"
    assert status_label(0.2) == "Needs Verification"


def test_correlation_email_domain():
    email = entity_from("email", "john@example.com")
    domain = entity_from("domain", "example.com")
    rels = correlate_entities([email, domain], [])
    assert any(r.relation == "uses_domain" and r.source_id == email.id
               and r.target_id == domain.id for r in rels)


def test_correlation_deduplicates():
    email = entity_from("email", "a@b.com")
    domain = entity_from("domain", "b.com")
    rels = correlate_entities([email, domain], [])
    assert len(rels) == 1


def test_find_domain_ip_links_from_dns():
    domain = entity_from("domain", "example.com")
    f = _dns_finding("example.com", {"A": ["93.1.2.3"], "AAAA": ["2001:db8::1"]})
    links = find_domain_ip_links(domain, [f])
    assert ("93.1.2.3", "resolves_to", 0.9) in links
    assert ("2001:db8::1", "resolves_to", 0.85) in links


def test_correlation_domain_ip():
    domain = entity_from("domain", "example.com")
    ip = entity_from("ip", "93.1.2.3")
    f = _dns_finding("example.com", {"A": ["93.1.2.3"]})
    rels = correlate_entities([domain, ip], [f])
    assert any(r.relation == "resolves_to" and r.source_id == domain.id
               and r.target_id == ip.id for r in rels)


def test_pipeline_expands_domain_to_ip(monkeypatch):
    """create_investigation must expand a domain->IP from DNS results."""
    from app.connectors.base import ConnectorResult
    from app.services import pipeline as pipeline_mod

    class DnsLike:
        name = "dns"
        source = "dns"

        def run(self, indicator_type, value):
            records = {"A": ["93.1.2.3"]} if indicator_type == "domain" else {}
            return ConnectorResult(
                name=self.name, query=value, value={"records": records},
                source=self.source, confidence=0.9, evidence_count=1,
            )

    monkeypatch.setattr(pipeline_mod, "connectors_for", lambda t: [DnsLike()])
    inv = pipeline_mod.create_investigation("example.com", "unit")
    values = {e.value for e in inv.entities}
    assert "93.1.2.3" in values
    assert any(v.type == "ip" for v in inv.entities)