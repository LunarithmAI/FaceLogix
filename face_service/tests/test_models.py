import cv2
import numpy as np
import pytest

from app.core.config import Settings
from app.core.errors import FaceServiceError
from app.models.loader import FaceModels
from app.pipeline.face import FacePipeline


@pytest.mark.model
def test_production_models_validate_warm_and_infer() -> None:
    settings = Settings(_env_file=None)
    assert settings.MODELS_DIR.exists()
    models = FaceModels.load(settings)
    pipeline = FacePipeline(models, settings)

    encoded_ok, encoded = cv2.imencode(
        ".png",
        np.zeros((640, 640, 3), dtype=np.uint8),
    )
    assert encoded_ok
    with pytest.raises(FaceServiceError) as exc_info:
        pipeline.analyze_bytes(encoded.tobytes(), "image/png")
    assert exc_info.value.code == "NO_FACE"
