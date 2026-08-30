import cv2
import numpy as np

from app.models.loader import PadModel


def inclusive_scaled_crop(
    image: np.ndarray,
    bbox_xyxy: tuple[int, int, int, int],
    model_scale: float,
) -> np.ndarray:
    image_height, image_width = image.shape[:2]
    x1, y1, x2, y2 = (int(value) for value in bbox_xyxy)
    width = x2 - x1
    height = y2 - y1
    if width <= 0 or height <= 0:
        raise ValueError("Face bounding box is empty")

    scale = min(
        (image_height - 1) / height,
        (image_width - 1) / width,
        model_scale,
    )
    center_x = x1 + width / 2.0
    center_y = y1 + height / 2.0
    scaled_width = width * scale
    scaled_height = height * scale
    crop_x1 = max(0, min(int(center_x - scaled_width / 2.0), image_width - 1))
    crop_y1 = max(0, min(int(center_y - scaled_height / 2.0), image_height - 1))
    crop_x2 = max(0, min(int(center_x + scaled_width / 2.0), image_width - 1))
    crop_y2 = max(0, min(int(center_y + scaled_height / 2.0), image_height - 1))
    if crop_x2 < crop_x1 or crop_y2 < crop_y1:
        raise ValueError("Scaled face crop is empty")
    return image[crop_y1 : crop_y2 + 1, crop_x1 : crop_x2 + 1]


def stable_softmax(logits: np.ndarray) -> np.ndarray:
    if logits.shape != (1, 3) or not np.isfinite(logits).all():
        raise RuntimeError("PAD inference returned invalid logits")
    shifted = logits - np.max(logits, axis=1, keepdims=True)
    exponentials = np.exp(shifted)
    return np.asarray(
        exponentials / np.sum(exponentials, axis=1, keepdims=True),
        dtype=np.float32,
    )


class PadAssessor:
    def __init__(self, models: tuple[PadModel, PadModel]):
        self.models = models

    def live_score(self, image: np.ndarray, bbox: tuple[int, int, int, int]) -> float:
        probabilities: list[np.ndarray] = []
        for model in self.models:
            crop = inclusive_scaled_crop(image, bbox, model.crop_scale)
            resized = cv2.resize(crop, model.input_size)
            tensor = resized.astype(np.float32).transpose(2, 0, 1)[None, ...]
            input_name = model.session.get_inputs()[0].name
            logits = np.asarray(model.session.run(None, {input_name: tensor})[0])
            probabilities.append(stable_softmax(logits))

        average = np.mean(np.stack(probabilities), axis=0)
        score = float(average[0, 1])
        if not np.isfinite(score):
            raise RuntimeError("PAD inference returned a non-finite score")
        return score
