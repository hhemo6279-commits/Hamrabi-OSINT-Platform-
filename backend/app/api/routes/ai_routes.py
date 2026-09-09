from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_user
from app.models.entities import User
from app.schemas.api import AIAnalysisOut
from app.services.ai import AIClient
from app.services.store import Store

router = APIRouter(prefix="/api/investigations")
AI = AIClient()


@router.get("/{inv_id}/social")
def social(inv_id: str, user: User = Depends(get_current_user)):
    """Summarise the social-media evidence attached to an investigation."""
    inv = Store.get_investigation(inv_id)
    if not inv or inv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Investigation not found")

    platforms = []
    analysis = {"comments": [], "counts": {"positive": 0, "negative": 0,
                "neutral": 0}, "total": 0, "good_ratio": 0.0, "bad_ratio": 0.0,
                "provider": "rules"}
    for f in inv.findings:
        if f.source != "social":
            continue
        value = f.value or {}
        if isinstance(value.get("platforms"), list):
            platforms.extend(value["platforms"])
        if isinstance(value.get("analysis"), dict):
            a = value["analysis"]
            for k in ("good_ratio", "bad_ratio", "provider", "total"):
                if k in a:
                    analysis[k] = a[k]
            for k in ("positive", "negative", "neutral"):
                if k in (a.get("counts") or {}):
                    analysis["counts"][k] += a["counts"][k]

    return {"handle": platforms[0]["handle"] if platforms else None,
            "platforms": platforms, "analysis": analysis}


@router.post("/{inv_id}/ai", response_model=AIAnalysisOut)
def analyze(inv_id: str, user: User = Depends(get_current_user)):
    inv = Store.get_investigation(inv_id)
    if not inv or inv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Investigation not found")

    summary = AI.summarize(inv)
    classification = AI.classify(inv)

    inv.ai_summary = summary
    inv.ai_classification = classification
    Store.save_investigation(inv)

    return AIAnalysisOut(
        summary=summary,
        classification=classification,
        provider=AI.provider,
        enabled=AI.enabled,
    )


@router.post("/{inv_id}/explain/{rel_id}")
def explain_rel(inv_id: str, rel_id: str, user: User = Depends(get_current_user)):
    inv = Store.get_investigation(inv_id)
    if not inv or inv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Investigation not found")
    rel = next((r for r in inv.relationships if build_rel_key(r) == rel_id), None)
    if rel is None:
        raise HTTPException(status_code=404, detail="Relationship not found")
    return {"explanation": AI.explain(inv, rel)}


def build_rel_key(r) -> str:
    return f"{r.source_id}-{r.target_id}-{r.relation}"