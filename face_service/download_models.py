#!/usr/bin/env python3
import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

import httpx
import onnx
import onnxruntime as ort

from app.core.config import Settings
from app.models.loader import ModelValidationError, validate_and_warm_session, verify_model_bytes
from app.models.manifest import MODEL_MANIFEST, ModelSpec


def validate_onnx(path: Path, spec: ModelSpec, settings: Settings) -> None:
    try:
        onnx.checker.check_model(str(path))
        options = ort.SessionOptions()
        options.intra_op_num_threads = settings.ORT_INTRA_OP_THREADS
        options.inter_op_num_threads = settings.ORT_INTER_OP_THREADS
        session = ort.InferenceSession(
            str(path),
            sess_options=options,
            providers=settings.ONNX_PROVIDERS,
        )
        validate_and_warm_session(session, spec)
    except ModelValidationError:
        raise
    except Exception as exc:
        raise ModelValidationError(f"Invalid ONNX model: {spec.filename}") from exc


def verify(path: Path, spec: ModelSpec, settings: Settings) -> None:
    verify_model_bytes(path, spec)
    validate_onnx(path, spec, settings)


def temporary_path(destination: Path) -> Path:
    file_descriptor, name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(file_descriptor)
    return Path(name)


def download(spec: ModelSpec, destination: Path, settings: Settings) -> None:
    temporary = temporary_path(destination)
    try:
        with httpx.stream("GET", spec.url, follow_redirects=True, timeout=120.0) as response:
            response.raise_for_status()
            with temporary.open("wb") as output:
                for chunk in response.iter_bytes(1024 * 1024):
                    output.write(chunk)
        verify_model_bytes(temporary, spec)
        validate_onnx(temporary, spec, settings)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def copy_offline(
    spec: ModelSpec,
    source_dir: Path,
    destination: Path,
    settings: Settings,
) -> None:
    source = source_dir / spec.filename
    verify(source, spec, settings)
    if source.resolve() == destination.resolve():
        return
    temporary = temporary_path(destination)
    try:
        with source.open("rb") as input_file, temporary.open("wb") as output_file:
            shutil.copyfileobj(input_file, output_file, length=1024 * 1024)
        verify_model_bytes(temporary, spec)
        validate_onnx(temporary, spec, settings)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install and verify FaceLogix ONNX models")
    parser.add_argument("--models-dir", type=Path, default=Path("models"))
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--copy-from", type=Path)
    args = parser.parse_args()
    if args.verify_only and args.copy_from is not None:
        parser.error("--verify-only and --copy-from are mutually exclusive")
    return args


def main() -> int:
    args = parse_args()
    models_dir: Path = args.models_dir
    models_dir.mkdir(parents=True, exist_ok=True)
    settings = Settings(MODELS_DIR=models_dir, _env_file=None)

    try:
        for spec in MODEL_MANIFEST:
            destination = models_dir / spec.filename
            if args.verify_only:
                verify(destination, spec, settings)
                continue
            if args.copy_from is not None:
                copy_offline(spec, args.copy_from, destination, settings)
            elif not destination.exists():
                download(spec, destination, settings)
            else:
                verify(destination, spec, settings)
            destination.chmod(0o644)
    except (httpx.HTTPError, OSError, ModelValidationError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
