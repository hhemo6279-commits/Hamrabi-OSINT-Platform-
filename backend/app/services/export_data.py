"""Investigation export helpers: JSON, CSV — reusable by the API routes.

Every export flattens investigations into a portable, human-readable record
that can be re-imported or shared (legal/academic use only).
"""
import csv
import io
from datetime import datetime, timezone


def _finding_row(f, inv):
    return {
        "investigation_id": inv.id,
        "target": inv.raw_input,
        "source": f.get("source", ""),
        "query": f.get("query", ""),
        "confidence": f.get("confidence", ""),
        "evidence_count": f.get("evidence_count", ""),
        "timestamp": f.get("timestamp", ""),
        "value": _safe_json(f.get("value", "")),
    }


def _safe_json(value) -> str:
    import json
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


def investigations_to_csv(invs) -> tuple[str, str]:
    """Returns (filename, csv_text)."""
    rows = []
    for inv in invs:
        for f in inv.findings or []:
            rows.append(_finding_row(f.__dict__, inv))
        if inv.ai_summary:
            rows.append({
                "investigation_id": inv.id,
                "target": inv.raw_input,
                "source": "ai",
                "query": "",
                "confidence": "", "evidence_count": "",
                "timestamp": inv.created_at,
                "value": _safe_json({"summary": inv.ai_summary,
                                     "classification": inv.ai_classification}),
            })
        if not (inv.findings or []):
            rows.append({
                "investigation_id": inv.id,
                "target": inv.raw_input,
                "source": "empty", "query": "",
                "confidence": "", "evidence_count": "",
                "timestamp": inv.created_at, "value": "",
            })

    keys = ["investigation_id", "target", "source", "query",
            "confidence", "evidence_count", "timestamp", "value"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=keys, restval="")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k, "") for k in keys})
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"enki_export_{ts}.csv", buf.getvalue()


def investigations_to_json(invs) -> tuple[str, str]:
    """Returns (filename, json_text)."""
    payload = [{
        "id": inv.id,
        "created_at": inv.created_at,
        "target": inv.raw_input,
        "input_type": inv.input_type,
        "tags": inv.tags or [],
        "entities": [e.__dict__ for e in inv.entities],
        "findings": [
            {
                "source": f.source, "query": f.query,
                "confidence": f.confidence, "evidence_count": f.evidence_count,
                "timestamp": f.timestamp, "value": f.value,
            }
            for f in inv.findings
        ],
        "relationships": [r.__dict__ for r in inv.relationships],
        "ai_summary": inv.ai_summary,
        "ai_classification": inv.ai_classification,
    } for inv in invs]
    import json
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"enki_export_{ts}.json", json.dumps(payload, ensure_ascii=False, indent=2)