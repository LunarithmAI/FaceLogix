from dataclasses import dataclass


@dataclass(slots=True)
class FaceServiceError(Exception):
    code: str
    message: str
    status_code: int

    def __str__(self) -> str:
        return self.code


def invalid_image() -> FaceServiceError:
    return FaceServiceError("INVALID_IMAGE", "The image could not be decoded", 400)
