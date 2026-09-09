"""Public share endpoint — lets anyone with a share token download the PDF
report of an investigation. The token is unguessable and stored with the
investigation; it does NOT expose the investigation data itself.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services.store import Store

router = APIRouter(prefix="/api/share", tags=["share"])


@router.get("/pdf/{token}")
def shared_pdf(token: str):
    inv = Store.get_investigation_by_share_token(token)
    if inv is None or not inv.report_path:
        raise HTTPException(status_code=404, detail="No shared report found")
    path = Path(inv.report_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report file is missing")
    filename = f"Hamrabi_{inv.id}.pdf"
    return FileResponse(str(path), media_type="application/pdf",
                        filename=filename)