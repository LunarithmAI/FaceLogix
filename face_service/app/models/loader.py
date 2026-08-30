import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import numpy as np
import onnxruntime as ort

from app.core.config import Settings
from app.models.manifest import MODEL_MANIFEST, ModelSpec


class ModelValidationError(RuntimeError):
    pass


def verify_model_bytes(path: Path, spec: ModelSpec) -> None:
    try:
        stat = path.stat()
    except FileNotFoundError as exc:
        raise ModelValidationError(f"Required model is missing: {spec.filename}") from exc
    if stat.st_size != spec.size:
        raise ModelValidationError(f"Model size mismatch: {spec.filename}")

    digest = hashlib.sha256()
    with path.open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != spec.sha256:
        raise ModelValidationError(f"Model checksum mismatch: {spec.filename}")


def _static_dimension(value: object, label: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise ModelValidationError(f"{label} must be a positive static dimension")
    return value


def _validate_node_names(session: ort.InferenceSession, spec: ModelSpec) -> None:
    inputs = session.get_inputs()
    outputs = session.get_outputs()
    if len(inputs) != 1 or not inputs[0].name or inputs[0].type != "tensor(float)":
        raise ModelValidationError(f"Unexpected input metadata: {spec.filename}")
    output_names = [node.name for node in outputs]
    if (
        not output_names
        or any(not name for name in output_names)
        or len(set(output_names)) != len(output_names)
    ):
        raise ModelValidationError(f"Unexpected output names: {spec.filename}")
    if any(node.type != "tensor(float)" for node in outputs):
        raise ModelValidationError(f"Unexpected output dtype: {spec.filename}")


def validate_and_warm_session(session: ort.InferenceSession, spec: ModelSpec) -> tuple[int, int]:
    _validate_node_names(session, spec)
    input_node = session.get_inputs()[0]
    if len(input_node.shape) != 4:
        raise ModelValidationError(f"Unexpected input rank: {spec.filename}")
    channels = _static_dimension(input_node.shape[1], f"{spec.filename} channels")
    if channels != 3:
        raise ModelValidationError(f"Unexpected input shape: {spec.filename}")
    batch = input_node.shape[0]
    if isinstance(batch, int) and batch != 1:
        raise ModelValidationError(f"Unexpected input batch: {spec.filename}")
    if spec.kind == "detector":
        width, height = 640, 640
    else:
        height = _static_dimension(input_node.shape[2], f"{spec.filename} height")
        width = _static_dimension(input_node.shape[3], f"{spec.filename} width")

    outputs = session.run(
        None, {input_node.name: np.zeros((1, 3, height, width), dtype=np.float32)}
    )
    if spec.kind == "detector":
        if len(outputs) != 9:
            raise ModelValidationError("Detector must expose nine outputs")
        expected_widths = (1, 1, 1, 4, 4, 4, 10, 10, 10)
        if any(
            array.ndim != 2 or array.shape[-1] != expected
            for array, expected in zip(outputs, expected_widths, strict=True)
        ):
            raise ModelValidationError("Detector output metadata is invalid")
    elif spec.kind == "embedder":
        if len(outputs) != 1 or outputs[0].size != 512 or not np.isfinite(outputs[0]).all():
            raise ModelValidationError("Embedder must return 512 finite values")
    elif spec.kind == "pad":
        if len(outputs) != 1 or outputs[0].shape != (1, 3) or not np.isfinite(outputs[0]).all():
            raise ModelValidationError("PAD model must return [1, 3] finite logits")
    else:
        raise ModelValidationError(f"Unknown model kind: {spec.kind}")
    return width, height


def create_session(
    path: Path,
    spec: ModelSpec,
    settings: Settings,
) -> tuple[ort.InferenceSession, tuple[int, int]]:
    verify_model_bytes(path, spec)
    options = ort.SessionOptions()
    options.intra_op_num_threads = settings.ORT_INTRA_OP_THREADS
    options.inter_op_num_threads = settings.ORT_INTER_OP_THREADS
    try:
        session = ort.InferenceSession(
            str(path),
            sess_options=options,
            providers=settings.ONNX_PROVIDERS,
        )
        input_size = validate_and_warm_session(session, spec)
    except ModelValidationError:
        raise
    except Exception as exc:
        raise ModelValidationError(f"Unable to load model: {spec.filename}") from exc
    return session, input_size


@dataclass(frozen=True, slots=True)
class PadModel:
    session: ort.InferenceSession
    input_size: tuple[int, int]
    crop_scale: float


@dataclass(frozen=True, slots=True)
class FaceModels:
    detector: ort.InferenceSession
    detector_input_size: tuple[int, int]
    embedder: ort.InferenceSession
    pad_models: tuple[PadModel, PadModel]

    @classmethod
    def load(cls, settings: Settings) -> "FaceModels":
        sessions: dict[str, ort.InferenceSession] = {}
        sizes: dict[str, tuple[int, int]] = {}
        for spec in MODEL_MANIFEST:
            session, input_size = create_session(
                settings.MODELS_DIR / spec.filename,
                spec,
                settings,
            )
            sessions[spec.filename] = session
            sizes[spec.filename] = input_size

        pad_specs = tuple(spec for spec in MODEL_MANIFEST if spec.kind == "pad")
        if len(pad_specs) != 2:
            raise ModelValidationError("Exactly two PAD models are required")
        pad_models = tuple(
            PadModel(
                session=sessions[spec.filename],
                input_size=sizes[spec.filename],
                crop_scale=cast(float, spec.crop_scale),
            )
            for spec in pad_specs
        )
        return cls(
            detector=sessions["det_10g.onnx"],
            detector_input_size=sizes["det_10g.onnx"],
            embedder=sessions["w600k_r50.onnx"],
            pad_models=cast(tuple[PadModel, PadModel], pad_models),
        )
