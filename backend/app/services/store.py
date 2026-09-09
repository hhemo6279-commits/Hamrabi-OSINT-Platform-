import json
import threading
from pathlib import Path

from app.core.config import DATABASE_PATH
from app.models.entities import User, Investigation


def _user_from_row(row: dict) -> User:
    return User(
        id=row["id"],
        username=row["username"],
        password_hash=row["password_hash"],
        role=row.get("role", "user"),
        created_at=row.get("created_at", ""),
    )


class _Store:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self._data = {"users": {}, "investigations": {}}
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {"users": {}, "investigations": {}}

    def _save(self):
        self.path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def create_user(self, user: User) -> User:
        with self._lock:
            self._data["users"][user.id] = {
                "id": user.id,
                "username": user.username,
                "password_hash": user.password_hash,
                "role": user.role,
                "created_at": user.created_at,
            }
            self._save()
            return user

    def get_user_by_username(self, username: str) -> User | None:
        with self._lock:
            for row in self._data["users"].values():
                if row["username"] == username:
                    return _user_from_row(row)
        return None

    def get_user_by_id(self, user_id: str) -> User | None:
        with self._lock:
            for row in self._data["users"].values():
                if row["id"] == user_id:
                    return _user_from_row(row)
        return None

    def save_investigation(self, inv: Investigation) -> Investigation:
        with self._lock:
            self._data["investigations"][inv.id] = {
                "id": inv.id,
                "user_id": inv.user_id,
                "raw_input": inv.raw_input,
                "input_type": inv.input_type,
                "entities": [e.__dict__ for e in inv.entities],
                "findings": [f.__dict__ for f in inv.findings],
                "relationships": [r.__dict__ for r in inv.relationships],
                "created_at": inv.created_at,
"report_path": inv.report_path,
                "share_token": inv.share_token,
                "ai_summary": inv.ai_summary,
                "ai_classification": inv.ai_classification,
                "tags": inv.tags or [],
            }
            self._save()
            return inv

    def set_tags(self, inv_id: str, tags: list, user_id: str) -> Investigation | None:
        inv = self.get_investigation(inv_id)
        if not inv or inv.user_id != user_id:
            return None
        inv.tags = [t.strip()[:40] for t in tags if t and t.strip()][:20]
        return self.save_investigation(inv)

    def get_investigation(self, inv_id: str) -> Investigation | None:
        with self._lock:
            row = self._data["investigations"].get(inv_id)
            if not row:
                return None
        inv = Investigation(
            id=row["id"],
            user_id=row["user_id"],
            raw_input=row["raw_input"],
            input_type=row["input_type"],
            entities=[EntityLike(**e) for e in row["entities"]],
            findings=[FindingLike(**f) for f in row["findings"]],
            relationships=[RelationshipLike(**r) for r in row["relationships"]],
created_at=row["created_at"],
            report_path=row.get("report_path"),
            share_token=row.get("share_token"),
            ai_summary=row.get("ai_summary"),
            ai_classification=row.get("ai_classification"),
            tags=row.get("tags", []) or [],
        )
        return inv

    def get_investigation_by_share_token(self, token: str) -> Investigation | None:
        with self._lock:
            inv_id = next((r.get("id") for r in self._data["investigations"].values()
                           if r.get("share_token") == token), None)
        if inv_id is None:
            return None
        return self.get_investigation(inv_id)

    def list_investigations(self, user_id: str) -> list[Investigation]:
        with self._lock:
            rows = [
                row
                for row in self._data["investigations"].values()
                if row["user_id"] == user_id
            ]
        rows.sort(key=lambda r: r["created_at"], reverse=True)
        out = []
        for row in rows:
            out.append(
                Investigation(
                    id=row["id"],
                    user_id=row["user_id"],
                    raw_input=row["raw_input"],
                    input_type=row["input_type"],
                    entities=[EntityLike(**e) for e in row["entities"]],
                    findings=[FindingLike(**f) for f in row["findings"]],
                    relationships=[RelationshipLike(**r) for r in row["relationships"]],
                    created_at=row["created_at"],
                    report_path=row.get("report_path"),
                    share_token=row.get("share_token"),
                    ai_summary=row.get("ai_summary"),
                    ai_classification=row.get("ai_classification"),
                    tags=row.get("tags", []) or [],
                )
            )
        return out


class EntityLike:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FindingLike:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class RelationshipLike:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


Store = _Store(DATABASE_PATH)
