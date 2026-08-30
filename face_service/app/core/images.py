import io

import cv2
import numpy as np
from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import Settings
from app.core.errors import FaceServiceError, invalid_image

SUPPORTED_CONTENT_TYPES = {"image/jpeg": "JPEG", "image/png": "PNG"}


async def read_upload(upload: UploadFile, settings: Settings) -> tuple[bytes, str]:
    content_type = (upload.content_type or "").lower()
    if content_type not in SUPPORTED_CONTENT_TYPES:
        raise FaceServiceError(
            "UNSUPPORTED_MEDIA_TYPE",
            "Only JPEG and PNG images are supported",
            415,
        )

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(min(1024 * 1024, settings.MAX_UPLOAD_BYTES + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > settings.MAX_UPLOAD_BYTES:
            raise FaceServiceError("IMAGE_TOO_LARGE", "Image exceeds the 10 MiB limit", 413)
    if total == 0:
        raise invalid_image()
    return b"".join(chunks), content_type


def decode_image(data: bytes, content_type: str, settings: Settings) -> np.ndarray:
    try:
        with Image.open(io.BytesIO(data)) as source:
            if source.format != SUPPORTED_CONTENT_TYPES.get(content_type):
                raise invalid_image()
            width, height = source.size
            if width <= 0 or height <= 0:
                raise invalid_image()
            if width > settings.MAX_IMAGE_DIMENSION or height > settings.MAX_IMAGE_DIMENSION:
                raise FaceServiceError("IMAGE_TOO_LARGE", "Image dimensions exceed the limit", 413)
            if width * height > settings.MAX_IMAGE_PIXELS:
                raise FaceServiceError(
                    "IMAGE_TOO_LARGE", "Decoded image exceeds the pixel limit", 413
                )
            source.load()
            oriented = ImageOps.exif_transpose(source)
            rgb = np.asarray(oriented.convert("RGB"), dtype=np.uint8)
    except FaceServiceError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise invalid_image() from exc

    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
