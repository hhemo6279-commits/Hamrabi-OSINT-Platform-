"""Persistent learning profile: the platform remembers what resources the user
investigated, which findings were useful, and suggests related indicators and
sources for the next investigation. This is fully local (access logs).
"""
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import BASE_DIR

LEARNING_PATH = BASE_DIR / "learning.json"

LOCK = threading.Lock()


def _default():
    return {"runs": [], "entities": {}, "source_counts": {}}


def _load() -> dict:
    if LEARNING_PATH.exists():
        try:
            return json.loads(LEARNING_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return _default()


def _save(data: dict):
    LEARNING_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def record_run(raw_input: str, input_type: str,
               entities: list, sources: list) -> None:
    """Learn from a scan: remember entities and sources that produced output."""
    with LOCK:
        data = _load()
        data["runs"].append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "raw_input": raw_input,
            "input_type": input_type,
        })
        data["runs"] = data["runs"][-200:]
        for e in entities:
            key = f"{e.type}:{e.value.lower()}"
            data["entities"][key] = data["entities"].get(key, 0) + 1
        for s in sources:
            data["source_counts"][s] = data["source_counts"].get(s, 0) + 1
        _save(data)


def suggestions(raw_input: str, limit: int = 4) -> list[dict]:
    """Suggest related indicators from what the user investigated before."""
    from app.modules.entity_extraction import extract_entities
    current = {f"{e['type']}:{e['value'].lower()}"
               for e in extract_entities(raw_input or "")}

    with LOCK:
        data = _load()
        scored = []
        for key, count in data["entities"].items():
            if key in current:
                continue
            etype, _, value = key.partition(":")
            if not value:
                continue
            scored.append({"type": etype, "value": value,
                           "times_seen": count, "hint": "seen before"})
        scored.sort(key=lambda x: -x["times_seen"])
        return scored[:limit]


def get_stats() -> dict:
    with LOCK:
        data = _load()
        return {
            "total_runs": len(data["runs"]),
            "entity_counts": data["entities"],
            "source_counts": data["source_counts"],
        }