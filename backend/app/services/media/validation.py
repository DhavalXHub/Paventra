"""Upload validation helpers — reject invalid images without inventing content."""
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

from app.core.config import settings

_IMAGE_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


def safe_upload_name(original: str | None, default_ext: str = ".jpg") -> str:
    """Return a random filename using only the original's suffix if it is allowed."""
    import secrets

    ext = Path(original or "").suffix.lower()
    allowed = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".avi", ".json"}
    if ext not in allowed:
        ext = default_ext
    return f"{secrets.token_hex(16)}{ext}"


def validate_image_bytes(content: bytes) -> None:
    """Reject empty, corrupt, or undersized images. Does not alter pixels."""
    if not content:
        raise HTTPException(status_code=400, detail="Empty image file")
    try:
        with Image.open(BytesIO(content)) as img:
            img.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid or corrupt image")

    try:
        with Image.open(BytesIO(content)) as img:
            width, height = img.size
            fmt = (img.format or "").upper()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid or corrupt image")

    if width < 10 or height < 10:
        raise HTTPException(status_code=400, detail="Image is too small to use as evidence")
    if fmt not in _IMAGE_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unsupported image format: {fmt or 'unknown'}")


def enforce_upload_size(content: bytes, *, max_bytes: int | None = None) -> None:
    limit = max_bytes if max_bytes is not None else settings.max_upload_bytes
    if len(content) > limit:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit",
        )
