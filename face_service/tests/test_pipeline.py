import io
from pathlib import Path
from types import SimpleNamespace

import anyio
import httpx
import numpy as np
import pytest
from fastapi import UploadFile
from PIL import Image
from starlette.datastructures import Headers

from app.api.deps import get_pipeline, run_inference
from app.core.config import Settings
from app.core.config import settings as runtime_settings
from app.core.errors import FaceServiceError
from app.core.images import decode_image, read_upload
from app.main import create_app, lifespan
from app.models.loader import ModelValidationError, PadModel
from app.models.manifest import MODEL_MANIFEST
from app.pipeline.detector import DetectedFace
from app.pipeline.face import FacePipeline
from app.pipeline.pad import PadAssessor, inclusive_scaled_crop, stable_softmax

EXPECTED_MANIFEST = {
    "det_10g.onnx": (
        16_923_827,
        "5838f7fe053675b1c7a08b633df49e7af5495cee0493c7dcf6697200b85b5b91",
    ),
    "w600k_r50.onnx": (
        174_383_860,
        "4c06341c33c2ca1f86781dab0e829f88ad5b64be9fba56e56bc9ebdefc619e43",
    ),
    "MiniFASNetV1SE.onnx": (
        1_742_335,
        "ebab7f90c7833fbccd46d3a555410e78d969db5438e169b6524be444862b3676",
    ),
    "MiniFASNetV2.onnx": (
        1_743_581,
        "b32929adc2d9c34b9486f8c4c7bc97c1b69bc0ea9befefc380e4faae4e463907",
    ),
}


def image_bytes(format_name: str = "JPEG", orientation: int | None = None) -> bytes:
    image = Image.new("RGB", (2, 3), color=(10, 20, 30))
    exif = Image.Exif()
    if orientation is not None:
        exif[274] = orientation
    output = io.BytesIO()
    image.save(output, format=format_name, exif=exif)
    return output.getvalue()


def upload(data: bytes, content_type: str) -> UploadFile:
    return UploadFile(file=io.BytesIO(data), headers=Headers({"content-type": content_type}))


def test_manifest_is_exact_and_immutable() -> None:
    assert {spec.filename: (spec.size, spec.sha256) for spec in MODEL_MANIFEST} == EXPECTED_MANIFEST
    assert [spec.crop_scale for spec in MODEL_MANIFEST if spec.kind == "pad"] == [4.0, 2.7]


@pytest.mark.asyncio
async def test_missing_and_corrupt_models_fail_startup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime_settings, "MODELS_DIR", tmp_path)
    with pytest.raises(ModelValidationError, match="missing"):
        async with lifespan(create_app()):
            pass

    detector = MODEL_MANIFEST[0]
    with (tmp_path / detector.filename).open("wb") as model_file:
        model_file.truncate(detector.size)
    with pytest.raises(ModelValidationError, match="checksum"):
        async with lifespan(create_app()):
            pass


@pytest.mark.asyncio
async def test_upload_is_bounded_and_rejects_media_type() -> None:
    settings = Settings(MAX_UPLOAD_BYTES=4, _env_file=None)
    with pytest.raises(FaceServiceError) as too_large:
        await read_upload(upload(b"12345", "image/jpeg"), settings)
    assert (too_large.value.code, too_large.value.status_code) == ("IMAGE_TOO_LARGE", 413)

    with pytest.raises(FaceServiceError) as unsupported:
        await read_upload(upload(b"123", "image/gif"), settings)
    assert (unsupported.value.code, unsupported.value.status_code) == (
        "UNSUPPORTED_MEDIA_TYPE",
        415,
    )


def test_jpeg_png_and_exif_orientation_decode_once() -> None:
    settings = Settings(_env_file=None)
    jpeg = decode_image(image_bytes("JPEG", orientation=6), "image/jpeg", settings)
    png = decode_image(image_bytes("PNG"), "image/png", settings)
    assert jpeg.shape == (2, 3, 3)
    assert png.shape == (3, 2, 3)
    assert jpeg.dtype == np.uint8


@pytest.mark.parametrize(
    "limit",
    ["dimension", "pixels"],
)
def test_decoded_image_limits(limit: str) -> None:
    settings = (
        Settings(MAX_IMAGE_DIMENSION=1, _env_file=None)
        if limit == "dimension"
        else Settings(MAX_IMAGE_PIXELS=5, _env_file=None)
    )
    with pytest.raises(FaceServiceError) as exc_info:
        decode_image(image_bytes("PNG"), "image/png", settings)
    assert exc_info.value.code == "IMAGE_TOO_LARGE"


def test_invalid_image_has_stable_error() -> None:
    with pytest.raises(FaceServiceError) as exc_info:
        decode_image(b"not-an-image", "image/jpeg", Settings(_env_file=None))
    assert (exc_info.value.code, exc_info.value.status_code) == ("INVALID_IMAGE", 400)


def test_inclusive_pad_crop_clamps_to_image() -> None:
    image = np.arange(10 * 10 * 3, dtype=np.uint8).reshape(10, 10, 3)
    crop = inclusive_scaled_crop(image, (0, 0, 4, 4), 4.0)
    assert crop.shape == (7, 7, 3)
    assert np.array_equal(crop[0, 0], image[0, 0])


def test_softmax_is_stable() -> None:
    probabilities = stable_softmax(np.array([[10_000.0, 10_001.0, 9_999.0]], dtype=np.float32))
    assert np.isfinite(probabilities).all()
    assert float(probabilities.sum()) == pytest.approx(1.0)


class FakeNode:
    name = "input"


