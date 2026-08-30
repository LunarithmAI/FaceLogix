from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelSpec:
    filename: str
    url: str
    size: int
    sha256: str
    kind: str
    crop_scale: float | None = None


MODEL_MANIFEST: tuple[ModelSpec, ...] = (
    ModelSpec(
        filename="det_10g.onnx",
        url="https://github.com/yakhyo/face-reidentification/releases/download/v0.0.1/det_10g.onnx",
        size=16_923_827,
        sha256="5838f7fe053675b1c7a08b633df49e7af5495cee0493c7dcf6697200b85b5b91",
        kind="detector",
    ),
    ModelSpec(
        filename="w600k_r50.onnx",
        url="https://github.com/yakhyo/face-reidentification/releases/download/v0.0.1/w600k_r50.onnx",
        size=174_383_860,
        sha256="4c06341c33c2ca1f86781dab0e829f88ad5b64be9fba56e56bc9ebdefc619e43",
        kind="embedder",
    ),
    ModelSpec(
        filename="MiniFASNetV1SE.onnx",
        url="https://github.com/yakhyo/face-anti-spoofing/releases/download/weights/MiniFASNetV1SE.onnx",
        size=1_742_335,
        sha256="ebab7f90c7833fbccd46d3a555410e78d969db5438e169b6524be444862b3676",
        kind="pad",
        crop_scale=4.0,
    ),
    ModelSpec(
        filename="MiniFASNetV2.onnx",
        url="https://github.com/yakhyo/face-anti-spoofing/releases/download/weights/MiniFASNetV2.onnx",
        size=1_743_581,
        sha256="b32929adc2d9c34b9486f8c4c7bc97c1b69bc0ea9befefc380e4faae4e463907",
        kind="pad",
        crop_scale=2.7,
    ),
)

MODEL_BY_FILENAME = {spec.filename: spec for spec in MODEL_MANIFEST}
