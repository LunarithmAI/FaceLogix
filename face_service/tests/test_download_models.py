from pathlib import Path

import pytest

import download_models
from app.models.manifest import ModelSpec


def test_existing_models_become_runtime_readable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = ModelSpec(
        filename="model.onnx",
        url="https://example.test/model.onnx",
        size=1,
        sha256="0" * 64,
        kind="detector",
    )
    model = tmp_path / spec.filename
    model.write_bytes(b"x")
    model.chmod(0o600)

    monkeypatch.setattr(download_models, "MODEL_MANIFEST", (spec,))
    monkeypatch.setattr(download_models, "verify", lambda *_args: None)
    monkeypatch.setattr(
        "sys.argv",
        ["download_models.py", "--models-dir", str(tmp_path)],
    )

    assert download_models.main() == 0
    assert model.stat().st_mode & 0o777 == 0o644
