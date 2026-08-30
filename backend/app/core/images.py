import base64
import binascii
from dataclasses import dataclass

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_BASE64_CHARACTERS = 4 * ((MAX_IMAGE_BYTES + 2) // 3)
DATA_URI_PREFIXES = {
    "data:image/jpeg;base64,": "image/jpeg",
    "data:image/png;base64,": "image/png",
}


@dataclass(slots=True)
class ImagePayloadError(Exception):
    code: str
    message: str
    status_code: int


def image_media_type(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    return None


def decode_image_payload(value: str) -> bytes:
    encoded = value
    declared_media_type: str | None = None
    if value.startswith("data:"):
        for prefix, media_type in DATA_URI_PREFIXES.items():
            if value.startswith(prefix):
                declared_media_type = media_type
                encoded = value[len(prefix) :]
                break
        else:
            raise ImagePayloadError(
                "UNSUPPORTED_MEDIA_TYPE",
                "Only JPEG and PNG data URIs are supported",
                415,
            )

    if not encoded:
        raise ImagePayloadError("INVALID_IMAGE", "Image data is empty", 400)
    if len(encoded) > MAX_BASE64_CHARACTERS:
        raise ImagePayloadError("IMAGE_TOO_LARGE", "Image exceeds the 10 MiB limit", 413)
    try:
        data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ImagePayloadError("INVALID_IMAGE", "Image data is not valid base64", 400) from exc
    if not data:
        raise ImagePayloadError("INVALID_IMAGE", "Image data is empty", 400)
    if len(data) > MAX_IMAGE_BYTES:
        raise ImagePayloadError("IMAGE_TOO_LARGE", "Image exceeds the 10 MiB limit", 413)

    detected_media_type = image_media_type(data)
    if detected_media_type is None:
        raise ImagePayloadError(
            "UNSUPPORTED_MEDIA_TYPE",
            "Only JPEG and PNG images are supported",
            415,
        )
    if declared_media_type is not None and declared_media_type != detected_media_type:
        raise ImagePayloadError("INVALID_IMAGE", "Data URI media type does not match image", 400)
    return data
