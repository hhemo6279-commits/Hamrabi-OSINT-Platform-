from fastapi import APIRouter, Depends, HTTPException
import secrets

from app.core.security import get_current_user
from app.models.entities import User
from app.schemas import api as schemas
from app.services.pipeline import create_investigation
from app.services.store import Store
import app.services.report as report_service

router = APIRouter(prefix="/api/investigations", tags=["investigations"])


@router.get("/suggestions")
def suggest(out: str = "", user: User = Depends(get_current_user)):
    from app.services import learning
    suggestions = learning.suggestions(out, limit=4)
    stats = learning.get_stats()
    return schemas.SuggestOut(suggestions=suggestions, stats={
        "total_runs": stats["total_runs"],
        "sources": stats["source_counts"],
    })


def _to_dto(inv):
    return schemas.InvestigationOut(
        id=inv.id,
        raw_input=inv.raw_input,
        input_type=inv.input_type,
        entities=[schemas.EntityOut(**e.__dict__) for e in inv.entities],
        findings=[schemas.FindingOut(**f.__dict__) for f in inv.findings],
        relationships=[schemas.RelationshipOut(
            key=f"{r.source_id}-{r.target_id}-{r.relation}",
            source_id=r.source_id, target_id=r.target_id,
            relation=r.relation, confidence=r.confidence,
        ) for r in inv.relationships],
        created_at=inv.created_at,
        report_path=inv.report_path,
        ai_summary=inv.ai_summary,
        ai_classification=inv.ai_classification,
        tags=inv.tags or [],
    )


@router.post("", response_model=schemas.InvestigationOut, status_code=201)
def new(body: schemas.NewInvestigationRequest, user: User = Depends(get_current_user)):
    inv = create_investigation(body.raw_input, user.id)
    return _to_dto(inv)


@router.get("", response_model=list[schemas.InvestigationOut])
def list_inv(user: User = Depends(get_current_user)):
    return [_to_dto(i) for i in Store.list_investigations(user.id)]


@router.get("/{inv_id}", response_model=schemas.InvestigationOut)
def get_inv(inv_id: str, user: User = Depends(get_current_user)):
    inv = Store.get_investigation(inv_id)
    if not inv or inv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return _to_dto(inv)


@router.get("/{inv_id}/graph", response_model=schemas.GraphOut)
def graph(inv_id: str, user: User = Depends(get_current_user)):
    inv = Store.get_investigation(inv_id)
    if not inv or inv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Investigation not found")
    nodes = [{"id": e.id, "label": e.value, "type": e.type} for e in inv.entities]
    links = [{"source": r.source_id, "target": r.target_id,
              "relation": r.relation} for r in inv.relationships]
    return schemas.GraphOut(nodes=nodes, links=links)


@router.post("/{inv_id}/report")
def report(inv_id: str, user: User = Depends(get_current_user)):
    inv = Store.get_investigation(inv_id)
    if not inv or inv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Investigation not found")
    path = report_service.generate_pdf(inv)
    if path is None:
        raise HTTPException(status_code=503,
                            detail="Report generation disabled (install reportlab)")
    inv.report_path = str(path)
    if not inv.share_token:
        inv.share_token = secrets.token_urlsafe(24)
    Store.save_investigation(inv)
    return {
        "path": str(path),
        "exists": path.exists(),
        "share_token": inv.share_token,
        "share_url": f"/api/share/pdf/{inv.share_token}",
    }


@router.patch("/{inv_id}/tags")
def update_tags(inv_id: str, body: schemas.TagRequest,
                user: User = Depends(get_current_user)):
    inv = Store.set_tags(inv_id, body.tags, user.id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return _to_dto(inv)


@router.get("/{inv_id}/export/json")
def export_json(inv_id: str, user: User = Depends(get_current_user)):
    inv = Store.get_investigation(inv_id)
    if not inv or inv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Investigation not found")
    from app.services.export_data import investigations_to_json
    filename, text = investigations_to_json([inv])
    from fastapi.responses import Response
    return Response(text, media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/{inv_id}/export/csv")
def export_csv(inv_id: str, user: User = Depends(get_current_user)):
    inv = Store.get_investigation(inv_id)
    if not inv or inv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Investigation not found")
    from app.services.export_data import investigations_to_csv
    filename, text = investigations_to_csv([inv])
    from fastapi.responses import Response
    return Response("\ufeff" + text, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/diff/{left_id}/{right_id}")
def compare_investigations(left_id: str, right_id: str,
                           user: User = Depends(get_current_user)):
    if left_id == "suggestions":
        raise HTTPException(status_code=404, detail="Not found")
    from app.services import compare as compare_svc
    left = Store.get_investigation(left_id)
    right = Store.get_investigation(right_id)
    if not left or not right:
        raise HTTPException(status_code=404, detail="Investigation not found")
    if left.user_id != user.id or right.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return compare_svc.compare(left, right)
