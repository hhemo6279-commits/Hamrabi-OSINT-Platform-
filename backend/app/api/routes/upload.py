from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from app.core.security import get_current_user
from app.models.entities import Finding, User
from app.modules.correlation import now_iso
from app.modules.ocr import extract_image_info
from app.schemas.api import InvestigationOut
from app.api.routes.investigations import _to_dto
from app.services.pipeline import create_investigation

router = APIRouter(prefix="/api/upload", tags=["upload"])

MAX_TEXT_UPLOAD = 512 * 1024


def _read_text(file: UploadFile) -> str:
    content = file.file.read(MAX_TEXT_UPLOAD + 1)
    if len(content) > MAX_TEXT_UPLOAD:
        raise HTTPException(status_code=413, detail="File too large (max 512 KB)")
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return content.decode("latin-1")
        except Exception:
            raise HTTPException(status_code=422, detail="Unsupported encoding")


@router.post("/text", response_model=InvestigationOut)
def process_text(file: UploadFile = File(...),
                 user: User = Depends(get_current_user)):
    name = (file.filename or "upload").lower()
    if not name.endswith((".txt", ".csv", ".log", ".json")):
        raise HTTPException(status_code=415,
                            detail="Only txt, csv, log or json files are supported")
    raw = _read_text(file).strip()
    if not raw:
        raise HTTPException(status_code=422, detail="File is empty")
    inv = create_investigation(raw, user.id)
    return _to_dto(inv)


@router.post("/image", response_model=InvestigationOut)
def process(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    info = extract_image_info(file)

    extra = []
    if info["exif"]:
        extra.append(Finding(
            key=f"image_metadata:{file.filename or 'image'}",
            value={"exif": info["exif"], "size": info["size"],
                   "format": info["format"]},
            source="image_metadata",
            query=file.filename or "upload",
            timestamp=now_iso(),
            confidence=0.6,
            evidence_count=len(info["exif"]),
        ))

    if not info["text"] and not extra:
        raise HTTPException(status_code=422, detail="No text or metadata found in image")

    inv = create_investigation(info["text"] or "[image upload]",
                               user.id, extra_findings=extra)
    return _to_dto(inv)