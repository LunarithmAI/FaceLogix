#!/usr/bin/env python3
"""
Script to download required ONNX models for face recognition.

Downloads RetinaFace detector and ArcFace embedder models from
InsightFace GitHub releases.

Usage:
    python download_models.py
"""

import sys
import urllib.request
from pathlib import Path


MODELS_DIR = Path("models")

# Model URLs from InsightFace releases
MODELS = {
    "det_10g.onnx": (
        "https://github.com/yakhyo/face-reidentification/releases"
        "/download/v0.0.1/det_10g.onnx"
    ),
    "w600k_r50.onnx": (
        "https://github.com/yakhyo/face-reidentification/releases"
        "/download/v0.0.1/w600k_r50.onnx"
    ),
}


def download_with_progress(url: str, filepath: Path) -> None:
    """
    Download a file with progress indication.
    
    Args:
        url: URL to download from
        filepath: Local path to save the file
    """
    def report_progress(block_num: int, block_size: int, total_size: int) -> None:
        if total_size > 0:
            percent = min(100, block_num * block_size * 100 // total_size)
            sys.stdout.write(f"\r  Progress: {percent}%")
            sys.stdout.flush()
    
    urllib.request.urlretrieve(url, filepath, reporthook=report_progress)
    print()  # New line after progress


def download_models() -> None:
    """
    Download all required ONNX models.
    
    Creates the models directory if it doesn't exist and downloads
    each model if not already present.
    """
    # Create models directory
    MODELS_DIR.mkdir(exist_ok=True)
    print(f"Models directory: {MODELS_DIR.absolute()}")
    print()
    
    for filename, url in MODELS.items():
        filepath = MODELS_DIR / filename
        
        if filepath.exists():
            print(f"[SKIP] {filename} already exists")
            continue
        
        print(f"[DOWNLOAD] {filename}")
        print(f"  URL: {url}")
        
        try:
            download_with_progress(url, filepath)
            file_size_mb = filepath.stat().st_size / (1024 * 1024)
            print(f"  Size: {file_size_mb:.1f} MB")
            print(f"  [OK] Downloaded successfully")
        except Exception as e:
            print(f"  [ERROR] Failed to download: {e}")
            # Clean up partial download
            if filepath.exists():
                filepath.unlink()
            raise
        
        print()
    
    print("=" * 50)
    print("All models downloaded successfully!")
    print()
    print("Model files:")
    for filename in MODELS.keys():
        filepath = MODELS_DIR / filename
        if filepath.exists():
            size_mb = filepath.stat().st_size / (1024 * 1024)
            print(f"  - {filename} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    download_models()
