import hashlib
import uuid
from datetime import datetime, timezone

from app.models.entities import Entity, Finding, Investigation, Relationship


def _entity_id(entity_type: str, value: str) -> str:
    key = f"{entity_type}:{value.lower()}".encode()
    return hashlib.sha1(key).hexdigest()[:16]


def entity_from(kind: str, value: str) -> Entity:
    return Entity(id=_entity_id(kind, value), type=kind, value=value)


def make_id() -> str:
    return uuid.uuid4().hex[:16]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_investigation(
    raw_input: str,
    input_type: str,
    user_id: str,
    entities: list[Entity],
    findings: list[Finding],
    relationships: list[Relationship],
) -> Investigation:
    return Investigation(
        id=make_id(),
        user_id=user_id,
        raw_input=raw_input,
        input_type=input_type,
        entities=entities,
        findings=findings,
        relationships=relationships,
    )


def correlate_entities(entities: list[Entity], findings: list[Finding]) -> list[Relationship]:
    """Derive relationships from entity types and finding attributes."""
    links: list[Relationship] = []
    by_value = {e.value.lower(): e for e in entities}

    # email -> domain  (from its own address suffix)
    for e in entities:
        if e.type == "email" and "@" in e.value:
            domain = e.value.split("@", 1)[1].lower()
            target = by_value.get(domain)
            if target:
                links.append(Relationship(e.id, target.id, "uses_domain", 0.95))

    # domain -> ip   (resolved from DNS records)
    for e in entities:
        if e.type != "domain":
            continue
        f = next((x for x in findings if getattr(x, "source", "") == "dns"
                  and str(getattr(x, "query", "")).lower() == e.value.lower()), None)
        if f and isinstance(f.value, dict):
            for rtype in ("A", "AAAA"):
                for addr in (f.value.get("records", {}).get(rtype, []) if isinstance(f.value.get("records"), dict) else []):
                    ip_entity = by_value.get(str(addr).lower())
                    if ip_entity:
                        links.append(
                            Relationship(e.id, ip_entity.id,
                                         "resolves_to", 0.9 if rtype == "A" else 0.85))

    # finding-originated links
    for f in findings:
        value = f.value
        refs = value.get("entities", []) if isinstance(value, dict) else []
        for ref in refs:
            trg = by_value.get(str(ref).lower())
            if trg and f.query:
                src = by_value.get(f.query.lower())
                if src:
                    links.append(Relationship(src.id, trg.id, f"linked_by_{f.source}", 0.6))

    # dedupe
    seen: set = set()
    unique: list[Relationship] = []
    for r in links:
        key = f"{r.source_id}-{r.target_id}-{r.relation}"
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def find_domain_ip_links(entity: Entity, findings: list[Finding]) -> list[tuple[str, str, float]]:
    """Return [(ip_value, relation, confidence), ...] that a domain resolves to."""
    out = []
    if entity.type != "domain":
        return out
    f = next((x for x in findings if getattr(x, "source", "") == "dns"
              and str(getattr(x, "query", "")).lower() == entity.value.lower()), None)
    if f is None or not isinstance(f.value, dict):
        return out
    for rtype, rel, conf in (("A", "resolves_to", 0.9), ("AAAA", "resolves_to", 0.85)):
        records = f.value.get("records", {})
        if isinstance(records, dict):
            for addr in records.get(rtype, []):
                out.append((str(addr), rel, conf))
    return out