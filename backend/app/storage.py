"""Image upload validation and disk storage."""

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from .config import get_settings

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}

# Tests monkeypatch this to a tmp dir.
UPLOAD_DIR = Path(get_settings().upload_dir)


def _max_bytes() -> int:
    return get_settings().max_upload_mb * 1024 * 1024


def save_upload(upload: UploadFile) -> str:
    """Validate and persist an uploaded image.

    Returns the public URL path (e.g. "/uploads/<uuid>.jpg").
    Raises HTTPException(400/413) on invalid input.
    """
    content_type = (upload.content_type or "").lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {upload.content_type or 'unknown'}. "
            "Allowed: JPEG, PNG, GIF, WebP.",
        )

    ext = ALLOWED_CONTENT_TYPES[content_type]
    filename = f"{uuid.uuid4().hex}{ext}"

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / filename

    size = 0
    max_bytes = _max_bytes()
    with dest.open("wb") as f:
        while chunk := upload.file.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File too large. Max {get_settings().max_upload_mb} MB.",
                )
            f.write(chunk)

    if size == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file.",
        )
    return f"/uploads/{filename}"


def delete_upload(image_url: str) -> None:
    """Best-effort removal of a previously saved upload (by its URL path)."""
    if not image_url.startswith("/uploads/"):
        return  # seeded/external URLs are not ours to delete
    try:
        (UPLOAD_DIR / Path(image_url).name).unlink(missing_ok=True)
    except OSError:
        pass