class FakePadSession:
    def __init__(self, logits: list[float]) -> None:
        self.logits = np.array([logits], dtype=np.float32)
        self.tensor: np.ndarray | None = None

    def get_inputs(self) -> list[FakeNode]:
        return [FakeNode()]

    def run(self, _outputs: object, feeds: dict[str, np.ndarray]) -> list[np.ndarray]:
        self.tensor = feeds["input"]
        return [self.logits]


def test_pad_ensemble_uses_raw_bgr_float_tensor() -> None:
    first = FakePadSession([0.0, 2.0, 0.0])
    second = FakePadSession([0.0, 0.0, 0.0])
    assessor = PadAssessor(
        (
            PadModel(first, (4, 4), 4.0),
            PadModel(second, (4, 4), 2.7),
        )
    )
    image = np.zeros((8, 8, 3), dtype=np.uint8)
    image[:, :, 0] = 255
    score = assessor.live_score(image, (2, 2, 6, 6))
    assert score == pytest.approx((0.786986 + 1 / 3) / 2, rel=1e-5)
    assert first.tensor is not None
    assert first.tensor.dtype == np.float32
    assert first.tensor.shape == (1, 3, 4, 4)
    assert np.all(first.tensor[0, 0] == 255)
    assert np.all(first.tensor[0, 2] == 0)


class FakeDetector:
    def __init__(self, faces: list[DetectedFace]) -> None:
        self.faces = faces

    def detect(self, _image: np.ndarray) -> list[DetectedFace]:
        return self.faces


class FakeQuality:
    def __init__(self, score: float = 0.9) -> None:
        self.score = score

    def assess(self, _image: np.ndarray, _face: DetectedFace) -> SimpleNamespace:
        return SimpleNamespace(overall=self.score)


class FakeAligner:
    def align(self, image: np.ndarray, _landmarks: np.ndarray) -> np.ndarray:
        return image


class FakeEmbedder:
    def generate(self, _image: np.ndarray) -> np.ndarray:
        return np.full(512, 1 / np.sqrt(512), dtype=np.float32)


class FakePad:
    def live_score(self, _image: np.ndarray, _bbox: tuple[int, int, int, int]) -> float:
        return 0.8


def fake_pipeline(faces: list[DetectedFace]) -> FacePipeline:
    pipeline = FacePipeline.__new__(FacePipeline)
    pipeline.settings = Settings(_env_file=None)
    pipeline.detector = FakeDetector(faces)  # type: ignore[assignment]
    pipeline.quality = FakeQuality()  # type: ignore[assignment]
    pipeline.aligner = FakeAligner()  # type: ignore[assignment]
    pipeline.embedder = FakeEmbedder()  # type: ignore[assignment]
    pipeline.pad = FakePad()  # type: ignore[assignment]
    pipeline.decode = lambda _data, _content_type: np.zeros(  # type: ignore[assignment]
        (32, 32, 3), dtype=np.uint8
    )
    return pipeline


def face() -> DetectedFace:
    return DetectedFace((4, 4, 24, 24), 0.99, np.zeros((5, 2), dtype=np.float32))


@pytest.mark.parametrize(
    ("faces", "code"),
    [([], "NO_FACE"), ([face(), face()], "MULTIPLE_FACES")],
)
def test_analysis_requires_exactly_one_face(faces: list[DetectedFace], code: str) -> None:
    with pytest.raises(FaceServiceError) as exc_info:
        fake_pipeline(faces).analyze_bytes(b"image", "image/jpeg")
    assert exc_info.value.code == code


def test_analysis_rejects_low_quality() -> None:
    pipeline = fake_pipeline([face()])
    pipeline.quality = FakeQuality(0.1)  # type: ignore[assignment]
    with pytest.raises(FaceServiceError) as exc_info:
        pipeline.analyze_bytes(b"image", "image/jpeg")
    assert exc_info.value.code == "LOW_QUALITY"


@pytest.mark.asyncio
async def test_analyze_endpoint_returns_exact_contract() -> None:
    pipeline = fake_pipeline([face()])
    application = create_app()
    application.state.inference_limiter = anyio.CapacityLimiter(1)
    application.dependency_overrides[get_pipeline] = lambda: pipeline
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/analyze",
            files={"image": ("face.jpg", b"image", "image/jpeg")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"embedding", "quality_score", "bbox", "pad_live_score"}
    assert len(payload["embedding"]) == 512
    assert payload["pad_live_score"] == 0.8


def test_analysis_returns_512_finite_embedding_and_pad_score() -> None:
    result = fake_pipeline([face()]).analyze_bytes(b"image", "image/jpeg")
    assert result.embedding.shape == (512,)
    assert np.isfinite(result.embedding).all()
    assert result.pad_live_score == 0.8


@pytest.mark.asyncio
async def test_inference_capacity_fails_without_waiting() -> None:
    limiter = anyio.CapacityLimiter(1)
    limiter.acquire_on_behalf_of_nowait("occupied")
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(inference_limiter=limiter)))
    try:
        with pytest.raises(FaceServiceError) as exc_info:
            await run_inference(request, lambda: 1)  # type: ignore[arg-type]
        assert (exc_info.value.code, exc_info.value.status_code) == (
            "INFERENCE_BUSY",
            429,
        )
    finally:
        limiter.release_on_behalf_of("occupied")


@pytest.mark.asyncio
async def test_health_distinguishes_liveness_from_readiness() -> None:
    application = create_app()
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        live = await client.get("/health/live")
        ready = await client.get("/health/ready")
    assert live.status_code == 200
    assert ready.status_code == 503
    assert ready.json()["detail"]["code"] == "MODEL_UNAVAILABLE"
