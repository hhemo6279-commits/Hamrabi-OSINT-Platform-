"""Investigation pipeline — orchestrates input -> entities -> connectors ->
confidence -> correlation -> expansion (domain->IP) -> persistence."""
from app.connectors import connectors_for
from app.models.entities import Entity, Finding
from app.modules.correlation import (
    build_investigation,
    correlate_entities,
    entity_from,
    find_domain_ip_links,
)
from app.modules.confidence import compute_confidence
from app.services.store import Store

MAX_TOTAL_ENTITIES = 15


def create_investigation(raw_input: str, user_id: str,
                         extra_findings: list[Finding] | None = None):
    from app.modules.input_manager import classify_input, primary_entities, sanitize

    raw_input = sanitize(raw_input)
    if not raw_input:
        raise ValueError("empty input after sanitization")

    input_type = classify_input(raw_input)
    entities: list[Entity] = []
    seen: set = set()

    for item in primary_entities(raw_input):
        kind = item["type"]
        value = item["value"].strip()
        key = f"{kind}:{value.lower()}"
        if key in seen:
            continue
        seen.add(key)
        entities.append(entity_from(kind, value))

    findings: list[Finding] = [f for f in (extra_findings or [])]

    # First pass: connectors on the input entities.
    initial_ids = {e.id for e in entities}
    for entity in entities:
        for res in _run_connectors(entity):
            findings.append(res.as_finding())

    # Expansion pass: turn DNS A/AAAA records into IP entities, then run
    # connectors on those newly created entities only (bounded).
    _expand_domain_ips(entities, findings)
    for entity in entities:
        if entity.id in initial_ids:
            continue
        for res in _run_connectors(entity):
            findings.append(res.as_finding())

    findings = enrich_findings_with_confidence(findings)
    relationships = correlate_entities(entities, findings)
    inv = build_investigation(raw_input, input_type, user_id, entities,
                              findings, relationships)
    Store.save_investigation(inv)
    try:
        from app.services import learning
        learning.record_run(raw_input, input_type, entities,
                            {f.source for f in findings})
    except Exception:
        pass  # learning must never break the pipeline
    return inv


def _expand_domain_ips(entities: list[Entity], findings: list[Finding]) -> None:
    """Add IP entities discovered from DNS A/AAAA records (depth 1)."""
    known = {e.value.lower() for e in entities}
    for parent in list(entities):
        if parent.type != "domain":
            continue
        for ip_value, _, _ in find_domain_ip_links(parent, findings):
            if len(entities) >= MAX_TOTAL_ENTITIES:
                return
            if ip_value.lower() in known:
                continue
            entities.append(entity_from("ip", ip_value))
            known.add(ip_value.lower())


def _run_connectors(entity: Entity):
    for connector in connectors_for(entity.type):
        yield connector.run(entity.type, entity.value)


def enrich_findings_with_confidence(findings: list[Finding]) -> list[Finding]:
    for f in findings:
        score, _ = compute_confidence(f.evidence_count, {f.source})
        f.confidence = round(max(f.confidence, score), 2)
    return findings