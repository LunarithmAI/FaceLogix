"""
ONNX Model Loader with singleton pattern.

Provides lazy-loading of face detection and embedding models with
warmup functionality for production deployments.
"""

from typing import Dict, Optional

import numpy as np
import onnxruntime as ort

from app.core.config import settings


class ModelLoader:
    """
    Singleton model loader for ONNX inference sessions.
    
    Lazily loads models on first access and caches them for subsequent use.
    Provides warmup functionality to pre-load models during application startup.
    
    Attributes:
        _instances: Dictionary cache of loaded ONNX inference sessions
    """
    
    _instances: Dict[str, ort.InferenceSession] = {}
    
    @classmethod
    def get_detector(cls) -> ort.InferenceSession:
        """
        Get the face detector ONNX inference session.
        
        Loads the RetinaFace detector model on first call.
        
        Returns:
            ort.InferenceSession: ONNX inference session for face detection
            
        Raises:
            FileNotFoundError: If detector model file is not found
        """
        key = "detector"
        if key not in cls._instances:
            model_path = settings.MODELS_DIR / settings.DETECTOR_MODEL
            if not model_path.exists():
                raise FileNotFoundError(
                    f"Detector model not found at {model_path}. "
                    "Run download_models.py to download required models."
                )
            cls._instances[key] = ort.InferenceSession(
                str(model_path),
                providers=settings.ONNX_PROVIDERS
            )
        return cls._instances[key]
    
    @classmethod
    def get_embedder(cls) -> ort.InferenceSession:
        """
        Get the face embedder ONNX inference session.
        
        Loads the ArcFace embedder model on first call.
        
        Returns:
            ort.InferenceSession: ONNX inference session for face embedding
            
        Raises:
            FileNotFoundError: If embedder model file is not found
        """
        key = "embedder"
        if key not in cls._instances:
            model_path = settings.MODELS_DIR / settings.EMBEDDER_MODEL
            if not model_path.exists():
                raise FileNotFoundError(
                    f"Embedder model not found at {model_path}. "
                    "Run download_models.py to download required models."
                )
            cls._instances[key] = ort.InferenceSession(
                str(model_path),
                providers=settings.ONNX_PROVIDERS
            )
        return cls._instances[key]
    
    @classmethod
    def warmup(cls) -> None:
        """
        Pre-load all models and run warmup inference.
        
        Should be called during application startup to ensure models
        are loaded and ready for inference. Performs a dummy inference
        to warm up the ONNX runtime.
        """
        # Load detector
        detector = cls.get_detector()
        detector_input = detector.get_inputs()[0]
        detector_shape = detector_input.shape
        # Create dummy input for warmup (handle dynamic dimensions)
        warmup_shape = [
            dim if isinstance(dim, int) else 1 
            for dim in detector_shape
        ]
        # Ensure we have proper shape for detector (batch, channels, height, width)
        if len(warmup_shape) == 4:
            warmup_shape = [1, 3, 640, 640]
        dummy_detector_input = np.zeros(warmup_shape, dtype=np.float32)
        detector.run(None, {detector_input.name: dummy_detector_input})
        
        # Load embedder
        embedder = cls.get_embedder()
        embedder_input = embedder.get_inputs()[0]
        # ArcFace input is (batch, channels, height, width) = (1, 3, 112, 112)
        dummy_embedder_input = np.zeros(
            (1, 3, settings.INPUT_SIZE[1], settings.INPUT_SIZE[0]),
            dtype=np.float32
        )
        embedder.run(None, {embedder_input.name: dummy_embedder_input})
        
        print("Models loaded and warmed up successfully")
    
    @classmethod
    def clear(cls) -> None:
        """
        Clear all cached model instances.
        
        Useful for testing or releasing memory.
        """
        cls._instances.clear()
