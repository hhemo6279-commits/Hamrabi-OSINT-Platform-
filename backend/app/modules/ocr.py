"""Image Intelligence — OCR text extraction plus image metadata (EXIF).

Separates the raw byte validation from text extraction so callers can
inspect metadata without running OCR.
"""
import io
import shutil

from fastapi import HTTPException, UploadFile

from app.core.config import ALLOWED_IMAGE_TYPES, MAX_UPLOAD_BYTES

# Magic byte signatures for allowed formats (independent of the Content-Type).
_MAGIC = {
    "image/png": bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]),
    "image/jpeg": bytes([0xFF, 0xD8, 0xFF]),
    "image/webp": b"RIFF",
}


def read_upload(file: UploadFile) -> bytes:
    content = file.file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image too large (max 5 MB)")
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported image type")
    if not _matches_magic(content, file.content_type):
        raise HTTPException(status_code=415, detail="File content does not match "
                                                    "declared image type")
    return content


def _matches_magic(content: bytes, content_type: str) -> bool:
    signature = _MAGIC.get(content_type)
    if signature is None:
        return False
    return content.startswith(signature)


def extract_text_from_image(file: UploadFile) -> str:
    content = read_upload(file)
    return _ocr(content)


def extract_image_info(file: UploadFile) -> dict:
    """Returns {'text': str, 'exif': {...}, 'size': (w,h), 'format': str}."""
    content = read_upload(file)
    result = {"text": _ocr(content), "exif": {}, "size": None, "format": None}
    try:
        from PIL import Image
    except ImportError:
        return result

    try:
        with Image.open(io.BytesIO(content)) as img:
            result["size"] = img.size
            result["format"] = img.format
            try:
                exif = img.getexif()
            except Exception:
                exif = {}
            if exif:
                result["exif"] = _exif_clean(exif)
    except Exception:
        pass
    return result


def _exif_clean(exif) -> dict:
    """Keep only the human-relevant EXIF fields (avoid dumping raw bytes)."""
    keep = {}
    mapping = {
        271: "make", 272: "model", 306: "datetime",
        36867: "datetime_original", 0x8825: "gps", 34855: "iso",
        33434: "exposure_time", 37386: "focal_length", 34850: "exposure_program",
    }
    for tag, label in mapping.items():
        if tag in exif:
            value = exif[tag]
            if isinstance(value, bytes):
                value = _decode_bytes(value)
            keep[label] = str(value)[:120]
    return keep


def _decode_bytes(value: bytes) -> str:
    try:
        return value.decode("utf-8", errors="replace").strip("\x00")
    except Exception:
        return repr(value)[:120]


def _ocr(content: bytes) -> str:
    try:
        from PIL import Image
        import pytesseract
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="OCR dependencies unavailable. Install pillow + pytesseract.",
        ) from exc

    if shutil.which("tesseract") is None:
        raise HTTPException(
            status_code=503,
            detail="Tesseract OCR engine not found on PATH. Install it from "
            "https://github.com/tesseract-ocr/tesseract",
        )

    try:
        image = Image.open(io.BytesIO(content))
        text = pytesseract.image_to_string(image)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"OCR failed: {exc}") from exc

    return text.strip()