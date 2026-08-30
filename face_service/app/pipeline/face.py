from dataclasses import dataclass

import numpy as np

from app.core.config import Settings
from app.core.errors import FaceServiceError
from app.core.images import decode_image
from app.models.loader import FaceModels
from app.pipeline.aligner import FaceAligner
from app.pipeline.detector import DetectedFace, FaceDetector
from app.pipeline.embedder import FaceEmbedder
from app.pipeline.pad import PadAssessor
from app.pipeline.quality import QualityAssessor


@dataclass(frozen=True, slots=True)
class FaceAnalysis:
    embedding: np.ndarray
    quality_score: float
    face: DetectedFace
    pad_live_score: float


class FacePipeline:
    def __init__(self, models: FaceModels, settings: Settings) -> None:
        self.settings = settings
        self.detector = FaceDetector(
            models.detector,
            models.detector_input_size,
            settings,
        )
        self.embedder = FaceEmbedder(models.embedder)
        self.aligner = FaceAligner(self.embedder.input_size)
        self.quality = QualityAssessor()
        self.pad = PadAssessor(models.pad_models)

    def decode(self, data: bytes, content_type: str) -> np.ndarray:
        return decode_image(data, content_type, self.settings)

    def analyze_bytes(self, data: bytes, content_type: str) -> FaceAnalysis:
        image = self.decode(data, content_type)
        faces = self.detector.detect(image)
        if not faces:
            raise FaceServiceError("NO_FACE", "Exactly one face is required", 400)
        if len(faces) != 1:
            raise FaceServiceError("MULTIPLE_FACES", "Exactly one face is required", 400)

        face = faces[0]
        quality = self.quality.assess(image, face).overall
        if quality < self.settings.MIN_QUALITY_SCORE:
            raise FaceServiceError("LOW_QUALITY", "Face image quality is too low", 400)

        aligned = self.aligner.align(image, face.landmarks)
        embedding = self.embedder.generate(aligned)
        pad_live_score = self.pad.live_score(image, face.bbox)
        return FaceAnalysis(
            embedding=embedding,
            quality_score=float(quality),
            face=face,
            pad_live_score=pad_live_score,
        )
