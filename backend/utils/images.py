"""Image handling for workshop photo uploads. Resize, strip EXIF, save to static dir."""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageOps

MAX_DIMENSION = 1600  # max width or height for stored full-size image
THUMB_DIMENSION = 400  # square-ish thumbnail
JPEG_QUALITY = 85
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}


class ImageProcessingError(Exception):
    """Raised when the upload cannot be decoded or fails validation."""


def process_upload(raw_bytes: bytes, dest_dir: Path, photo_id: str) -> tuple[str, str]:
    """Decode, normalize, resize, strip EXIF, save full + thumb.

    Returns (full_filename, thumb_filename).
    Raises ImageProcessingError if the bytes are not a valid image.
    """
    try:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            img = ImageOps.exif_transpose(img)  # honor EXIF orientation, then strip
            if img.mode in ("RGBA", "P", "LA"):
                img = img.convert("RGB")

            dest_dir.mkdir(parents=True, exist_ok=True)

            # Full-size (capped)
            full = img.copy()
            full.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
            full_name = f"{photo_id}.jpg"
            full.save(dest_dir / full_name, "JPEG", quality=JPEG_QUALITY, optimize=True)

            # Thumb
            thumb = img.copy()
            thumb.thumbnail((THUMB_DIMENSION, THUMB_DIMENSION), Image.Resampling.LANCZOS)
            thumb_name = f"{photo_id}_thumb.jpg"
            thumb.save(dest_dir / thumb_name, "JPEG", quality=80, optimize=True)

            return full_name, thumb_name
    except ImageProcessingError:
        raise
    except Exception as e:
        raise ImageProcessingError(f"Could not process image: {e}") from e
